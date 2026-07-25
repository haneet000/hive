from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import RepeatPurchaseRateResponse, CityAOVResponse
from app.crud import get_repeat_purchase_rate, get_aov_by_city

router = APIRouter(prefix="/stats", tags=["Statistics"])

@router.get(
    "/repeat-purchase-rate",
    response_model=RepeatPurchaseRateResponse,
    summary="Get Repeat Purchase Rate",
    description="Percentage of customers with more than 1 completed order."
)
def repeat_purchase_rate(db: Session = Depends(get_db)):
    return get_repeat_purchase_rate(db=db)

@router.get(
    "/aov-by-city",
    response_model=CityAOVResponse,
    summary="Get Average Order Value by City",
    description="Calculates total completed orders, total revenue, and Average Order Value (AOV) grouped by customer city."
)
def aov_by_city(db: Session = Depends(get_db)):
    return get_aov_by_city(db=db)
