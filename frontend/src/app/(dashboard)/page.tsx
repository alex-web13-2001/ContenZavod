"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

  if (!stats) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-zinc-100">Дашборд</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="bg-zinc-900/50 border-zinc-800 animate-pulse">
              <CardContent className="p-6 h-24" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const cards = [
    {
      title: "Источники",
      value: stats.sources.total,
      subtitle: `${stats.sources.active} активных`,
      icon: Radio,
      gradient: "from-blue-500 to-cyan-500",
    },
    {
      title: "Материалы",
      value: stats.materials.total,
      subtitle: `${stats.materials.by_status["new"] || 0} новых`,
      icon: FileText,
      gradient: "from-indigo-500 to-purple-500",
    },
    {
      title: "Каналы",
      value: stats.channels.total,
      subtitle: "публикации",
      icon: Send,
      gradient: "from-emerald-500 to-teal-500",
    },
    {
      title: "Публикации",
      value: Object.values(stats.publish_jobs.by_status).reduce((a, b) => a + b, 0),
      subtitle: `${stats.publish_jobs.by_status["published"] || 0} опубликовано`,
      icon: BarChart3,
      gradient: "from-amber-500 to-orange-500",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Дашборд</h1>
        <p className="text-zinc-500 mt-1">Обзор контент-платформы</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card) => (
          <Card
            key={card.title}
            className="bg-zinc-900/50 border-zinc-800 hover:border-zinc-700 transition-colors"
          >
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-zinc-500">{card.title}</p>
                  <p className="text-3xl font-bold text-zinc-100 mt-1">{card.value}</p>
                  <p className="text-xs text-zinc-500 mt-1">{card.subtitle}</p>
                </div>
                <div
                  className={`h-12 w-12 rounded-xl bg-gradient-to-br ${card.gradient} flex items-center justify-center opacity-80`}
                >
                  <card.icon className="h-6 w-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Material Pipeline */}
      {stats.materials.total > 0 && (
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg text-zinc-200">Воронка материалов</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 flex-wrap">
              {Object.entries(stats.materials.by_status).map(([status, count]) => (
                <div
                  key={status}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-800/50 border border-zinc-700/50"
                >
                  <span className="text-sm text-zinc-400">
                    {statusLabels[status] || status}
                  </span>
                  <span className="text-lg font-semibold text-zinc-200">{count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
