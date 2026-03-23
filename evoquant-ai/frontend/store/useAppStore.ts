import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  totp_enabled: boolean;
  preferred_broker?: string;
}

interface AppStore {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isPaper: boolean;
  sidebarCollapsed: boolean;
  theme: "dark" | "light";
  setUser: (user: User | null) => void;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
  togglePaper: () => void;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isPaper: true,
      sidebarCollapsed: false,
      theme: "dark",
      setUser: (user) => set({ user }),
      setTokens: (access, refresh) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", access);
          localStorage.setItem("refresh_token", refresh);
        }
        set({ accessToken: access, refreshToken: refresh });
      },
      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        }
        set({ user: null, accessToken: null, refreshToken: null });
      },
      togglePaper: () => set((s) => ({ isPaper: !s.isPaper })),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
    }),
    {
      name: "evoquant-app",
      partialize: (s) => ({
        user: s.user,
        accessToken: s.accessToken,
        refreshToken: s.refreshToken,
        isPaper: s.isPaper,
        sidebarCollapsed: s.sidebarCollapsed,
        theme: s.theme,
      }),
    }
  )
);
