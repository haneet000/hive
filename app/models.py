from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    signup_date = Column(Date, nullable=False)
    email = Column(String(255), nullable=True)

    orders = relationship("Order", back_populates="customer")

class Order(Base):
    __tablename__ = "orders"

    id = Column(String(50), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    order_date = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # completed, refunded, cancelled
    total_amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="INR")

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    sku = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    qty = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")

class IngestionReject(Base):
    __tablename__ = "ingestion_rejects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=True)
    raw_data = Column(Text, nullable=False)
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
