"""
Order Domain Models
===================
Schemas and status lifecycle definitions for customer orders.
"""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Lifecycle state of an order."""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderItem(BaseModel):
    """Line item in a customer order."""
    product_id: str
    product_name: str
    quantity: int = Field(gt=0, description="Must be positive")
    unit_price: float = Field(gt=0, description="Price per unit in USD")


class CreateOrderRequest(BaseModel):
    """Payload to submit a new order."""
    user_id: str
    items: List[OrderItem]
    shipping_address: str


class Order(BaseModel):
    """Database representation of an order."""
    id: str
    user_id: str
    items: List[OrderItem]
    total_amount: float
    shipping_address: str
    status: OrderStatus = OrderStatus.PENDING


class OrderResponse(BaseModel):
    """Public representation of an order."""
    id: str
    user_id: str
    items: List[OrderItem]
    total_amount: float
    shipping_address: str
    status: OrderStatus
