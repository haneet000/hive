import pytest
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Customer, Order, OrderItem, IngestionReject

# Set up SQLite in-memory engine with StaticPool so all connections reuse the same DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Clear existing test data
    db.query(OrderItem).delete()
    db.query(Order).delete()
    db.query(Customer).delete()
    db.query(IngestionReject).delete()
    db.commit()

    # Seed test data: 4 distinct customer personas
    c1 = Customer(id="CUST-0001", name="Alice", city="Mumbai", signup_date=date(2025, 1, 1), email="alice@test.com")
    c2 = Customer(id="CUST-0002", name="Bob", city="Delhi", signup_date=date(2025, 2, 1), email="bob@test.com")
    c3 = Customer(id="CUST-0003", name="Charlie", city="Bengaluru", signup_date=date(2025, 3, 1), email="charlie@test.com")
    c4 = Customer(id="CUST-0004", name="David", city="Pune", signup_date=date(2025, 4, 1), email="david@test.com") # 0 orders
    db.add_all([c1, c2, c3, c4])

    # Orders setup
    # Alice: 2 completed orders (1000 + 500 = 1500) -> Repeat Buyer
    o1 = Order(
        id="ORD-001",
        customer_id="CUST-0001",
        order_date=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        status="completed",
        total_amount=1000.0,
        currency="INR"
    )
    o2 = Order(
        id="ORD-002",
        customer_id="CUST-0001",
        order_date=datetime(2026, 1, 20, 14, 0, 0, tzinfo=timezone.utc),
        status="completed",
        total_amount=500.0,
        currency="INR"
    )

    # Bob: 1 refunded, 1 cancelled order -> 0 completed orders
    o3 = Order(
        id="ORD-003",
        customer_id="CUST-0002",
        order_date=datetime(2026, 1, 22, 9, 0, 0, tzinfo=timezone.utc),
        status="refunded",
        total_amount=-300.0,
        currency="INR"
    )
    o4 = Order(
        id="ORD-004",
        customer_id="CUST-0002",
        order_date=datetime(2026, 1, 25, 11, 0, 0, tzinfo=timezone.utc),
        status="cancelled",
        total_amount=800.0,
        currency="INR"
    )

    # Charlie: 1 completed order (300.0) -> Single Buyer
    o6 = Order(
        id="ORD-006",
        customer_id="CUST-0003",
        order_date=datetime(2026, 1, 28, 16, 0, 0, tzinfo=timezone.utc),
        status="completed",
        total_amount=300.0,
        currency="INR"
    )

    # Orphaned Order: customer_id = None, status = completed (250.0) -> Preserved in DB
    o5 = Order(
        id="ORD-005",
        customer_id=None,
        order_date=datetime(2026, 1, 26, 12, 0, 0, tzinfo=timezone.utc),
        status="completed",
        total_amount=250.0,
        currency="INR"
    )

    db.add_all([o1, o2, o3, o4, o5, o6])

    i1 = OrderItem(order_id="ORD-001", sku="SKU-1", name="Widget 1", qty=2, unit_price=500.0)
    i2 = OrderItem(order_id="ORD-002", sku="SKU-2", name="Widget 2", qty=1, unit_price=500.0)
    db.add_all([i1, i2])

    r1 = IngestionReject(
        entity_type="order",
        entity_id="ORD-DUP",
        raw_data="{}",
        reason="DUPLICATE_ORDER_ID_SUPERSEDED",
        created_at=datetime.now(timezone.utc)
    )
    r2 = IngestionReject(
        entity_type="order",
        entity_id="ORD-005",
        raw_data="{}",
        reason="ORPHANED_CUSTOMER_ID: referenced unknown customer CUST-9000",
        created_at=datetime.now(timezone.utc)
    )
    db.add_all([r1, r2])

    db.commit()
    db.close()

    yield

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_revenue_endpoint_completed_only():
    response = client.get("/revenue?granularity=day")
    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "day"
    assert data["include_refunds"] is False
    # Completed orders: o1 (1000) + o2 (500) + o5 orphan (250) + o6 (300) = 2050.0
    assert data["total_revenue"] == 2050.0

def test_revenue_endpoint_with_refunds():
    response = client.get("/revenue?granularity=day&include_refunds=true")
    assert response.status_code == 200
    data = response.json()
    assert data["include_refunds"] is True
    # Net revenue: 2050 - 300 (refunded) = 1750.0
    assert data["total_revenue"] == 1750.0

def test_revenue_endpoint_invalid_granularity():
    response = client.get("/revenue?granularity=month")
    assert response.status_code == 400
    assert "Invalid granularity" in response.json()["detail"]

def test_top_customers_by_spend():
    response = client.get("/customers/top?by=spend&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["by"] == "spend"
    # Alice (1500) > Charlie (300)
    assert len(data["data"]) == 2
    assert data["data"][0]["customer_id"] == "CUST-0001"
    assert data["data"][0]["total_spend"] == 1500.0
    assert data["data"][1]["customer_id"] == "CUST-0003"
    assert data["data"][1]["total_spend"] == 300.0

def test_customer_orders_found():
    response = client.get("/customers/CUST-0001/orders")
    assert response.status_code == 200
    data = response.json()
    assert data["customer"]["id"] == "CUST-0001"
    assert data["total"] == 2
    assert len(data["orders"]) == 2
    assert len(data["orders"][0]["items"]) > 0

def test_customer_orders_not_found():
    response = client.get("/customers/CUST-NONEXISTENT/orders")
    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]

def test_repeat_purchase_rate():
    response = client.get("/stats/repeat-purchase-rate")
    assert response.status_code == 200
    data = response.json()
    # 2 customers with completed orders (Alice: 2, Charlie: 1)
    # 1 customer with >1 completed order (Alice)
    # Rate = 1 / 2 = 50.0%
    assert data["total_customers_with_orders"] == 2
    assert data["repeat_customers_count"] == 1
    assert data["repeat_purchase_rate_pct"] == 50.0

def test_aov_by_city():
    response = client.get("/stats/aov-by-city")
    assert response.status_code == 200
    data = response.json()
    # Cities with completed orders: Mumbai (1500 / 2 orders = 750 AOV), Bengaluru (300 / 1 order = 300 AOV)
    assert len(data["data"]) == 2
    assert data["data"][0]["city"] == "Mumbai"
    assert data["data"][0]["total_revenue"] == 1500.0
    assert data["data"][0]["aov"] == 750.0
    assert data["data"][1]["city"] == "Bengaluru"
    assert data["data"][1]["total_revenue"] == 300.0
    assert data["data"][1]["aov"] == 300.0

def test_ingestion_rejects_endpoint():
    response = client.get("/ingestion/rejects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

def test_revenue_discrepancy_reconciliation():
    """
    Verifies that system-wide Gross Revenue (/revenue) exceeds City Revenue (/stats/aov-by-city)
    by exactly the sum of completed orphaned orders (customer_id = NULL).
    """
    rev_resp = client.get("/revenue?granularity=day").json()
    city_resp = client.get("/stats/aov-by-city").json()

    gross_rev = rev_resp["total_revenue"] # 2050.0 (includes 250.0 orphan)
    city_rev_sum = sum(item["total_revenue"] for item in city_resp["data"]) # 1800.0 (1500 Mumbai + 300 Bengaluru)
    gap = round(gross_rev - city_rev_sum, 2)

    # Gap must equal 250.0 (the orphaned completed order total_amount)
    assert gap == 250.0

def test_repeat_purchase_rate_denominator():
    """
    Verifies that total_customers_with_orders denominator counts only active purchasing buyers
    (customers with >=1 completed order = 2: Alice, Charlie) out of total registered customers (4).
    """
    response = client.get("/stats/repeat-purchase-rate")
    assert response.status_code == 200
    data = response.json()
    
    # Denominator must be 2 (Alice and Charlie), NOT 4 (which includes Bob and David)
    assert data["total_customers_with_orders"] == 2
    assert data["repeat_customers_count"] == 1
    assert data["repeat_purchase_rate_pct"] == 50.0
