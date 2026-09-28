from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated

Barcode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50)]


class ErrorDetail(BaseModel):
    field: str
    issue: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: list[ErrorDetail] = []
    timestamp: datetime


class LoginRequest(BaseModel):
    staff_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class StaffResponse(BaseModel):
    staff_id: str
    name: str
    role: str


class CustomerLookupResponse(BaseModel):
    customer_id: str
    found: bool
    name: str | None = None
    message: str


class ProductResponse(BaseModel):
    product_code: str
    name: str
    base_price: Decimal


class CartItemInput(BaseModel):
    product_code: Barcode
    quantity: int = Field(ge=1, le=999)


class QuoteRequest(BaseModel):
    customer_id: str | None = Field(default=None, max_length=50)
    items: list[CartItemInput] = Field(min_length=1)


class QuoteItem(BaseModel):
    product_code: str
    product_name: str
    quantity: int
    base_price: Decimal
    discounted_price: Decimal
    final_amount: Decimal


class QuoteResponse(BaseModel):
    customer_found: bool
    tax_rate: Decimal
    subtotal_excl_tax: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    items: list[QuoteItem]


class ConfirmPurchaseRequest(QuoteRequest):
    client_total_amount: Decimal = Field(ge=0)


class ConfirmPurchaseResponse(BaseModel):
    purchase_id: int
    purchased_at: datetime
    total_amount: Decimal


class ResetPasswordRequest(BaseModel):
    new_password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class PurchaseRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchased_at: datetime
    staff_id: str
    customer_id: str | None
    total_amount: Decimal
