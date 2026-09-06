"""
Authentication Routes
=====================
Endpoints for user registration, token generation, and profile management.
"""

from fastapi import APIRouter, HTTPException, Depends
from models.user import UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse
from services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: UserRegisterRequest):
    """Register a new customer account."""
    user = auth_service.register_user(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    if not user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest):
    """Authenticate customer credentials and return a bearer JWT."""
    token = auth_service.authenticate(payload.email, payload.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str):
    """Retrieve profile of the currently authenticated customer."""
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user
