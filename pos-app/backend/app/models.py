from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Staff(Base):
    __tablename__ = "staff"

    staff_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="STAFF")


class Customer(Base):
    __tablename__ = "customer"

    customer_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class Product(Base):
    __tablename__ = "product"

    product_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DiscountPlan(Base):
    __tablename__ = "discount_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_code: Mapped[str] = mapped_column(ForeignKey("product.product_code"), nullable=False)
    customer_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # RATE or AMOUNT
    discount_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TaxRate(Base):
    __tablename__ = "tax_rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rate: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Purchase(Base):
    __tablename__ = "purchase"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    staff_id: Mapped[str] = mapped_column(ForeignKey("staff.staff_id"), nullable=False)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customer.customer_id"), nullable=True)
    subtotal_excl_tax: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tax_rate_applied: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)

    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchase.id"), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discounted_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    final_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    purchase = relationship("Purchase", back_populates="items")
