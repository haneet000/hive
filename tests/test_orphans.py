import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Order, IngestionReject
from scripts.ingest import ingest_data

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_orphans.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

def test_orphaned_customer_orders(temp_db, tmp_path):
    session = temp_db

    cust_file = tmp_path / "customers.csv"
    cust_file.write_text("customer_id,name,city,signup_date,email\nCUST-0001,Known User,Delhi,2025-01-01,known@example.com\n")

    orders_data = [
        {
            "order_id": "ORD-ORPHAN1",
            "customer_id": "CUST-9000",  # Orphaned ID not in customers.csv
            "order_date": "2026-03-01T12:00:00Z",
            "items": [{"sku": "SKU-99", "name": "Item Orphan", "qty": 1, "unit_price": 500}],
            "total_amount": 500,
            "currency": "INR",
            "status": "completed"
        }
    ]

    orders_file = tmp_path / "orders.json"
    orders_file.write_text(json.dumps(orders_data))

    ingest_data(str(cust_file), str(orders_file), db=session)

    # Order is stored in database with customer_id=None
    order = session.query(Order).filter(Order.id == "ORD-ORPHAN1").first()
    assert order is not None
    assert order.customer_id is None

    # Verify orphan rejection record is logged
    rejects = session.query(IngestionReject).filter(IngestionReject.entity_id == "ORD-ORPHAN1").all()
    assert len(rejects) == 1
    assert "ORPHANED_CUSTOMER_ID" in rejects[0].reason
    assert "CUST-9000" in rejects[0].reason
