"use client";

type StatusKey =
  | "new"
  | "classified"
  | "adapted"
  | "approved"
  | "published"
  | "rejected"
  | "failed"
  | "draft"
  | "pending";

const statusLabels: Record<string, string> = {
  new: "Новый",
  classified: "Классифицирован",
  adapted: "Адаптирован",
  approved: "Одобрен",
  published: "Опубликован",
  rejected: "Отклонён",
  failed: "Ошибка",
  draft: "Черновик",
  pending: "Ожидание",
};

interface CzStatusBadgeProps {
  status: string;
  label?: string;
  dot?: boolean;
}

export function CzStatusBadge({ status, label, dot = true }: CzStatusBadgeProps) {
  const statusKey = status.toLowerCase() as StatusKey;
  const displayLabel = label || statusLabels[statusKey] || status;

  return (
    <span className={`cz-status cz-status--${statusKey}`}>
      {dot && <span className="cz-status__dot" />}
      {displayLabel}
    </span>
  );
}
