"use client";
import React from "react";
import { ExternalLink, Sparkles, Zap, Check, X, ArrowRight, RotateCcw, Eye, Heart, Share2, MessageCircle, Image, Clock, Send } from "lucide-react";
import { CzCard, CzBadge, CzButton } from "@/components/ui-system";
import { Material, Adaptation, categoryLabels, formatLabels, renderMarkdownToHtml } from "./types";

/* ═══ Shared: date formatter ═══ */
function RelativeDate({ iso }: { iso: string }) {
  const d = new Date(iso);
  const now = new Date();
  const diffH = Math.floor((now.getTime() - d.getTime()) / 3600000);
  const isToday = d.toDateString() === now.toDateString();
  const isYesterday = d.toDateString() === new Date(now.getTime() - 86400000).toDateString();
  const text = isToday ? `Сегодня, ${d.toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" })}`
    : isYesterday ? `Вчера, ${d.toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" })}`
    : d.toLocaleDateString("ru", { day: "numeric", month: "long", year: "numeric" });
  return (
    <span style={{ fontSize: 15, fontWeight: 700, color: diffH < 6 ? "hsl(var(--cz-accent))" : "hsl(var(--cz-text-secondary))" }}>
      🕐 {text}
    </span>
  );
}

/** Resolve best Russian title: headline_ru → summary_ru first sentence → material_title */
function resolveTitle(m: Material): string {
  if (m.headline_ru) return m.headline_ru;
  if (m.summary_ru) {
    // First sentence as fallback title
    const first = m.summary_ru.split(/[.!?]/)[0]?.trim();
    if (first && first.length > 10) return first;
  }
  return m.material_title || "Без заголовка";
}

function ScoreBar({ score, maxScore = 10 }: { score: number; maxScore?: number }) {
  const pct = (score / maxScore) * 100;
  const color = pct >= 80 ? "var(--cz-success)" : pct >= 50 ? "var(--cz-warning)" : "var(--cz-text-muted)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ width: 50, height: 5, borderRadius: 3, backgroundColor: `hsl(${color} / 0.15)`, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", borderRadius: 3, backgroundColor: `hsl(${color})`, transition: "width 0.5s ease" }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, color: `hsl(${color})`, minWidth: 20 }}>{score}</span>
    </div>
  );
}

/* ═══ Language flags & helpers ═══ */
const LANG_FLAGS: Record<string, string> = {
  ru: "🇷🇺", en: "🇬🇧", el: "🇬🇷", de: "🇩🇪", uk: "🇺🇦", es: "🇪🇸", fr: "🇫🇷", zh: "🇨🇳",
};

const LANG_LABELS: Record<string, string> = {
  ru: "Русский", en: "English", el: "Ελληνικά", de: "Deutsch", uk: "Українська", es: "Español", fr: "Français", zh: "中文",
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010/api/v1";

/** Format stats number: 0→"—", 1200→"1.2K", etc. */
function formatStat(n: number | null | undefined): string {
  if (n == null || n === 0) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

/* ═══ 1. INBOX CARD — clean, no adaptations ═══ */
export function InboxCard({ m, onTake, onReject, onAutopilot }: {
  m: Material;
  onTake: (id: string) => void;
  onReject: (id: string) => void;
  /** Optional: open "send to autopilot" dialog for this material. */
  onAutopilot?: (id: string) => void;
}) {
  const cat = m.category ? categoryLabels[m.category] : null;
  const title = resolveTitle(m);
  return (
    <CzCard padding="lg">
      {/* Date + badges */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <RelativeDate iso={m.created_at} />
          {cat && <span style={{ padding: "3px 10px", fontSize: 12, fontWeight: 600, borderRadius: 6, backgroundColor: "hsl(var(--cz-bg-surface))", color: "hsl(var(--cz-text-secondary))" }}>{cat.emoji} {cat.label}</span>}
          {m.is_breaking && <CzBadge variant="error"><Zap size={12} /> Срочно</CzBadge>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {m.relevance_score != null && <div style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ fontSize: 11, color: "hsl(var(--cz-text-muted))" }}>Рел.</span><ScoreBar score={m.relevance_score} /></div>}
          {m.hype_score != null && <div style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ fontSize: 11, color: "hsl(var(--cz-text-muted))" }}>Хайп</span><ScoreBar score={m.hype_score} /></div>}
        </div>
      </div>

      {/* Headline + lead */}
      <h3 style={{ margin: "0 0 6px 0", fontSize: 22, fontWeight: 800, lineHeight: 1.3, color: "hsl(var(--cz-text-primary))" }}>
        {m.is_breaking && <span style={{ color: "hsl(var(--cz-error))" }}>⚡ </span>}
        {title}
      </h3>
      {m.summary_ru && <p style={{ margin: "0 0 10px 0", fontSize: 15, lineHeight: 1.55, color: "hsl(var(--cz-text-secondary))" }}>{m.summary_ru}</p>}

      {/* AI rationale */}
      {m.explanation && (
        <details style={{ marginBottom: 14, borderRadius: 10, backgroundColor: "hsl(var(--cz-success) / 0.06)", border: "1px solid hsl(var(--cz-success) / 0.15)" }}>
          <summary style={{ padding: "10px 16px", cursor: "pointer", fontSize: 13, fontWeight: 700, color: "hsl(var(--cz-success))", listStyle: "none", display: "flex", alignItems: "center", gap: 6 }}>
            🤖 Почему подходит <span style={{ marginLeft: "auto", fontSize: 11, opacity: 0.6 }}>▼</span>
          </summary>
          <div style={{ padding: "0 16px 12px", fontSize: 14, lineHeight: 1.65, color: "hsl(var(--cz-text-secondary))" }}>{m.explanation}</div>
        </details>
      )}

      {/* Source link + action buttons — proper flex layout */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10, paddingTop: 4 }}>
        <a href={m.material_url || "#"} target="_blank" rel="noopener noreferrer" className="cz-link-pill" style={{ fontSize: 12 }}>
          <ExternalLink size={12} /> Источник
        </a>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button onClick={() => onReject(m.id)} style={{
            display: "flex", alignItems: "center", gap: 5, padding: "8px 16px", borderRadius: 8,
            border: "1px solid hsl(var(--cz-border) / 0.5)", cursor: "pointer", fontSize: 13, fontWeight: 600,
            backgroundColor: "transparent", color: "hsl(var(--cz-text-muted))",
          }}><X size={14} /> Отклонить</button>
          {onAutopilot && (
            <button onClick={() => onAutopilot(m.id)} style={{
              display: "flex", alignItems: "center", gap: 5, padding: "8px 16px", borderRadius: 8,
              border: "1px solid hsl(var(--cz-warning) / 0.4)", cursor: "pointer", fontSize: 13, fontWeight: 700,
              backgroundColor: "hsl(var(--cz-warning) / 0.08)", color: "hsl(var(--cz-warning))",
            }} title="Поставить в очередь автопилота"><Zap size={14} /> В автопилот</button>
          )}
          <button onClick={() => onTake(m.id)} style={{
            display: "flex", alignItems: "center", gap: 5, padding: "8px 18px", borderRadius: 8,
            border: "none", cursor: "pointer", fontSize: 13, fontWeight: 700,
            backgroundColor: "hsl(var(--cz-primary))", color: "white",
          }}><ArrowRight size={14} /> Взять в работу</button>
        </div>
      </div>
    </CzCard>
  );
}


/* ═══ 2. LANGUAGE POST CARD — Telegram-style preview per language ═══ */

interface LanguagePostCardProps {
  ad: Adaptation;
  mode: "in_progress" | "published";
  onGenerateCover?: (adaptationId: string) => void;
  generatingCover?: boolean;
  onAction?: (id: string, action: "approved" | "rejected") => void;
  stats?: { views?: number | null; reactions?: number | null; forwards?: number | null; comments?: number | null };
}

export function LanguagePostCard({ ad, mode, onGenerateCover, generatingCover, onAction, stats }: LanguagePostCardProps) {
  const flag = LANG_FLAGS[ad.language] || "🏳️";
  const langLabel = LANG_LABELS[ad.language] || ad.language.toUpperCase();
  const coverStatus = generatingCover ? "generating" : ad.cover_status;
  const coverUrl = ad.cover_image_url;

  // Status badge config
  const STATUS_UI: Record<string, { bg: string; color: string; label: string; pulse?: boolean }> = {
    draft: { bg: "hsl(var(--cz-warning) / 0.12)", color: "hsl(var(--cz-warning))", label: "Черновик" },
    approved: { bg: "hsl(var(--cz-accent) / 0.15)", color: "hsl(var(--cz-accent))", label: "⏳ Публикуется...", pulse: true },
    published: { bg: "hsl(var(--cz-success) / 0.12)", color: "hsl(var(--cz-success))", label: "✅ Опубликовано" },
    rejected: { bg: "hsl(var(--cz-error) / 0.12)", color: "hsl(var(--cz-error))", label: "Отклонён" },
  };
  const sui = STATUS_UI[ad.status] || STATUS_UI.draft;

  return (
    <div style={{
      borderRadius: 14, overflow: "hidden",
      border: "1px solid hsl(var(--cz-border) / 0.5)",
      backgroundColor: "hsl(var(--cz-bg-surface))",
      opacity: ad.status === "rejected" ? 0.5 : 1,
      transition: "all 0.3s ease",
    }}>
      {/* ── Language header bar ── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 16px",
        background: "linear-gradient(135deg, hsl(var(--cz-accent) / 0.06), hsl(var(--cz-bg-surface)))",
        borderBottom: "1px solid hsl(var(--cz-border) / 0.3)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 18 }}>{flag}</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: "hsl(var(--cz-text-primary))" }}>{langLabel}</span>
          {ad.channel_name && (
            <span style={{ fontSize: 12, color: "hsl(var(--cz-text-muted))" }}>• {ad.channel_name}</span>
          )}
          <span style={{
            padding: "2px 8px", borderRadius: 5, fontSize: 11, fontWeight: 700,
            backgroundColor: "hsl(var(--cz-info) / 0.1)", color: "hsl(var(--cz-info))",
          }}>
            {formatLabels[ad.content_format] || ad.content_format}
          </span>
        </div>
        <span style={{
          padding: "3px 10px", fontSize: 11, fontWeight: 700, borderRadius: 6,
          backgroundColor: sui.bg, color: sui.color,
          animation: sui.pulse ? "cz-pulse 1.5s ease-in-out infinite" : undefined,
        }}>{sui.label}</span>
      </div>

      {/* ── Cover Image area ── */}
      {coverStatus === "ready" && coverUrl ? (
        <div style={{ aspectRatio: "16/9", maxHeight: 220, overflow: "hidden", position: "relative" }}>
          <img
            src={`${API_URL}${coverUrl.startsWith("/api/v1") ? coverUrl.replace("/api/v1", "") : coverUrl}`}
            alt={ad.headline}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        </div>
      ) : coverStatus === "generating" ? (
        <div style={{
          aspectRatio: "16/9", maxHeight: 220,
          backgroundColor: "hsl(var(--cz-bg-base) / 0.7)",
          border: "none",
          display: "flex", alignItems: "center", justifyContent: "center",
          animation: "cz-pulse 2s ease-in-out infinite",
        }}>
          <div style={{ textAlign: "center" }}>
            <Sparkles size={24} style={{ color: "hsl(var(--cz-accent))", marginBottom: 6 }} />
            <div style={{ fontSize: 12, fontWeight: 600, color: "hsl(var(--cz-text-muted))" }}>
              🎨 AI генерирует обложку...
            </div>
          </div>
        </div>
      ) : (
        /* Placeholder with generate button */
        <div
          style={{
            aspectRatio: "16/9", maxHeight: 180,
            backgroundColor: "hsl(var(--cz-bg-base) / 0.4)",
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: mode === "in_progress" && ad.status !== "rejected" ? "pointer" : "default",
            transition: "background-color 0.2s ease",
          }}
          onClick={() => {
            if (mode === "in_progress" && ad.status !== "rejected" && coverStatus !== "error") {
              onGenerateCover?.(ad.id);
            }
          }}
          onMouseEnter={(e) => {
            if (mode === "in_progress") e.currentTarget.style.backgroundColor = "hsl(var(--cz-accent) / 0.06)";
          }}
          onMouseLeave={(e) => {
            if (mode === "in_progress") e.currentTarget.style.backgroundColor = "hsl(var(--cz-bg-base) / 0.4)";
          }}
        >
          <div style={{ textAlign: "center" }}>
            <Image size={28} style={{ color: "hsl(var(--cz-text-muted))", marginBottom: 6, opacity: 0.4 }} />
            {coverStatus === "error" ? (
              <button
                onClick={(e) => { e.stopPropagation(); onGenerateCover?.(ad.id); }}
                style={{
                  display: "flex", alignItems: "center", gap: 5, padding: "6px 14px", borderRadius: 7,
                  border: "1px solid hsl(var(--cz-error) / 0.5)", cursor: "pointer", fontSize: 12,
                  fontWeight: 700, backgroundColor: "hsl(var(--cz-error) / 0.08)", color: "hsl(var(--cz-error))",
                }}
              >
                <X size={12} /> Ошибка — повторить
              </button>
            ) : mode === "in_progress" && ad.status !== "rejected" ? (
              <div style={{ fontSize: 12, fontWeight: 600, color: "hsl(var(--cz-accent))", opacity: 0.7 }}>
                🎨 Сгенерировать обложку
              </div>
            ) : (
              <div style={{ fontSize: 12, color: "hsl(var(--cz-text-muted))", opacity: 0.4 }}>
                Нет обложки
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Post content: headline + body ── */}
      <div style={{ padding: "14px 16px" }}>
        {ad.headline && (
          <div style={{
            fontSize: 15, fontWeight: 700, lineHeight: 1.35,
            color: "hsl(var(--cz-text-primary))", marginBottom: 8,
          }}>
            {ad.headline}
          </div>
        )}
        {ad.body && (
          <div
            style={{
              fontSize: 13, lineHeight: 1.6,
              color: "hsl(var(--cz-text-secondary))",
              maxHeight: 140, overflowY: "auto",
            }}
            dangerouslySetInnerHTML={{ __html: renderMarkdownToHtml(ad.body) }}
          />
        )}
      </div>

      {/* ── Action / Stats footer ── */}
      {mode === "in_progress" && ad.status === "draft" && onAction && (
        <div style={{
          display: "flex", justifyContent: "flex-end", gap: 8,
          padding: "8px 16px 12px",
          borderTop: "1px solid hsl(var(--cz-border) / 0.2)",
        }}>
          <button onClick={() => onAction(ad.id, "rejected")} style={{
            display: "flex", alignItems: "center", gap: 4, padding: "5px 12px", borderRadius: 7,
            border: "1px solid hsl(var(--cz-border) / 0.5)", cursor: "pointer", fontSize: 12, fontWeight: 600,
            backgroundColor: "transparent", color: "hsl(var(--cz-text-muted))",
          }}><X size={12} /> Отклонить</button>
        </div>
      )}

      {mode === "published" && stats && (
        <div style={{
          display: "flex", alignItems: "center", gap: 14,
          padding: "8px 16px 12px",
          borderTop: "1px solid hsl(var(--cz-border) / 0.2)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, color: "hsl(var(--cz-text-muted))" }}>
            <Eye size={14} />
            <span style={{ fontWeight: 600 }}>{formatStat(stats.views)}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, color: "hsl(var(--cz-text-muted))" }}>
            <Heart size={14} />
            <span style={{ fontWeight: 600 }}>{formatStat(stats.reactions)}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, color: "hsl(var(--cz-text-muted))" }}>
            <MessageCircle size={14} />
            <span style={{ fontWeight: 600 }}>{formatStat(stats.comments)}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, color: "hsl(var(--cz-text-muted))" }}>
            <Share2 size={14} />
            <span style={{ fontWeight: 600 }}>{formatStat(stats.forwards)}</span>
          </div>
        </div>
      )}
    </div>
  );
}


/* ═══ 3. PUBLISHED CARD — news header + language post cards ═══ */

interface PublishedPost {
  adaptation_id: string;
  lang: string;
  format: string;
  headline: string;
  body: string;
  channel_name: string;
  channel_type: string;
  published_at: string | null;
  platform_post_id: string | null;
  views: number | null;
  reactions: number | null;
  forwards: number | null;
  comments: number | null;
  cover_image_url?: string | null;
  cover_status?: string | null;
}

export function PublishedCard({ m }: { m: Material }) {
  const cat = m.category ? categoryLabels[m.category] : null;
  const pubDate = m.published_at
    ? new Date(m.published_at).toLocaleDateString("ru", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
    : null;
  // Always Russian title
  const title = resolveTitle(m);

  // Get published posts from backend
  const posts: PublishedPost[] = (m as any).published_posts || [];

  return (
    <CzCard padding="lg">
      {/* Material header: date + category */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8, flexWrap: "wrap" }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: "hsl(var(--cz-success))" }}>
          ✅ {pubDate || "Опубликовано"}
        </span>
        {cat && <span style={{ fontSize: 12, color: "hsl(var(--cz-text-muted))" }}>{cat.emoji} {cat.label}</span>}
        <span style={{ fontSize: 12, color: "hsl(var(--cz-text-muted))", marginLeft: "auto" }}>
          {posts.length} {posts.length === 1 ? "пост" : posts.length < 5 ? "поста" : "постов"}
        </span>
      </div>

      {/* Russian title — always */}
      <h3 style={{ margin: "0 0 14px 0", fontSize: 22, fontWeight: 800, lineHeight: 1.3, color: "hsl(var(--cz-text-primary))" }}>
        {title}
      </h3>

      {/* Individual post cards */}
      {posts.length > 0 ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 14 }}>
          {posts.map((post, i) => {
            // Convert published post to Adaptation-like object for LanguagePostCard
            const fakeAd: Adaptation = {
              id: post.adaptation_id || `post-${i}`,
              material_id: m.material_id || m.id,
              channel_id: "",
              language: post.lang,
              content_format: post.format,
              headline: post.headline,
              body: post.body,
              priority: "normal",
              status: "published",
              created_at: post.published_at || m.created_at,
              material_title: m.material_title,
              channel_name: post.channel_name,
              channel_type: post.channel_type,
              cover_image_url: post.cover_image_url || null,
              cover_status: post.cover_status || null,
            };
            return (
              <LanguagePostCard
                key={post.adaptation_id || i}
                ad={fakeAd}
                mode="published"
                stats={{
                  views: post.views,
                  reactions: post.reactions,
                  comments: post.comments,
                }}
              />
            );
          })}
        </div>
      ) : (
        <p style={{ margin: 0, fontSize: 14, color: "hsl(var(--cz-text-muted))" }}>
          {m.summary_ru || "Пост опубликован"}
        </p>
      )}
    </CzCard>
  );
}

/* ═══ 4. REJECTED CARD — minimal ═══ */
export function RejectedCard({ m, onRestore }: { m: Material; onRestore: (id: string) => void }) {
  const d = new Date(m.created_at).toLocaleDateString("ru", { day: "numeric", month: "short" });
  const cat = m.category ? categoryLabels[m.category] : null;
  const title = resolveTitle(m);
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 18px",
      borderRadius: 10, backgroundColor: "hsl(var(--cz-bg-surface))", border: "1px solid hsl(var(--cz-border) / 0.3)",
      opacity: 0.7, transition: "opacity 0.2s",
    }}
      onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
      onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.7")}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0, flex: 1 }}>
        <span style={{ fontSize: 12, color: "hsl(var(--cz-text-muted))", flexShrink: 0 }}>{d}</span>
        {cat && <span style={{ fontSize: 11 }}>{cat.emoji}</span>}
        <span style={{ fontSize: 14, fontWeight: 600, color: "hsl(var(--cz-text-secondary))", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {title}
        </span>
      </div>
      <button onClick={() => onRestore(m.id)} style={{
        display: "flex", alignItems: "center", gap: 5, padding: "6px 14px", borderRadius: 7,
        border: "1px solid hsl(var(--cz-border) / 0.5)", cursor: "pointer", fontSize: 12, fontWeight: 600,
        backgroundColor: "transparent", color: "hsl(var(--cz-text-muted))", flexShrink: 0,
      }}>
        <RotateCcw size={12} /> Вернуть
      </button>
    </div>
  );
}

/* ═══ 5. IN_PROGRESS CARD header — news meta only (no cover here) ═══ */
export function InProgressCardHeader({ m }: {
  m: Material;
}) {
  const cat = m.category ? categoryLabels[m.category] : null;
  const title = resolveTitle(m);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <RelativeDate iso={m.created_at} />
          {cat && <span style={{ padding: "3px 10px", fontSize: 12, fontWeight: 600, borderRadius: 6, backgroundColor: "hsl(var(--cz-bg-surface))", color: "hsl(var(--cz-text-secondary))" }}>{cat.emoji} {cat.label}</span>}
          {m.is_breaking && <CzBadge variant="error"><Zap size={12} /> Срочно</CzBadge>}
        </div>
      </div>
      <h3 style={{ margin: "0 0 6px 0", fontSize: 22, fontWeight: 800, lineHeight: 1.3, color: "hsl(var(--cz-text-primary))" }}>
        {m.is_breaking && <span style={{ color: "hsl(var(--cz-error))" }}>⚡ </span>}
        {title}
      </h3>
      {m.summary_ru && <p style={{ margin: "0 0 10px 0", fontSize: 15, lineHeight: 1.55, color: "hsl(var(--cz-text-secondary))" }}>{m.summary_ru}</p>}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
        <a href={m.material_url || "#"} target="_blank" rel="noopener noreferrer" className="cz-link-pill" style={{ fontSize: 12 }}>
          <ExternalLink size={12} /> Источник
        </a>
        <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 12px", borderRadius: 7, border: "1px dashed hsl(var(--cz-border) / 0.5)", color: "hsl(var(--cz-text-muted))", fontSize: 11 }}>
          <Clock size={13} /> Расписание
        </div>
      </div>
    </>
  );
}
