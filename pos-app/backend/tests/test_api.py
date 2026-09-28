from datetime import datetime
from decimal import Decimal
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Customer, DiscountPlan, Product, Purchase, PurchaseItem, Staff, TaxRate


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    db.add(Staff(staff_id="STAFF001", name="staff", password_hash=hash_password("password"), role="STAFF"))
    db.add(Staff(staff_id="ADMIN001", name="admin", password_hash=hash_password("password"), role="ADMIN"))
    db.add(Customer(customer_id="MEM001", name="member"))
    db.add(Product(product_code="4901234567894", name="water", base_price=Decimal("100.00"), is_active=True))
    db.add(Product(product_code="4901234567895", name="bread", base_price=Decimal("220.00"), is_active=True))
    db.add(TaxRate(rate=Decimal("0.10"), start_date=datetime(2020, 1, 1)))
    db.add(
        DiscountPlan(
            product_code="4901234567894",
            customer_only=True,
            discount_type="RATE",
            discount_value=Decimal("10.00"),
            start_date=datetime(2020, 1, 1),
        )
    )
    db.commit()
    db.close()

    def override_get_db():
        test_db = TestingSessionLocal()
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c, TestingSessionLocal

    app.dependency_overrides.clear()


def login(client):
    res = client.post("/api/auth/login", json={"staff_id": "STAFF001", "password": "password"})
    assert res.status_code == 200


def test_login_success(client):
    client, _ = client
    response = client.post("/api/auth/login", json={"staff_id": "STAFF001", "password": "password"})
    assert response.status_code == 200
    assert response.json()["staff_id"] == "STAFF001"
    assert "pos_access_token" in response.cookies


def test_customer_not_found_is_not_error(client):
    client, _ = client
    login(client)
    response = client.get("/api/customers/UNKNOWN001")
    assert response.status_code == 200
    assert response.json()["found"] is False
    assert response.json()["message"] == "該当会員なし"


def test_quote_reapplies_discount_for_member(client):
    client, _ = client
    login(client)
    payload = {
        "customer_id": "MEM001",
        "items": [{"product_code": "4901234567894", "quantity": 1}],
    }
    response = client.post("/api/purchase/quote", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["customer_found"] is True
    assert body["items"][0]["discounted_price"] == "90.00"
    assert body["total_amount"] == "99.00"


def test_confirm_rejects_amount_tampering(client):
    client, _ = client
    login(client)
    payload = {
        "customer_id": "MEM001",
        "items": [{"product_code": "4901234567894", "quantity": 1}],
        "client_total_amount": "1.00",
    }
    response = client.post("/api/purchase/confirm", json=payload)
    assert response.status_code == 400
    assert "INVALID_AMOUNT_MISMATCH" in response.json()["message"]


def test_quote_total_matches_sum_of_item_snapshots(client):
    client, _ = client
    login(client)
    payload = {
        "customer_id": "MEM001",
        "items": [
            {"product_code": "4901234567894", "quantity": 1},
            {"product_code": "4901234567895", "quantity": 1},
        ],
    }
    response = client.post("/api/purchase/quote", json=payload)
    assert response.status_code == 200
    body = response.json()
    total_from_items = sum(Decimal(item["final_amount"]) for item in body["items"])
    assert total_from_items == Decimal(body["total_amount"])


def test_confirm_persists_purchase_snapshot_successfully(client):
    client, TestingSessionLocal = client
    login(client)

    quote_payload = {
        "customer_id": "MEM001",
        "items": [{"product_code": "4901234567894", "quantity": 2}],
    }
    quote_res = client.post("/api/purchase/quote", json=quote_payload)
    assert quote_res.status_code == 200
    quoted_total = quote_res.json()["total_amount"]

    confirm_res = client.post(
        "/api/purchase/confirm",
        json={**quote_payload, "client_total_amount": quoted_total},
    )
    assert confirm_res.status_code == 200
    purchase_id = confirm_res.json()["purchase_id"]

    db = TestingSessionLocal()
    try:
        purchase = db.get(Purchase, purchase_id)
        assert purchase is not None
        assert str(purchase.total_amount) == "198.00"
        item = db.query(PurchaseItem).filter(PurchaseItem.purchase_id == purchase_id).one()
        assert item.product_code == "4901234567894"
        assert item.quantity == 2
        assert str(item.base_price) == "100.00"
        assert str(item.discounted_price) == "90.00"
        assert str(item.final_amount) == "198.00"
    finally:
        db.close()


def test_confirm_non_member_persists_null_customer(client):
    client, TestingSessionLocal = client
    login(client)

    quote_payload = {
        "customer_id": "UNKNOWN999",
        "items": [{"product_code": "4901234567894", "quantity": 1}],
    }
    quote_res = client.post("/api/purchase/quote", json=quote_payload)
    assert quote_res.status_code == 200
    confirm_res = client.post(
        "/api/purchase/confirm",
        json={**quote_payload, "client_total_amount": quote_res.json()["total_amount"]},
    )
    assert confirm_res.status_code == 200
    purchase_id = confirm_res.json()["purchase_id"]

    db = TestingSessionLocal()
    try:
        purchase = db.get(Purchase, purchase_id)
        assert purchase is not None
        assert purchase.customer_id is None
    finally:
        db.close()


def test_mysql_integration_smoke_when_configured():
    mysql_url = os.getenv("MYSQL_TEST_DATABASE_URL")
    if not mysql_url:
        pytest.skip("MYSQL_TEST_DATABASE_URL is not set")

    engine = create_engine(mysql_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    suffix = uuid4().hex[:8]
    staff_id = f"TST{suffix}"
    product_code = f"99{suffix}"
    customer_id = f"MEM{suffix}"

    db = SessionLocal()
    try:
        db.add(Staff(staff_id=staff_id, name="mysql-staff", password_hash=hash_password("password"), role="STAFF"))
        db.add(Customer(customer_id=customer_id, name="mysql-member"))
        db.add(Product(product_code=product_code, name="mysql-product", base_price=Decimal("100.00"), is_active=True))
        db.add(TaxRate(rate=Decimal("0.10"), start_date=datetime(2020, 1, 1)))
        db.commit()

        stored = db.get(Product, product_code)
        assert stored is not None
        assert str(stored.base_price) == "100.00"
    finally:
        db.close()
