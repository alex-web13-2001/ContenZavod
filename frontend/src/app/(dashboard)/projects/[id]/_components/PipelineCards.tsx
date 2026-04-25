"use client";
import React from "react";
import { ExternalLink, Sparkles, Zap, Check, X, ArrowRight, RotateCcw, Eye, Heart, MessageCircle, Image, Clock, Send } from "lucide-react";
import { CzCard, CzBadge, CzButton } from "@/components/ui-system";
import { Material, categoryLabels, formatLabels, renderMarkdownToHtml } from "./types";

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

/* ═══ 1. INBOX CARD — clean, no adaptations ═══ */
export function InboxCard({ m, onTake, onReject }: {
  m: Material;
  onTake: (id: string) => void;
  onReject: (id: string) => void;
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

/* ═══ 2. PUBLISHED CARD — shows each post per channel/language ═══ */
const LANG_FLAGS: Record<string, string> = {
  ru: "🇷🇺", en: "🇬🇧", el: "🇬🇷", de: "🇩🇪", uk: "🇺🇦", es: "🇪🇸", fr: "🇫🇷", zh: "🇨🇳",
};

const CHANNEL_TYPE_ICONS: Record<string, { icon: string; color: string }> = {
  telegram: { icon: "✈️", color: "var(--cz-info)" },
  website: { icon: "🌐", color: "var(--cz-accent)" },
  youtube: { icon: "▶️", color: "var(--cz-error)" },
};

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
  comments: number | null;
}

/** Individual Telegram-style post preview */
function PostCard({ post }: { post: PublishedPost }) {
  const chType = CHANNEL_TYPE_ICONS[post.channel_type] || CHANNEL_TYPE_ICONS.telegram;
  const pubTime = post.published_at
    ? new Date(post.published_at).toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div style={{
      borderRadius: 12,
      overflow: "hidden",
      border: "1px solid hsl(var(--cz-border) / 0.4)",
      backgroundColor: "hsl(var(--cz-bg-base) / 0.5)",
    }}>
      {/* Channel header bar */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 16px",
        background: `linear-gradient(135deg, hsl(${chType.color} / 0.08), hsl(${chType.color} / 0.03))`,
        borderBottom: "1px solid hsl(var(--cz-border) / 0.3)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16 }}>{chType.icon}</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: "hsl(var(--cz-text-primary))" }}>
            {post.channel_name || "Канал"}
          </span>
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 4,
            padding: "2px 8px", borderRadius: 5, fontSize: 12, fontWeight: 700,
            backgroundColor: `hsl(${chType.color} / 0.12)`,
            color: `hsl(${chType.color})`,
          }}>
            {LANG_FLAGS[post.lang] || "🏳️"} {post.lang.toUpperCase()}
          </span>
          {post.format && (
            <span style={{
              display: "inline-flex", alignItems: "center",
              padding: "2px 8px", borderRadius: 5, fontSize: 11, fontWeight: 600,
              backgroundColor: "hsl(var(--cz-accent) / 0.1)",
              color: "hsl(var(--cz-accent))",
              textTransform: "uppercase", letterSpacing: "0.03em",
            }}>
              {formatLabels[post.format] || post.format}
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {pubTime && (
            <span style={{ fontSize: 11, color: "hsl(var(--cz-text-muted))" }}>
              {pubTime}
            </span>
          )}
          {post.platform_post_id && (
            <span style={{ fontSize: 10, color: "hsl(var(--cz-text-muted))", fontFamily: "monospace" }}>
              #{post.platform_post_id}
            </span>
          )}
        </div>
      </div>

      {/* Post body — Telegram style */}
      {post.body && (
        <div style={{
          padding: "14px 16px",
          fontSize: 14, lineHeight: 1.65,
          color: "hsl(var(--cz-text-secondary))",
          maxHeight: 250, overflowY: "auto",
        }} dangerouslySetInnerHTML={{ __html: renderMarkdownToHtml(post.body) }} />
      )}

      {/* Stats footer */}
      <div style={{
        display: "flex", alignItems: "center", gap: 16,
        padding: "8px 16px",
        borderTop: "1px solid hsl(var(--cz-border) / 0.2)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, color: "hsl(var(--cz-text-muted))" }}>
          <Eye size={14} />
          <span style={{ fontWeight: 600 }}>{post.views ?? "—"}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, color: "hsl(var(--cz-text-muted))" }}>
          <Heart size={14} />
          <span style={{ fontWeight: 600 }}>{post.reactions ?? "—"}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13, color: "hsl(var(--cz-text-muted))" }}>
          <MessageCircle size={14} />
          <span style={{ fontWeight: 600 }}>{post.comments ?? "—"}</span>
        </div>
      </div>
    </div>
  );
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
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {posts.map((post, i) => (
            <PostCard key={post.adaptation_id || i} post={post} />
          ))}
        </div>
      ) : (
        <p style={{ margin: 0, fontSize: 14, color: "hsl(var(--cz-text-muted))" }}>
          {m.summary_ru || "Пост опубликован"}
        </p>
      )}

      {/* TODO: Adapt button — add more language versions */}
    </CzCard>
  );
}

/* ═══ 3. REJECTED CARD — minimal ═══ */
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

/* ═══ 4. IN_PROGRESS CARD header ═══ */
export function InProgressCardHeader({ m }: { m: Material }) {
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
        {/* Placeholders */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 12px", borderRadius: 7, border: "1px dashed hsl(var(--cz-border) / 0.5)", color: "hsl(var(--cz-text-muted))", fontSize: 11 }}>
          <Image size={13} /> Картинка
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 12px", borderRadius: 7, border: "1px dashed hsl(var(--cz-border) / 0.5)", color: "hsl(var(--cz-text-muted))", fontSize: 11 }}>
          <Clock size={13} /> Расписание
        </div>
      </div>
    </>
  );
}
