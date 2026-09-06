/**
 * Frontend TypeScript Domain Interfaces
 * Mirrors backend Pydantic models for type-safe API communication.
 */

export interface User {
  id: string;
  email: string;
  fullName: string;
  isActive: boolean;
}

export interface AuthResponse {
  accessToken: string;
  tokenType: string;
}

export type OrderStatus = "PENDING" | "CONFIRMED" | "SHIPPED" | "DELIVERED" | "CANCELLED";

export interface OrderItem {
  productId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
}

export interface Order {
  id: string;
  userId: string;
  items: OrderItem[];
  totalAmount: number;
  shippingAddress: string;
  status: OrderStatus;
}

export interface CreateOrderPayload {
  userId: string;
  items: OrderItem[];
  shippingAddress: string;
}
