"use client";

import type { ReactNode } from "react";
import { CzCard } from "./CzCard";

interface CzEmptyStateProps {
  icon: ReactNode;
  title: string;
  text?: string;
  action?: ReactNode;
}

export function CzEmptyState({ icon, title, text, action }: CzEmptyStateProps) {
  return (
    <CzCard>
      <div className="cz-empty-state">
        <div className="cz-empty-state__icon">{icon}</div>
        <h3 className="cz-empty-state__title">{title}</h3>
        {text && <p className="cz-empty-state__text">{text}</p>}
        {action && <div className="cz-empty-state__action">{action}</div>}
      </div>
    </CzCard>
  );
}
