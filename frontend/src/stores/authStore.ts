import { create } from "zustand";
import { api } from "@/lib/api";

interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  tenant_id: string;
  tenant_name: string | null;
  is_active: boolean;
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
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;

    if (!token) {
      set({ initialized: true, user: null });
      return;
    }

    try {
      set({ loading: true });
      const user = await api.get<User>("/auth/me");
      set({ user, loading: false, initialized: true });
    } catch {
      set({ user: null, loading: false, initialized: true });
    }
  },

  login: async (email: string, password: string) => {
    set({ loading: true });
    await api.login(email, password);
    const user = await api.get<User>("/auth/me");
    set({ user, loading: false });
  },

  logout: () => {
    set({ user: null });
    api.logout();
  },
}));
