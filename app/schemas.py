from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class OrderItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    sku: str
    name: str
    qty: int
    unit_price: float

class CustomerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    city: str
    signup_date: date
    email: Optional[str] = None

class OrderSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: Optional[str] = None
    order_date: datetime
    status: str
    total_amount: float
    currency: str
    items: List[OrderItemSchema] = []

class CustomerOrdersResponse(BaseModel):
    customer: CustomerSchema
    orders: List[OrderSchema]
    total: int
    page: int
    limit: int

class RevenueDataPoint(BaseModel):
    period: str
    revenue: float
    order_count: int

class RevenueResponse(BaseModel):
    granularity: str
    total_revenue: float
    include_refunds: bool
    data: List[RevenueDataPoint]

class TopCustomerItem(BaseModel):
    customer_id: str
    name: str
    city: str
    email: Optional[str] = None
    total_spend: float
    order_count: int

class TopCustomersResponse(BaseModel):
    by: str
    limit: int
    page: int
    total_customers: int
    data: List[TopCustomerItem]

class RepeatPurchaseRateResponse(BaseModel):
    total_customers_with_orders: int
    repeat_customers_count: int
    repeat_purchase_rate_pct: float

class CityAOVItem(BaseModel):
    city: str
    total_orders: int
    total_revenue: float
    aov: float

class CityAOVResponse(BaseModel):
    data: List[CityAOVItem]

class IngestionRejectSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: Optional[str] = None
    raw_data: str
    reason: str
    created_at: datetime

