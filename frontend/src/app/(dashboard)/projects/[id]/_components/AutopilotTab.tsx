"use client";

import React, { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { CzButton, CzBadge, useToast } from "@/components/ui-system";
import {
  Bot,
  Play,
  Pause,
  Settings2,
  Clock,
  CheckCircle2,
  XCircle,
  Zap,
  Image,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Loader2,
  Eye,
  ShieldCheck,
  Timer,
  BarChart3,
  AlertTriangle,
} from "lucide-react";

/* ── Types ── */

interface AutopilotChannelConfig {
  channel_id: string;
  channel_name: string;
  languages: string[];
  content_formats: string[];
  autopilot: {
    enabled: boolean;
    shadow_mode: boolean;
    max_posts_per_day: number;
    min_interval_minutes: number;
    min_score_threshold: number;
    cover_policy: string;
    schedule_slots: string[];
    strategies: string[];
    category_limits: Record<string, number>;
    ttl_hours: Record<string, number>;
    language_settings: Record<string, {
      max_posts_per_day?: number;
      min_interval_minutes?: number;
      min_score_threshold?: number;
    }>;
    format_ratios: Record<string, number>;
    longread_max_per_day: number;
    max_material_age_hours: number;
  };
}

interface QueueItem {
  id: string;
  channel_id: string;
  channel_name: string;
  adaptation_id: string;
  language: string;
  headline: string;
  body_preview: string;
  body: string;
  content_format: string;
  cover_status: string | null;
  cover_image_url: string | null;
  strategy: string;
  final_score: number;
  freshness_score: number;
  status: string;
  scheduled_at: string | null;
  created_at: string;
  material_published_at: string | null;
  material_scraped_at: string | null;
}

interface AutopilotStats {
  today: Record<string, number>;
  published_today: number;
  queued: number;
  shadow_pending: number;
  format_counts: Record<string, number>;
  next_scheduled: {
    id: string;
    scheduled_at: string;
    strategy: string;
    score: number;
  } | null;
}

interface Props {
  projectId: string;
}

const SLOT_LABELS: Record<string, string> = {
  morning: "🌅 Утро (08–09)",
  lunch: "☀️ Обед (12–13)",
  evening: "🌆 Вечер (18–19)",
  night: "🌙 Ночь (21–22)",
};

const COVER_LABELS: Record<string, string> = {
  short_post_optional: "Short без обложки",
  always_required: "Всегда с обложкой",
  never: "Без обложек",
};

const FORMAT_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  flash: { label: "Молния", icon: "⚡", color: "var(--cz-warning)" },
  short_post: { label: "Стандарт", icon: "📝", color: "var(--cz-info)" },
  longread: { label: "Лонгрид", icon: "📊", color: "var(--cz-success)" },
};

const STRATEGY_LABELS: Record<string, { label: string; icon: React.ReactNode }> = {
  smart_queue: { label: "Smart Queue", icon: <BarChart3 size={12} /> },
  express: { label: "Express", icon: <Zap size={12} /> },
};

const LANG_LABELS: Record<string, { flag: string; name: string }> = {
  ru: { flag: "🇷🇺", name: "Русский" },
  en: { flag: "🇬🇧", name: "English" },
  el: { flag: "🇬🇷", name: "Ελληνικά" },
  tr: { flag: "🇹🇷", name: "Türkçe" },
  de: { flag: "🇩🇪", name: "Deutsch" },
  fr: { flag: "🇫🇷", name: "Français" },
};

/* ── Component ── */

export function AutopilotTab({ projectId }: Props) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [configs, setConfigs] = useState<AutopilotChannelConfig[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [stats, setStats] = useState<AutopilotStats | null>(null);
  const [expandedChannel, setExpandedChannel] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  /* ── Fetch data ── */
  const fetchAll = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [cfgRes, queueRes, statsRes] = await Promise.all([
        api.get<{ channels: AutopilotChannelConfig[] }>(`/projects/${projectId}/autopilot/config`),
        api.get<{ items: QueueItem[] }>(`/projects/${projectId}/autopilot/queue`),
        api.get<AutopilotStats>(`/projects/${projectId}/autopilot/stats`),
      ]);
      setConfigs(cfgRes.channels);
      setQueue(queueRes.items);
      setStats(statsRes);
    } catch (e) {
      console.error("Autopilot fetch error:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleRefresh = () => { setRefreshing(true); fetchAll(true); };

  /* ── Config update ── */
  const updateConfig = async (channelId: string, updates: Record<string, unknown>) => {
    setSaving(channelId);
    try {
      await api.put(`/projects/${projectId}/autopilot/config`, {
        channel_id: channelId,
        ...updates,
      });
      showToast("Настройки сохранены", "success");
      fetchAll(true);
    } catch (e) {
      showToast("Ошибка сохранения", "error");
      console.error(e);
    } finally {
      setSaving(null);
    }
  };

  /* ── Queue actions ── */
  const approveItem = async (queueItemId: string) => {
    setActionLoading(queueItemId);
    try {
      await api.post(`/projects/${projectId}/autopilot/approve`, { queue_item_id: queueItemId });
      showToast("Одобрено → будет опубликовано", "success");
      fetchAll(true);
    } catch (e) {
      showToast("Ошибка одобрения", "error");
      console.error(e);
    } finally {
      setActionLoading(null);
    }
  };

  const rejectItem = async (queueItemId: string) => {
    setActionLoading(queueItemId);
    try {
      await api.post(`/projects/${projectId}/autopilot/reject`, { queue_item_id: queueItemId });
      showToast("Отклонено", "info");
      fetchAll(true);
    } catch (e) {
      showToast("Ошибка отклонения", "error");
      console.error(e);
    } finally {
      setActionLoading(null);
    }
  };

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className="cz-flex-col" style={{ gap: 16 }}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="cz-skeleton--card" style={{ height: i === 1 ? 100 : 180 }} />
        ))}
      </div>
    );
  }

  const anyEnabled = configs.some((c) => c.autopilot.enabled);

  return (
    <div className="cz-flex-col stagger-children" style={{ gap: 20 }}>
      {/* ═══ Section 1: Status Bar ═══ */}
      <div className="cz-glass-panel animate-page-in" style={{ padding: 0 }}>
        <div className="ap-status-bar">
          <div className="ap-status-bar__header">
            <div className="cz-flex cz-items-center cz-gap-12">
              <div className={`ap-status-indicator ${anyEnabled ? "ap-status-indicator--active" : ""}`}>
                <Bot size={18} />
              </div>
              <div>
                <div className="cz-text-base cz-font-semibold">
                  Автопилот: {anyEnabled ? "Активен" : "Выключен"}
                </div>
                {stats && anyEnabled && (
                  <div className="cz-text-xs cz-text-muted" style={{ marginTop: 2 }}>
                    Shadow mode • Требуется одобрение
                  </div>
                )}
              </div>
            </div>
            <div className="cz-flex cz-items-center cz-gap-8">
              <button
                className="ap-refresh-btn"
                onClick={handleRefresh}
                disabled={refreshing}
                title="Обновить"
              >
                <RefreshCw size={14} className={refreshing ? "ap-spin" : ""} />
              </button>
            </div>
          </div>

          {stats && anyEnabled && (
            <div className="ap-stats-row">
              <div className="ap-stat">
                <div className="ap-stat__value">{stats.published_today}</div>
                <div className="ap-stat__label">Опубликовано</div>
              </div>
              <div className="ap-stat-divider" />
              <div className="ap-stat">
                <div className="ap-stat__value">{stats.queued}</div>
                <div className="ap-stat__label">В очереди</div>
              </div>
              <div className="ap-stat-divider" />
              <div className="ap-stat">
                <div className="ap-stat__value ap-stat__value--accent">{stats.shadow_pending}</div>
                <div className="ap-stat__label">Ожидают одобрения</div>
              </div>
              <div className="ap-stat-divider" />
              {/* Format mix mini-stats */}
              <div className="ap-stat">
                <div className="ap-stat__value" style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {Object.entries(stats.format_counts || {}).map(([fmt, cnt]) => {
                    const info = FORMAT_LABELS[fmt];
                    return info ? (
                      <span key={fmt} title={info.label} style={{ fontSize: 12, color: `hsl(${info.color})` }}>
                        {info.icon}{cnt}
                      </span>
                    ) : null;
                  })}
                  {Object.keys(stats.format_counts || {}).length === 0 && "—"}
                </div>
                <div className="ap-stat__label">Формат-микс</div>
              </div>
              <div className="ap-stat-divider" />
              <div className="ap-stat">
                <div className="ap-stat__value">
                  {stats.next_scheduled ? (
                    <span className="cz-flex cz-items-center cz-gap-4">
                      <Clock size={13} />
                      {new Date(stats.next_scheduled.scheduled_at).toLocaleTimeString("ru", {
                        hour: "2-digit", minute: "2-digit",
                      })}
                    </span>
                  ) : "—"}
                </div>
                <div className="ap-stat__label">Следующая</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ═══ Section 2: Channel Configs ═══ */}
      <div className="cz-glass-panel animate-page-in">
        <div className="cz-flex-between cz-items-center" style={{ marginBottom: 16 }}>
          <h3 className="cz-text-lg cz-font-semibold cz-flex cz-items-center cz-gap-8">
            <Settings2 size={18} className="cz-text-muted" />
            Настройки каналов
          </h3>
        </div>

        <div className="cz-flex-col" style={{ gap: 8 }}>
          {configs.map((cfg) => (
            <ChannelConfigCard
              key={cfg.channel_id}
              config={cfg}
              expanded={expandedChannel === cfg.channel_id}
              onToggle={() => setExpandedChannel(expandedChannel === cfg.channel_id ? null : cfg.channel_id)}
              onUpdate={(updates) => updateConfig(cfg.channel_id, updates)}
              saving={saving === cfg.channel_id}
            />
          ))}
          {configs.length === 0 && (
            <div className="cz-empty-state" style={{ padding: 32 }}>
              <AlertTriangle size={32} className="cz-text-muted" />
              <div className="cz-text-sm cz-text-muted" style={{ marginTop: 8 }}>
                Нет активных каналов в проекте
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ═══ Section 3: Queue ═══ */}
      <div className="cz-glass-panel animate-page-in">
        <div className="cz-flex-between cz-items-center" style={{ marginBottom: 16 }}>
          <h3 className="cz-text-lg cz-font-semibold cz-flex cz-items-center cz-gap-8">
            <Timer size={18} className="cz-text-muted" />
            Очередь публикации
            {queue.length > 0 && (
              <span className="ap-queue-badge">{queue.length}</span>
            )}
          </h3>
        </div>

        {queue.length === 0 ? (
          <div className="cz-empty-state" style={{ padding: 32 }}>
            <Bot size={36} className="cz-text-muted" style={{ opacity: 0.4 }} />
            <div className="cz-empty-state__title">Очередь пуста</div>
            <div className="cz-empty-state__text">
              {anyEnabled
                ? "Автопилот ещё не добавил материалы в очередь. Подождите 15 минут."
                : "Включите автопилот для канала, чтобы начать автоматический отбор."}
            </div>
          </div>
        ) : (
          <div className="cz-flex-col" style={{ gap: 10 }}>
            {queue.map((item) => (
              <QueueItemCard
                key={item.id}
                item={item}
                onApprove={() => approveItem(item.id)}
                onReject={() => rejectItem(item.id)}
                loading={actionLoading === item.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Sub-component: Channel Config Card
   ═══════════════════════════════════════════════════════ */

function ChannelConfigCard({
  config,
  expanded,
  onToggle,
  onUpdate,
  saving,
}: {
  config: AutopilotChannelConfig;
  expanded: boolean;
  onToggle: () => void;
  onUpdate: (updates: Record<string, unknown>) => void;
  saving: boolean;
}) {
  const ap = config.autopilot;
  const [localConfig, setLocalConfig] = useState(ap);

  // Sync local state when config changes from server
  useEffect(() => { setLocalConfig(ap); }, [ap]);

  const hasChanges = JSON.stringify(localConfig) !== JSON.stringify(ap);

  const handleSave = () => {
    onUpdate(localConfig);
  };

  return (
    <div className={`ap-channel-card ${ap.enabled ? "ap-channel-card--enabled" : ""}`}>
      {/* Header */}
      <div className="ap-channel-header" onClick={onToggle}>
        <div className="cz-flex cz-items-center cz-gap-12">
          <div
            className={`ap-toggle ${localConfig.enabled ? "ap-toggle--on" : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              const newVal = !localConfig.enabled;
              setLocalConfig({ ...localConfig, enabled: newVal });
              onUpdate({ enabled: newVal });
            }}
          >
            <div className="ap-toggle__thumb" />
          </div>
          <div>
            <div className="cz-text-sm cz-font-semibold">{config.channel_name}</div>
            <div className="cz-text-xs cz-text-muted">
              {config.languages.join(", ")} • {ap.enabled ? "Включён" : "Выключен"}
            </div>
          </div>
        </div>
        <div className="cz-flex cz-items-center cz-gap-8">
          {ap.enabled && (
            <span className="ap-mode-badge">
              <ShieldCheck size={11} />
              {ap.shadow_mode ? "Shadow" : "Auto"}
            </span>
          )}
          {expanded ? <ChevronUp size={16} className="cz-text-muted" /> : <ChevronDown size={16} className="cz-text-muted" />}
        </div>
      </div>

      {/* Expanded settings */}
      {expanded && (
        <div className="ap-channel-body">
          {/* Row 1: Main params */}
          <div className="ap-settings-grid">
            <div className="ap-setting">
              <label className="cz-form-label">Макс постов/день</label>
              <input
                type="number"
                className="cz-input focus-ring ap-input--compact"
                value={localConfig.max_posts_per_day}
                min={1}
                max={30}
                onChange={(e) => setLocalConfig({ ...localConfig, max_posts_per_day: Number(e.target.value) })}
              />
            </div>
            <div className="ap-setting">
              <label className="cz-form-label">Мин интервал (мин)</label>
              <input
                type="number"
                className="cz-input focus-ring ap-input--compact"
                value={localConfig.min_interval_minutes}
                min={10}
                max={240}
                step={5}
                onChange={(e) => setLocalConfig({ ...localConfig, min_interval_minutes: Number(e.target.value) })}
              />
            </div>
            <div className="ap-setting">
              <label className="cz-form-label">Порог оценки</label>
              <div className="ap-score-input">
                <input
                  type="range"
                  min={4}
                  max={9.5}
                  step={0.5}
                  value={localConfig.min_score_threshold}
                  onChange={(e) => setLocalConfig({ ...localConfig, min_score_threshold: Number(e.target.value) })}
                  className="ap-slider"
                />
                <span className="ap-score-value">{localConfig.min_score_threshold.toFixed(1)}</span>
              </div>
            </div>
            <div className="ap-setting">
              <label className="cz-form-label">Обложки</label>
              <select
                className="cz-input focus-ring ap-input--compact"
                value={localConfig.cover_policy}
                onChange={(e) => setLocalConfig({ ...localConfig, cover_policy: e.target.value })}
              >
                {Object.entries(COVER_LABELS).map(([val, label]) => (
                  <option key={val} value={val}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Row 2: Shadow mode toggle */}
          <div className="ap-setting-row">
            <div className="cz-flex cz-items-center cz-gap-10">
              <div
                className={`ap-toggle ap-toggle--sm ${localConfig.shadow_mode ? "ap-toggle--on" : ""}`}
                onClick={() => setLocalConfig({ ...localConfig, shadow_mode: !localConfig.shadow_mode })}
              >
                <div className="ap-toggle__thumb" />
              </div>
              <div>
                <div className="cz-text-sm cz-font-medium">Shadow Mode</div>
                <div className="cz-text-xs cz-text-muted">Требовать одобрения перед публикацией</div>
              </div>
            </div>
          </div>

          {/* Row 2.5: Per-language settings (only for multi-language channels) */}
          {config.languages.length > 1 && (
            <div className="ap-setting-section">
              <label className="cz-form-label">Настройки по языкам</label>
              <div className="ap-lang-grid">
                {config.languages.map((lang) => {
                  const langSettings = (localConfig.language_settings || {})[lang] || {};
                  const langLabel = LANG_LABELS[lang] || { flag: "🌐", name: lang.toUpperCase() };
                  const effectiveMax = langSettings.max_posts_per_day ?? localConfig.max_posts_per_day;
                  const effectiveInterval = langSettings.min_interval_minutes ?? localConfig.min_interval_minutes;

                  const updateLang = (field: string, value: number) => {
                    const currentLangSettings = { ...(localConfig.language_settings || {}) };
                    currentLangSettings[lang] = {
                      ...(currentLangSettings[lang] || {}),
                      [field]: value,
                    };
                    setLocalConfig({ ...localConfig, language_settings: currentLangSettings });
                  };

                  return (
                    <div key={lang} className="ap-lang-card">
                      <div className="ap-lang-card__header">
                        <span className="ap-lang-flag">{langLabel.flag}</span>
                        <span className="ap-lang-name">{langLabel.name}</span>
                      </div>
                      <div className="ap-lang-card__body">
                        <div className="ap-lang-field">
                          <label className="ap-lang-label">Постов/день</label>
                          <input
                            type="number"
                            className="cz-input focus-ring ap-input--compact ap-lang-input"
                            value={effectiveMax}
                            min={1}
                            max={30}
                            onChange={(e) => updateLang("max_posts_per_day", Number(e.target.value))}
                          />
                        </div>
                        <div className="ap-lang-field">
                          <label className="ap-lang-label">Интервал (мин)</label>
                          <input
                            type="number"
                            className="cz-input focus-ring ap-input--compact ap-lang-input"
                            value={effectiveInterval}
                            min={10}
                            max={240}
                            step={5}
                            onChange={(e) => updateLang("min_interval_minutes", Number(e.target.value))}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Row 3: Time slots */}
          <div className="ap-setting-section">
            <label className="cz-form-label">Расписание</label>
            <div className="cz-flex" style={{ gap: 6, flexWrap: "wrap" }}>
              {Object.entries(SLOT_LABELS).map(([slot, label]) => {
                const active = localConfig.schedule_slots.includes(slot);
                return (
                  <button
                    key={slot}
                    className={`ap-slot-chip ${active ? "ap-slot-chip--active" : ""}`}
                    onClick={() => {
                      const slots = active
                        ? localConfig.schedule_slots.filter((s) => s !== slot)
                        : [...localConfig.schedule_slots, slot];
                      setLocalConfig({ ...localConfig, schedule_slots: slots });
                    }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Row 4: Strategies */}
          <div className="ap-setting-section">
            <label className="cz-form-label">Стратегии</label>
            <div className="cz-flex" style={{ gap: 6 }}>
              {Object.entries(STRATEGY_LABELS).map(([key, { label, icon }]) => {
                const active = localConfig.strategies.includes(key);
                return (
                  <button
                    key={key}
                    className={`ap-slot-chip ${active ? "ap-slot-chip--active" : ""}`}
                    onClick={() => {
                      const strats = active
                        ? localConfig.strategies.filter((s) => s !== key)
                        : [...localConfig.strategies, key];
                      setLocalConfig({ ...localConfig, strategies: strats });
                    }}
                  >
                    {icon} {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Row 5: Format Mix */}
          <div className="ap-setting-section">
            <label className="cz-form-label">Формат-микс</label>
            <div className="ap-format-mix-grid">
              {Object.entries(FORMAT_LABELS).map(([fmt, { label, icon, color }]) => {
                const ratio = (localConfig.format_ratios || {})[fmt] ?? 0;
                const pct = Math.round(ratio * 100);
                return (
                  <div key={fmt} className="ap-format-ratio-item">
                    <div className="ap-format-ratio-header">
                      <span style={{ color: `hsl(${color})` }}>{icon}</span>
                      <span className="cz-text-xs cz-font-medium">{label}</span>
                      <span className="cz-text-xs cz-text-muted">{pct}%</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={5}
                      value={pct}
                      className="ap-slider"
                      onChange={(e) => {
                        const newPct = Number(e.target.value) / 100;
                        const updatedRatios = { ...(localConfig.format_ratios || {}) };
                        updatedRatios[fmt] = newPct;
                        setLocalConfig({ ...localConfig, format_ratios: updatedRatios });
                      }}
                    />
                  </div>
                );
              })}
            </div>
            <div className="ap-settings-grid" style={{ marginTop: 8 }}>
              <div className="ap-setting">
                <label className="cz-form-label">Лонгридов/день макс</label>
                <input
                  type="number"
                  className="cz-input focus-ring ap-input--compact"
                  value={localConfig.longread_max_per_day}
                  min={0}
                  max={10}
                  onChange={(e) => setLocalConfig({ ...localConfig, longread_max_per_day: Number(e.target.value) })}
                />
              </div>
              <div className="ap-setting">
                <label className="cz-form-label" title="Материалы старше этого возраста никогда не попадут в очередь автопилота">
                  Свежесть, часов
                </label>
                <input
                  type="number"
                  className="cz-input focus-ring ap-input--compact"
                  value={localConfig.max_material_age_hours}
                  min={1}
                  max={168}
                  onChange={(e) => setLocalConfig({ ...localConfig, max_material_age_hours: Number(e.target.value) })}
                />
              </div>
            </div>
          </div>

          {/* Save button */}
          {hasChanges && (
            <div className="ap-save-row">
              <CzButton
                onClick={handleSave}
                disabled={saving}
                size="sm"
              >
                {saving ? <Loader2 size={13} className="ap-spin" /> : null}
                {saving ? "Сохранение..." : "Сохранить настройки"}
              </CzButton>
              <button
                className="ap-cancel-link"
                onClick={() => setLocalConfig(ap)}
              >
                Отмена
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Sub-component: Queue Item Card
   ═══════════════════════════════════════════════════════ */

function QueueItemCard({
  item,
  onApprove,
  onReject,
  loading,
}: {
  item: QueueItem;
  onApprove: () => void;
  onReject: () => void;
  loading: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const isExpress = item.strategy === "express";
  const isShadow = item.status === "shadow";
  const scheduledTime = item.scheduled_at
    ? new Date(item.scheduled_at).toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" })
    : "—";

  // Material freshness — prefer source publication date, fallback to scrape time
  const materialIso = item.material_published_at || item.material_scraped_at;
  const materialFreshness = (() => {
    if (!materialIso) return null;
    const d = new Date(materialIso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffH = diffMs / 3600000;
    const isToday = d.toDateString() === now.toDateString();
    const isYesterday = d.toDateString() === new Date(now.getTime() - 86400000).toDateString();
    const time = d.toLocaleTimeString("ru", { hour: "2-digit", minute: "2-digit" });
    let label: string;
    if (isToday) label = `сегодня ${time}`;
    else if (isYesterday) label = `вчера ${time}`;
    else label = d.toLocaleDateString("ru", { day: "numeric", month: "short" }) + ` ${time}`;
    // Color: fresh (<6h) → success, medium (<24h) → muted, stale → warning
    const color =
      diffH < 6 ? "var(--cz-success)" :
      diffH < 24 ? "var(--cz-text-muted)" :
      "var(--cz-warning)";
    return { label, color };
  })();

  const coverIcon = () => {
    if (!item.cover_status || item.cover_status === "none") return null;
    if (item.cover_status === "ready") return <Image size={12} style={{ color: "hsl(var(--cz-success))" }} />;
    if (item.cover_status === "generating") return <Loader2 size={12} className="ap-spin" style={{ color: "hsl(var(--cz-warning))" }} />;
    if (item.cover_status === "error" || item.cover_status === "permanently_failed")
      return <AlertTriangle size={12} style={{ color: "hsl(var(--cz-error))" }} />;
    return null;
  };

  const statusColor = () => {
    if (item.status === "shadow") return "var(--cz-warning)";
    if (item.status === "queued" || item.status === "approved") return "var(--cz-success)";
    if (item.status === "publishing") return "var(--cz-info)";
    return "var(--cz-text-muted)";
  };

  const statusLabel = () => {
    if (item.status === "shadow") return "Ожидает";
    if (item.status === "queued") return "В очереди";
    if (item.status === "approved") return "Одобрен";
    if (item.status === "publishing") return "Публикуется";
    return item.status;
  };

  return (
    <div className={`ap-queue-item ${isExpress ? "ap-queue-item--express" : ""} ${expanded ? "ap-queue-item--expanded" : ""}`}>
      {/* Main row — always visible */}
      <div className="ap-queue-item__main" onClick={() => setExpanded(!expanded)} style={{ cursor: "pointer" }}>
        {/* Score badge */}
        <div className="ap-queue-score" title="Final Score">
          {item.final_score.toFixed(1)}
        </div>

        {/* Content */}
        <div className="ap-queue-content">
          <div className="ap-queue-headline">
            {item.content_format === "flash" ? (item.body_preview || "⚡ Flash") : (item.headline || "Без заголовка")}
          </div>
          <div className="ap-queue-meta">
            {materialFreshness && (
              <span
                className="ap-queue-meta-item"
                style={{ color: `hsl(${materialFreshness.color})` }}
                title="Когда опубликован материал"
              >
                📰 {materialFreshness.label}
              </span>
            )}
            <span className="ap-queue-meta-item" title="Когда автопилот опубликует">
              <Clock size={11} /> {scheduledTime}
            </span>
            <span className="ap-queue-meta-item" style={{ textTransform: "uppercase" }}>
              {item.language}
            </span>
            {(() => {
              const fmtInfo = FORMAT_LABELS[item.content_format];
              return fmtInfo ? (
                <span
                  className="ap-queue-format-badge"
                  style={{ color: `hsl(${fmtInfo.color})`, borderColor: `hsla(${fmtInfo.color}, 0.3)` }}
                >
                  {fmtInfo.icon} {fmtInfo.label}
                </span>
              ) : (
                <span className="ap-queue-meta-item">{item.content_format}</span>
              );
            })()}
            {item.content_format !== "flash" && coverIcon() && (
              <span className="ap-queue-meta-item">
                {coverIcon()} Обложка
              </span>
            )}
            {isExpress && (
              <span className="ap-queue-express-badge">
                <Zap size={10} /> Express
              </span>
            )}
          </div>
          {/* Body preview when collapsed */}
          {!expanded && item.body_preview && (
            <div className="ap-queue-body-preview">
              {item.body_preview}
            </div>
          )}
        </div>

        {/* Status + Actions */}
        <div className="ap-queue-actions">
          <span className="ap-queue-status" style={{ color: `hsl(${statusColor()})` }}>
            <span className="cz-status__dot" />
            {statusLabel()}
          </span>

          {isShadow && (
            <div className="cz-flex cz-gap-4">
              <button
                className="ap-action-btn ap-action-btn--approve"
                onClick={(e) => { e.stopPropagation(); onApprove(); }}
                disabled={loading}
                title="Одобрить"
              >
                {loading ? <Loader2 size={14} className="ap-spin" /> : <CheckCircle2 size={14} />}
              </button>
              <button
                className="ap-action-btn ap-action-btn--reject"
                onClick={(e) => { e.stopPropagation(); onReject(); }}
                disabled={loading}
                title="Отклонить"
              >
                <XCircle size={14} />
              </button>
            </div>
          )}

          <button
            className="ap-expand-toggle"
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            title={expanded ? "Свернуть" : "Развернуть"}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {/* Expanded content — body + cover */}
      {expanded && (
        <div className="ap-queue-item__expanded">
          {/* Cover image or status */}
          {item.cover_image_url ? (
            <div className="ap-queue-cover">
              <img
                src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010/api/v1"}${item.cover_image_url.startsWith("/api/v1") ? item.cover_image_url.replace("/api/v1", "") : item.cover_image_url}`}
                alt="Обложка"
                className="ap-queue-cover__img"
              />
            </div>
          ) : (
            <div className="ap-queue-cover-status">
              {item.cover_status === "generating" && (
                <>
                  <Loader2 size={14} className="ap-spin" style={{ color: "hsl(var(--cz-warning))" }} />
                  <span>Обложка генерируется…</span>
                </>
              )}
              {item.cover_status === "error" && (
                <>
                  <AlertTriangle size={14} style={{ color: "hsl(var(--cz-error))" }} />
                  <span>Ошибка генерации обложки — автоповтор через 10 мин</span>
                </>
              )}
              {item.cover_status === "permanently_failed" && (
                <>
                  <XCircle size={14} style={{ color: "hsl(var(--cz-error))" }} />
                  <span>Генерация обложки не удалась</span>
                </>
              )}
              {!item.cover_status && (
                <>
                  <Image size={14} className="cz-text-muted" />
                  <span>Обложка не запрошена</span>
                </>
              )}
            </div>
          )}

          {/* Full post body */}
          <div className="ap-queue-body">
            {item.body ? (
              <div className="ap-queue-body__text">
                {item.body.split("\n").map((line, i) => (
                  <React.Fragment key={i}>
                    {line}
                    {i < item.body.split("\n").length - 1 && <br />}
                  </React.Fragment>
                ))}
              </div>
            ) : (
              <div className="ap-queue-body__empty">
                <AlertTriangle size={14} className="cz-text-muted" />
                <span>Текст поста отсутствует</span>
              </div>
            )}
          </div>

          {/* Action buttons in expanded view */}
          {isShadow && (
            <div className="ap-queue-expanded-actions">
              <button
                className="ap-expanded-btn ap-expanded-btn--approve"
                onClick={onApprove}
                disabled={loading}
              >
                {loading ? <Loader2 size={14} className="ap-spin" /> : <CheckCircle2 size={14} />}
                Одобрить к публикации
              </button>
              <button
                className="ap-expanded-btn ap-expanded-btn--reject"
                onClick={onReject}
                disabled={loading}
              >
                <XCircle size={14} />
                Отклонить
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
