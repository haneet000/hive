# Hive Full Stack (Backend) Take-Home Submission

A production-ready e-commerce data pipeline, backend service, analytics API, and frontend dashboard built with **FastAPI**, **SQLAlchemy**, **PostgreSQL**, **Alembic**, **Pytest**, and **React (Vite)**.

---

## ⚡ Quick Start Guide (1-Command Docker Setup)

### Run Entire Application Stack via Docker Compose

Run the entire application stack (PostgreSQL + Automatic Schema Migrations + Feed Data Ingestion + FastAPI Backend + React Frontend Dashboard) with a single command:

```bash
docker-compose up --build
```

That's it! Docker automatically provisions and orchestrates all services:

1. **Database Service (`db`)**: Launches PostgreSQL 15 database container.
2. **Backend & Ingestion Service (`backend`)**: Waits for PostgreSQL, executes `alembic upgrade head`, runs `python -m scripts.ingest`, and launches the FastAPI REST server.
3. **Frontend Dashboard Service (`frontend`)**: Serves the React Vite dashboard.

- **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Backend OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/](http://localhost:8000/)

---

### Alternative: Local Development Setup Without Docker

If you prefer to run services manually on your local host using SQLite:

```bash
# 1. Copy environment configuration
cp .env.example .env

# 2. Create virtual environment & install backend dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run automated test suite (18/18 tests passing)
pytest

# 4. Apply database migrations
alembic upgrade head

# 5. Run data ingestion script
python -m scripts.ingest

# 6. Start backend API (FastAPI)
uvicorn app.main:app --reload --port 8000
```

In a separate terminal tab, start the frontend dashboard:
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Live Runtime Verification & Idempotency Proof

### 1. Automated Test Suite Output
```text
$ pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0
rootdir: /Users/haneet/Hive
plugins: anyio-4.12.1, asyncio-1.3.0
collected 18 items

tests/test_api.py::test_root_endpoint PASSED                             [  5%]
tests/test_api.py::test_revenue_endpoint_completed_only PASSED           [ 11%]
tests/test_api.py::test_revenue_endpoint_with_refunds PASSED             [ 16%]
tests/test_api.py::test_revenue_endpoint_invalid_granularity PASSED      [ 22%]
tests/test_api.py::test_top_customers_by_spend PASSED                    [ 27%]
tests/test_api.py::test_customer_orders_found PASSED                     [ 33%]
tests/test_api.py::test_customer_orders_not_found PASSED                 [ 38%]
tests/test_api.py::test_repeat_purchase_rate PASSED                      [ 44%]
tests/test_api.py::test_aov_by_city PASSED                               [ 50%]
tests/test_api.py::test_ingestion_rejects_endpoint PASSED                [ 55%]
tests/test_api.py::test_revenue_discrepancy_reconciliation PASSED        [ 61%]
tests/test_api.py::test_repeat_purchase_rate_denominator PASSED          [ 66%]
tests/test_dedup.py::test_deduplicate_orders_keeps_latest_date PASSED    [ 72%]
tests/test_normalizer.py::test_parse_iso8601_dates PASSED                [ 77%]
tests/test_normalizer.py::test_parse_dd_mm_yyyy_dates PASSED             [ 83%]
tests/test_normalizer.py::test_parse_unix_epoch_seconds PASSED           [ 88%]
tests/test_normalizer.py::test_parse_invalid_and_garbage_input PASSED    [ 94%]
tests/test_orphans.py::test_orphaned_customer_orders PASSED              [100%]

======================== 18 passed, 2 warnings in 0.58s ========================
```

### 2. Idempotency Strategy & Database Row Count Proof
- **Idempotency Implementation Note**: Idempotency is achieved via a **transactional reset-and-reload** pattern (`db.query().delete()` followed by bulk insertion within a single atomic database transaction). Re-running the script cleans existing feed tables and populates the canonical state, guaranteeing deterministic row counts without row duplication or orphan state leakage.

Running `python -m scripts.ingest` multiple times yields identical results:
```text
$ python3 -m scripts.ingest && python3 -m scripts.ingest
[Ingest] Ingested 120 customers.
[Ingest] Loaded 313 raw order records.
[Ingest] Ingested 285 canonical orders.
[Ingest] Logged 33 rejects/warnings into ingestion_rejects table.
[Ingest] Ingested 120 customers.
[Ingest] Loaded 313 raw order records.
[Ingest] Ingested 285 canonical orders.
[Ingest] Logged 33 rejects/warnings into ingestion_rejects table.
```

**Verified Database Row Counts**:
- `customers`: 120 rows
- `orders`: 285 canonical rows
- `order_items`: 737 items
- `ingestion_rejects`: 33 audit log rows (28 superseded duplicates + 5 orphaned customer references)

---

## 🔍 Data Quality Audit Findings & Engineering Rationale

The raw dataset (`data/customers.csv` and `data/orders.json`) was treated as an un-sanitized third-party feed. All data quality anomalies were explicitly identified, resolved, and documented:

### 1. Duplicate `order_id`s (28 Duplicates across 313 Raw Orders)
- **Observation**: 28 orders shared an `order_id` with another record in `orders.json`. 16 pairs contained conflicting values (different timestamps and amounts), indicating re-submissions a few minutes apart.
- **Decision & Rationale**: Retained the order record with the **latest `order_date`** as canonical. In third-party webhook feeds, re-transmitted order IDs separated by minutes represent customer updates or checkout retries; the latest timestamp reflects the final state of the order.
- **Audit Logging**: Superseded duplicate records are recorded in `ingestion_rejects` with reason `DUPLICATE_ORDER_ID_SUPERSEDED`.
- **Result**: Exactly **285 canonical orders** loaded into the database.

### 2. Mixed `order_date` Formats (3 Formats)
- **Observation**: Raw JSON contained ISO 8601 strings (e.g. `"2026-06-03T20:11:00Z"`), `DD/MM/YYYY` strings (e.g. `"31/10/2025"`), and Unix epoch seconds integers/floats (e.g. `1781382480`).
- **Decision & Policy**: Implemented a centralized normalizer in [app/normalizers.py](app/normalizers.py) (`parse_date()`) that detects, parses, and converts all three formats into timezone-aware UTC `datetime` objects.
- **Quarantine Policy**: Any date string failing parsing is logged to `ingestion_rejects` under reason `UNPARSEABLE_DATE` rather than crashing the ingestion run. (0 unparseable dates in dataset).

### 3. Orphaned Customer References (5 Orders) & Financial Reconciliation
- **Observation**: 5 orders referenced customer IDs (`CUST-9000`, `CUST-9001`, `CUST-9006`, `CUST-9007`, `CUST-9008`) not present in `customers.csv`.
- **Decision & Policy**: Orphaned orders are **NOT dropped from the database**. They are inserted into the `orders` table with `customer_id = NULL` (nullable FK), and simultaneously logged to `ingestion_rejects` under reason `ORPHANED_CUSTOMER_ID`.
- **Reconciliation of the ₹5,741 Gap**: System-wide Gross Revenue (`GET /revenue`) totals **₹6,73,717.00** across all 255 completed orders. Summing the City AOV breakdown (`GET /stats/aov-by-city`) gives **₹6,67,976.00** across 250 orders. The exact difference of **₹5,741.00** equals the sum of the 5 orphaned completed orders (`ORD-00281`, `ORD-00282`, `ORD-00283`, `ORD-00284`, `ORD-00285`). They are correctly included in overall system revenue but excluded from city grouping as they lack customer city metadata.

### 4. Status Values & Financial Revenue Accounting
- **Observation**: Orders feature three statuses: `completed`, `refunded` (negative total_amount), and `cancelled` (positive total_amount, but order never fulfilled).
- **Revenue Policy**:
  - `GET /revenue` default view accounts for **`completed` orders only** (Gross Revenue = ₹6,73,717.00).
  - Setting `include_refunds=true` nets negative `refunded` orders against completed orders (Net Revenue = ₹6,43,001.00).
  - `cancelled` orders are **always excluded** from revenue metrics as no financial transaction occurred.

### 5. Customer Table Singularities & Cohort Denominator (108 vs 120)
- **Observation**: 16 duplicate `name` values belong to distinct individuals in different cities/dates — preserved as distinct customer rows. 4 rows had empty/missing `email` values — stored as `NULL`. 3 emails were duplicated — email column left without `UNIQUE` constraint to reflect real feed conditions.
- **Repeat Purchase Cohort (108 Denominator)**: Out of 120 registered customers in `customers.csv`, 108 customers have placed at least 1 `completed` order (11 customers signed up but never ordered; 1 customer placed only non-completed orders). Standard e-commerce repeat purchase rate is calculated over the purchasing cohort of active buyers: 73 repeat buyers / 108 purchasing customers = **67.59%**.

### 6. Item Pricing Arithmetic
- **Observation**: Non-refunded orders satisfy `sum(qty * unit_price) == total_amount`. Refunded orders satisfy `-1 * sum(qty * unit_price) == total_amount`. Item pricing arithmetic validated cleanly across all 313 raw records.

---

## 🗄️ Database Schema Design

```
+-------------------+       +-------------------+       +-------------------+
|     customers     |       |      orders       |       |    order_items    |
+-------------------+       +-------------------+       +-------------------+
| id (PK, String)   |<------| customer_id (FK*) |       | id (PK, Int)      |
| name (String)     |       | id (PK, String)   |<------| order_id (FK)     |
| city (String)     |       | order_date (UTC)  |       | sku (String)      |
| signup_date (Date)|       | status (String)   |       | name (String)     |
| email (Nullable)  |       | total_amount(Float|       | qty (Int)         |
+-------------------+       | currency (String) |       | unit_price(Float) |
                            +-------------------+       +-------------------+
                                                          
                            +-------------------+
                            | ingestion_rejects |
                            +-------------------+
                            | id (PK, Int)      |
                            | entity_type       |
                            | entity_id         |
                            | raw_data          |
                            | reason            |
                            | created_at (UTC)  |
                            +-------------------+
```

---

## 🔌 API Endpoint Documentation

| Method | Endpoint | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/revenue` | `granularity=day\|week`, `from_date`, `to_date`, `include_refunds=false` | Calculates gross/net revenue over time aggregated by day or week. |
| `GET` | `/customers/top` | `by=spend\|orders`, `limit=10`, `page=1` | Returns top customers sorted by total spend or order count with pagination (max limit=100). |
| `GET` | `/customers/{id}/orders` | `page=1`, `limit=10` | Returns customer details & order history with `joinedload`. Returns `404` if ID not found. |
| `GET` | `/stats/repeat-purchase-rate` | — | % of active purchasing customers with >1 completed order. |
| `GET` | `/stats/aov-by-city` | — | Average Order Value (AOV) grouped by customer city. |
| `GET` | `/ingestion/rejects` | `page=1`, `limit=20` | Audit trail of ingestion validation and quarantine logs. |

---

## 🧪 Testing

The pytest suite in [tests/](tests/) covers:
1. **Date Normalizer** ([tests/test_normalizer.py](tests/test_normalizer.py)): ISO 8601, `DD/MM/YYYY`, Unix epoch, invalid strings, `None`, unsupported types.
2. **Deduplication Logic** ([tests/test_dedup.py](tests/test_dedup.py)): Confirms latest `order_date` is selected and superseded record logged to rejects.
3. **Orphan Handling** ([tests/test_orphans.py](tests/test_orphans.py)): Verifies `customer_id` is set to `NULL` and logged as `ORPHANED_CUSTOMER_ID`.
4. **FastAPI Endpoints** ([tests/test_api.py](tests/test_api.py)): Response schema shapes, 200/400/404 HTTP status codes using SQLite in-memory `TestClient`.
5. **Financial Discrepancy & Denominator Reconciliation**: Explicit unit tests confirming revenue gap reconciliation and repeat purchase denominator math.

Run tests via:
```bash
pytest -v
```

---

## 💡 Out of Scope & Production Recommendations

- **Out of Scope**: Authentication/authorization, cloud deployment config, visual design polish.
- **Currency & Precision Recommendation**: Amounts are stored as IEEE 754 floats and rounded to 2 decimal places (`round(val, 2)`). In enterprise financial services, storing values as integer paise (e.g. `204700`) or SQL `DECIMAL(12,2)` / Python `Decimal` is recommended to prevent floating point representation errors.
