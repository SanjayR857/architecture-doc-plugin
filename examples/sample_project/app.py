"""
Sample E-Commerce API Entry Point
==================================
FastAPI application entry point tying together routes, database, and middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.auth_routes import router as auth_router
from routes.order_routes import router as order_router
from db.database import init_db

app = FastAPI(
    title="ShopFlow API",
    description="Sample e-commerce microservice demonstrating clean architecture.",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Sub-Routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(order_router, prefix="/api/v1/orders", tags=["Orders"])


@app.on_event("startup")
async def on_startup():
    """Initialize database tables on application start."""
    init_db()


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify service liveness."""
    return {"status": "healthy", "service": "shopflow-api", "version": "1.0.0"}
