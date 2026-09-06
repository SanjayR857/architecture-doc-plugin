"""
User Domain Models
==================
Schemas and DTOs for customer identity and profiles.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """Database representation of customer."""
    id: str
    email: str
    password_hash: str
    full_name: str
    is_active: bool = True


class UserRegisterRequest(BaseModel):
    """Payload for account registration."""
    email: EmailStr
    password: str
    full_name: str


class UserLoginRequest(BaseModel):
    """Payload for authentication."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public customer profile DTO."""
    id: str
    email: str
    full_name: str
    is_active: bool


class TokenResponse(BaseModel):
    """JWT bearer token response."""
    access_token: str
    token_type: str = "bearer"
