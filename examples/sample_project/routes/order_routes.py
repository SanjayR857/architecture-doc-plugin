"""
Order Processing Routes
=======================
Endpoints for submitting, retrieving, and cancelling customer orders.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from models.order import CreateOrderRequest, OrderResponse, OrderStatus
from services.order_service import OrderService

router = APIRouter()
order_service = OrderService()


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(payload: CreateOrderRequest):
    """Place a new customer order and allocate inventory."""
    try:
        order = order_service.place_order(
            user_id=payload.user_id,
            items=payload.items,
            shipping_address=payload.shipping_address,
        )
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    """Fetch order details by unique order ID."""
    order = order_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/user/{user_id}", response_model=List[OrderResponse])
async def list_user_orders(user_id: str):
    """List all historical orders for a given customer."""
    return order_service.list_user_orders(user_id)


@router.delete("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(order_id: str):
    """Cancel a pending order and release held inventory."""
    order = order_service.cancel_order(order_id)
    if not order:
        raise HTTPException(status_code=400, detail="Cannot cancel finalized or missing order")
    return order
