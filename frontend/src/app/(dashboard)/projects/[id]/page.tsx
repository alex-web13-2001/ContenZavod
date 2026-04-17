"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { CzCard, CzBadge } from "@/components/ui-system";
import {
  ArrowLeft,
  Send,
  Globe,
  Video,
  Settings,
  Sparkles,
  FileText,
  Zap,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Plus,
  X,
  Pencil,
  Trash2,
  Save,
  Check,
} from "lucide-react";
import Link from "next/link";

interface Project {
  id: string;
  name: string;
  description: string;
  topic_guidelines: string;
  target_audience: string;
  is_active: boolean;
}

interface Channel {
  id: string;
  name: string;
  channel_type: string;
  content_formats: string[];
  tone_of_voice: string;
  languages: string[];
  is_active: boolean;
}

interface Material {
  id: string;
  material_id: string;
  material_title: string | null;
  material_url: string | null;
  material_status: string | null;
  relevance_score: number;
  hype_score: number;
  is_recommended: boolean;
  explanation: string;
  created_at: string;
  // From old model (keep for backwards compat)
  title?: string;
  original_url?: string;
  category?: string | null;
  tags?: string[];
  summary_ru?: string | null;
  is_breaking?: boolean;
  project_relevance_score?: number | null;
  project_hype_score?: number | null;
  project_explanation?: string | null;
}

interface Adaptation {
  id: string;
  material_id: string;
  channel_id: string;
  language: string;
  content_format: string;
  headline: string;
  body: string;
  priority: string;
  status: string;
  created_at: string;
  material_title: string | null;
  channel_name: string | null;
  channel_type: string | null;
}

const platformConfig: Record<string, { icon: typeof Send; label: string; color: string }> = {
  telegram: { icon: Send, label: "Telegram", color: "var(--cz-info)" },
  website: { icon: Globe, label: "Сайт", color: "var(--cz-accent)" },
  youtube: { icon: Video, label: "YouTube", color: "var(--cz-error)" },
};

const formatLabels: Record<string, string> = {
  short_post: "Пост",
  longread: "Лонгрид",
  video_script: "Видео-скрипт",
  digest: "Дайджест",
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

function ScoreBar({ score, maxScore = 10 }: { score: number; maxScore?: number }) {
  const pct = (score / maxScore) * 100;
  const color =
    pct >= 80
      ? "var(--cz-success)"
      : pct >= 50
      ? "var(--cz-warning)"
      : "var(--cz-text-muted)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
      <div
        style={{
          width: "50px",
          height: "5px",
          borderRadius: "3px",
          backgroundColor: `hsl(${color} / 0.15)`,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            borderRadius: "3px",
            backgroundColor: `hsl(${color})`,
            transition: "width 0.5s ease",
          }}
        />
      </div>
      <span
        style={{
          fontSize: "12px",
          fontWeight: 600,
          color: `hsl(${color})`,
          minWidth: "20px",
        }}
      >
        {score}
      </span>
    </div>
  );
}

/** Lightweight markdown→HTML for AI-generated adaptation text */
function renderMarkdownToHtml(text: string): string {
  if (!text) return "";
  let html = text
    // Escape HTML
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    // Bold: **text** or __text__
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    // Italic: *text* or _text_ (but not inside words)
    .replace(/(?<![\w*])\*([^*]+?)\*(?![\w*])/g, "<em>$1</em>")
    .replace(/(?<!\w)_([^_]+?)_(?!\w)/g, "<em>$1</em>")
    // Headers: ### text → bold block
    .replace(/^#{1,3}\s+(.+)$/gm, "<strong style=\"display:block;margin:8px 0 4px\">$1</strong>")
    // Section markers: [Хук: 0-5 секунд], [ОСНОВНАЯ ЧАСТЬ] etc → bold section header
    .replace(/^\[([A-ZА-ЯЁa-zа-яё][A-ZА-ЯЁa-zа-яё\s\-:0-9]+)\]$/gm, "<strong style=\"display:block;margin:12px 0 4px;font-size:0.9em;color:hsl(var(--cz-text-muted))\">$1</strong>")
    // Links: [text](url) → clickable link
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "<a href=\"$2\" target=\"_blank\" rel=\"noopener\" style=\"color:hsl(var(--cz-accent));text-decoration:underline\">$1</a>")
    // Line breaks
    .replace(/\n/g, "<br/>");
  return html;
}

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [adaptations, setAdaptations] = useState<Record<string, Adaptation[]>>({});
  // loadingAdaptations removed — adaptations loaded eagerly
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"recommendations" | "channels" | "settings">(
    "recommendations"
  );
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [onlyRecommended, setOnlyRecommended] = useState(true);

  // Channel creation form
  const [showChannelForm, setShowChannelForm] = useState(false);
  const [channelSaving, setChannelSaving] = useState(false);
  const [channelForm, setChannelForm] = useState({
    name: "",
    channel_type: "telegram",
    content_formats: ["short_post"],
    tone_of_voice: "",
    languages: ["ru"],
  });

  const handleCreateChannel = async () => {
    if (!channelForm.name.trim()) return;
    setChannelSaving(true);
    try {
      await api.post("/channels", {
        ...channelForm,
        project_id: projectId,
      });
      setShowChannelForm(false);
      setChannelForm({ name: "", channel_type: "telegram", content_formats: ["short_post"], tone_of_voice: "", languages: ["ru"] });
      fetchChannels();
    } catch (e) {
      console.error(e);
    } finally {
      setChannelSaving(false);
    }
  };

  // Channel editing
  const [editChannelId, setEditChannelId] = useState<string | null>(null);
  const [editChannelForm, setEditChannelForm] = useState({
    name: "",
    channel_type: "telegram",
    content_formats: ["short_post"],
    tone_of_voice: "",
    languages: ["ru"],
    is_active: true,
  });

  const startEditChannel = (ch: Channel) => {
    setEditChannelId(ch.id);
    setEditChannelForm({
      name: ch.name,
      channel_type: ch.channel_type,
      content_formats: ch.content_formats,
      tone_of_voice: ch.tone_of_voice,
      languages: ch.languages,
      is_active: ch.is_active,
    });
    setShowChannelForm(false);
  };

  const handleSaveChannel = async () => {
    if (!editChannelId || !editChannelForm.name.trim()) return;
    setChannelSaving(true);
    try {
      await api.patch(`/channels/${editChannelId}`, editChannelForm);
      setEditChannelId(null);
      fetchChannels();
    } catch (e) {
      console.error(e);
    } finally {
      setChannelSaving(false);
    }
  };

  const handleDeleteChannel = async (channelId: string) => {
    if (!confirm("Удалить канал? Это действие нельзя отменить.")) return;
    try {
      await api.delete(`/channels/${channelId}`);
      fetchChannels();
    } catch (e) {
      console.error(e);
    }
  };

  // Project editing
  const [editingProject, setEditingProject] = useState(false);
  const [projectSaving, setProjectSaving] = useState(false);
  const [projectForm, setProjectForm] = useState({
    name: "",
    description: "",
    topic_guidelines: "",
    target_audience: "",
  });

  const startEditProject = () => {
    if (!project) return;
    setProjectForm({
      name: project.name,
      description: project.description,
      topic_guidelines: project.topic_guidelines,
      target_audience: project.target_audience,
    });
    setEditingProject(true);
  };

  const handleSaveProject = async () => {
    setProjectSaving(true);
    try {
      await api.patch(`/projects/${projectId}`, projectForm);
      setEditingProject(false);
      fetchProject();
    } catch (e) {
      console.error(e);
    } finally {
      setProjectSaving(false);
    }
  };

  const fetchProject = useCallback(async () => {
    try {
      const data = await api.get<Project>(`/projects/${projectId}`);
      setProject(data);
    } catch (e) {
      console.error(e);
    }
  }, [projectId]);

  const fetchChannels = useCallback(async () => {
    try {
      const data = await api.get<{ items: Channel[] }>(
        `/channels?project_id=${projectId}`
      );
      setChannels(data.items);
    } catch (e) {
      console.error(e);
    }
  }, [projectId]);

  const fetchRecommendationsAndAdaptations = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("per_page", "50");
      if (onlyRecommended) params.set("recommended_only", "true");
      else params.set("recommended_only", "false");

      // Fetch recommendations AND all adaptations in parallel
      const [recsData, adapData] = await Promise.all([
        api.get<{ items: Material[]; total: number }>(
          `/projects/${projectId}/recommendations?${params}`
        ),
        api.get<{ items: Adaptation[] }>(
          `/adaptations?project_id=${projectId}&per_page=200`
        ),
      ]);

      const mapped = recsData.items.map((m) => ({
        ...m,
        title: m.material_title || "Untitled",
        original_url: m.material_url || "",
        project_relevance_score: m.relevance_score,
        project_hype_score: m.hype_score,
        project_explanation: m.explanation,
      }));
      setMaterials(mapped);

      // Group adaptations by material_id
      const grouped: Record<string, Adaptation[]> = {};
      for (const a of adapData.items) {
        if (!grouped[a.material_id]) grouped[a.material_id] = [];
        grouped[a.material_id].push(a);
      }
      setAdaptations(grouped);
    } finally {
      setLoading(false);
    }
  }, [projectId, onlyRecommended]);

  const handleAdaptationAction = async (adaptationId: string, action: "approved" | "rejected") => {
    try {
      await api.patch(`/adaptations/${adaptationId}`, { status: action });
      // Refresh everything
      fetchRecommendationsAndAdaptations();
    } catch (e) {
      console.error(e);
    }
  };

  // On-demand format generation
  const [generatingFormats, setGeneratingFormats] = useState<Record<string, boolean>>({});

  const handleGenerateFormat = async (
    materialId: string,
    channelId: string,
    contentFormat: string,
    language: string = "ru"
  ) => {
    const key = `${materialId}-${channelId}-${contentFormat}`;
    setGeneratingFormats((prev) => ({ ...prev, [key]: true }));
    try {
      await api.post("/adaptations/generate", {
        material_id: materialId,
        channel_id: channelId,
        content_format: contentFormat,
        language,
      });
      // Poll for the new adaptation after a delay
      setTimeout(() => {
        fetchRecommendationsAndAdaptations();
        setGeneratingFormats((prev) => ({ ...prev, [key]: false }));
      }, 3000);
      // Also poll again at 8s and 15s for slower generations
      setTimeout(() => fetchRecommendationsAndAdaptations(), 8000);
      setTimeout(() => fetchRecommendationsAndAdaptations(), 15000);
    } catch (e: unknown) {
      const err = e as { response?: { status?: number } };
      if (err?.response?.status === 409) {
        // Already exists, just refresh
        fetchRecommendationsAndAdaptations();
      } else {
        console.error(e);
      }
      setGeneratingFormats((prev) => ({ ...prev, [key]: false }));
    }
  };

  useEffect(() => {
    fetchProject();
    fetchChannels();
  }, [fetchProject, fetchChannels]);

  useEffect(() => {
    if (tab === "recommendations") fetchRecommendationsAndAdaptations();
  }, [tab, fetchRecommendationsAndAdaptations]);

  if (!project) {
    return (
      <div style={{ padding: "48px", textAlign: "center" }}>
        <div className="skeleton" style={{ height: "200px" }} />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header */}
      <div>
        <Link
          href="/projects"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "12px",
            color: `hsl(var(--cz-text-muted))`,
            textDecoration: "none",
            marginBottom: "12px",
          }}
        >
          <ArrowLeft size={14} /> Проекты
        </Link>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "var(--cz-radius-md)",
                background: `linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontSize: "18px",
                fontWeight: 700,
              }}
            >
              {project.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1
                style={{
                  fontSize: "22px",
                  fontWeight: 700,
                  color: `hsl(var(--cz-text-primary))`,
                  letterSpacing: "-0.02em",
                }}
              >
                {project.name}
              </h1>
              {project.description && (
                <p
                  style={{
                    fontSize: "13px",
                    color: `hsl(var(--cz-text-muted))`,
                    marginTop: "2px",
                  }}
                >
                  {project.description}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: "4px",
          borderBottom: `1px solid hsl(var(--cz-border-subtle))`,
          paddingBottom: "0",
        }}
      >
        {[
          { key: "recommendations" as const, label: "Рекомендации", icon: Sparkles },
          { key: "channels" as const, label: "Каналы", icon: Send },
          { key: "settings" as const, label: "Настройки", icon: Settings },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "10px 16px",
              fontSize: "13px",
              fontWeight: tab === t.key ? 600 : 500,
              color: tab === t.key ? `hsl(var(--cz-primary))` : `hsl(var(--cz-text-muted))`,
              background: "none",
              border: "none",
              borderBottom:
                tab === t.key
                  ? `2px solid hsl(var(--cz-primary))`
                  : "2px solid transparent",
              cursor: "pointer",
              transition: "all 0.2s ease",
              marginBottom: "-1px",
            }}
          >
            <t.icon size={14} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "recommendations" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Filter bar */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "15px",
                color: `hsl(var(--cz-text-secondary))`,
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={onlyRecommended}
                onChange={(e) => setOnlyRecommended(e.target.checked)}
                style={{ accentColor: `hsl(var(--cz-primary))`, width: "18px", height: "18px" }}
              />
              Только рекомендованные
            </label>
            <span
              style={{
                fontSize: "14px",
                color: `hsl(var(--cz-text-muted))`,
              }}
            >
              {materials.length} материалов
            </span>
          </div>

          {/* Materials list */}
          {loading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton" style={{ height: "200px", borderRadius: "16px" }} />
              ))}
            </div>
          ) : materials.length === 0 ? (
            <CzCard>
              <div style={{ textAlign: "center", padding: "64px 24px" }}>
                <Sparkles
                  size={56}
                  style={{ color: `hsl(var(--cz-text-muted))`, margin: "0 auto 20px" }}
                />
                <h3
                  style={{
                    fontSize: "20px",
                    fontWeight: 600,
                    color: `hsl(var(--cz-text-secondary))`,
                  }}
                >
                  {onlyRecommended
                    ? "Нет рекомендованных материалов"
                    : "Нет оценённых материалов"}
                </h3>
                <p
                  style={{
                    fontSize: "15px",
                    color: `hsl(var(--cz-text-muted))`,
                    marginTop: "8px",
                  }}
                >
                  Материалы появятся после классификации и AI-оценки
                </p>
              </div>
            </CzCard>
          ) : (
            <div
              className="stagger-children"
              style={{ display: "flex", flexDirection: "column", gap: "20px" }}
            >
              {materials.map((m) => {
                const matAdapts = adaptations[m.material_id || m.id] || [];
                const cat = m.category ? categoryLabels[m.category] : null;
                const isExpanded = expandedId === m.id;

                return (
                  <CzCard key={m.id} padding="lg">
                    {/* ─── Header: badges + scores ─── */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "14px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                        {m.is_recommended && (
                          <span
                            style={{
                              padding: "3px 10px",
                              fontSize: "12px",
                              fontWeight: 700,
                              borderRadius: "6px",
                              backgroundColor: `hsl(var(--cz-success))`,
                              color: "white",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "5px",
                            }}
                          >
                            <Sparkles size={13} /> РЕКОМЕНДОВАНО
                          </span>
                        )}
                        {m.is_breaking && (
                          <span
                            style={{
                              padding: "3px 10px",
                              fontSize: "12px",
                              fontWeight: 700,
                              borderRadius: "6px",
                              backgroundColor: `hsl(var(--cz-error))`,
                              color: "white",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "5px",
                            }}
                          >
                            <Zap size={13} /> СРОЧНО
                          </span>
                        )}
                        {cat && (
                          <span style={{ fontSize: "14px", color: `hsl(var(--cz-text-secondary))` }}>
                            {cat.emoji} {cat.label}
                          </span>
                        )}
                        <span style={{ fontSize: "13px", color: `hsl(var(--cz-text-muted))` }}>
                          {new Date(m.created_at).toLocaleDateString("ru", { day: "numeric", month: "short", year: "numeric" })}
                        </span>
                      </div>

                      {/* Scores */}
                      <div style={{ display: "flex", alignItems: "center", gap: "16px", flexShrink: 0 }}>
                        {m.project_relevance_score != null && (
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span style={{ fontSize: "13px", color: `hsl(var(--cz-text-muted))` }}>Релевантность</span>
                            <ScoreBar score={m.project_relevance_score} />
                          </div>
                        )}
                        {m.project_hype_score != null && (
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span style={{ fontSize: "13px", color: `hsl(var(--cz-text-muted))` }}>Хайп</span>
                            <ScoreBar score={m.project_hype_score} />
                          </div>
                        )}
                      </div>
                    </div>

                    {/* ─── AI Rationale (why this material) ─── */}
                    {m.project_explanation && (
                      <div
                        style={{
                          padding: "14px 18px",
                          borderRadius: "12px",
                          backgroundColor: m.is_recommended
                            ? `hsl(var(--cz-success) / 0.08)`
                            : `hsl(var(--cz-warning) / 0.08)`,
                          border: `1px solid ${
                            m.is_recommended
                              ? `hsl(var(--cz-success) / 0.2)`
                              : `hsl(var(--cz-warning) / 0.2)`
                          }`,
                          marginBottom: "16px",
                        }}
                      >
                        <div
                          style={{
                            fontSize: "12px",
                            fontWeight: 700,
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                            color: m.is_recommended
                              ? `hsl(var(--cz-success))`
                              : `hsl(var(--cz-warning))`,
                            marginBottom: "6px",
                          }}
                        >
                          🤖 Почему эта новость
                        </div>
                        <div
                          style={{
                            fontSize: "15px",
                            lineHeight: "1.6",
                            color: `hsl(var(--cz-text-primary))`,
                          }}
                        >
                          {m.project_explanation}
                        </div>
                      </div>
                    )}

                    {/* ─── Original source link ─── */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        marginBottom: "16px",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "15px",
                          fontWeight: 600,
                          color: `hsl(var(--cz-text-secondary))`,
                          flex: 1,
                        }}
                      >
                        📰 {m.title}
                      </span>
                      <a
                        href={m.original_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontSize: "13px",
                          color: `hsl(var(--cz-accent))`,
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "5px",
                          textDecoration: "none",
                          flexShrink: 0,
                          padding: "4px 12px",
                          borderRadius: "8px",
                          border: `1px solid hsl(var(--cz-accent) / 0.2)`,
                          backgroundColor: `hsl(var(--cz-accent) / 0.05)`,
                        }}
                      >
                        <ExternalLink size={14} /> Оригинал
                      </a>
                    </div>

                    {/* ─── Adaptations (shown immediately!) ─── */}
                    {matAdapts.length > 0 ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                        <div
                          style={{
                            fontSize: "13px",
                            fontWeight: 700,
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                            color: `hsl(var(--cz-text-muted))`,
                          }}
                        >
                          ✍️ Адаптации для каналов ({matAdapts.length})
                        </div>
                        {matAdapts.map((ad) => {
                          const statusColors: Record<string, string> = {
                            draft: "var(--cz-warning)",
                            approved: "var(--cz-success)",
                            rejected: "var(--cz-error)",
                            published: "var(--cz-info)",
                          };
                          const statusLabels: Record<string, string> = {
                            draft: "Черновик",
                            approved: "Одобрен",
                            rejected: "Отклонён",
                            published: "Опубликован",
                          };
                          return (
                            <div
                              key={ad.id}
                              style={{
                                padding: "16px 20px",
                                borderRadius: "12px",
                                backgroundColor: `hsl(var(--cz-bg-surface))`,
                                border: `1px solid hsl(var(--cz-border))`,
                              }}
                            >
                              {/* Adaptation header */}
                              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                  <span style={{ fontSize: "14px", fontWeight: 600, color: `hsl(var(--cz-text-primary))` }}>
                                    {ad.channel_name || "Канал"}
                                  </span>
                                  <span style={{
                                    padding: "3px 10px",
                                    fontSize: "12px",
                                    fontWeight: 600,
                                    borderRadius: "6px",
                                    backgroundColor: `hsl(var(--cz-accent) / 0.1)`,
                                    color: `hsl(var(--cz-accent))`,
                                  }}>
                                    {formatLabels[ad.content_format] || ad.content_format}
                                  </span>
                                  <span style={{
                                    fontSize: "13px",
                                    fontWeight: 500,
                                    color: `hsl(var(--cz-text-muted))`,
                                  }}>
                                    {ad.language.toUpperCase()}
                                  </span>
                                </div>
                                <span style={{
                                  padding: "4px 12px",
                                  fontSize: "12px",
                                  fontWeight: 700,
                                  borderRadius: "6px",
                                  backgroundColor: `hsl(${statusColors[ad.status] || "var(--cz-text-muted)"} / 0.15)`,
                                  color: `hsl(${statusColors[ad.status] || "var(--cz-text-muted)"})`,
                                  textTransform: "uppercase",
                                }}>
                                  {statusLabels[ad.status] || ad.status}
                                </span>
                              </div>

                              {/* Headline */}
                              {ad.headline && (
                                <div style={{
                                  fontSize: "17px",
                                  fontWeight: 700,
                                  color: `hsl(var(--cz-text-primary))`,
                                  marginBottom: "8px",
                                  lineHeight: "1.4",
                                }}>
                                  <span dangerouslySetInnerHTML={{ __html: renderMarkdownToHtml(ad.headline) }} />
                                </div>
                              )}

                              {/* Body */}
                              <div
                                onClick={() => setExpandedId(isExpanded && expandedId === ad.id ? null : ad.id)}
                                style={{
                                  fontSize: "15px",
                                  lineHeight: "1.7",
                                  color: `hsl(var(--cz-text-secondary))`,
                                  maxHeight: expandedId === ad.id ? "none" : "160px",
                                  overflow: "hidden",
                                  cursor: "pointer",
                                  position: "relative",
                                }}
                              >
                                <span dangerouslySetInnerHTML={{ __html: renderMarkdownToHtml(ad.body) }} />
                                {expandedId !== ad.id && ad.body && ad.body.length > 300 && (
                                  <div style={{
                                    position: "absolute",
                                    bottom: 0,
                                    left: 0,
                                    right: 0,
                                    height: "50px",
                                    background: `linear-gradient(transparent, hsl(var(--cz-bg-surface)))`,
                                    display: "flex",
                                    alignItems: "flex-end",
                                    justifyContent: "center",
                                    paddingBottom: "4px",
                                  }}>
                                    <span style={{ fontSize: "13px", color: `hsl(var(--cz-accent))`, fontWeight: 600 }}>
                                      Читать полностью ↓
                                    </span>
                                  </div>
                                )}
                              </div>

                              {/* Action buttons */}
                              {ad.status === "draft" && (
                                <div style={{ display: "flex", gap: "10px", marginTop: "14px" }}>
                                  <button
                                    onClick={() => handleAdaptationAction(ad.id, "approved")}
                                    style={{
                                      padding: "8px 24px",
                                      fontSize: "14px",
                                      fontWeight: 600,
                                      borderRadius: "8px",
                                      border: "none",
                                      backgroundColor: `hsl(var(--cz-success))`,
                                      color: "white",
                                      cursor: "pointer",
                                      display: "flex",
                                      alignItems: "center",
                                      gap: "6px",
                                      transition: "opacity 0.2s",
                                    }}
                                    onMouseOver={(e) => (e.currentTarget.style.opacity = "0.85")}
                                    onMouseOut={(e) => (e.currentTarget.style.opacity = "1")}
                                  >
                                    <Check size={16} /> Одобрить
                                  </button>
                                  <button
                                    onClick={() => handleAdaptationAction(ad.id, "rejected")}
                                    style={{
                                      padding: "8px 24px",
                                      fontSize: "14px",
                                      fontWeight: 600,
                                      borderRadius: "8px",
                                      border: `1px solid hsl(var(--cz-error) / 0.3)`,
                                      backgroundColor: "transparent",
                                      color: `hsl(var(--cz-error))`,
                                      cursor: "pointer",
                                      display: "flex",
                                      alignItems: "center",
                                      gap: "6px",
                                      transition: "opacity 0.2s",
                                    }}
                                    onMouseOver={(e) => (e.currentTarget.style.opacity = "0.85")}
                                    onMouseOut={(e) => (e.currentTarget.style.opacity = "1")}
                                  >
                                    <X size={16} /> Отклонить
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        })}

                        {/* ─── Generate additional formats ─── */}
                        {(() => {
                          // Group existing adaptations by channel
                          const existingByChannel: Record<string, string[]> = {};
                          matAdapts.forEach((ad) => {
                            if (!existingByChannel[ad.channel_id]) existingByChannel[ad.channel_id] = [];
                            existingByChannel[ad.channel_id].push(ad.content_format);
                          });

                          // For each channel, find formats NOT yet generated
                          const channelIds = Object.keys(existingByChannel);
                          const buttons: React.ReactNode[] = [];

                          channelIds.forEach((chId) => {
                            const ch = channels.find((c) => c.id === chId);
                            if (!ch) return;
                            const generated = existingByChannel[chId];
                            const missing = ch.content_formats.filter((f) => !generated.includes(f));
                            if (missing.length === 0) return;

                            missing.forEach((fmt) => {
                              const genKey = `${m.material_id || m.id}-${chId}-${fmt}`;
                              const isGen = generatingFormats[genKey];
                              buttons.push(
                                <button
                                  key={genKey}
                                  disabled={isGen}
                                  onClick={() =>
                                    handleGenerateFormat(
                                      m.material_id || m.id,
                                      chId,
                                      fmt,
                                      ch.languages[0] || "ru"
                                    )
                                  }
                                  style={{
                                    padding: "6px 14px",
                                    fontSize: "13px",
                                    fontWeight: 500,
                                    borderRadius: "8px",
                                    border: `1px dashed hsl(var(--cz-accent) / 0.4)`,
                                    backgroundColor: isGen
                                      ? `hsl(var(--cz-accent) / 0.08)`
                                      : "transparent",
                                    color: `hsl(var(--cz-accent))`,
                                    cursor: isGen ? "wait" : "pointer",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "6px",
                                    transition: "all 0.2s",
                                    opacity: isGen ? 0.7 : 1,
                                  }}
                                  onMouseOver={(e) => {
                                    if (!isGen) {
                                      e.currentTarget.style.backgroundColor = `hsl(var(--cz-accent) / 0.1)`;
                                      e.currentTarget.style.borderStyle = "solid";
                                    }
                                  }}
                                  onMouseOut={(e) => {
                                    if (!isGen) {
                                      e.currentTarget.style.backgroundColor = "transparent";
                                      e.currentTarget.style.borderStyle = "dashed";
                                    }
                                  }}
                                >
                                  {isGen ? (
                                    <>⏳ Генерация...</>
                                  ) : (
                                    <>
                                      <Sparkles size={14} />
                                      {ch.name}: {formatLabels[fmt] || fmt}
                                    </>
                                  )}
                                </button>
                              );
                            });
                          });

                          if (buttons.length === 0) return null;
                          return (
                            <div
                              style={{
                                marginTop: "8px",
                                paddingTop: "12px",
                                borderTop: `1px dashed hsl(var(--cz-border) / 0.3)`,
                                display: "flex",
                                flexWrap: "wrap",
                                gap: "8px",
                                alignItems: "center",
                              }}
                            >
                              <span
                                style={{
                                  fontSize: "12px",
                                  fontWeight: 600,
                                  textTransform: "uppercase",
                                  letterSpacing: "0.04em",
                                  color: `hsl(var(--cz-text-muted))`,
                                  marginRight: "4px",
                                }}
                              >
                                + ещё формат:
                              </span>
                              {buttons}
                            </div>
                          );
                        })()}
                      </div>
                    ) : m.is_recommended ? (
                      <div
                        style={{
                          padding: "20px",
                          borderRadius: "12px",
                          backgroundColor: `hsl(var(--cz-bg-surface))`,
                          border: `1px dashed hsl(var(--cz-border))`,
                          textAlign: "center",
                        }}
                      >
                        <div style={{ fontSize: "15px", color: `hsl(var(--cz-text-muted))` }}>
                          ⏳ AI генерирует адаптации для каналов...
                        </div>
                      </div>
                    ) : null}
                  </CzCard>
                );
              })}
            </div>
          )}
        </div>
      )}



      {tab === "channels" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span
              style={{
                fontSize: "13px",
                color: `hsl(var(--cz-text-muted))`,
              }}
            >
              {channels.length} каналов в проекте
            </span>
            <button
              onClick={() => setShowChannelForm(!showChannelForm)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                fontSize: "12px",
                fontWeight: 600,
                borderRadius: "var(--cz-radius-md)",
                backgroundColor: showChannelForm ? `hsl(var(--cz-text-muted))` : `hsl(var(--cz-accent))`,
                color: "white",
                border: "none",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              {showChannelForm ? <><X size={12} /> Отмена</> : <><Plus size={12} /> Добавить канал</>}
            </button>
          </div>

          {/* Channel creation form */}
          {showChannelForm && (
            <div
              className="animate-page-in"
              style={{
                padding: "24px",
                borderRadius: "var(--cz-radius-xl)",
                backgroundColor: `hsl(var(--cz-bg-surface) / 0.6)`,
                backdropFilter: "blur(16px)",
                border: `1px solid hsl(var(--cz-border-subtle))`,
                boxShadow: "var(--cz-shadow-lg), inset 0 1px 0 hsl(var(--cz-border-subtle) / 0.5)",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                {/* Header */}
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "var(--cz-radius-md)",
                      background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Plus size={16} style={{ color: "white" }} />
                  </div>
                  <div>
                    <h3 style={{ fontSize: "16px", fontWeight: 600, color: `hsl(var(--cz-text-primary))`, letterSpacing: "-0.01em" }}>
                      Новый канал
                    </h3>
                    <p style={{ fontSize: "12px", color: `hsl(var(--cz-text-muted))`, marginTop: "1px" }}>
                      Настройте платформу и стиль контента
                    </p>
                  </div>
                </div>

                {/* Name input */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Название канала
                  </label>
                  <input
                    type="text"
                    placeholder="@mychannel или название"
                    value={channelForm.name}
                    onChange={(e) => setChannelForm({ ...channelForm, name: e.target.value })}
                    className="focus-ring"
                    style={{
                      width: "100%",
                      height: "44px",
                      padding: "0 16px",
                      fontSize: "14px",
                      fontFamily: "var(--cz-font-sans)",
                      color: `hsl(var(--cz-text-primary))`,
                      backgroundColor: `hsl(var(--cz-bg-input))`,
                      border: `1px solid hsl(var(--cz-border))`,
                      borderRadius: "var(--cz-radius-md)",
                      outline: "none",
                      transition: "all var(--cz-duration-fast) var(--cz-ease)",
                    }}
                  />
                </div>

                {/* Channel type — card selector */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Платформа
                  </label>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
                    {[
                      { value: "telegram", icon: Send, label: "Telegram", color: "var(--cz-info)" },
                      { value: "website", icon: Globe, label: "Сайт", color: "var(--cz-accent)" },
                      { value: "youtube", icon: Video, label: "YouTube", color: "var(--cz-error)" },
                    ].map((opt) => {
                      const isActive = channelForm.channel_type === opt.value;
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => setChannelForm({ ...channelForm, channel_type: opt.value })}
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            gap: "8px",
                            padding: "16px 12px",
                            borderRadius: "var(--cz-radius-lg)",
                            backgroundColor: isActive ? `hsl(${opt.color} / 0.12)` : `hsl(var(--cz-bg-hover))`,
                            border: isActive ? `2px solid hsl(${opt.color})` : `1px solid hsl(var(--cz-border-subtle))`,
                            cursor: "pointer",
                            transition: "all 0.2s ease",
                            transform: isActive ? "scale(1.02)" : "scale(1)",
                          }}
                        >
                          <opt.icon
                            size={22}
                            style={{ color: isActive ? `hsl(${opt.color})` : `hsl(var(--cz-text-muted))` }}
                          />
                          <span
                            style={{
                              fontSize: "12px",
                              fontWeight: isActive ? 600 : 500,
                              color: isActive ? `hsl(${opt.color})` : `hsl(var(--cz-text-secondary))`,
                            }}
                          >
                            {opt.label}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Content format — pill selector */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Формат контента
                  </label>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {[
                      { value: "short_post", label: "📝 Короткий пост" },
                      { value: "longread", label: "📖 Лонгрид" },
                      { value: "video_script", label: "🎬 Видео-скрипт" },
                      { value: "digest", label: "📋 Дайджест" },
                    ].map((opt) => {
                      const isActive = channelForm.content_formats.includes(opt.value);
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => {
                            const formats = isActive
                              ? channelForm.content_formats.filter((f) => f !== opt.value)
                              : [...channelForm.content_formats, opt.value];
                            if (formats.length > 0) setChannelForm({ ...channelForm, content_formats: formats });
                          }}
                          style={{
                            padding: "8px 16px",
                            fontSize: "13px",
                            fontWeight: isActive ? 600 : 400,
                            borderRadius: "var(--cz-radius-full)",
                            backgroundColor: isActive ? `hsl(var(--cz-primary))` : "transparent",
                            color: isActive ? "white" : `hsl(var(--cz-text-secondary))`,
                            border: isActive ? "none" : `1px solid hsl(var(--cz-border))`,
                            cursor: "pointer",
                            transition: "all 0.2s ease",
                          }}
                        >
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Languages — flag pills */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Языки контента
                  </label>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {[
                      { code: "ru", flag: "🇷🇺", label: "RU" },
                      { code: "en", flag: "🇬🇧", label: "EN" },
                      { code: "de", flag: "🇩🇪", label: "DE" },
                      { code: "uk", flag: "🇺🇦", label: "UA" },
                      { code: "es", flag: "🇪🇸", label: "ES" },
                      { code: "fr", flag: "🇫🇷", label: "FR" },
                      { code: "zh", flag: "🇨🇳", label: "ZH" },
                    ].map((lang) => {
                      const isSelected = channelForm.languages.includes(lang.code);
                      return (
                        <button
                          key={lang.code}
                          type="button"
                          onClick={() => {
                            const langs = isSelected
                              ? channelForm.languages.filter((l) => l !== lang.code)
                              : [...channelForm.languages, lang.code];
                            if (langs.length > 0) setChannelForm({ ...channelForm, languages: langs });
                          }}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "6px 14px",
                            fontSize: "13px",
                            fontWeight: isSelected ? 600 : 400,
                            borderRadius: "var(--cz-radius-full)",
                            backgroundColor: isSelected ? `hsl(var(--cz-primary) / 0.15)` : "transparent",
                            color: isSelected ? `hsl(var(--cz-primary))` : `hsl(var(--cz-text-muted))`,
                            border: isSelected ? `1.5px solid hsl(var(--cz-primary))` : `1px solid hsl(var(--cz-border-subtle))`,
                            cursor: "pointer",
                            transition: "all 0.2s ease",
                            transform: isSelected ? "scale(1.05)" : "scale(1)",
                          }}
                        >
                          <span style={{ fontSize: "16px" }}>{lang.flag}</span>
                          {lang.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Tone of voice */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Tone of Voice
                  </label>
                  <p style={{ fontSize: "11px", color: `hsl(var(--cz-text-muted))`, margin: 0 }}>
                    Опишите стиль: формальный / неформальный, с юмором, emoji и т.д.
                  </p>
                  <textarea
                    placeholder="Информативный деловой тон с элементами живого языка. Короткие абзацы, допустимы emoji для акцентов."
                    value={channelForm.tone_of_voice}
                    onChange={(e) => setChannelForm({ ...channelForm, tone_of_voice: e.target.value })}
                    rows={3}
                    className="focus-ring"
                    style={{
                      width: "100%",
                      padding: "12px 16px",
                      fontSize: "13px",
                      fontFamily: "var(--cz-font-sans)",
                      color: `hsl(var(--cz-text-primary))`,
                      backgroundColor: `hsl(var(--cz-bg-input))`,
                      border: `1px solid hsl(var(--cz-border))`,
                      borderRadius: "var(--cz-radius-md)",
                      outline: "none",
                      resize: "vertical",
                      lineHeight: "1.6",
                      transition: "all var(--cz-duration-fast) var(--cz-ease)",
                    }}
                  />
                </div>

                {/* Divider */}
                <div style={{ height: "1px", backgroundColor: `hsl(var(--cz-border-subtle))` }} />

                {/* Actions */}
                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={() => setShowChannelForm(false)}
                    style={{
                      padding: "10px 20px",
                      fontSize: "13px",
                      fontWeight: 500,
                      borderRadius: "var(--cz-radius-md)",
                      backgroundColor: "transparent",
                      color: `hsl(var(--cz-text-muted))`,
                      border: `1px solid hsl(var(--cz-border))`,
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                    }}
                  >
                    Отмена
                  </button>
                  <button
                    type="button"
                    onClick={handleCreateChannel}
                    disabled={!channelForm.name.trim() || channelSaving}
                    style={{
                      padding: "10px 24px",
                      fontSize: "13px",
                      fontWeight: 600,
                      borderRadius: "var(--cz-radius-md)",
                      background: !channelForm.name.trim()
                        ? `hsl(var(--cz-text-muted) / 0.3)`
                        : "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
                      color: "white",
                      border: "none",
                      cursor: !channelForm.name.trim() ? "not-allowed" : "pointer",
                      opacity: channelSaving ? 0.6 : 1,
                      transition: "all 0.2s ease",
                      boxShadow: channelForm.name.trim() ? "0 4px 16px hsl(var(--cz-primary) / 0.3)" : "none",
                    }}
                  >
                    {channelSaving ? "Сохранение..." : "✨ Создать канал"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {channels.length === 0 ? (
            <CzCard>
              <div style={{ textAlign: "center", padding: "48px 24px" }}>
                <Send
                  size={48}
                  style={{
                    color: `hsl(var(--cz-text-muted))`,
                    margin: "0 auto 16px",
                  }}
                />
                <h3
                  style={{
                    fontSize: "16px",
                    fontWeight: 600,
                    color: `hsl(var(--cz-text-secondary))`,
                  }}
                >
                  Нет каналов
                </h3>
                <p
                  style={{
                    fontSize: "13px",
                    color: `hsl(var(--cz-text-muted))`,
                    marginTop: "6px",
                  }}
                >
                  Добавьте Telegram-канал, сайт или YouTube
                </p>
              </div>
            </CzCard>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {channels.map((ch) => {
                const cfg = platformConfig[ch.channel_type];
                const Icon = cfg?.icon || Send;
                const isEditing = editChannelId === ch.id;

                if (isEditing) {
                  // Inline edit form
                  return (
                    <div
                      key={ch.id}
                      className="animate-page-in"
                      style={{
                        padding: "20px",
                        borderRadius: "var(--cz-radius-xl)",
                        backgroundColor: `hsl(var(--cz-bg-surface) / 0.6)`,
                        backdropFilter: "blur(16px)",
                        border: `1px solid hsl(var(--cz-primary) / 0.3)`,
                        boxShadow: "var(--cz-shadow-lg)",
                      }}
                    >
                      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                          <h4 style={{ fontSize: "14px", fontWeight: 600, color: `hsl(var(--cz-text-primary))` }}>
                            ✏️ Редактирование канала
                          </h4>
                          <button
                            onClick={() => setEditChannelId(null)}
                            style={{ background: "none", border: "none", cursor: "pointer", color: `hsl(var(--cz-text-muted))` }}
                          >
                            <X size={16} />
                          </button>
                        </div>

                        {/* Name */}
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>Название</label>
                          <input
                            type="text"
                            value={editChannelForm.name}
                            onChange={(e) => setEditChannelForm({ ...editChannelForm, name: e.target.value })}
                            className="focus-ring"
                            style={{
                              width: "100%", height: "40px", padding: "0 14px", fontSize: "14px",
                              fontFamily: "var(--cz-font-sans)", color: `hsl(var(--cz-text-primary))`,
                              backgroundColor: `hsl(var(--cz-bg-input))`, border: `1px solid hsl(var(--cz-border))`,
                              borderRadius: "var(--cz-radius-md)", outline: "none",
                            }}
                          />
                        </div>

                        {/* Platform cards */}
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>Платформа</label>
                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "6px" }}>
                            {[
                              { value: "telegram", icon: Send, label: "Telegram", color: "var(--cz-info)" },
                              { value: "website", icon: Globe, label: "Сайт", color: "var(--cz-accent)" },
                              { value: "youtube", icon: Video, label: "YouTube", color: "var(--cz-error)" },
                            ].map((opt) => {
                              const isActive = editChannelForm.channel_type === opt.value;
                              return (
                                <button key={opt.value} type="button"
                                  onClick={() => setEditChannelForm({ ...editChannelForm, channel_type: opt.value })}
                                  style={{
                                    display: "flex", flexDirection: "column", alignItems: "center", gap: "6px",
                                    padding: "12px 8px", borderRadius: "var(--cz-radius-lg)",
                                    backgroundColor: isActive ? `hsl(${opt.color} / 0.12)` : `hsl(var(--cz-bg-hover))`,
                                    border: isActive ? `2px solid hsl(${opt.color})` : `1px solid hsl(var(--cz-border-subtle))`,
                                    cursor: "pointer", transition: "all 0.2s ease",
                                  }}
                                >
                                  <opt.icon size={18} style={{ color: isActive ? `hsl(${opt.color})` : `hsl(var(--cz-text-muted))` }} />
                                  <span style={{ fontSize: "11px", fontWeight: isActive ? 600 : 500, color: isActive ? `hsl(${opt.color})` : `hsl(var(--cz-text-secondary))` }}>{opt.label}</span>
                                </button>
                              );
                            })}
                          </div>
                        </div>

                        {/* Content formats */}
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>Форматы контента</label>
                          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                            {[
                              { value: "short_post", label: "📝 Пост" }, { value: "longread", label: "📖 Лонгрид" },
                              { value: "video_script", label: "🎬 Видео" }, { value: "digest", label: "📋 Дайджест" },
                            ].map((opt) => {
                              const isActive = editChannelForm.content_formats.includes(opt.value);
                              return (
                                <button key={opt.value} type="button"
                                  onClick={() => {
                                    const fmts = isActive ? editChannelForm.content_formats.filter(f => f !== opt.value) : [...editChannelForm.content_formats, opt.value];
                                    if (fmts.length > 0) setEditChannelForm({ ...editChannelForm, content_formats: fmts });
                                  }}
                                  style={{
                                    padding: "6px 14px", fontSize: "12px", fontWeight: isActive ? 600 : 400,
                                    borderRadius: "var(--cz-radius-full)",
                                    backgroundColor: isActive ? `hsl(var(--cz-primary))` : "transparent",
                                    color: isActive ? "white" : `hsl(var(--cz-text-secondary))`,
                                    border: isActive ? "none" : `1px solid hsl(var(--cz-border))`,
                                    cursor: "pointer", transition: "all 0.2s ease",
                                  }}
                                >{opt.label}</button>
                              );
                            })}
                          </div>
                        </div>

                        {/* Languages */}
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>Языки</label>
                          <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                            {[
                              { code: "ru", flag: "🇷🇺" }, { code: "en", flag: "🇬🇧" }, { code: "de", flag: "🇩🇪" },
                              { code: "uk", flag: "🇺🇦" }, { code: "es", flag: "🇪🇸" }, { code: "fr", flag: "🇫🇷" }, { code: "zh", flag: "🇨🇳" },
                            ].map((lang) => {
                              const isSel = editChannelForm.languages.includes(lang.code);
                              return (
                                <button key={lang.code} type="button"
                                  onClick={() => {
                                    const ls = isSel ? editChannelForm.languages.filter(l => l !== lang.code) : [...editChannelForm.languages, lang.code];
                                    if (ls.length > 0) setEditChannelForm({ ...editChannelForm, languages: ls });
                                  }}
                                  style={{
                                    display: "flex", alignItems: "center", gap: "4px",
                                    padding: "4px 10px", fontSize: "12px", fontWeight: isSel ? 600 : 400,
                                    borderRadius: "var(--cz-radius-full)",
                                    backgroundColor: isSel ? `hsl(var(--cz-primary) / 0.15)` : "transparent",
                                    color: isSel ? `hsl(var(--cz-primary))` : `hsl(var(--cz-text-muted))`,
                                    border: isSel ? `1.5px solid hsl(var(--cz-primary))` : `1px solid hsl(var(--cz-border-subtle))`,
                                    cursor: "pointer", transition: "all 0.2s ease",
                                  }}
                                ><span style={{ fontSize: "14px" }}>{lang.flag}</span> {lang.code.toUpperCase()}</button>
                              );
                            })}
                          </div>
                        </div>

                        {/* ToV */}
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>Tone of Voice</label>
                          <textarea
                            value={editChannelForm.tone_of_voice}
                            onChange={(e) => setEditChannelForm({ ...editChannelForm, tone_of_voice: e.target.value })}
                            rows={2}
                            className="focus-ring"
                            style={{
                              width: "100%", padding: "10px 14px", fontSize: "13px", fontFamily: "var(--cz-font-sans)",
                              color: `hsl(var(--cz-text-primary))`, backgroundColor: `hsl(var(--cz-bg-input))`,
                              border: `1px solid hsl(var(--cz-border))`, borderRadius: "var(--cz-radius-md)",
                              outline: "none", resize: "vertical", lineHeight: "1.5",
                            }}
                          />
                        </div>

                        {/* Actions */}
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <button
                            onClick={() => handleDeleteChannel(ch.id)}
                            style={{
                              display: "flex", alignItems: "center", gap: "6px",
                              padding: "8px 14px", fontSize: "12px", fontWeight: 500,
                              borderRadius: "var(--cz-radius-md)", backgroundColor: `hsl(var(--cz-error) / 0.1)`,
                              color: `hsl(var(--cz-error))`, border: "none", cursor: "pointer",
                            }}
                          ><Trash2 size={13} /> Удалить</button>
                          <div style={{ display: "flex", gap: "8px" }}>
                            <button onClick={() => setEditChannelId(null)}
                              style={{
                                padding: "8px 16px", fontSize: "12px", fontWeight: 500,
                                borderRadius: "var(--cz-radius-md)", backgroundColor: "transparent",
                                color: `hsl(var(--cz-text-muted))`, border: `1px solid hsl(var(--cz-border))`, cursor: "pointer",
                              }}
                            >Отмена</button>
                            <button onClick={handleSaveChannel} disabled={channelSaving}
                              style={{
                                display: "flex", alignItems: "center", gap: "6px",
                                padding: "8px 18px", fontSize: "12px", fontWeight: 600,
                                borderRadius: "var(--cz-radius-md)",
                                background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
                                color: "white", border: "none", cursor: "pointer",
                                opacity: channelSaving ? 0.6 : 1,
                                boxShadow: "0 4px 16px hsl(var(--cz-primary) / 0.3)",
                              }}
                            ><Save size={13} /> {channelSaving ? "..." : "Сохранить"}</button>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                }

                // Normal channel card
                return (
                  <CzCard key={ch.id} padding="sm">
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "12px",
                        }}
                      >
                        <div
                          style={{
                            width: "36px",
                            height: "36px",
                            borderRadius: "var(--cz-radius-md)",
                            backgroundColor: `hsl(${cfg?.color || "var(--cz-accent)"} / 0.1)`,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          <Icon
                            size={18}
                            style={{
                              color: `hsl(${cfg?.color || "var(--cz-accent)"})`,
                            }}
                          />
                        </div>
                        <div>
                          <div
                            style={{
                              fontSize: "14px",
                              fontWeight: 600,
                              color: `hsl(var(--cz-text-primary))`,
                            }}
                          >
                            {ch.name}
                          </div>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "8px",
                              fontSize: "12px",
                              color: `hsl(var(--cz-text-muted))`,
                              marginTop: "2px",
                            }}
                          >
                            <span>{cfg?.label}</span>
                            <span>·</span>
                            <span>{ch.content_formats.map(f => formatLabels[f] || f).join(", ")}</span>
                            <span>·</span>
                            <span>
                              {ch.languages.map((l) => l.toUpperCase()).join(", ")}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <button
                          onClick={() => startEditChannel(ch)}
                          title="Редактировать"
                          style={{
                            width: "30px", height: "30px", display: "flex", alignItems: "center", justifyContent: "center",
                            borderRadius: "var(--cz-radius-md)", backgroundColor: `hsl(var(--cz-bg-hover))`,
                            border: "none", cursor: "pointer", transition: "all 0.15s ease",
                            color: `hsl(var(--cz-text-muted))`,
                          }}
                        >
                          <Pencil size={14} />
                        </button>
                        <CzBadge variant={ch.is_active ? "success" : "default"}>
                          {ch.is_active ? "Активен" : "Выкл"}
                        </CzBadge>
                      </div>
                    </div>
                    {ch.tone_of_voice && (
                      <div
                        style={{
                          marginTop: "8px",
                          padding: "6px 10px",
                          borderRadius: "var(--cz-radius-sm)",
                          backgroundColor: `hsl(var(--cz-bg-hover))`,
                          fontSize: "12px",
                          color: `hsl(var(--cz-text-muted))`,
                          lineHeight: "1.5",
                        }}
                      >
                        <strong>ToV:</strong> {ch.tone_of_voice}
                      </div>
                    )}
                  </CzCard>
                );
              })}
            </div>
          )}
        </div>
      )}

      {tab === "settings" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div
            className="animate-page-in"
            style={{
              padding: "24px",
              borderRadius: "var(--cz-radius-xl)",
              backgroundColor: `hsl(var(--cz-bg-surface) / 0.6)`,
              backdropFilter: "blur(16px)",
              border: `1px solid hsl(var(--cz-border-subtle))`,
              boxShadow: "var(--cz-shadow-lg), inset 0 1px 0 hsl(var(--cz-border-subtle) / 0.5)",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <h3 style={{ fontSize: "16px", fontWeight: 600, color: `hsl(var(--cz-text-primary))` }}>
                  Настройки проекта
                </h3>
                {!editingProject ? (
                  <button onClick={startEditProject}
                    style={{
                      display: "flex", alignItems: "center", gap: "6px",
                      padding: "8px 16px", fontSize: "12px", fontWeight: 600,
                      borderRadius: "var(--cz-radius-md)",
                      background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
                      color: "white", border: "none", cursor: "pointer",
                      boxShadow: "0 4px 16px hsl(var(--cz-primary) / 0.3)",
                    }}
                  ><Pencil size={13} /> Редактировать</button>
                ) : (
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button onClick={() => setEditingProject(false)}
                      style={{
                        padding: "8px 16px", fontSize: "12px", fontWeight: 500,
                        borderRadius: "var(--cz-radius-md)", backgroundColor: "transparent",
                        color: `hsl(var(--cz-text-muted))`, border: `1px solid hsl(var(--cz-border))`, cursor: "pointer",
                      }}
                    >Отмена</button>
                    <button onClick={handleSaveProject} disabled={projectSaving}
                      style={{
                        display: "flex", alignItems: "center", gap: "6px",
                        padding: "8px 18px", fontSize: "12px", fontWeight: 600,
                        borderRadius: "var(--cz-radius-md)",
                        background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
                        color: "white", border: "none", cursor: "pointer",
                        opacity: projectSaving ? 0.6 : 1,
                        boxShadow: "0 4px 16px hsl(var(--cz-primary) / 0.3)",
                      }}
                    ><Save size={13} /> {projectSaving ? "..." : "Сохранить"}</button>
                  </div>
                )}
              </div>

              {/* Name */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Название проекта
                </label>
                {editingProject ? (
                  <input type="text" value={projectForm.name}
                    onChange={(e) => setProjectForm({ ...projectForm, name: e.target.value })}
                    className="focus-ring"
                    style={{
                      width: "100%", height: "44px", padding: "0 16px", fontSize: "14px",
                      fontFamily: "var(--cz-font-sans)", color: `hsl(var(--cz-text-primary))`,
                      backgroundColor: `hsl(var(--cz-bg-input))`, border: `1px solid hsl(var(--cz-border))`,
                      borderRadius: "var(--cz-radius-md)", outline: "none",
                    }}
                  />
                ) : (
                  <div style={{
                    padding: "10px 16px", borderRadius: "var(--cz-radius-md)",
                    backgroundColor: `hsl(var(--cz-bg-hover))`, fontSize: "14px", fontWeight: 500,
                    color: `hsl(var(--cz-text-primary))`,
                  }}>{project.name}</div>
                )}
              </div>

              {/* Description */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Описание
                </label>
                {editingProject ? (
                  <textarea value={projectForm.description}
                    onChange={(e) => setProjectForm({ ...projectForm, description: e.target.value })}
                    rows={2} className="focus-ring"
                    style={{
                      width: "100%", padding: "12px 16px", fontSize: "13px",
                      fontFamily: "var(--cz-font-sans)", color: `hsl(var(--cz-text-primary))`,
                      backgroundColor: `hsl(var(--cz-bg-input))`, border: `1px solid hsl(var(--cz-border))`,
                      borderRadius: "var(--cz-radius-md)", outline: "none", resize: "vertical", lineHeight: "1.6",
                    }}
                  />
                ) : (
                  <div style={{
                    padding: "10px 16px", borderRadius: "var(--cz-radius-md)",
                    backgroundColor: `hsl(var(--cz-bg-hover))`, fontSize: "13px", lineHeight: "1.6",
                    color: `hsl(var(--cz-text-secondary))`, whiteSpace: "pre-wrap", minHeight: "40px",
                  }}>{project.description || "Не задано"}</div>
                )}
              </div>

              {/* Topic Guidelines */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Тематика (Topic Guidelines)
                </label>
                {editingProject ? (
                  <textarea value={projectForm.topic_guidelines}
                    onChange={(e) => setProjectForm({ ...projectForm, topic_guidelines: e.target.value })}
                    rows={4} className="focus-ring"
                    placeholder="Опишите тематику проекта, ключевые темы, что публикуем и что НЕ публикуем..."
                    style={{
                      width: "100%", padding: "12px 16px", fontSize: "13px",
                      fontFamily: "var(--cz-font-sans)", color: `hsl(var(--cz-text-primary))`,
                      backgroundColor: `hsl(var(--cz-bg-input))`, border: `1px solid hsl(var(--cz-border))`,
                      borderRadius: "var(--cz-radius-md)", outline: "none", resize: "vertical", lineHeight: "1.6",
                    }}
                  />
                ) : (
                  <div style={{
                    padding: "10px 16px", borderRadius: "var(--cz-radius-md)",
                    backgroundColor: `hsl(var(--cz-bg-hover))`, fontSize: "13px", lineHeight: "1.6",
                    color: `hsl(var(--cz-text-secondary))`, whiteSpace: "pre-wrap", minHeight: "60px",
                  }}>{project.topic_guidelines || "Не задано"}</div>
                )}
              </div>

              {/* Target Audience */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ fontSize: "12px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))`, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Целевая аудитория
                </label>
                {editingProject ? (
                  <textarea value={projectForm.target_audience}
                    onChange={(e) => setProjectForm({ ...projectForm, target_audience: e.target.value })}
                    rows={3} className="focus-ring"
                    placeholder="Кто читает? Возраст, интересы, язык, география..."
                    style={{
                      width: "100%", padding: "12px 16px", fontSize: "13px",
                      fontFamily: "var(--cz-font-sans)", color: `hsl(var(--cz-text-primary))`,
                      backgroundColor: `hsl(var(--cz-bg-input))`, border: `1px solid hsl(var(--cz-border))`,
                      borderRadius: "var(--cz-radius-md)", outline: "none", resize: "vertical", lineHeight: "1.6",
                    }}
                  />
                ) : (
                  <div style={{
                    padding: "10px 16px", borderRadius: "var(--cz-radius-md)",
                    backgroundColor: `hsl(var(--cz-bg-hover))`, fontSize: "13px", lineHeight: "1.6",
                    color: `hsl(var(--cz-text-secondary))`, whiteSpace: "pre-wrap", minHeight: "40px",
                  }}>{project.target_audience || "Не задано"}</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
