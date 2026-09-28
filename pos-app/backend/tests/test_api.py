from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Customer, DiscountPlan, Product, Staff, TaxRate


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
        yield c

    app.dependency_overrides.clear()


def login(client):
    res = client.post("/api/auth/login", json={"staff_id": "STAFF001", "password": "password"})
    assert res.status_code == 200


def test_login_success(client):
    response = client.post("/api/auth/login", json={"staff_id": "STAFF001", "password": "password"})
    assert response.status_code == 200
    assert response.json()["staff_id"] == "STAFF001"
    assert "pos_access_token" in response.cookies


def test_customer_not_found_is_not_error(client):
    login(client)
    response = client.get("/api/customers/UNKNOWN001")
    assert response.status_code == 200
    assert response.json()["found"] is False
    assert response.json()["message"] == "該当会員なし"


def test_quote_reapplies_discount_for_member(client):
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
    login(client)
    payload = {
        "customer_id": "MEM001",
        "items": [{"product_code": "4901234567894", "quantity": 1}],
        "client_total_amount": "1.00",
    }
    response = client.post("/api/purchase/confirm", json=payload)
    assert response.status_code == 400
    assert "INVALID_AMOUNT_MISMATCH" in response.json()["message"]
