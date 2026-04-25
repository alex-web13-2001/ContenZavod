"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { CzCard, CzBadge, CzSelect, CzButton, CzPageHeader, CzEmptyState, CzSkeletonTable } from "@/components/ui-system";
import { FileText, Sparkles, ExternalLink, ChevronDown, ChevronUp, Zap, Globe, TrendingUp } from "lucide-react";

interface Material {
  id: string;
  title: string;
  original_url: string;
  status: string;
  word_count: number | null;
  created_at: string;
  category: string | null;
  tags: string[];
  summary_ru: string | null;
  relevance_score: number | null;
  sentiment: string | null;
  is_breaking: boolean;
  classified_by: string | null;
  channel_relevance_score?: number | null;
  channel_hype_score?: number | null;
  is_recommended_for_channel?: boolean | null;
  channel_explanation?: string | null;
}

interface Channel {
  id: string;
  name: string;
}

const statusConfig: Record<string, { label: string; variant: "default" | "success" | "warning" | "error" | "info" }> = {
  new: { label: "Новый", variant: "info" },
  classifying: { label: "Классификация...", variant: "warning" },
  classified: { label: "Классифицирован", variant: "default" },
  adapted: { label: "Адаптирован", variant: "warning" },
  published: { label: "Опубликован", variant: "success" },
  rejected: { label: "Отклонён", variant: "error" },
};

const categoryLabels: Record<string, { label: string; emoji: string }> = {
  politics: { label: "Политика", emoji: "🏛️" },
  economy: { label: "Экономика", emoji: "💰" },
  society: { label: "Общество", emoji: "👥" },
  culture: { label: "Культура", emoji: "🎭" },
  sport: { label: "Спорт", emoji: "⚽" },
  tech: { label: "Технологии", emoji: "💻" },
  opinion: { label: "Мнения", emoji: "💬" },
  lifestyle: { label: "Лайфстайл", emoji: "✨" },
  crime: { label: "Криминал", emoji: "🚨" },
  environment: { label: "Экология", emoji: "🌿" },
  health: { label: "Здоровье", emoji: "🏥" },
  world: { label: "В мире", emoji: "🌍" },
};

const sentimentLabels: Record<string, { label: string; color: string }> = {
  positive: { label: "Позитив", color: "var(--cz-success)" },
  negative: { label: "Негатив", color: "var(--cz-error)" },
  neutral: { label: "Нейтрал", color: "var(--cz-text-muted)" },
  mixed: { label: "Смешан.", color: "var(--cz-warning)" },
};

const statusOptions = [
  { value: "all", label: "Все статусы" },
  { value: "new", label: "Новый" },
  { value: "classified", label: "Классифицирован" },
  { value: "adapted", label: "Адаптирован" },
  { value: "published", label: "Опубликован" },
  { value: "rejected", label: "Отклонён" },
];

function RelevanceBar({ score }: { score: number }) {
  const color = score >= 80 ? "var(--cz-success)" : score >= 50 ? "var(--cz-warning)" : "var(--cz-text-muted)";
  return (
    <div className="cz-flex cz-items-center cz-gap-8">
      <div style={{ width: 60, height: 6, borderRadius: 3, backgroundColor: `hsl(${color} / 0.15)`, overflow: "hidden" }}>
        <div style={{ width: `${score}%`, height: "100%", borderRadius: 3, backgroundColor: `hsl(${color})`, transition: "width 0.5s ease" }} />
      </div>
      <span className="cz-text-sm cz-font-semibold" style={{ color: `hsl(${color})`, minWidth: 28 }}>{score}</span>
    </div>
  );
}

function TagChip({ tag }: { tag: string }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", padding: "2px 8px", fontSize: 11, fontWeight: 500,
      borderRadius: 6, backgroundColor: "hsl(var(--cz-accent) / 0.08)", color: "hsl(var(--cz-accent))",
      border: "1px solid hsl(var(--cz-accent) / 0.15)",
    }}>{tag}</span>
  );
}

export default function MaterialsPage() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [channels, setChannels] = useState<{ value: string; label: string }[]>([
    { value: "all", label: "Все каналы (Без оценки)" }
  ]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [channelFilter, setChannelFilter] = useState("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [classifyLoading, setClassifyLoading] = useState(false);

  useEffect(() => {
    api.get<{ items: Channel[] }>("/channels").then((data) => {
      const opts = data.items.map((c) => ({ value: c.id, label: c.name }));
      setChannels([{ value: "all", label: "Все каналы (Без оценки)" }, ...opts]);
    }).catch(console.error);
  }, []);

  const fetchMaterials = useCallback(async (status?: string, channelId?: string) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (status && status !== "all") params.set("status", status);
      if (channelId && channelId !== "all") params.set("channel_id", channelId);
      params.set("per_page", "50");
      const data = await api.get<{ items: Material[]; total: number }>(`/materials?${params}`);
      setMaterials(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchMaterials(statusFilter, channelFilter); }, [statusFilter, channelFilter, fetchMaterials]);

  const handleClassifyAll = async () => {
    setClassifyLoading(true);
    try {
      await api.post("/materials/classify-all", {});
      setTimeout(() => fetchMaterials(statusFilter, channelFilter), 5000);
      setTimeout(() => fetchMaterials(statusFilter, channelFilter), 15000);
      setTimeout(() => fetchMaterials(statusFilter, channelFilter), 30000);
    } finally {
      setTimeout(() => setClassifyLoading(false), 3000);
    }
  };

  const newCount = materials.filter(m => m.status === "new").length;
  const classifiedCount = materials.filter(m => m.status === "classified").length;
  const avgRelevance = materials.filter(m => m.relevance_score != null)
    .reduce((acc, m, _, arr) => acc + (m.relevance_score! / arr.length), 0);

  return (
    <div className="cz-page">
      {/* Header */}
      <CzPageHeader title="Материалы" subtitle={`${total} материалов`}>
        {newCount > 0 && (
          <CzButton onClick={handleClassifyAll} disabled={classifyLoading} icon={<Sparkles size={14} />}>
            {classifyLoading ? "Классификация..." : `Классифицировать (${newCount})`}
          </CzButton>
        )}
        <div style={{ width: 220 }}>
          <CzSelect value={channelFilter} onChange={setChannelFilter} options={channels} />
        </div>
        <div style={{ width: 160 }}>
          <CzSelect value={statusFilter} onChange={setStatusFilter} options={statusOptions} />
        </div>
      </CzPageHeader>

      {/* Stats bar */}
      {classifiedCount > 0 && (
        <div className="cz-card-grid--stats">
          {[
            { icon: Sparkles, color: "var(--cz-success)", value: classifiedCount, label: "Классифицировано" },
            { icon: TrendingUp, color: "var(--cz-accent)", value: Math.round(avgRelevance), label: "Ср. релевантность" },
            { icon: Globe, color: "var(--cz-info)", value: new Set(materials.map(m => m.category).filter(Boolean)).size, label: "Категорий" },
          ].map((stat) => (
            <CzCard key={stat.label} padding="sm">
              <div className="cz-flex cz-items-center cz-gap-12">
                <div className="cz-icon-box cz-icon-box--sm" style={{ backgroundColor: `hsl(${stat.color} / 0.1)` }}>
                  <stat.icon size={18} style={{ color: `hsl(${stat.color})` }} />
                </div>
                <div>
                  <div className="cz-font-bold" style={{ fontSize: 20 }}>{stat.value}</div>
                  <div className="cz-text-xs cz-text-muted">{stat.label}</div>
                </div>
              </div>
            </CzCard>
          ))}
        </div>
      )}

      {/* Materials list */}
      {loading ? (
        <CzSkeletonTable rows={5} />
      ) : materials.length === 0 ? (
        <CzEmptyState
          icon={<FileText size={48} />}
          title="Нет материалов"
          text="Материалы появятся после парсинга источников"
        />
      ) : (
        <div className="cz-flex-col cz-gap-6 stagger-children">
          {materials.map((m) => {
            const sc = statusConfig[m.status] || statusConfig.new;
            const cat = m.category ? categoryLabels[m.category] : null;
            const sent = m.sentiment ? sentimentLabels[m.sentiment] : null;
            const isExpanded = expandedId === m.id;

            return (
              <CzCard key={m.id} interactive padding="sm">
                <div onClick={() => setExpandedId(isExpanded ? null : m.id)} style={{ cursor: "pointer" }}>
                  {/* Main row */}
                  <div className="cz-flex-between cz-items-start cz-gap-16" style={{ padding: "4px 0" }}>
                    <div className="cz-flex-1">
                      <div className="cz-flex cz-items-center cz-gap-8">
                        {m.is_breaking && (
                          <span className="cz-flex cz-items-center cz-gap-4" style={{
                            padding: "1px 6px", fontSize: 10, fontWeight: 700, borderRadius: 4,
                            backgroundColor: "hsl(var(--cz-error))", color: "white",
                            textTransform: "uppercase", letterSpacing: "0.05em",
                          }}>
                            <Zap size={10} />BREAKING
                          </span>
                        )}
                        {m.is_recommended_for_channel && (
                          <span className="cz-flex cz-items-center cz-gap-4" style={{
                            padding: "1px 6px", fontSize: 10, fontWeight: 700, borderRadius: 4,
                            backgroundColor: "hsl(var(--cz-success))", color: "white",
                            textTransform: "uppercase", letterSpacing: "0.05em",
                          }}>
                            <Sparkles size={10} />РЕКОМЕНДОВАНО
                          </span>
                        )}
                        <span className="cz-text-lg cz-font-medium cz-truncate">{m.title}</span>
                      </div>

                      {/* AI summary */}
                      {m.summary_ru && (
                        <div className="cz-text-sm cz-text-secondary" style={{
                          marginTop: 4, lineHeight: 1.5, overflow: "hidden", textOverflow: "ellipsis",
                          display: "-webkit-box", WebkitLineClamp: isExpanded ? 10 : 2, WebkitBoxOrient: "vertical",
                        }}>
                          {m.summary_ru}
                        </div>
                      )}

                      {/* Tags */}
                      {m.tags && m.tags.length > 0 && (
                        <div className="cz-flex cz-flex-wrap cz-gap-4" style={{ marginTop: 6 }}>
                          {m.tags.slice(0, isExpanded ? 10 : 3).map((tag) => <TagChip key={tag} tag={tag} />)}
                          {!isExpanded && m.tags.length > 3 && (
                            <span className="cz-text-xs cz-text-muted" style={{ alignSelf: "center" }}>+{m.tags.length - 3}</span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Right meta */}
                    <div className="cz-flex-col cz-items-end cz-gap-6 cz-flex-shrink-0">
                      <div className="cz-flex cz-items-center cz-gap-8">
                        {cat && (
                          <span className="cz-text-sm cz-font-medium cz-text-secondary cz-flex cz-items-center cz-gap-4">
                            <span>{cat.emoji}</span>{cat.label}
                          </span>
                        )}
                        <CzBadge variant={sc.variant}>{sc.label}</CzBadge>
                      </div>

                      <div className="cz-flex cz-items-center cz-gap-12">
                        {m.channel_hype_score != null && (
                          <div title="Hype Score">
                            <span className="cz-text-xs cz-text-muted">Hype:</span><RelevanceBar score={m.channel_hype_score * 10} />
                          </div>
                        )}
                        {m.channel_relevance_score != null ? (
                           <div title="Channel Relevance">
                            <span className="cz-text-xs cz-text-muted">Релев:</span><RelevanceBar score={m.channel_relevance_score * 10} />
                           </div>
                        ) : m.relevance_score != null ? (
                          <RelevanceBar score={m.relevance_score} />
                        ) : null}
                        {sent && <span className="cz-text-xs cz-font-medium" style={{ color: `hsl(${sent.color})` }}>{sent.label}</span>}
                      </div>

                      <div className="cz-flex cz-items-center cz-gap-8">
                        {m.word_count && <span className="cz-text-xs cz-text-muted">{m.word_count} сл.</span>}
                        <span className="cz-text-xs cz-text-muted">{new Date(m.created_at).toLocaleDateString("ru")}</span>
                        {isExpanded ? <ChevronUp size={14} className="cz-text-muted" /> : <ChevronDown size={14} className="cz-text-muted" />}
                      </div>
                    </div>
                  </div>

                  {/* Expanded */}
                  {isExpanded && (
                    <div className="cz-flex-col cz-gap-8" style={{
                      marginTop: 12, paddingTop: 12, borderTop: "1px solid hsl(var(--cz-border))",
                    }}>
                      {m.channel_explanation && (
                         <div style={{
                          padding: 10, borderRadius: "var(--cz-radius-md)",
                          backgroundColor: m.is_recommended_for_channel ? "hsl(var(--cz-success) / 0.1)" : "hsl(var(--cz-warning) / 0.1)",
                          border: `1px solid ${m.is_recommended_for_channel ? "hsl(var(--cz-success) / 0.2)" : "hsl(var(--cz-warning) / 0.2)"}`,
                          fontSize: 13, lineHeight: 1.5,
                         }}>
                           <strong className="cz-font-semibold" style={{
                             display: "block", marginBottom: 4,
                             color: m.is_recommended_for_channel ? "hsl(var(--cz-success))" : "hsl(var(--cz-warning))",
                           }}>
                             Оценка редактора (Канал):
                           </strong>
                           {m.channel_explanation}
                         </div>
                      )}
                      <div className="cz-flex cz-items-center cz-gap-16 cz-flex-wrap">
                        <a href={m.original_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
                          className="cz-flex cz-items-center cz-gap-4 cz-text-sm" style={{ color: "hsl(var(--cz-accent))", textDecoration: "none" }}>
                          <ExternalLink size={12} /> Оригинал
                        </a>
                        {m.classified_by && <span className="cz-text-xs cz-text-muted">AI: {m.classified_by}</span>}
                      </div>
                    </div>
                  )}
                </div>
              </CzCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
