from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import TopCustomersResponse, CustomerOrdersResponse
from app.crud import get_top_customers, get_customer_orders

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.get(
    "/top",
    response_model=TopCustomersResponse,
    summary="Get Top Customers",
    description="Returns top customers sorted by total spend or order count, with pagination."
)
def get_top(
    by: str = Query("spend", description="Sorting criteria: 'spend' or 'orders'"),
    limit: int = Query(10, ge=1, le=100, description="Page size"),
    page: int = Query(1, ge=1, description="Page number"),
    db: Session = Depends(get_db)
):
    if by not in ("spend", "orders"):
        raise HTTPException(
            status_code=400,
            detail="Invalid 'by' parameter. Must be 'spend' or 'orders'."
        )

    return get_top_customers(db=db, by=by, limit=limit, page=page)

@router.get(
    "/{customer_id}/orders",
    response_model=CustomerOrdersResponse,
    summary="Get Customer Order History",
    description="Returns an individual customer's details and order history. Returns 404 if customer not found."
)
def get_orders(
    customer_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
):
    res = get_customer_orders(db=db, customer_id=customer_id, page=page, limit=limit)
    if not res:
        raise HTTPException(
            status_code=404,
            detail=f"Customer with ID '{customer_id}' was not found."
        )
    return res
