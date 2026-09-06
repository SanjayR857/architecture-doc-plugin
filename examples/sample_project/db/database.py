"""
Database Access Layer
=====================
In-memory persistence layer simulating database operations for users and orders.
"""

from typing import Dict, List, Optional
from models.user import User
from models.order import Order


class DatabaseClient:
    """Simulated database connection and repository."""

    _users_by_id: Dict[str, User] = {}
    _users_by_email: Dict[str, User] = {}
    _sessions: Dict[str, str] = {}  # token -> user_id
    _orders_by_id: Dict[str, Order] = {}

    def save_user(self, user: User) -> None:
        """Store user by id and email."""
        self._users_by_id[user.id] = user
        self._users_by_email[user.email] = user

    def get_user(self, user_id: str) -> Optional[User]:
        """Fetch user by id."""
        return self._users_by_id.get(user_id)

    def find_user_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email."""
        return self._users_by_email.get(email)

    def save_session(self, token: str, user_id: str) -> None:
        """Store session token."""
        self._sessions[token] = user_id

    def get_session_user_id(self, token: str) -> Optional[str]:
        """Retrieve user id mapped to token."""
        return self._sessions.get(token)

    def save_order(self, order: Order) -> None:
        """Persist or update order record."""
        self._orders_by_id[order.id] = order

    def get_order(self, order_id: str) -> Optional[Order]:
        """Fetch order by id."""
        return self._orders_by_id.get(order_id)

    def find_orders_by_user(self, user_id: str) -> List[Order]:
        """Find all orders belonging to a given user id."""
        return [o for o in self._orders_by_id.values() if o.user_id == user_id]


def init_db():
    """Seed initial demo data."""
    client = DatabaseClient()
    demo_user = User(
        id="usr_demo_101",
        email="developer@example.com",
        password_hash="demo_hash_abc123",
        full_name="Demo Developer",
    )
    client.save_user(demo_user)
