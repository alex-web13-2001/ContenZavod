"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { CzCard, CzBadge, CzSelect } from "@/components/ui-system";
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
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <div style={{
        width: "60px", height: "6px", borderRadius: "3px",
        backgroundColor: `hsl(${color} / 0.15)`, overflow: "hidden",
      }}>
        <div style={{
          width: `${score}%`, height: "100%", borderRadius: "3px",
          backgroundColor: `hsl(${color})`,
          transition: "width 0.5s ease",
        }} />
      </div>
      <span style={{ fontSize: "12px", fontWeight: 600, color: `hsl(${color})`, minWidth: "28px" }}>{score}</span>
    </div>
  );
}

function TagChip({ tag }: { tag: string }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 8px", fontSize: "11px", fontWeight: 500,
      borderRadius: "6px",
      backgroundColor: `hsl(var(--cz-accent) / 0.08)`,
      color: `hsl(var(--cz-accent))`,
      border: `1px solid hsl(var(--cz-accent) / 0.15)`,
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
      // Poll for results
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
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, color: `hsl(var(--cz-text-primary))`, letterSpacing: "-0.02em" }}>Материалы</h1>
          <p style={{ fontSize: "14px", color: `hsl(var(--cz-text-muted))`, marginTop: "4px" }}>{total} материалов</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {newCount > 0 && (
            <button
              onClick={handleClassifyAll}
              disabled={classifyLoading}
              style={{
                display: "inline-flex", alignItems: "center", gap: "8px",
                padding: "8px 16px", fontSize: "13px", fontWeight: 600,
                borderRadius: "var(--cz-radius-md)",
                backgroundColor: `hsl(var(--cz-accent))`,
                color: "white", border: "none", cursor: classifyLoading ? "not-allowed" : "pointer",
                opacity: classifyLoading ? 0.6 : 1,
                transition: "all 0.2s ease",
              }}
            >
              <Sparkles size={14} />
              {classifyLoading ? "Классификация..." : `Классифицировать (${newCount})`}
            </button>
          )}
          <div style={{ width: "220px" }}>
            <CzSelect value={channelFilter} onChange={setChannelFilter} options={channels} />
          </div>
          <div style={{ width: "160px" }}>
            <CzSelect value={statusFilter} onChange={setStatusFilter} options={statusOptions} />
          </div>
        </div>
      </div>

      {/* Stats bar */}
      {classifiedCount > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px" }}>
          <CzCard padding="sm">
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div style={{
                width: "36px", height: "36px", borderRadius: "var(--cz-radius-md)",
                backgroundColor: `hsl(var(--cz-success) / 0.1)`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Sparkles size={18} style={{ color: `hsl(var(--cz-success))` }} />
              </div>
              <div>
                <div style={{ fontSize: "20px", fontWeight: 700, color: `hsl(var(--cz-text-primary))` }}>{classifiedCount}</div>
                <div style={{ fontSize: "11px", color: `hsl(var(--cz-text-muted))` }}>Классифицировано</div>
              </div>
            </div>
          </CzCard>
          <CzCard padding="sm">
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div style={{
                width: "36px", height: "36px", borderRadius: "var(--cz-radius-md)",
                backgroundColor: `hsl(var(--cz-accent) / 0.1)`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <TrendingUp size={18} style={{ color: `hsl(var(--cz-accent))` }} />
              </div>
              <div>
                <div style={{ fontSize: "20px", fontWeight: 700, color: `hsl(var(--cz-text-primary))` }}>{Math.round(avgRelevance)}</div>
                <div style={{ fontSize: "11px", color: `hsl(var(--cz-text-muted))` }}>Ср. релевантность</div>
              </div>
            </div>
          </CzCard>
          <CzCard padding="sm">
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div style={{
                width: "36px", height: "36px", borderRadius: "var(--cz-radius-md)",
                backgroundColor: `hsl(var(--cz-info) / 0.1)`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Globe size={18} style={{ color: `hsl(var(--cz-info))` }} />
              </div>
              <div>
                <div style={{ fontSize: "20px", fontWeight: 700, color: `hsl(var(--cz-text-primary))` }}>
                  {new Set(materials.map(m => m.category).filter(Boolean)).size}
                </div>
                <div style={{ fontSize: "11px", color: `hsl(var(--cz-text-muted))` }}>Категорий</div>
              </div>
            </div>
          </CzCard>
        </div>
      )}

      {/* Materials list */}
      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton" style={{ height: "80px" }} />)}
        </div>
      ) : materials.length === 0 ? (
        <CzCard>
          <div style={{ textAlign: "center", padding: "48px 24px" }}>
            <FileText size={48} style={{ color: `hsl(var(--cz-text-muted))`, margin: "0 auto 16px" }} />
            <h3 style={{ fontSize: "16px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))` }}>Нет материалов</h3>
            <p style={{ fontSize: "13px", color: `hsl(var(--cz-text-muted))`, marginTop: "6px" }}>Материалы появятся после парсинга источников</p>
          </div>
        </CzCard>
      ) : (
        <div className="stagger-children" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {materials.map((m) => {
            const sc = statusConfig[m.status] || statusConfig.new;
            const cat = m.category ? categoryLabels[m.category] : null;
            const sent = m.sentiment ? sentimentLabels[m.sentiment] : null;
            const isExpanded = expandedId === m.id;

            return (
              <CzCard key={m.id} interactive padding="sm">
                <div
                  onClick={() => setExpandedId(isExpanded ? null : m.id)}
                  style={{ cursor: "pointer" }}
                >
                  {/* Main row */}
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px", padding: "4px 0" }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        {m.is_breaking && (
                          <span style={{
                            display: "inline-flex", alignItems: "center", gap: "3px",
                            padding: "1px 6px", fontSize: "10px", fontWeight: 700,
                            borderRadius: "4px", backgroundColor: `hsl(var(--cz-error))`, color: "white",
                            textTransform: "uppercase", letterSpacing: "0.05em",
                          }}>
                            <Zap size={10} />BREAKING
                          </span>
                        )}
                        {m.is_recommended_for_channel && (
                          <span style={{
                            display: "inline-flex", alignItems: "center", gap: "3px",
                            padding: "1px 6px", fontSize: "10px", fontWeight: 700,
                            borderRadius: "4px", backgroundColor: `hsl(var(--cz-success))`, color: "white",
                            textTransform: "uppercase", letterSpacing: "0.05em",
                          }}>
                            <Sparkles size={10} />РЕКОМЕНДОВАНО
                          </span>
                        )}
                        <span style={{
                          fontSize: "14px", fontWeight: 500,
                          color: `hsl(var(--cz-text-primary))`,
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        }}>
                          {m.title}
                        </span>
                      </div>

                      {/* AI summary */}
                      {m.summary_ru && (
                        <div style={{
                          fontSize: "12px", color: `hsl(var(--cz-text-secondary))`,
                          marginTop: "4px", lineHeight: "1.5",
                          overflow: "hidden", textOverflow: "ellipsis",
                          display: "-webkit-box", WebkitLineClamp: isExpanded ? 10 : 2,
                          WebkitBoxOrient: "vertical",
                        }}>
                          {m.summary_ru}
                        </div>
                      )}

                      {/* Tags row */}
                      {m.tags && m.tags.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "6px" }}>
                          {m.tags.slice(0, isExpanded ? 10 : 3).map((tag) => (
                            <TagChip key={tag} tag={tag} />
                          ))}
                          {!isExpanded && m.tags.length > 3 && (
                            <span style={{ fontSize: "11px", color: `hsl(var(--cz-text-muted))`, alignSelf: "center" }}>
                              +{m.tags.length - 3}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Right side: meta */}
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "6px", flexShrink: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        {cat && (
                          <span style={{
                            fontSize: "12px", fontWeight: 500,
                            color: `hsl(var(--cz-text-secondary))`,
                            display: "flex", alignItems: "center", gap: "4px",
                          }}>
                            <span>{cat.emoji}</span>
                            {cat.label}
                          </span>
                        )}
                        <CzBadge variant={sc.variant}>{sc.label}</CzBadge>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        {m.channel_hype_score != null && (
                          <div title="Hype Score">
                            <span style={{ fontSize: "11px", color: "var(--cz-text-muted)" }}>Hype:</span><RelevanceBar score={m.channel_hype_score * 10} />
                          </div>
                        )}
                        {m.channel_relevance_score != null ? (
                           <div title="Channel Relevance">
                            <span style={{ fontSize: "11px", color: "var(--cz-text-muted)" }}>Релев:</span><RelevanceBar score={m.channel_relevance_score * 10} />
                           </div>
                        ) : m.relevance_score != null ? (
                          <RelevanceBar score={m.relevance_score} />
                        ) : null}
                        {sent && (
                          <span style={{
                            fontSize: "11px", fontWeight: 500,
                            color: `hsl(${sent.color})`,
                          }}>
                            {sent.label}
                          </span>
                        )}
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        {m.word_count && (
                          <span style={{ fontSize: "11px", color: `hsl(var(--cz-text-muted))` }}>{m.word_count} сл.</span>
                        )}
                        <span style={{ fontSize: "11px", color: `hsl(var(--cz-text-muted))` }}>
                          {new Date(m.created_at).toLocaleDateString("ru")}
                        </span>
                        {isExpanded ? <ChevronUp size={14} style={{ color: `hsl(var(--cz-text-muted))` }} /> : <ChevronDown size={14} style={{ color: `hsl(var(--cz-text-muted))` }} />}
                      </div>
                    </div>
                  </div>

                  {/* Expanded section */}
                  {isExpanded && (
                    <div style={{
                      marginTop: "12px", paddingTop: "12px",
                      borderTop: `1px solid hsl(var(--cz-border))`,
                      display: "flex", flexDirection: "column", gap: "8px",
                    }}>
                      {m.channel_explanation && (
                         <div style={{
                          padding: "10px",
                          borderRadius: "var(--cz-radius-md)",
                          backgroundColor: m.is_recommended_for_channel ? `hsl(var(--cz-success) / 0.1)` : `hsl(var(--cz-warning) / 0.1)`,
                          border: `1px solid ${m.is_recommended_for_channel ? `hsl(var(--cz-success) / 0.2)` : `hsl(var(--cz-warning) / 0.2)`}`,
                          fontSize: "13px",
                          lineHeight: "1.5",
                          color: `hsl(var(--cz-text-secondary))`
                         }}>
                           <strong style={{ display: "block", marginBottom: "4px", color: m.is_recommended_for_channel ? `hsl(var(--cz-success))` : `hsl(var(--cz-warning))` }}>
                             Оценка редактора (Канал):
                           </strong>
                           {m.channel_explanation}
                         </div>
                      )}
                      
                      <div style={{ display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
                        <a
                          href={m.original_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            fontSize: "12px", color: `hsl(var(--cz-accent))`,
                            display: "flex", alignItems: "center", gap: "4px",
                            textDecoration: "none",
                          }}
                        >
                          <ExternalLink size={12} /> Оригинал
                        </a>
                        {m.classified_by && (
                          <span style={{ fontSize: "11px", color: `hsl(var(--cz-text-muted))` }}>
                            AI: {m.classified_by}
                          </span>
                        )}
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
