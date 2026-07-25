import os
import json
import csv
import argparse
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import SessionLocal, engine, Base
from app.models import Customer, Order, OrderItem, IngestionReject
from app.normalizers import parse_date

def ingest_data(customers_path: str, orders_path: str, db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    try:
        # Clear existing data for idempotent re-runs
        db.query(OrderItem).delete()
        db.query(Order).delete()
        db.query(Customer).delete()
        db.query(IngestionReject).delete()
        db.commit()

        # 1. Ingest Customers
        valid_customer_ids = set()
        customers_to_insert = []

        if os.path.exists(customers_path):
            with open(customers_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cust_id = row["customer_id"].strip()
                    name = row["name"].strip()
                    city = row["city"].strip()
                    signup_date_str = row["signup_date"].strip()
                    email_raw = row.get("email", "").strip()
                    email = email_raw if email_raw else None

                    try:
                        signup_dt = parse_date(signup_date_str).date()
                    except Exception as e:
                        db.add(IngestionReject(
                            entity_type="customer",
                            entity_id=cust_id,
                            raw_data=json.dumps(row),
                            reason=f"INVALID_SIGNUP_DATE: {e}"
                        ))
                        continue

                    valid_customer_ids.add(cust_id)
                    customers_to_insert.append(Customer(
                        id=cust_id,
                        name=name,
                        city=city,
                        signup_date=signup_dt,
                        email=email
                    ))

            db.bulk_save_objects(customers_to_insert)
            db.commit()
            print(f"[Ingest] Ingested {len(customers_to_insert)} customers.")
        else:
            print(f"[Ingest Warning] File not found: {customers_path}")

        # 2. Ingest Orders
        if os.path.exists(orders_path):
            with open(orders_path, mode="r", encoding="utf-8") as f:
                raw_orders = json.load(f)

            print(f"[Ingest] Loaded {len(raw_orders)} raw order records.")

            # Group by order_id for deduplication
            orders_by_id = {}
            for record in raw_orders:
                oid = record.get("order_id")
                if not oid:
                    db.add(IngestionReject(
                        entity_type="order",
                        entity_id=None,
                        raw_data=json.dumps(record),
                        reason="MISSING_ORDER_ID"
                    ))
                    continue

                if oid not in orders_by_id:
                    orders_by_id[oid] = []
                orders_by_id[oid].append(record)

            total_ingested_orders = 0
            total_rejects = 0

            for oid, records in orders_by_id.items():
                parsed_records = []

                for rec in records:
                    raw_date = rec.get("order_date")
                    try:
                        dt = parse_date(raw_date)
                        parsed_records.append((dt, rec))
                    except Exception as e:
                        total_rejects += 1
                        db.add(IngestionReject(
                            entity_type="order",
                            entity_id=oid,
                            raw_data=json.dumps(rec),
                            reason=f"UNPARSEABLE_DATE: {raw_date} - {e}"
                        ))

                if not parsed_records:
                    continue

                # Deduplicate rule: Sort by order_date ascending, keep the latest
                parsed_records.sort(key=lambda x: x[0])
                canonical_dt, canonical_rec = parsed_records[-1]

                # Record superseded duplicates in rejects table
                if len(parsed_records) > 1:
                    for dup_dt, dup_rec in parsed_records[:-1]:
                        total_rejects += 1
                        db.add(IngestionReject(
                            entity_type="order",
                            entity_id=oid,
                            raw_data=json.dumps(dup_rec),
                            reason=f"DUPLICATE_ORDER_ID_SUPERSEDED: kept latest date {canonical_dt.isoformat()}"
                        ))

                # Handle orphan customer check
                cust_id = canonical_rec.get("customer_id")
                final_cust_id = cust_id
                if cust_id and cust_id not in valid_customer_ids:
                    total_rejects += 1
                    db.add(IngestionReject(
                        entity_type="order",
                        entity_id=oid,
                        raw_data=json.dumps(canonical_rec),
                        reason=f"ORPHANED_CUSTOMER_ID: referenced unknown customer {cust_id}"
                    ))
                    # Set customer_id to None to satisfy DB integrity while preserving order
                    final_cust_id = None

                # Create Order model instance
                order_obj = Order(
                    id=oid,
                    customer_id=final_cust_id,
                    order_date=canonical_dt,
                    status=canonical_rec.get("status", "completed"),
                    total_amount=float(canonical_rec.get("total_amount", 0.0)),
                    currency=canonical_rec.get("currency", "INR")
                )
                db.add(order_obj)

                # Create OrderItem instances
                items = canonical_rec.get("items", [])
                for item in items:
                    item_obj = OrderItem(
                        order_id=oid,
                        sku=item.get("sku", ""),
                        name=item.get("name", ""),
                        qty=int(item.get("qty", 1)),
                        unit_price=float(item.get("unit_price", 0.0))
                    )
                    db.add(item_obj)

                total_ingested_orders += 1

            db.commit()
            print(f"[Ingest] Ingested {total_ingested_orders} canonical orders.")
            print(f"[Ingest] Logged {total_rejects} rejects/warnings into ingestion_rejects table.")

        else:
            print(f"[Ingest Warning] File not found: {orders_path}")

    finally:
        if close_db:
            db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest e-commerce data into DB")
    parser.add_argument("--customers", default="data/customers.csv", help="Path to customers CSV")
    parser.add_argument("--orders", default="data/orders.json", help="Path to orders JSON")
    args = parser.parse_args()

    ingest_data(args.customers, args.orders)
