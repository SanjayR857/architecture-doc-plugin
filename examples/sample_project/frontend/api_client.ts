/**
 * API Client Layer
 * Communicates with ShopFlow FastAPI backend using path aliases.
 */

import type { User, AuthResponse, Order, CreateOrderPayload } from "@/types";

export class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = "http://localhost:8000/api/v1") {
    this.baseUrl = baseUrl;
  }

  setToken(token: string): void {
    this.token = token;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await fetch(`${this.baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error("Authentication failed");
    const data = await res.json();
    this.setToken(data.access_token);
    return data;
  }

  async getProfile(): Promise<User> {
    const res = await fetch(`${this.baseUrl}/auth/me?token=${this.token}`);
    if (!res.ok) throw new Error("Failed to fetch user profile");
    return res.json();
  }

  async createOrder(payload: CreateOrderPayload): Promise<Order> {
    const res = await fetch(`${this.baseUrl}/orders/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.token}`,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Order placement failed");
    return res.json();
  }
}
