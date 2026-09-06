"""
Authentication Service
======================
Handles user verification, password hashing, and token issuance.
"""

import hashlib
import uuid
from typing import Optional
from models.user import User
from db.database import DatabaseClient


class AuthService:
    """Core authentication business logic."""

    def __init__(self, db: Optional[DatabaseClient] = None):
        self.db = db or DatabaseClient()

    def _hash_password(self, password: str) -> str:
        """Produce salted SHA-256 hash."""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, email: str, password: str, full_name: str) -> Optional[User]:
        """Register user if email is unique."""
        existing = self.db.find_user_by_email(email)
        if existing:
            return None

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=self._hash_password(password),
            full_name=full_name,
        )
        self.db.save_user(user)
        return user

    def authenticate(self, email: str, password: str) -> Optional[str]:
        """Verify password and return pseudo-JWT session token."""
        user = self.db.find_user_by_email(email)
        if not user or user.password_hash != self._hash_password(password):
            return None
        token = f"jwt_{user.id}_{uuid.uuid4().hex[:12]}"
        self.db.save_session(token, user.id)
        return token

    def get_user_by_token(self, token: str) -> Optional[User]:
        """Retrieve user profile mapped to active session token."""
        user_id = self.db.get_session_user_id(token)
        if not user_id:
            return None
        return self.db.get_user(user_id)
