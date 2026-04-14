"use client";

interface CzBadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info";
  size?: "sm" | "md";
}

const variantColors = {
  default: { bg: "var(--cz-bg-overlay)", text: "var(--cz-text-secondary)", border: "var(--cz-border)" },
  success: { bg: "var(--cz-success)", text: "var(--cz-success)", border: "var(--cz-success)" },
  warning: { bg: "var(--cz-warning)", text: "var(--cz-warning)", border: "var(--cz-warning)" },
  error: { bg: "var(--cz-error)", text: "var(--cz-error)", border: "var(--cz-error)" },
  info: { bg: "var(--cz-info)", text: "var(--cz-info)", border: "var(--cz-info)" },
};

export function CzBadge({ children, variant = "default", size = "sm" }: CzBadgeProps) {
  const colors = variantColors[variant];
  const isDefault = variant === "default";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: size === "sm" ? "2px 8px" : "4px 12px",
        fontSize: size === "sm" ? "11px" : "12px",
        fontWeight: 500,
        letterSpacing: "0.02em",
        borderRadius: "var(--cz-radius-full)",
        backgroundColor: isDefault ? `hsl(${colors.bg})` : `hsl(${colors.bg} / 0.1)`,
        color: isDefault ? `hsl(${colors.text})` : `hsl(${colors.text})`,
        border: `1px solid ${isDefault ? `hsl(${colors.border})` : `hsl(${colors.border} / 0.2)`}`,
        whiteSpace: "nowrap",
      }}
    >
      {!isDefault && (
        <span
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            backgroundColor: `hsl(${colors.bg})`,
            marginRight: "6px",
            flexShrink: 0,
          }}
        />
      )}
      {children}
    </span>
  );
}
