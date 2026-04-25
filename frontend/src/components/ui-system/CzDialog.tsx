"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

interface CzDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  maxWidth?: string;
}

export function CzDialog({ open, onClose, title, children, maxWidth = "480px" }: CzDialogProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Portal needs to wait for client mount
  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    if (open) {
      setVisible(true);
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
      const t = setTimeout(() => setVisible(false), 200);
      return () => clearTimeout(t);
    }
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  if (!visible || !mounted) return null;

  const dialog = (
    <div
      ref={overlayRef}
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
        backgroundColor: "hsl(0 0% 0% / 0.6)",
        backdropFilter: "blur(4px)",
        opacity: open ? 1 : 0,
        transition: `opacity var(--cz-duration-fast) var(--cz-ease)`,
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth,
          maxHeight: "90vh",
          overflowY: "auto",
          backgroundColor: `hsl(var(--cz-bg-surface))`,
          border: `1px solid hsl(var(--cz-border))`,
          borderRadius: "var(--cz-radius-xl)",
          boxShadow: "var(--cz-shadow-lg)",
          transform: open ? "scale(1) translateY(0)" : "scale(0.95) translateY(8px)",
          opacity: open ? 1 : 0,
          transition: `all var(--cz-duration-base) var(--cz-ease)`,
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "20px 24px 0",
          }}
        >
          <h2
            style={{
              fontSize: "17px",
              fontWeight: 600,
              color: `hsl(var(--cz-text-primary))`,
            }}
          >
            {title}
          </h2>
          <button
            onClick={onClose}
            className="focus-ring"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "32px",
              height: "32px",
              borderRadius: "var(--cz-radius-sm)",
              border: "none",
              background: "transparent",
              color: `hsl(var(--cz-text-muted))`,
              cursor: "pointer",
              transition: `all var(--cz-duration-fast) var(--cz-ease)`,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = `hsl(var(--cz-bg-hover))`;
              e.currentTarget.style.color = `hsl(var(--cz-text-primary))`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "transparent";
              e.currentTarget.style.color = `hsl(var(--cz-text-muted))`;
            }}
          >
            <X size={18} />
          </button>
        </div>
        {/* Body */}
        <div style={{ padding: "20px 24px 24px" }}>{children}</div>
      </div>
    </div>
  );

  return createPortal(dialog, document.body);
}

