"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface CzButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  fullWidth?: boolean;
}

const variantStyles: Record<Variant, React.CSSProperties> = {
  primary: {
    background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
    color: "white",
    border: "none",
    boxShadow: "0 2px 12px hsl(var(--cz-primary) / 0.3)",
  },
  secondary: {
    background: `hsl(var(--cz-bg-elevated))`,
    color: `hsl(var(--cz-text-primary))`,
    border: `1px solid hsl(var(--cz-border))`,
  },
  ghost: {
    background: "transparent",
    color: `hsl(var(--cz-text-secondary))`,
    border: "1px solid transparent",
  },
  danger: {
    background: `hsl(var(--cz-error) / 0.1)`,
    color: `hsl(var(--cz-error))`,
    border: `1px solid hsl(var(--cz-error) / 0.2)`,
  },
};

const sizeStyles: Record<Size, React.CSSProperties> = {
  sm: { height: "32px", padding: "0 12px", fontSize: "12px", gap: "6px" },
  md: { height: "40px", padding: "0 18px", fontSize: "13px", gap: "8px" },
  lg: { height: "48px", padding: "0 24px", fontSize: "14px", gap: "10px" },
};

export const CzButton = forwardRef<HTMLButtonElement, CzButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading,
      icon,
      iconRight,
      fullWidth,
      disabled,
      children,
      style,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className="focus-ring"
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "var(--cz-radius-md)",
          fontWeight: 600,
          fontFamily: "var(--cz-font-sans)",
          cursor: disabled || loading ? "not-allowed" : "pointer",
          opacity: disabled ? 0.5 : 1,
          transition: `all var(--cz-duration-fast) var(--cz-ease)`,
          width: fullWidth ? "100%" : "auto",
          whiteSpace: "nowrap",
          letterSpacing: "0.01em",
          ...variantStyles[variant],
          ...sizeStyles[size],
          ...style,
        }}
        onMouseEnter={(e) => {
          if (!disabled && !loading) {
            e.currentTarget.style.transform = "translateY(-1px)";
            e.currentTarget.style.filter = "brightness(1.1)";
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = "translateY(0)";
          e.currentTarget.style.filter = "brightness(1)";
        }}
        onMouseDown={(e) => {
          if (!disabled && !loading) {
            e.currentTarget.style.transform = "translateY(0) scale(0.98)";
          }
        }}
        onMouseUp={(e) => {
          e.currentTarget.style.transform = "translateY(-1px) scale(1)";
        }}
        {...props}
      >
        {loading ? (
          <svg
            style={{ width: "16px", height: "16px", animation: "spin 1s linear infinite" }}
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="60" strokeDashoffset="20" strokeLinecap="round" />
          </svg>
        ) : icon ? (
          <span style={{ display: "flex", flexShrink: 0 }}>{icon}</span>
        ) : null}
        {children && <span>{children}</span>}
        {iconRight && <span style={{ display: "flex", flexShrink: 0 }}>{iconRight}</span>}
      </button>
    );
  }
);
CzButton.displayName = "CzButton";
