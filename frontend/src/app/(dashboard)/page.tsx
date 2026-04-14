"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CzCard } from "@/components/ui-system";
import { Radio, FileText, Send, BarChart3 } from "lucide-react";

interface DashboardStats {
  sources: { total: number; active: number };
  materials: { total: number; by_status: Record<string, number> };
  channels: { total: number };
  publish_jobs: { by_status: Record<string, number> };
}

const statusLabels: Record<string, string> = {
  new: "Новые",
  classified: "Классифицированы",
  adapted: "Адаптированы",
  published: "Опубликованы",
  rejected: "Отклонены",
};

const statusColors: Record<string, string> = {
  new: "var(--cz-info)",
  classified: "var(--cz-primary)",
  adapted: "var(--cz-warning)",
  published: "var(--cz-success)",
  rejected: "var(--cz-error)",
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    api.get<DashboardStats>("/dashboard/stats").then(setStats);
  }, []);

  const cards = stats
    ? [
        {
          title: "Источники",
          value: stats.sources.total,
          sub: `${stats.sources.active} активных`,
          icon: Radio,
          gradient: "135deg, hsl(210 80% 55%), hsl(190 70% 50%)",
        },
        {
          title: "Материалы",
          value: stats.materials.total,
          sub: `${stats.materials.by_status["new"] || 0} новых`,
          icon: FileText,
          gradient: "135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent))",
        },
        {
          title: "Каналы",
          value: stats.channels.total,
          sub: "публикации",
          icon: Send,
          gradient: "135deg, hsl(152 60% 45%), hsl(170 55% 42%)",
        },
        {
          title: "Публикации",
          value: Object.values(stats.publish_jobs.by_status).reduce((a, b) => a + b, 0),
          sub: `${stats.publish_jobs.by_status["published"] || 0} опубликовано`,
          icon: BarChart3,
          gradient: "135deg, hsl(38 85% 55%), hsl(20 80% 55%)",
        },
      ]
    : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: "24px", fontWeight: 700, color: `hsl(var(--cz-text-primary))`, letterSpacing: "-0.02em" }}>
          Дашборд
        </h1>
        <p style={{ fontSize: "14px", color: `hsl(var(--cz-text-muted))`, marginTop: "4px" }}>
          Обзор контент-платформы
        </p>
      </div>

      {/* Stat cards */}
      <div
        className="stagger-children"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: "16px",
        }}
      >
        {cards
          ? cards.map((card) => (
              <CzCard key={card.title} interactive>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                  <div>
                    <p style={{ fontSize: "13px", color: `hsl(var(--cz-text-muted))`, marginBottom: "8px" }}>{card.title}</p>
                    <p style={{ fontSize: "32px", fontWeight: 700, color: `hsl(var(--cz-text-primary))`, lineHeight: 1, letterSpacing: "-0.03em" }}>
                      {card.value}
                    </p>
                    <p style={{ fontSize: "12px", color: `hsl(var(--cz-text-muted))`, marginTop: "6px" }}>{card.sub}</p>
                  </div>
                  <div
                    style={{
                      width: "44px",
                      height: "44px",
                      borderRadius: "var(--cz-radius-md)",
                      background: `linear-gradient(${card.gradient})`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      opacity: 0.85,
                      flexShrink: 0,
                    }}
                  >
                    <card.icon size={22} color="white" />
                  </div>
                </div>
              </CzCard>
            ))
          : [1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton" style={{ height: "120px" }} />
            ))}
      </div>

      {/* Pipeline */}
      {stats && stats.materials.total > 0 && (
        <CzCard>
          <h3 style={{ fontSize: "16px", fontWeight: 600, color: `hsl(var(--cz-text-primary))`, marginBottom: "16px" }}>
            Воронка материалов
          </h3>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            {Object.entries(stats.materials.by_status).map(([status, count]) => (
              <div
                key={status}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "10px 16px",
                  borderRadius: "var(--cz-radius-md)",
                  backgroundColor: `hsl(var(--cz-bg-elevated))`,
                  border: `1px solid hsl(var(--cz-border-subtle))`,
                }}
              >
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: `hsl(${statusColors[status] || "var(--cz-text-muted)"})` }} />
                <span style={{ fontSize: "13px", color: `hsl(var(--cz-text-secondary))` }}>
                  {statusLabels[status] || status}
                </span>
                <span style={{ fontSize: "16px", fontWeight: 600, color: `hsl(var(--cz-text-primary))` }}>
                  {count}
                </span>
              </div>
            ))}
          </div>
        </CzCard>
      )}
    </div>
  );
}
