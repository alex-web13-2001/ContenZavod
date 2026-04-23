const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010/api/v1";

/** Custom event for auth failures — layout listens and does router.push */
function emitAuthFailure() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("cz_token");
    window.dispatchEvent(new CustomEvent("cz:auth-failure"));
  }
}

class ApiClient {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("cz_token");
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    const token = this.getToken();
    if (token) h["Authorization"] = `Bearer ${token}`;
    return h;
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, {
      method,
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
    });

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
      throw new Error(message);
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
