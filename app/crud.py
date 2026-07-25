from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, case
from app.models import Customer, Order, OrderItem, IngestionReject
from app.schemas import (
    RevenueResponse, RevenueDataPoint,
    TopCustomersResponse, TopCustomerItem,
    CustomerOrdersResponse, CustomerSchema, OrderSchema,
    RepeatPurchaseRateResponse,
    CityAOVResponse, CityAOVItem,
    IngestionRejectSchema
)

def get_revenue_analytics(
    db: Session,
    granularity: str = "day",
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    include_refunds: bool = False
) -> RevenueResponse:
    query = db.query(Order)

    if include_refunds:
        query = query.filter(Order.status.in_(["completed", "refunded"]))
    else:
        query = query.filter(Order.status == "completed")

    if from_date:
        query = query.filter(Order.order_date >= from_date)
    if to_date:
        query = query.filter(Order.order_date <= to_date)

    orders = query.order_by(Order.order_date.asc()).all()

    # Group by period in Python to ensure portable behavior across SQLite and Postgres
    grouped: Dict[str, Dict[str, Any]] = {}
    total_rev = 0.0

    for ord in orders:
        if granularity == "week":
            # Format as Year-Week (e.g., 2026-W22)
            period_str = ord.order_date.strftime("%Y-W%U")
        else:
            # Default to day (YYYY-MM-DD)
            period_str = ord.order_date.strftime("%Y-%m-%d")

        if period_str not in grouped:
            grouped[period_str] = {"revenue": 0.0, "count": 0}

        grouped[period_str]["revenue"] += ord.total_amount
        grouped[period_str]["count"] += 1
        total_rev += ord.total_amount

    data_points = [
        RevenueDataPoint(
            period=period,
            revenue=round(info["revenue"], 2),
            order_count=info["count"]
        )
        for period, info in grouped.items()
    ]

    return RevenueResponse(
        granularity=granularity,
        total_revenue=round(total_rev, 2),
        include_refunds=include_refunds,
        data=data_points
    )

def get_top_customers(
    db: Session,
    by: str = "spend",
    limit: int = 10,
    page: int = 1
) -> TopCustomersResponse:
    query = (
        db.query(
            Customer.id.label("customer_id"),
            Customer.name,
            Customer.city,
            Customer.email,
            func.coalesce(func.sum(Order.total_amount), 0.0).label("total_spend"),
            func.count(Order.id).label("order_count")
        )
        .join(Order, Customer.id == Order.customer_id)
        .filter(Order.status == "completed")
        .group_by(Customer.id, Customer.name, Customer.city, Customer.email)
    )

    if by == "orders":
        query = query.order_by(desc("order_count"), desc("total_spend"))
    else:
        query = query.order_by(desc("total_spend"), desc("order_count"))

    # Get total count of customers with completed orders
    total_customers = query.count()

    offset = (page - 1) * limit
    results = query.offset(offset).limit(limit).all()

    top_items = [
        TopCustomerItem(
            customer_id=r.customer_id,
            name=r.name,
            city=r.city,
            email=r.email,
            total_spend=round(float(r.total_spend), 2),
            order_count=int(r.order_count)
        )
        for r in results
    ]

    return TopCustomersResponse(
        by=by,
        limit=limit,
        page=page,
        total_customers=total_customers,
        data=top_items
    )

def get_customer_orders(
    db: Session,
    customer_id: str,
    page: int = 1,
    limit: int = 10
) -> Optional[CustomerOrdersResponse]:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return None

    orders_query = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.customer_id == customer_id)
        .order_by(Order.order_date.desc())
    )

    total_orders = orders_query.count()
    offset = (page - 1) * limit
    orders = orders_query.offset(offset).limit(limit).all()

    return CustomerOrdersResponse(
        customer=CustomerSchema.model_validate(customer),
        orders=[OrderSchema.model_validate(o) for o in orders],
        total=total_orders,
        page=page,
        limit=limit
    )

def get_repeat_purchase_rate(db: Session) -> RepeatPurchaseRateResponse:
    # Subquery: completed order count per customer
    subq = (
        db.query(
            Order.customer_id,
            func.count(Order.id).label("completed_count")
        )
        .filter(Order.customer_id.isnot(None))
        .filter(Order.status == "completed")
        .group_by(Order.customer_id)
        .subquery()
    )

    total_custs = db.query(func.count(subq.c.customer_id)).scalar() or 0
    repeat_custs = (
        db.query(func.count(subq.c.customer_id))
        .filter(subq.c.completed_count > 1)
        .scalar() or 0
    )

    pct = round((repeat_custs / total_custs * 100.0), 2) if total_custs > 0 else 0.0

    return RepeatPurchaseRateResponse(
        total_customers_with_orders=total_custs,
        repeat_customers_count=repeat_custs,
        repeat_purchase_rate_pct=pct
    )

def get_aov_by_city(db: Session) -> CityAOVResponse:
    results = (
        db.query(
            Customer.city,
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total_amount).label("total_revenue")
        )
        .join(Order, Customer.id == Order.customer_id)
        .filter(Order.status == "completed")
        .group_by(Customer.city)
        .order_by(desc("total_revenue"))
        .all()
    )

    items = []
    for r in results:
        tot_orders = int(r.total_orders)
        tot_rev = float(r.total_revenue or 0.0)
        aov = round(tot_rev / tot_orders, 2) if tot_orders > 0 else 0.0
        items.append(CityAOVItem(
            city=r.city,
            total_orders=tot_orders,
            total_revenue=round(tot_rev, 2),
            aov=aov
        ))

    return CityAOVResponse(data=items)

def get_ingestion_rejects(
    db: Session,
    page: int = 1,
    limit: int = 20
) -> List[IngestionRejectSchema]:
    offset = (page - 1) * limit
    rejects = (
        db.query(IngestionReject)
        .order_by(IngestionReject.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [IngestionRejectSchema.model_validate(r) for r in rejects]
