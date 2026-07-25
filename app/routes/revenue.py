from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import RevenueResponse
from app.crud import get_revenue_analytics

router = APIRouter(tags=["Revenue"])

@router.get(
    "/revenue",
    response_model=RevenueResponse,
    summary="Get Revenue over time",
    description="Calculates revenue aggregated by day or week over an optional date range. "
                "By default, includes only completed orders. Set include_refunds=true to net refunded orders."
)
def get_revenue(
    granularity: str = Query("day", description="Aggregation period: 'day' or 'week'"),
    from_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    include_refunds: bool = Query(False, description="Include negative refunded order amounts"),
    db: Session = Depends(get_db)
):
    if granularity not in ("day", "week"):
        raise HTTPException(
            status_code=400,
            detail="Invalid granularity parameter. Must be 'day' or 'week'."
        )

    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail="from_date cannot be greater than to_date."
        )

    return get_revenue_analytics(
        db=db,
        granularity=granularity,
        from_date=from_date,
        to_date=to_date,
        include_refunds=include_refunds
    )
