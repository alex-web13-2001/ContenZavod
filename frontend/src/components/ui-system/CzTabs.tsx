"use client";

import type { ReactNode } from "react";

interface Tab {
  id: string;
  label: string;
  icon?: ReactNode;
  count?: number;
}

interface CzTabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (tabId: string) => void;
}

export function CzTabs({ tabs, activeTab, onChange }: CzTabsProps) {
  return (
    <div className="cz-tabs">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`cz-tab ${activeTab === tab.id ? "cz-tab--active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.icon}
          <span>{tab.label}</span>
          {tab.count !== undefined && (
            <span className="cz-tab__badge">{tab.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}
