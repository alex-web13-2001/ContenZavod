"use client";

import { forwardRef, type InputHTMLAttributes } from "react";

interface CzInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const CzInput = forwardRef<HTMLInputElement, CzInputProps>(
  ({ label, error, icon, className = "", id, ...props }, ref) => {
    const inputId = id || `input-${label?.toLowerCase().replace(/\s/g, "-")}`;

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            style={{
              fontSize: "13px",
              fontWeight: 500,
              color: `hsl(var(--cz-text-secondary))`,
              letterSpacing: "0.01em",
            }}
          >
            {label}
          </label>
        )}
        <div style={{ position: "relative" }}>
          {icon && (
            <div
              style={{
                position: "absolute",
                left: "14px",
                top: "50%",
                transform: "translateY(-50%)",
                color: `hsl(var(--cz-text-muted))`,
                display: "flex",
                pointerEvents: "none",
              }}
            >
              {icon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={`focus-ring ${className}`}
            style={{
              width: "100%",
              height: "44px",
              padding: icon ? "0 16px 0 44px" : "0 16px",
              fontSize: "14px",
              fontFamily: "var(--cz-font-sans)",
              color: `hsl(var(--cz-text-primary))`,
              backgroundColor: `hsl(var(--cz-bg-input))`,
              border: `1px solid ${error ? `hsl(var(--cz-error))` : `hsl(var(--cz-border))`}`,
              borderRadius: "var(--cz-radius-md)",
              outline: "none",
              transition: `all var(--cz-duration-fast) var(--cz-ease)`,
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = `hsl(var(--cz-primary))`;
              e.currentTarget.style.boxShadow = `var(--cz-shadow-glow)`;
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = error
                ? `hsl(var(--cz-error))`
                : `hsl(var(--cz-border))`;
              e.currentTarget.style.boxShadow = "none";
            }}
            {...props}
          />
        </div>
        {error && (
          <span style={{ fontSize: "12px", color: `hsl(var(--cz-error))` }}>
            {error}
          </span>
        )}
      </div>
    );
  }
);
CzInput.displayName = "CzInput";
