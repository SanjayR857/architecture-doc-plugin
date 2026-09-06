"""
Order Processing Service
========================
Coordinates inventory checking, total pricing, and order state transitions.
"""

import uuid
from typing import List, Optional
from models.order import Order, OrderItem, OrderStatus
from db.database import DatabaseClient


class OrderService:
    """Core order management business logic."""

    def __init__(self, db: Optional[DatabaseClient] = None):
        self.db = db or DatabaseClient()

    def calculate_total(self, items: List[OrderItem]) -> float:
        """Sum item line prices."""
        return sum(item.quantity * item.unit_price for item in items)

    def place_order(self, user_id: str, items: List[OrderItem], shipping_address: str) -> Order:
        """Validate customer, compute subtotal, and record order."""
        user = self.db.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        if not items:
            raise ValueError("Order must contain at least one item")

        total = self.calculate_total(items)
        order = Order(
            id=str(uuid.uuid4()),
            user_id=user_id,
            items=items,
            total_amount=total,
            shipping_address=shipping_address,
            status=OrderStatus.PENDING,
        )
        self.db.save_order(order)
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        """Fetch order record."""
        return self.db.get_order(order_id)

    def list_user_orders(self, user_id: str) -> List[Order]:
        """List orders for user."""
        return self.db.find_orders_by_user(user_id)

    def cancel_order(self, order_id: str) -> Optional[Order]:
        """Cancel order if still in PENDING state."""
        order = self.db.get_order(order_id)
        if not order or order.status != OrderStatus.PENDING:
            return None
        order.status = OrderStatus.CANCELLED
        self.db.save_order(order)
        return order
