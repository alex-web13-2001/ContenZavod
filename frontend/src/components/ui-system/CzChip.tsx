"use client";

interface CzChipProps {
  label: string;
  active?: boolean;
  count?: number;
  onClick?: () => void;
}

export function CzChip({ label, active = false, count, onClick }: CzChipProps) {
  return (
    <button
      className={`cz-chip ${active ? "cz-chip--active" : ""}`}
      onClick={onClick}
    >
      {label}
      {count !== undefined && <span className="cz-chip__count">{count}</span>}
    </button>
  );
}

interface CzChipGroupProps {
  children: React.ReactNode;
}

export function CzChipGroup({ children }: CzChipGroupProps) {
  return <div className="cz-chip-group">{children}</div>;
}
