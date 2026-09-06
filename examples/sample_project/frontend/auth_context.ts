/**
 * Authentication Context & State Management
 * Coordinates active session state with ApiClient.
 */

import { ApiClient } from "@/api_client";
import type { User } from "@/types";

export class AuthContext {
  private client: ApiClient;
  private currentUser: User | null = null;

  constructor(client?: ApiClient) {
    this.client = client || new ApiClient();
  }

  async signIn(email: string, pass: string): Promise<User> {
    await this.client.login(email, pass);
    this.currentUser = await this.client.getProfile();
    return this.currentUser;
  }

  getUser(): User | null {
    return this.currentUser;
  }

  isAuthenticated(): boolean {
    return this.currentUser !== null;
  }
}
