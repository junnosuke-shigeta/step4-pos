from datetime import datetime, timezone
from decimal import Decimal

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import create_access_token, get_staff_from_token, hash_password, verify_password
from .config import settings
from .database import get_db
from .models import Customer, Product, Purchase, PurchaseItem, Staff
from .schemas import (
    ConfirmPurchaseRequest,
    ConfirmPurchaseResponse,
    CustomerLookupResponse,
    ErrorDetail,
    ErrorResponse,
    LoginRequest,
    ProductResponse,
    PurchaseRecordResponse,
    QuoteRequest,
    QuoteResponse,
    ResetPasswordRequest,
    StaffResponse,
)
from .services import calculate_quote, money


def _docs_url() -> str | None:
    return None if settings.app_env.lower() == "production" else "/docs"


app = FastAPI(title=settings.app_name, docs_url=_docs_url(), redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    status_to_code = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR",
    }
    body = ErrorResponse(
        error_code=status_to_code.get(exc.status_code, "ERROR"),
        message=str(exc.detail),
        details=[],
        timestamp=datetime.now(timezone.utc),
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    details = [ErrorDetail(field=".".join(map(str, err["loc"])), issue=err["msg"]) for err in exc.errors()]
    body = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="入力値が不正です",
        details=details,
        timestamp=datetime.now(timezone.utc),
    )
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))


@app.get("/health")
def health():
    return {"status": "ok"}


def get_current_staff_from_cookie(
    pos_access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not pos_access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_staff_from_token(pos_access_token, db)


def require_admin_cookie(staff=Depends(get_current_staff_from_cookie)):
    if staff.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return staff


@app.post("/api/auth/login", response_model=StaffResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    staff = db.get(Staff, payload.staff_id)
    if not staff or not verify_password(payload.password, staff.password_hash):
        raise HTTPException(status_code=401, detail="スタッフIDまたはパスワードが不正です")

    token = create_access_token({"sub": staff.staff_id, "name": staff.name, "role": staff.role})
    response.set_cookie(
        key="pos_access_token",
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=60 * 60 * settings.access_token_expire_hours,
    )
    return StaffResponse(staff_id=staff.staff_id, name=staff.name, role=staff.role)


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie("pos_access_token")
    return {"message": "logged out"}


@app.get("/api/auth/me", response_model=StaffResponse)
def me(staff=Depends(get_current_staff_from_cookie)):
    return StaffResponse(staff_id=staff.staff_id, name=staff.name, role=staff.role)


@app.get("/api/customers/{customer_id}", response_model=CustomerLookupResponse)
def lookup_customer(customer_id: str, db: Session = Depends(get_db), _=Depends(get_current_staff_from_cookie)):
    customer = db.execute(select(Customer).where(Customer.customer_id == customer_id)).scalar_one_or_none()

    if not customer:
        return CustomerLookupResponse(
            customer_id=customer_id,
            found=False,
            name=None,
            message="該当会員なし",
        )

    return CustomerLookupResponse(
        customer_id=customer.customer_id,
        found=True,
        name=customer.name,
        message="会員を確認しました",
    )


@app.get("/api/products/{product_code}", response_model=ProductResponse)
def get_product(product_code: str, db: Session = Depends(get_db), _=Depends(get_current_staff_from_cookie)):
    product = db.get(Product, product_code)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="商品が見つかりません")
    return ProductResponse(product_code=product.product_code, name=product.name, base_price=Decimal(str(product.base_price)))


@app.post("/api/purchase/quote", response_model=QuoteResponse)
def quote(payload: QuoteRequest, db: Session = Depends(get_db), _=Depends(get_current_staff_from_cookie)):
    result = calculate_quote(db, payload.items, payload.customer_id)
    return QuoteResponse(
        customer_found=result.customer_found,
        tax_rate=result.tax_rate,
        subtotal_excl_tax=result.subtotal_excl_tax,
        tax_amount=result.tax_amount,
        total_amount=result.total_amount,
        items=result.items,
    )


@app.post("/api/purchase/confirm", response_model=ConfirmPurchaseResponse)
def confirm_purchase(payload: ConfirmPurchaseRequest, db: Session = Depends(get_db), staff=Depends(get_current_staff_from_cookie)):
    result = calculate_quote(db, payload.items, payload.customer_id)

    if money(payload.client_total_amount) != result.total_amount:
        raise HTTPException(
            status_code=400,
            detail=f"INVALID_AMOUNT_MISMATCH: 正しい金額は{result.total_amount}円ですが、{money(payload.client_total_amount)}円が送信されました",
        )

    purchase = Purchase(
        purchased_at=datetime.now(timezone.utc).replace(tzinfo=None),
        staff_id=staff.staff_id,
        customer_id=payload.customer_id if result.customer_found else None,
        subtotal_excl_tax=result.subtotal_excl_tax,
        tax_amount=result.tax_amount,
        total_amount=result.total_amount,
        tax_rate_applied=result.tax_rate,
    )
    try:
        db.add(purchase)
        db.flush()

        for item in result.items:
            db.add(
                PurchaseItem(
                    purchase_id=purchase.id,
                    product_code=item.product_code,
                    product_name=item.product_name,
                    quantity=item.quantity,
                    base_price=item.base_price,
                    discounted_price=item.discounted_price,
                    final_amount=item.final_amount,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(purchase)
    return ConfirmPurchaseResponse(
        purchase_id=purchase.id,
        purchased_at=purchase.purchased_at,
        total_amount=Decimal(str(purchase.total_amount)),
    )


@app.get("/api/admin/purchases", response_model=list[PurchaseRecordResponse], dependencies=[Depends(require_admin_cookie)])
def list_purchases(db: Session = Depends(get_db)):
    return db.query(Purchase).order_by(Purchase.id.desc()).all()


@app.post("/api/admin/staff/{staff_id}/reset-password", dependencies=[Depends(require_admin_cookie)])
def reset_staff_password(staff_id: str, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    staff = db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    staff.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "password reset"}
