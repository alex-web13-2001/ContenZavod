"use client";

interface CzSelectProps {
  label?: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  className?: string;
}

export function CzSelect({ label, value, onChange, options, className = "" }: CzSelectProps) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label && (
        <label
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
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="focus-ring"
        style={{
          width: "100%",
          height: "44px",
          padding: "0 36px 0 16px",
          fontSize: "14px",
          fontFamily: "var(--cz-font-sans)",
          color: `hsl(var(--cz-text-primary))`,
          backgroundColor: `hsl(var(--cz-bg-input))`,
          border: `1px solid hsl(var(--cz-border))`,
          borderRadius: "var(--cz-radius-md)",
          outline: "none",
          appearance: "none",
          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%236b6b80' viewBox='0 0 16 16'%3E%3Cpath d='M4 6l4 4 4-4'/%3E%3C/svg%3E")`,
          backgroundRepeat: "no-repeat",
          backgroundPosition: "right 12px center",
          cursor: "pointer",
          transition: `all var(--cz-duration-fast) var(--cz-ease)`,
        }}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
