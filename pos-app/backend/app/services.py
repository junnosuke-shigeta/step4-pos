from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from .models import Customer, DiscountPlan, Product, TaxRate
from .schemas import CartItemInput, QuoteItem

MONEY_Q = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_Q, rounding=ROUND_HALF_UP)


@dataclass
class QuoteResult:
    customer_found: bool
    tax_rate: Decimal
    subtotal_excl_tax: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    items: list[QuoteItem]


_tax_cache: dict[str, datetime | Decimal | None] = {"expires_at": None, "rate": None}


def get_customer_status(db: Session, customer_id: str | None) -> tuple[bool, Customer | None]:
    if not customer_id:
        return False, None
    customer = db.get(Customer, customer_id)
    return customer is not None, customer


def get_effective_tax_rate(db: Session, now: datetime) -> Decimal:
    expires_at = _tax_cache["expires_at"]
    rate = _tax_cache["rate"]
    if isinstance(expires_at, datetime) and isinstance(rate, Decimal) and expires_at > now:
        return rate

    stmt = (
        select(TaxRate)
        .where(and_(TaxRate.start_date <= now, or_(TaxRate.end_date.is_(None), TaxRate.end_date >= now)))
        .order_by(TaxRate.start_date.desc())
        .limit(1)
    )
    row = db.execute(stmt).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=500, detail="Tax rate is not configured")

    next_boundary_stmt = (
        select(TaxRate.start_date)
        .where(TaxRate.start_date > now)
        .order_by(TaxRate.start_date.asc())
        .limit(1)
    )
    next_start = db.execute(next_boundary_stmt).scalar_one_or_none()
    ttl_expiry = now + timedelta(hours=1)
    boundaries = [ttl_expiry]
    if next_start:
        boundaries.append(next_start)
    if row.end_date:
        boundaries.append(row.end_date)
    expiry = min(boundaries)

    resolved_rate = Decimal(str(row.rate))
    _tax_cache["expires_at"] = expiry
    _tax_cache["rate"] = resolved_rate
    return resolved_rate


def get_discounted_unit_price(
    db: Session,
    product: Product,
    customer_found: bool,
    now: datetime,
) -> Decimal:
    stmt = (
        select(DiscountPlan)
        .where(
            and_(
                DiscountPlan.product_code == product.product_code,
                DiscountPlan.is_active.is_(True),
                DiscountPlan.start_date <= now,
                or_(DiscountPlan.end_date.is_(None), DiscountPlan.end_date >= now),
            )
        )
        .order_by(DiscountPlan.id.asc())
    )
    plans = db.execute(stmt).scalars().all()

    base = Decimal(str(product.base_price))
    best = base
    for plan in plans:
        if plan.customer_only and not customer_found:
            continue
        if plan.discount_type == "RATE":
            discounted = base * (Decimal("1") - Decimal(str(plan.discount_value)) / Decimal("100"))
        else:
            discounted = base - Decimal(str(plan.discount_value))
        if discounted < 0:
            discounted = Decimal("0")
        discounted = money(discounted)
        if discounted < best:
            best = discounted
    return best


def calculate_quote(db: Session, items: list[CartItemInput], customer_id: str | None) -> QuoteResult:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    customer_found, _ = get_customer_status(db, customer_id)
    tax_rate = get_effective_tax_rate(db, now)

    quote_items: list[QuoteItem] = []
    subtotal = Decimal("0")
    for item in items:
        product = db.get(Product, item.product_code)
        if not product or not product.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product not found: {item.product_code}")

        base = Decimal(str(product.base_price))
        discounted = get_discounted_unit_price(db, product, customer_found, now)
        line_base = discounted * item.quantity
        line_tax = line_base * tax_rate
        final_amount = money(line_base + line_tax)

        subtotal += line_base
        quote_items.append(
            QuoteItem(
                product_code=product.product_code,
                product_name=product.name,
                quantity=item.quantity,
                base_price=money(base),
                discounted_price=money(discounted),
                final_amount=final_amount,
            )
        )

    subtotal = money(subtotal)
    tax_amount = money(subtotal * tax_rate)
    total = money(subtotal + tax_amount)

    return QuoteResult(
        customer_found=customer_found,
        tax_rate=tax_rate,
        subtotal_excl_tax=subtotal,
        tax_amount=tax_amount,
        total_amount=total,
        items=quote_items,
    )
