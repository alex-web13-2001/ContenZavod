"use client";
import React from "react";
import { Inbox, PenTool, CheckCircle2, Trash2 } from "lucide-react";
import type { PipelineCounts } from "./types";

export type PipelineStatus = "inbox" | "in_progress" | "published" | "rejected";

const STAGES: { key: PipelineStatus; label: string; icon: typeof Inbox; color: string }[] = [
  { key: "inbox", label: "Входящие", icon: Inbox, color: "var(--cz-info)" },
  { key: "in_progress", label: "В работе", icon: PenTool, color: "var(--cz-warning)" },
  { key: "published", label: "Опубликовано", icon: CheckCircle2, color: "var(--cz-success)" },
  { key: "rejected", label: "Отклонено", icon: Trash2, color: "var(--cz-text-muted)" },
];

const DATE_PRESETS = [
  { label: "Сегодня", value: "today" },
  { label: "3 дня", value: "3d" },
  { label: "Неделя", value: "7d" },
  { label: "Месяц", value: "30d" },
  { label: "Всё", value: "" },
];

function getDateFromPreset(preset: string): string {
  if (!preset) return "";
  const now = new Date();
  // "today" = start of today in local time; "3d" = 3 days ago, etc.
  if (preset === "today") {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return d.toISOString().slice(0, 19); // full datetime for precision
  }
  const days = preset === "3d" ? 3 : preset === "7d" ? 7 : 30;
  const d = new Date(now.getTime() - days * 86400000);
  return d.toISOString().slice(0, 10);
}

interface Props {
  active: PipelineStatus;
  counts: PipelineCounts;
  dateFrom: string;
  onChangeStatus: (s: PipelineStatus) => void;
  onChangeDate: (iso: string) => void;
}

export function PipelineNav({ active, counts, dateFrom, onChangeStatus, onChangeDate }: Props) {
  const activePreset = !dateFrom ? "" : DATE_PRESETS.find(p => getDateFromPreset(p.value) === dateFrom)?.value || "";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Pipeline tabs */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {STAGES.map((s) => {
          const isActive = active === s.key;
          const Icon = s.icon;
          const count = counts[s.key];
          return (
            <button key={s.key} onClick={() => onChangeStatus(s.key)} style={{
              display: "flex", alignItems: "center", gap: 7,
              padding: "9px 16px", borderRadius: 10, border: "none", cursor: "pointer",
              fontSize: 14, fontWeight: isActive ? 700 : 500, transition: "all 0.2s ease",
              backgroundColor: isActive ? `hsl(${s.color} / 0.12)` : "hsl(var(--cz-bg-surface))",
              color: isActive ? `hsl(${s.color})` : "hsl(var(--cz-text-secondary))",
              boxShadow: isActive ? `0 0 0 1.5px hsl(${s.color} / 0.3)` : "0 0 0 1px hsl(var(--cz-border) / 0.4)",
            }}>
              <Icon size={15} />
              {s.label}
              {count > 0 && (
                <span style={{
                  padding: "1px 7px", borderRadius: 8, fontSize: 11, fontWeight: 700,
                  backgroundColor: isActive ? `hsl(${s.color} / 0.2)` : "hsl(var(--cz-border) / 0.5)",
                  color: isActive ? `hsl(${s.color})` : "hsl(var(--cz-text-muted))",
                  minWidth: 20, textAlign: "center",
                }}>{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Date filter chips */}
      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "hsl(var(--cz-text-muted))", marginRight: 4 }}>📅</span>
        {DATE_PRESETS.map((p) => {
          const isActive = activePreset === p.value;
          return (
            <button key={p.value} onClick={() => onChangeDate(getDateFromPreset(p.value))} style={{
              padding: "5px 12px", borderRadius: 7, border: "none", cursor: "pointer",
              fontSize: 12, fontWeight: isActive ? 700 : 500,
              backgroundColor: isActive ? "hsl(var(--cz-primary) / 0.12)" : "transparent",
              color: isActive ? "hsl(var(--cz-primary))" : "hsl(var(--cz-text-muted))",
            }}>
              {p.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
