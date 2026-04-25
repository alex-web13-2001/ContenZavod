"use client";
import React, { createContext, useContext, useState, useCallback, useRef } from "react";
import { CheckCircle2, AlertCircle, Info, X, Undo2 } from "lucide-react";

/* ────── Types ────── */
type ToastVariant = "success" | "error" | "info";

interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
  undoAction?: () => void;
  exiting?: boolean;
}

interface ToastContextType {
  showToast: (message: string, variant?: ToastVariant, undoAction?: () => void) => void;
}

const ToastContext = createContext<ToastContextType>({ showToast: () => {} });
export const useToast = () => useContext(ToastContext);

/* ────── Icons & colors ────── */
const VARIANT_CONFIG: Record<ToastVariant, { icon: React.ReactNode; bg: string; border: string; color: string }> = {
  success: {
    icon: <CheckCircle2 size={18} />,
    bg: "hsl(var(--cz-success) / 0.12)",
    border: "hsl(var(--cz-success) / 0.3)",
    color: "hsl(var(--cz-success))",
  },
  error: {
    icon: <AlertCircle size={18} />,
    bg: "hsl(var(--cz-error) / 0.12)",
    border: "hsl(var(--cz-error) / 0.3)",
    color: "hsl(var(--cz-error))",
  },
  info: {
    icon: <Info size={18} />,
    bg: "hsl(var(--cz-primary) / 0.12)",
    border: "hsl(var(--cz-primary) / 0.3)",
    color: "hsl(var(--cz-primary))",
  },
};

/* ────── Provider ────── */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counterRef = useRef(0);

  const showToast = useCallback((message: string, variant: ToastVariant = "success", undoAction?: () => void) => {
    const id = `toast-${++counterRef.current}`;
    setToasts((prev) => [...prev, { id, message, variant, undoAction }]);

    // Auto-dismiss after 4s
    setTimeout(() => {
      setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)));
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 350);
    }, 4000);
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)));
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 350);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}

      {/* Toast container */}
      {toasts.length > 0 && (
        <div style={{
          position: "fixed", bottom: 24, right: 24, zIndex: 9999,
          display: "flex", flexDirection: "column-reverse", gap: 8,
          pointerEvents: "none",
        }}>
          {toasts.map((toast) => {
            const cfg = VARIANT_CONFIG[toast.variant];
            return (
              <div key={toast.id} style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "12px 16px", borderRadius: 10, minWidth: 300, maxWidth: 450,
                backgroundColor: cfg.bg, border: `1px solid ${cfg.border}`,
                backdropFilter: "blur(12px)",
                boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
                pointerEvents: "auto",
                animation: toast.exiting ? "cz-toast-out 0.3s ease forwards" : "cz-toast-in 0.3s ease",
              }}>
                <span style={{ color: cfg.color, flexShrink: 0 }}>{cfg.icon}</span>
                <span style={{ fontSize: 14, fontWeight: 600, color: "hsl(var(--cz-text-primary))", flex: 1 }}>
                  {toast.message}
                </span>
                {toast.undoAction && (
                  <button onClick={() => { toast.undoAction?.(); dismiss(toast.id); }} style={{
                    display: "flex", alignItems: "center", gap: 4, padding: "4px 10px",
                    borderRadius: 6, border: "1px solid hsl(var(--cz-border) / 0.5)",
                    cursor: "pointer", fontSize: 12, fontWeight: 700,
                    backgroundColor: "transparent", color: "hsl(var(--cz-text-secondary))",
                    flexShrink: 0,
                  }}>
                    <Undo2 size={12} /> Вернуть
                  </button>
                )}
                <button onClick={() => dismiss(toast.id)} style={{
                  background: "none", border: "none", cursor: "pointer",
                  color: "hsl(var(--cz-text-muted))", padding: 2, flexShrink: 0,
                }}>
                  <X size={14} />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </ToastContext.Provider>
  );
}
