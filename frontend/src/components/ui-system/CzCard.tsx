"use client";

import { type ReactNode } from "react";

interface CzCardProps {
  children: ReactNode;
  interactive?: boolean;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
  onClick?: () => void;
}

const paddings = {
  none: "0",
  sm: "16px",
  md: "24px",
  lg: "32px",
};

export function CzCard({
  children,
  interactive = false,
  className = "",
  padding = "md",
  onClick,
}: CzCardProps) {
  return (
    <div
      className={`${interactive ? "card-interactive" : ""} ${className}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      style={{
        padding: paddings[padding],
        backgroundColor: `hsl(var(--cz-bg-surface))`,
        border: `1px solid hsl(var(--cz-border-subtle))`,
        borderRadius: "var(--cz-radius-lg)",
        cursor: onClick ? "pointer" : "default",
      }}
    >
      {children}
    </div>
  );
}

export function CzCardHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        marginBottom: subtitle || action ? "16px" : "0",
      }}
    >
      <div>
        <h3
          style={{
            fontSize: "15px",
            fontWeight: 600,
            color: `hsl(var(--cz-text-primary))`,
            lineHeight: 1.3,
          }}
        >
          {title}
        </h3>
        {subtitle && (
          <p
            style={{
              fontSize: "13px",
              color: `hsl(var(--cz-text-muted))`,
              marginTop: "4px",
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
