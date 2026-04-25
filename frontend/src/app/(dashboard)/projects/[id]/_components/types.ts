import { Send, Globe, Video } from "lucide-react";

export interface Project {
  id: string;
  name: string;
  description: string;
  topic_guidelines: string;
  target_audience: string;
  is_active: boolean;
}

export interface Channel {
  id: string;
  name: string;
  channel_type: string;
  content_formats: string[];
  tone_of_voice: string;
  formatting_rules: string;
  languages: string[];
  is_active: boolean;
  config?: { bot_token?: string; chat_id?: string };
}

export interface Material {
  id: string;
  material_id: string;
  material_title: string | null;
  headline_ru?: string | null;
  material_url: string | null;
  material_status: string | null;
  relevance_score: number;
  hype_score: number;
  is_recommended: boolean;
  explanation: string;
  editorial_status: string;
  created_at: string;
  title?: string;
  original_url?: string;
  category?: string | null;
  tags?: string[];
  summary_ru?: string | null;
  is_breaking?: boolean;
  cover_image_url?: string | null;
  cover_status?: string | null;
  published_at?: string | null;
  platform_post_id?: string | null;
  published_headline?: string | null;
  published_body?: string | null;
  published_language?: string | null;
  published_format?: string | null;
  project_relevance_score?: number | null;
  project_hype_score?: number | null;
  project_explanation?: string | null;
}

export interface PipelineCounts {
  inbox: number;
  in_progress: number;
  published: number;
  rejected: number;
}

export interface Adaptation {
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

export const platformConfig: Record<string, { icon: typeof Send; label: string; color: string }> = {
  telegram: { icon: Send, label: "Telegram", color: "var(--cz-info)" },
  website: { icon: Globe, label: "Сайт", color: "var(--cz-accent)" },
  youtube: { icon: Video, label: "YouTube", color: "var(--cz-error)" },
};

export const formatLabels: Record<string, string> = {
  short_post: "Пост",
  longread: "Лонгрид",
  video_script: "Видео-скрипт",
  digest: "Дайджест",
};

export const categoryLabels: Record<string, { label: string; emoji: string }> = {
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

/** Lightweight markdown→HTML for AI-generated adaptation text */
export function renderMarkdownToHtml(text: string): string {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    .replace(/(?<![\\w*])\*([^*]+?)\*(?![\\w*])/g, "<em>$1</em>")
    .replace(/(?<!\\w)_([^_]+?)_(?!\\w)/g, "<em>$1</em>")
    .replace(/^#{1,3}\s+(.+)$/gm, '<strong style="display:block;margin:8px 0 4px">$1</strong>')
    .replace(/^\[([A-ZА-ЯЁa-zа-яё][A-ZА-ЯЁa-zа-яё\s\-:0-9]+)\]$/gm, '<strong style="display:block;margin:12px 0 4px;font-size:0.9em;color:hsl(var(--cz-text-muted))">$1</strong>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" style="color:hsl(var(--cz-accent));text-decoration:underline">$1</a>')
    .replace(/\n/g, "<br/>");
}
