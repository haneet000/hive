import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Order, IngestionReject
from scripts.ingest import ingest_data

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_dedup.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session, engine
    session.close()

def test_deduplicate_orders_keeps_latest_date(temp_db, tmp_path):
    session, engine = temp_db

    # Create dummy customers CSV
    cust_file = tmp_path / "customers.csv"
    cust_file.write_text("customer_id,name,city,signup_date,email\nCUST-0001,Test User,Delhi,2025-01-01,test@example.com\n")

    # Create dummy orders JSON with duplicate order_id ORD-9999
    orders_data = [
        {
            "order_id": "ORD-9999",
            "customer_id": "CUST-0001",
            "order_date": "2026-01-01T10:00:00Z",
            "items": [{"sku": "SKU1", "name": "Item 1", "qty": 1, "unit_price": 100}],
            "total_amount": 100,
            "currency": "INR",
            "status": "completed"
        },
        {
            "order_id": "ORD-9999",
            "customer_id": "CUST-0001",
            "order_date": "2026-01-01T10:15:00Z",  # Latest timestamp
            "items": [{"sku": "SKU1", "name": "Item 1 Updated", "qty": 2, "unit_price": 100}],
            "total_amount": 200,
            "currency": "INR",
            "status": "completed"
        }
    ]

    orders_file = tmp_path / "orders.json"
    orders_file.write_text(json.dumps(orders_data))

    # Run ingestion
    ingest_data(str(cust_file), str(orders_file), db=session)

    # Verify only 1 canonical order exists in DB
    db_orders = session.query(Order).filter(Order.id == "ORD-9999").all()
    assert len(db_orders) == 1
    assert db_orders[0].total_amount == 200.0
    assert db_orders[0].order_date.isoformat().startswith("2026-01-01T10:15:00")

    # Verify rejected superseded record is in ingestion_rejects
    rejects = session.query(IngestionReject).filter(IngestionReject.entity_id == "ORD-9999").all()
    assert len(rejects) == 1
    assert "DUPLICATE_ORDER_ID_SUPERSEDED" in rejects[0].reason
