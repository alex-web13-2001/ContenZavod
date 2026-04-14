import { create } from "zustand";
import { api } from "@/lib/api";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  tenant_id: string;
  tenant_name: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  init: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,

  init: async () => {
    const token = localStorage.getItem("cz_token");
    if (!token) {
      set({ initialized: true, loading: false });
      return;
    }

    set({ loading: true });
    try {
      const user = await api.get<User>("/auth/me");
      set({ user, initialized: true, loading: false });
    } catch {
      localStorage.removeItem("cz_token");
      set({ user: null, initialized: true, loading: false });
    }
  },

  login: async (email, password) => {
    // Login returns tokens, then we fetch user
    const tokens = await api.post<{ access_token: string }>("/auth/login", { email, password });
    localStorage.setItem("cz_token", tokens.access_token);
    // Now fetch user with the new token
    const user = await api.get<User>("/auth/me");
    set({ user, initialized: true });
  },

  logout: () => {
    localStorage.removeItem("cz_token");
    set({ user: null });
    window.location.href = "/login";
  },
}));
