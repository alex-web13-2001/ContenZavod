"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import Link from "next/link";
import {
  LayoutDashboard,
  Radio,
  FileText,
  Send,
  FolderOpen,
  LogOut,
  Loader2,
  ChevronLeft,
  Menu,
} from "lucide-react";
import { ToastProvider } from "@/components/ui-system";

const navItems = [
  { href: "/", label: "Дашборд", icon: LayoutDashboard },
  { href: "/projects", label: "Проекты", icon: FolderOpen },
  { href: "/sources", label: "Источники", icon: Radio },
  { href: "/materials", label: "Материалы", icon: FileText },
  { href: "/channels", label: "Каналы", icon: Send },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading, initialized, init, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Init auth
  useEffect(() => {
    if (!initialized) init();
  }, [initialized, init]);

  // Redirect on logout / unauthorized
  useEffect(() => {
    if (initialized && !user && !loading) router.push("/login");
  }, [initialized, user, loading, router]);

  // Listen for API 401 events → smooth redirect
  useEffect(() => {
    const handler = () => {
      useAuthStore.getState().logout();
      router.push("/login");
    };
    window.addEventListener("cz:auth-failure", handler);
    return () => window.removeEventListener("cz:auth-failure", handler);
  }, [router]);

  // Close mobile menu on route change
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  // Mobile detection
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const handler = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
      if (e.matches) setSidebarOpen(false);
    };
    setIsMobile(mq.matches);
    if (mq.matches) setSidebarOpen(false);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  if (!initialized || loading) {
    return (
      <div className="cz-flex-center" style={{ minHeight: "100dvh" }}>
        <Loader2 size={32} className="cz-text-primary" style={{ animation: "spin 1s linear infinite" }} />
      </div>
    );
  }

  if (!user) return null;

  const initials = user.full_name
    ? user.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : user.email[0].toUpperCase();

  const sidebarWidth = sidebarOpen ? "var(--cz-sidebar-width)" : "var(--cz-sidebar-collapsed)";

  return (
    <ToastProvider>
    <div className="cz-flex" style={{ minHeight: "100dvh" }}>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="cz-overlay animate-fade-in" onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar */}
      <aside
        className={`cz-sidebar ${isMobile ? "cz-sidebar--desktop-only" : ""} ${mobileOpen ? "cz-sidebar--mobile-open" : ""}`}
        style={isMobile ? undefined : { width: sidebarWidth, minWidth: sidebarWidth }}
      >
        {/* Logo */}
        <div style={{ padding: sidebarOpen ? "24px 20px 16px" : "24px 16px 16px" }}>
          <Link href="/" className="cz-flex cz-items-center cz-gap-12" style={{ textDecoration: "none" }}>
            <div className="cz-flex-center cz-flex-shrink-0" style={{
              width: 36, height: 36, borderRadius: "var(--cz-radius-md)",
              background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
              color: "white", fontSize: 14, fontWeight: 700,
            }}>
              CZ
            </div>
            {sidebarOpen && (
              <div style={{ overflow: "hidden" }}>
                <div className="cz-text-lg cz-font-semibold cz-text-primary" style={{ whiteSpace: "nowrap" }}>
                  ContenZavod
                </div>
                <div className="cz-text-xs cz-text-muted cz-truncate" style={{ maxWidth: 160 }}>
                  {user.tenant_name || "Проект"}
                </div>
              </div>
            )}
          </Link>
        </div>

        {/* Collapse toggle */}
        {!isMobile && (
          <button className="cz-sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <ChevronLeft size={14} style={{
              transform: sidebarOpen ? "rotate(0)" : "rotate(180deg)",
              transition: `transform var(--cz-duration-fast) var(--cz-ease)`,
            }} />
          </button>
        )}

        {/* Navigation */}
        <nav className="cz-flex-col cz-gap-2" style={{ flex: 1, padding: "8px 12px" }}>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`cz-nav-link ${isActive ? "cz-nav-link--active" : ""} ${!sidebarOpen && !isMobile ? "cz-nav-link--collapsed" : ""}`}
              >
                <item.icon size={18} className="cz-flex-shrink-0" />
                {(sidebarOpen || isMobile) && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div className="cz-user-section">
          <div className="cz-flex cz-items-center cz-gap-10" style={{ padding: 8 }}>
            <div className="cz-icon-box cz-icon-box--sm cz-text-sm cz-font-semibold">
              {initials}
            </div>
            {(sidebarOpen || isMobile) && (
              <>
                <div className="cz-flex-1" style={{ minWidth: 0 }}>
                  <div className="cz-text-base cz-font-medium cz-truncate">
                    {user.full_name || user.email}
                  </div>
                  <div className="cz-text-xs cz-text-muted">{user.role}</div>
                </div>
                <button className="cz-logout-btn" onClick={logout}>
                  <LogOut size={16} />
                </button>
              </>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, minWidth: 0, overflow: "auto" }}>
        {/* Mobile header */}
        <div className="cz-mobile-header">
          <button
            className="cz-flex-center"
            style={{ width: 36, height: 36, border: "none", background: "transparent", cursor: "pointer" }}
            onClick={() => setMobileOpen(true)}
          >
            <Menu size={20} className="cz-text-primary" />
          </button>
          <span className="cz-text-lg cz-font-semibold cz-text-primary">
            {navItems.find((n) => n.href === pathname)?.label || "ContenZavod"}
          </span>
        </div>

        <div className="animate-page-in" style={{ padding: "clamp(16px, 3vw, 40px)" }}>
          {children}
        </div>
      </main>
    </div>
    </ToastProvider>
  );
}
