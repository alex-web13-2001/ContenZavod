"use client";

type SkeletonVariant = "text" | "title" | "card" | "row" | "avatar";

interface CzSkeletonProps {
  variant?: SkeletonVariant;
  count?: number;
  className?: string;
}

export function CzSkeleton({ variant = "row", count = 1, className = "" }: CzSkeletonProps) {
  const items = Array.from({ length: count }, (_, i) => i);
  const variantClass = variant ? `cz-skeleton--${variant}` : "";

  return (
    <div className="cz-skeleton-group">
      {items.map((i) => (
        <div key={i} className={`cz-skeleton ${variantClass} ${className}`} />
      ))}
    </div>
  );
}

/** Skeleton for a card grid layout */
export function CzSkeletonGrid({ count = 3 }: { count?: number }) {
  return (
    <div className="cz-card-grid">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="cz-skeleton cz-skeleton--card" />
      ))}
    </div>
  );
}

/** Skeleton for table rows */
export function CzSkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="cz-skeleton-group">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="cz-skeleton cz-skeleton--row" />
      ))}
    </div>
  );
}
