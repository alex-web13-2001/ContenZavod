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

  useEffect(() => {
    if (!initialized) init();
  }, [initialized, init]);

  useEffect(() => {
    if (initialized && !user && !loading) router.push("/login");
  }, [initialized, user, loading, router]);

  // Close mobile menu on route change
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  // Check mobile
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const handler = (e: MediaQueryListEvent) => { if (e.matches) setSidebarOpen(false); };
    if (mq.matches) setSidebarOpen(false);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  if (!initialized || loading) {
    return (
      <div style={{
        minHeight: "100dvh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: `hsl(var(--cz-bg-root))`,
      }}>
        <Loader2 size={32} style={{ color: `hsl(var(--cz-primary))`, animation: "spin 1s linear infinite" }} />
      </div>
    );
  }

  if (!user) return null;

  const initials = user.full_name
    ? user.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : user.email[0].toUpperCase();

  const sidebarWidth = sidebarOpen ? "var(--cz-sidebar-width)" : "var(--cz-sidebar-collapsed)";

  return (
    <div style={{ display: "flex", minHeight: "100dvh", backgroundColor: `hsl(var(--cz-bg-root))` }}>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 40,
            backgroundColor: "hsl(0 0% 0% / 0.5)",
            backdropFilter: "blur(4px)",
          }}
          className="animate-fade-in"
        />
      )}

      {/* Sidebar */}
      <aside
        style={{
          width: sidebarWidth,
          minWidth: sidebarWidth,
          display: "flex",
          flexDirection: "column",
          borderRight: `1px solid hsl(var(--cz-border-subtle))`,
          backgroundColor: `hsl(var(--cz-bg-surface) / 0.6)`,
          backdropFilter: "blur(12px)",
          transition: `all var(--cz-duration-base) var(--cz-ease)`,
          position: "relative",
          zIndex: 41,
          ...(typeof window !== "undefined" && window.innerWidth < 769 ? {
            position: "fixed" as const,
            top: 0,
            bottom: 0,
            left: 0,
            transform: mobileOpen ? "translateX(0)" : "translateX(-100%)",
            width: "var(--cz-sidebar-width)",
          } : {}),
        }}
      >
        {/* Logo area */}
        <div style={{ padding: sidebarOpen ? "24px 20px 16px" : "24px 16px 16px" }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--cz-radius-md)",
                background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontSize: "14px",
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              CZ
            </div>
            {sidebarOpen && (
              <div style={{ overflow: "hidden" }}>
                <div style={{ fontSize: "14px", fontWeight: 600, color: `hsl(var(--cz-text-primary))`, whiteSpace: "nowrap" }}>
                  ContenZavod
                </div>
                <div style={{ fontSize: "11px", color: `hsl(var(--cz-text-muted))`, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "160px" }}>
                  {user.tenant_name || "Проект"}
                </div>
              </div>
            )}
          </Link>
        </div>

        {/* Collapse toggle (desktop) */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          style={{
            position: "absolute",
            right: "-12px",
            top: "36px",
            width: "24px",
            height: "24px",
            borderRadius: "50%",
            border: `1px solid hsl(var(--cz-border))`,
            backgroundColor: `hsl(var(--cz-bg-elevated))`,
            color: `hsl(var(--cz-text-muted))`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            zIndex: 10,
            transition: `all var(--cz-duration-fast) var(--cz-ease)`,
          }}
          className="hidden md:flex"
        >
          <ChevronLeft size={14} style={{ transform: sidebarOpen ? "rotate(0)" : "rotate(180deg)", transition: `transform var(--cz-duration-fast) var(--cz-ease)` }} />
        </button>

        {/* Nav */}
        <nav style={{ flex: 1, padding: "8px 12px", display: "flex", flexDirection: "column", gap: "2px" }}>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: sidebarOpen ? "10px 14px" : "10px 14px",
                  borderRadius: "var(--cz-radius-md)",
                  fontSize: "13px",
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? `hsl(var(--cz-primary))` : `hsl(var(--cz-text-secondary))`,
                  backgroundColor: isActive ? `hsl(var(--cz-primary) / 0.08)` : "transparent",
                  textDecoration: "none",
                  transition: `all var(--cz-duration-fast) var(--cz-ease)`,
                  justifyContent: sidebarOpen ? "flex-start" : "center",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = `hsl(var(--cz-bg-hover))`;
                    e.currentTarget.style.color = `hsl(var(--cz-text-primary))`;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = "transparent";
                    e.currentTarget.style.color = `hsl(var(--cz-text-secondary))`;
                  }
                }}
              >
                <item.icon size={18} style={{ flexShrink: 0 }} />
                {sidebarOpen && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div style={{ padding: "12px", borderTop: `1px solid hsl(var(--cz-border-subtle))` }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "8px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "var(--cz-radius-sm)",
                backgroundColor: `hsl(var(--cz-bg-overlay))`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "12px",
                fontWeight: 600,
                color: `hsl(var(--cz-text-secondary))`,
                flexShrink: 0,
              }}
            >
              {initials}
            </div>
            {sidebarOpen && (
              <>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "13px", fontWeight: 500, color: `hsl(var(--cz-text-primary))`, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {user.full_name || user.email}
                  </div>
                  <div style={{ fontSize: "11px", color: `hsl(var(--cz-text-muted))` }}>{user.role}</div>
                </div>
                <button
                  onClick={logout}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "32px",
                    height: "32px",
                    border: "none",
                    background: "transparent",
                    borderRadius: "var(--cz-radius-sm)",
                    color: `hsl(var(--cz-text-muted))`,
                    cursor: "pointer",
                    transition: `all var(--cz-duration-fast) var(--cz-ease)`,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = `hsl(var(--cz-error))`;
                    e.currentTarget.style.backgroundColor = `hsl(var(--cz-error) / 0.08)`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = `hsl(var(--cz-text-muted))`;
                    e.currentTarget.style.backgroundColor = "transparent";
                  }}
                >
                  <LogOut size={16} />
                </button>
              </>
            )}
          </div>
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex: 1, minWidth: 0, overflow: "auto" }}>
        {/* Mobile header */}
        <div
          className="md:hidden"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            padding: "12px 16px",
            borderBottom: `1px solid hsl(var(--cz-border-subtle))`,
            backgroundColor: `hsl(var(--cz-bg-surface) / 0.6)`,
            backdropFilter: "blur(12px)",
            position: "sticky",
            top: 0,
            zIndex: 30,
          }}
        >
          <button
            onClick={() => setMobileOpen(true)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "36px",
              height: "36px",
              border: "none",
              background: "transparent",
              color: `hsl(var(--cz-text-primary))`,
              cursor: "pointer",
            }}
          >
            <Menu size={20} />
          </button>
          <span style={{ fontSize: "15px", fontWeight: 600, color: `hsl(var(--cz-text-primary))` }}>
            {navItems.find((n) => n.href === pathname)?.label || "ContenZavod"}
          </span>
        </div>

        <div className="animate-page-in" style={{ padding: "clamp(16px, 3vw, 40px)" }}>
          {children}
        </div>
      </main>
    </div>
  );
}
