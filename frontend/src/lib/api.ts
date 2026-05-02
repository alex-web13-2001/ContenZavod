const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010/api/v1";

/** Custom event for auth failures — layout listens and does router.push */
function emitAuthFailure() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("cz_token");
    localStorage.removeItem("cz_refresh_token");
    window.dispatchEvent(new CustomEvent("cz:auth-failure"));
  }
}

class ApiClient {
  private refreshPromise: Promise<boolean> | null = null;

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("cz_token");
  }

  private getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("cz_refresh_token");
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    const token = this.getToken();
    if (token) h["Authorization"] = `Bearer ${token}`;
    return h;
  }

  /** Try to get new tokens using the refresh token. Returns true on success. */
  private async tryRefresh(): Promise<boolean> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) return false;

      const tokens = await res.json();
      localStorage.setItem("cz_token", tokens.access_token);
      localStorage.setItem("cz_refresh_token", tokens.refresh_token);
      return true;
    } catch {
      return false;
    }
  }

  /** Deduplicated refresh — only one refresh request at a time. */
  private async refresh(): Promise<boolean> {
    if (!this.refreshPromise) {
      this.refreshPromise = this.tryRefresh().finally(() => {
        this.refreshPromise = null;
      });
    }
    return this.refreshPromise;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    let res = await fetch(`${API_URL}${path}`, {
      method,
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
    });

    // On 401 — try to refresh the token and retry once
    if (res.status === 401 && this.getRefreshToken()) {
      const refreshed = await this.refresh();
      if (refreshed) {
        res = await fetch(`${API_URL}${path}`, {
          method,
          headers: this.headers(),
          body: body ? JSON.stringify(body) : undefined,
        });
      }
    }

    if (res.status === 401) {
      emitAuthFailure();
      throw new Error("Не авторизован");
    }

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      // FastAPI 422 returns detail as array of validation errors
      let message = `Ошибка ${res.status}`;
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = data.detail.map((e: { msg?: string }) => e.msg || "").filter(Boolean).join("; ");
      }
      const error = new Error(message) as Error & { status: number };
      error.status = res.status;
      throw error;
    }

    if (res.status === 204) return undefined as T;
    return res.json();
  }

  get<T>(path: string) { return this.request<T>("GET", path); }
  post<T>(path: string, body?: unknown) { return this.request<T>("POST", path, body); }
  patch<T>(path: string, body?: unknown) { return this.request<T>("PATCH", path, body); }
  put<T>(path: string, body?: unknown) { return this.request<T>("PUT", path, body); }
  delete<T>(path: string) { return this.request<T>("DELETE", path); }
}

export const api = new ApiClient();
