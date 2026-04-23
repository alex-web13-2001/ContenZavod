"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CzCard, CzPageHeader, CzStatusBadge } from "@/components/ui-system";
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
    <div className="cz-page">
      <CzPageHeader title="Дашборд" subtitle="Обзор контент-платформы" />

      {/* Stat cards */}
      <div className="cz-card-grid--stats stagger-children">
        {cards
          ? cards.map((card) => (
              <CzCard key={card.title} interactive>
                <div className="cz-flex-between cz-items-start">
                  <div>
                    <p className="cz-text-base cz-text-muted" style={{ marginBottom: 8 }}>{card.title}</p>
                    <p className="cz-font-bold" style={{ fontSize: 32, lineHeight: 1, letterSpacing: "-0.03em" }}>
                      {card.value}
                    </p>
                    <p className="cz-text-sm cz-text-muted" style={{ marginTop: 6 }}>{card.sub}</p>
                  </div>
                  <div className="cz-flex-center cz-flex-shrink-0" style={{
                    width: 44, height: 44, borderRadius: "var(--cz-radius-md)",
                    background: `linear-gradient(${card.gradient})`, opacity: 0.85,
                  }}>
                    <card.icon size={22} color="white" />
                  </div>
                </div>
              </CzCard>
            ))
          : [1, 2, 3, 4].map((i) => (
              <div key={i} className="cz-skeleton cz-skeleton--card" style={{ height: 120 }} />
            ))}
      </div>

      {/* Pipeline */}
      {stats && stats.materials.total > 0 && (
        <CzCard>
          <h3 className="cz-text-lg cz-font-semibold" style={{ marginBottom: 16 }}>
            Воронка материалов
          </h3>
          <div className="cz-flex cz-gap-12 cz-flex-wrap">
            {Object.entries(stats.materials.by_status).map(([status, count]) => (
              <div key={status} className="cz-flex cz-items-center cz-gap-10" style={{
                padding: "10px 16px", borderRadius: "var(--cz-radius-md)",
                backgroundColor: "hsl(var(--cz-bg-elevated))",
                border: "1px solid hsl(var(--cz-border-subtle))",
              }}>
                <CzStatusBadge status={status} label={`${statusLabels[status] || status}: ${count}`} />
              </div>
            ))}
          </div>
        </CzCard>
      )}
    </div>
  );
}
