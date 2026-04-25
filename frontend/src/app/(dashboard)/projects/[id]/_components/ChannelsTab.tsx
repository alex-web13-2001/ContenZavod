"use client";

import React, { useState } from "react";
import { CzCard, CzBadge, CzButton, CzEmptyState } from "@/components/ui-system";
import { Send, Globe, Video, Plus, X, Pencil, Trash2, Save, Check, ChevronDown, ChevronUp } from "lucide-react";
import { Channel, platformConfig, formatLabels } from "./types";

const PLATFORM_OPTIONS = [
  { value: "telegram", icon: Send, label: "Telegram", color: "var(--cz-info)" },
  { value: "website", icon: Globe, label: "Сайт", color: "var(--cz-accent)" },
  { value: "youtube", icon: Video, label: "YouTube", color: "var(--cz-error)" },
];

const FORMAT_OPTIONS = [
  { value: "short_post", label: "📝 Короткий пост" },
  { value: "longread", label: "📖 Лонгрид" },
  { value: "video_script", label: "🎬 Видео-скрипт" },
  { value: "digest", label: "📋 Дайджест" },
];

const LANG_OPTIONS = [
  { code: "ru", flag: "🇷🇺", label: "RU" },
  { code: "en", flag: "🇬🇧", label: "EN" },
  { code: "el", flag: "🇬🇷", label: "EL" },
  { code: "de", flag: "🇩🇪", label: "DE" },
  { code: "uk", flag: "🇺🇦", label: "UA" },
  { code: "es", flag: "🇪🇸", label: "ES" },
  { code: "fr", flag: "🇫🇷", label: "FR" },
  { code: "zh", flag: "🇨🇳", label: "ZH" },
];

/* ────── Form Section Wrapper ────── */
function FormSection({ title, children, hint }: { title: string; children: React.ReactNode; hint?: string }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: 10,
      padding: "16px 20px",
      backgroundColor: "hsl(var(--cz-bg-hover) / 0.4)",
      borderRadius: "var(--cz-radius-lg)",
      border: "1px solid hsl(var(--cz-border-subtle) / 0.5)",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <label style={{
          fontSize: 11, fontWeight: 700, color: "hsl(var(--cz-text-muted))",
          textTransform: "uppercase", letterSpacing: "0.08em",
        }}>{title}</label>
        {hint && <span style={{ fontSize: 11, color: "hsl(var(--cz-text-muted) / 0.6)" }}>{hint}</span>}
      </div>
      {children}
    </div>
  );
}

/* ────── Platform Card Selector ────── */
function PlatformSelector({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
      {PLATFORM_OPTIONS.map((opt) => {
        const active = value === opt.value;
        return (
          <button key={opt.value} type="button" onClick={() => onChange(opt.value)}
            style={{
              display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
              padding: "18px 12px",
              borderRadius: "var(--cz-radius-lg)",
              backgroundColor: active ? "hsl(var(--cz-primary) / 0.12)" : "hsl(var(--cz-bg-card))",
              border: active ? "2px solid hsl(var(--cz-primary))" : "1px solid hsl(var(--cz-border-subtle))",
              cursor: "pointer",
              transition: "all 0.2s ease",
              color: active ? "hsl(var(--cz-primary))" : "hsl(var(--cz-text-muted))",
              fontSize: 12, fontWeight: active ? 600 : 500,
              transform: active ? "scale(1.02)" : "scale(1)",
              position: "relative",
            }}>
            {active && (
              <div style={{
                position: "absolute", top: 6, right: 6, width: 16, height: 16,
                borderRadius: "50%", backgroundColor: "hsl(var(--cz-primary))",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Check size={10} style={{ color: "white" }} />
              </div>
            )}
            <opt.icon size={24} />
            <span>{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/* ────── Pill Toggle (formats & languages) ────── */
function PillToggle({ options, selected, onToggle, type = "default" }: {
  options: { value: string; label: string; flag?: string }[];
  selected: string[];
  onToggle: (v: string) => void;
  type?: "default" | "lang";
}) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {options.map((opt) => {
        const active = selected.includes(opt.value);
        return (
          <button key={opt.value} type="button" onClick={() => onToggle(opt.value)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: type === "lang" ? "7px 14px" : "8px 16px",
              fontSize: 13, fontWeight: active ? 600 : 400,
              borderRadius: 9999,
              backgroundColor: active
                ? type === "lang" ? "hsl(var(--cz-primary) / 0.15)" : "hsl(var(--cz-primary))"
                : "transparent",
              color: active
                ? type === "lang" ? "hsl(var(--cz-primary))" : "white"
                : "hsl(var(--cz-text-secondary))",
              border: active
                ? type === "lang" ? "1.5px solid hsl(var(--cz-primary))" : "1px solid hsl(var(--cz-primary))"
                : "1px solid hsl(var(--cz-border))",
              cursor: "pointer",
              transition: "all 0.2s ease",
              transform: active ? "scale(1.03)" : "scale(1)",
            }}>
            {"flag" in opt && opt.flag && <span style={{ fontSize: 15, lineHeight: 1 }}>{opt.flag}</span>}
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

/* ────── Channel Form (create/edit) ────── */
interface ChannelFormData {
  name: string;
  channel_type: string;
  content_formats: string[];
  tone_of_voice: string;
  formatting_rules: string;
  languages: string[];
  bot_token: string;
  chat_id: string;
  /** Per-language Chat IDs: { ru: "@chan_ru", en: "@chan_en" } */
  endpoints: Record<string, string>;
  is_active?: boolean;
}

function ChannelForm({
  form, onChange, onSave, onCancel, saving, title, onDelete,
}: {
  form: ChannelFormData;
  onChange: (f: ChannelFormData) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
  title: string;
  onDelete?: () => void;
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const toggleFormat = (v: string) => {
    const fmts = form.content_formats.includes(v) ? form.content_formats.filter(f => f !== v) : [...form.content_formats, v];
    if (fmts.length > 0) onChange({ ...form, content_formats: fmts });
  };
  const toggleLang = (v: string) => {
    const ls = form.languages.includes(v) ? form.languages.filter(l => l !== v) : [...form.languages, v];
    if (ls.length > 0) {
      // Sync endpoints: add empty entry for new languages, remove old ones
      const newEndpoints = { ...form.endpoints };
      ls.forEach(l => { if (!(l in newEndpoints)) newEndpoints[l] = ""; });
      Object.keys(newEndpoints).forEach(k => { if (!ls.includes(k)) delete newEndpoints[k]; });
      onChange({ ...form, languages: ls, endpoints: newEndpoints });
    }
  };

  const updateEndpoint = (lang: string, chatId: string) => {
    onChange({ ...form, endpoints: { ...form.endpoints, [lang]: chatId } });
  };

  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: 0,
      borderRadius: "var(--cz-radius-xl)",
      border: "1px solid hsl(var(--cz-border))",
      backgroundColor: "hsl(var(--cz-bg-card))",
      overflow: "hidden",
      animation: "fadeIn 0.25s ease-out",
    }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 12, padding: "18px 24px",
        borderBottom: "1px solid hsl(var(--cz-border-subtle))",
        background: "linear-gradient(135deg, hsl(var(--cz-primary) / 0.06), transparent)",
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: "var(--cz-radius-md)",
          background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          <Pencil size={16} style={{ color: "white" }} />
        </div>
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "hsl(var(--cz-text-primary))", lineHeight: 1.2 }}>{title}</h3>
          <p style={{ fontSize: 12, color: "hsl(var(--cz-text-muted))", marginTop: 2 }}>Настройте платформу и стиль контента</p>
        </div>
      </div>

      {/* Form Body */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "20px 24px" }}>

        {/* Name */}
        <FormSection title="Название канала" hint="ID или @username">
          <input type="text" placeholder="@mychannel или название"
            value={form.name} onChange={(e) => onChange({ ...form, name: e.target.value })}
            style={{
              width: "100%", height: 44, padding: "0 16px",
              fontSize: 14, fontWeight: 500,
              borderRadius: "var(--cz-radius-md)",
              backgroundColor: "hsl(var(--cz-bg-root))",
              color: "hsl(var(--cz-text-primary))",
              border: "1px solid hsl(var(--cz-border))",
              outline: "none",
              transition: "border-color 0.2s, box-shadow 0.2s",
            }}
            onFocus={(e) => {
              e.target.style.borderColor = "hsl(var(--cz-primary))";
              e.target.style.boxShadow = "0 0 0 3px hsl(var(--cz-primary) / 0.15)";
            }}
            onBlur={(e) => {
              e.target.style.borderColor = "hsl(var(--cz-border))";
              e.target.style.boxShadow = "none";
            }}
          />
        </FormSection>

        {/* Platform */}
        <FormSection title="Платформа" hint="Выберите одну">
          <PlatformSelector value={form.channel_type} onChange={(v) => onChange({ ...form, channel_type: v })} />
        </FormSection>

        {/* Content formats */}
        <FormSection title="Формат контента" hint={`${form.content_formats.length} выбрано`}>
          <PillToggle
            options={FORMAT_OPTIONS.map(o => ({ value: o.value, label: o.label }))}
            selected={form.content_formats}
            onToggle={toggleFormat}
          />
        </FormSection>

        {/* Languages */}
        <FormSection title="Языки контента" hint={`${form.languages.length} выбрано`}>
          <PillToggle
            options={LANG_OPTIONS.map(l => ({ value: l.code, label: l.label, flag: l.flag }))}
            selected={form.languages}
            onToggle={toggleLang}
            type="lang"
          />
        </FormSection>

        {/* Tone of Voice */}
        <FormSection title="Tone of Voice" hint="Стиль общения">
          <textarea placeholder="Информативный деловой тон, с элементами юмора..."
            rows={3}
            value={form.tone_of_voice}
            onChange={(e) => onChange({ ...form, tone_of_voice: e.target.value })}
            style={{
              width: "100%", padding: "12px 16px",
              fontSize: 14, lineHeight: 1.6,
              borderRadius: "var(--cz-radius-md)",
              backgroundColor: "hsl(var(--cz-bg-root))",
              color: "hsl(var(--cz-text-primary))",
              border: "1px solid hsl(var(--cz-border))",
              outline: "none", resize: "vertical",
              transition: "border-color 0.2s, box-shadow 0.2s",
            }}
            onFocus={(e) => {
              e.target.style.borderColor = "hsl(var(--cz-primary))";
              e.target.style.boxShadow = "0 0 0 3px hsl(var(--cz-primary) / 0.15)";
            }}
            onBlur={(e) => {
              e.target.style.borderColor = "hsl(var(--cz-border))";
              e.target.style.boxShadow = "none";
            }}
          />
        </FormSection>

        {/* Formatting Rules */}
        <FormSection title="Правила форматирования" hint="Обязательные правила структуры текста">
          <textarea placeholder={"Примеры:\n• Текст делится на абзацы по 2-3 предложения\n• Между абзацами — пустая строка\n• Вопрос в конце поста выделяется жирным и отделяется пустой строкой\n• Эмодзи ставятся в начале абзаца"}
            rows={4}
            value={form.formatting_rules}
            onChange={(e) => onChange({ ...form, formatting_rules: e.target.value })}
            style={{
              width: "100%", padding: "12px 16px",
              fontSize: 14, lineHeight: 1.6,
              borderRadius: "var(--cz-radius-md)",
              backgroundColor: "hsl(var(--cz-bg-root))",
              color: "hsl(var(--cz-text-primary))",
              border: "1px solid hsl(var(--cz-border))",
              outline: "none", resize: "vertical",
              transition: "border-color 0.2s, box-shadow 0.2s",
            }}
            onFocus={(e) => {
              e.target.style.borderColor = "hsl(var(--cz-primary))";
              e.target.style.boxShadow = "0 0 0 3px hsl(var(--cz-primary) / 0.15)";
            }}
            onBlur={(e) => {
              e.target.style.borderColor = "hsl(var(--cz-border))";
              e.target.style.boxShadow = "none";
            }}
          />
        </FormSection>

        {/* Telegram config — collapsible */}
        {form.channel_type === "telegram" && (
          <div style={{
            borderRadius: "var(--cz-radius-lg)",
            border: "1px solid hsl(var(--cz-info) / 0.2)",
            overflow: "hidden",
          }}>
            <button type="button" onClick={() => setShowAdvanced(!showAdvanced)}
              style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                width: "100%", padding: "12px 20px",
                backgroundColor: "hsl(var(--cz-info) / 0.06)",
                border: "none", cursor: "pointer",
                color: "hsl(var(--cz-info))", fontSize: 13, fontWeight: 600,
              }}>
              <span>🤖 Настройки Telegram-бота</span>
              {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {showAdvanced && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10, padding: "16px 20px" }}>
                <input type="password" placeholder="Bot Token (от @BotFather)"
                  value={form.bot_token} onChange={(e) => onChange({ ...form, bot_token: e.target.value })}
                  style={{
                    width: "100%", height: 40, padding: "0 14px",
                    fontSize: 13, fontFamily: "monospace",
                    borderRadius: "var(--cz-radius-md)",
                    backgroundColor: "hsl(var(--cz-bg-root))",
                    color: "hsl(var(--cz-text-primary))",
                    border: "1px solid hsl(var(--cz-border))",
                    outline: "none",
                  }}
                />

                {/* Per-language Chat IDs */}
                {form.languages.length > 1 ? (
                  <>
                    <p style={{ fontSize: 12, color: "hsl(var(--cz-info))", margin: "4px 0 0", fontWeight: 600 }}>
                      📡 Chat ID для каждого языка:
                    </p>
                    {form.languages.map(lang => {
                      const langOpt = LANG_OPTIONS.find(l => l.code === lang);
                      return (
                        <div key={lang} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{
                            minWidth: 52, fontSize: 12, fontWeight: 600,
                            color: "hsl(var(--cz-text-secondary))",
                            display: "flex", alignItems: "center", gap: 4,
                          }}>
                            {langOpt?.flag} {lang.toUpperCase()}
                          </span>
                          <input type="text"
                            placeholder={`Chat ID для ${lang.toUpperCase()} (напр. @channel_${lang})`}
                            value={form.endpoints[lang] || ""}
                            onChange={(e) => updateEndpoint(lang, e.target.value)}
                            style={{
                              flex: 1, height: 36, padding: "0 12px",
                              fontSize: 13, fontFamily: "monospace",
                              borderRadius: "var(--cz-radius-md)",
                              backgroundColor: "hsl(var(--cz-bg-root))",
                              color: "hsl(var(--cz-text-primary))",
                              border: "1px solid hsl(var(--cz-border))",
                              outline: "none",
                            }}
                          />
                        </div>
                      );
                    })}
                  </>
                ) : (
                  <input type="text" placeholder="Chat ID канала (напр. @ecocyprus_ru)"
                    value={form.chat_id} onChange={(e) => onChange({ ...form, chat_id: e.target.value })}
                    style={{
                      width: "100%", height: 40, padding: "0 14px",
                      fontSize: 13, fontFamily: "monospace",
                      borderRadius: "var(--cz-radius-md)",
                      backgroundColor: "hsl(var(--cz-bg-root))",
                      color: "hsl(var(--cz-text-primary))",
                      border: "1px solid hsl(var(--cz-border))",
                      outline: "none",
                    }}
                  />
                )}

                <p style={{ fontSize: 11, color: "hsl(var(--cz-text-muted))", margin: 0 }}>
                  Бот должен быть администратором канала с правами на публикацию
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "14px 24px",
        borderTop: "1px solid hsl(var(--cz-border-subtle))",
        backgroundColor: "hsl(var(--cz-bg-hover) / 0.3)",
      }}>
        {onDelete ? (
          <CzButton variant="ghost-danger" onClick={onDelete} icon={<Trash2 size={13} />} size="sm">Удалить</CzButton>
        ) : <div />}
        <div style={{ display: "flex", gap: 8 }}>
          <CzButton variant="ghost" onClick={onCancel}>Отмена</CzButton>
          <CzButton onClick={onSave} disabled={!form.name.trim() || saving} icon={<Save size={13} />}>
            {saving ? "Сохранение..." : "Сохранить"}
          </CzButton>
        </div>
      </div>
    </div>
  );
}

/* ────── Main Tab ────── */
interface ChannelsTabProps {
  channels: Channel[];
  projectId: string;
  onCreateChannel: (form: ChannelFormData) => Promise<void>;
  onSaveChannel: (id: string, form: ChannelFormData) => Promise<void>;
  onDeleteChannel: (id: string) => Promise<void>;
}

export function ChannelsTab({ channels, projectId, onCreateChannel, onSaveChannel, onDeleteChannel }: ChannelsTabProps) {
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editChannelId, setEditChannelId] = useState<string | null>(null);
  const [form, setForm] = useState<ChannelFormData>({
    name: "", channel_type: "telegram", content_formats: ["short_post"], tone_of_voice: "", formatting_rules: "", languages: ["ru"], bot_token: "", chat_id: "", endpoints: {},
  });

  const resetForm = () => setForm({ name: "", channel_type: "telegram", content_formats: ["short_post"], tone_of_voice: "", formatting_rules: "", languages: ["ru"], bot_token: "", chat_id: "", endpoints: {} });

  const handleCreate = async () => {
    setSaving(true);
    try { await onCreateChannel(form); setShowForm(false); resetForm(); } finally { setSaving(false); }
  };

  const startEdit = (ch: Channel) => {
    setEditChannelId(ch.id);
    setShowForm(false);
    // Reconstruct per-language endpoints from config
    const endpoints: Record<string, string> = {};
    const configEndpoints = (ch.config as Record<string, unknown>)?.endpoints as Record<string, { chat_id?: string }> | undefined;
    if (configEndpoints) {
      Object.entries(configEndpoints).forEach(([lang, ep]) => {
        endpoints[lang] = ep?.chat_id || "";
      });
    }
    setForm({
      name: ch.name, channel_type: ch.channel_type, content_formats: ch.content_formats,
      tone_of_voice: ch.tone_of_voice, formatting_rules: ch.formatting_rules || "", languages: ch.languages, is_active: ch.is_active,
      bot_token: ch.config?.bot_token || "", chat_id: ch.config?.chat_id || "",
      endpoints,
    });
  };

  const handleSaveEdit = async () => {
    if (!editChannelId) return;
    setSaving(true);
    try { await onSaveChannel(editChannelId, form); setEditChannelId(null); resetForm(); } finally { setSaving(false); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить канал? Это действие нельзя отменить.")) return;
    await onDeleteChannel(id);
    setEditChannelId(null);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 14, color: "hsl(var(--cz-text-muted))" }}>
          {channels.length} {channels.length === 1 ? "канал" : "каналов"} в проекте
        </span>
        <CzButton onClick={() => { setShowForm(!showForm); setEditChannelId(null); if (!showForm) resetForm(); }}
          icon={showForm ? <X size={12} /> : <Plus size={12} />} size="sm">
          {showForm ? "Отмена" : "Добавить канал"}
        </CzButton>
      </div>

      {/* Create form */}
      {showForm && (
        <ChannelForm form={form} onChange={setForm} onSave={handleCreate}
          onCancel={() => { setShowForm(false); resetForm(); }} saving={saving} title="Новый канал" />
      )}

      {/* Channels list */}
      {channels.length === 0 && !showForm ? (
        <CzEmptyState icon={<Send size={48} />} title="Нет каналов" text="Добавьте Telegram-канал, сайт или YouTube"
          action={<CzButton onClick={() => setShowForm(true)} icon={<Plus size={14} />}>Добавить канал</CzButton>} />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {channels.map((ch) => {
            const cfg = platformConfig[ch.channel_type];
            const Icon = cfg?.icon || Send;

            if (editChannelId === ch.id) {
              return (
                <ChannelForm key={ch.id} form={form} onChange={setForm} onSave={handleSaveEdit}
                  onCancel={() => { setEditChannelId(null); resetForm(); }} saving={saving}
                  title="Редактирование канала" onDelete={() => handleDelete(ch.id)} />
              );
            }

            return (
              <div key={ch.id} style={{
                display: "flex", flexDirection: "column", gap: 0,
                borderRadius: "var(--cz-radius-lg)",
                border: "1px solid hsl(var(--cz-border-subtle))",
                backgroundColor: "hsl(var(--cz-bg-card))",
                overflow: "hidden",
                transition: "border-color 0.2s",
              }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = "hsl(var(--cz-border))"}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = "hsl(var(--cz-border-subtle))"}
              >
                {/* Card main row */}
                <div style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "16px 20px",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <div style={{
                      width: 42, height: 42, borderRadius: "var(--cz-radius-md)",
                      backgroundColor: `hsl(${cfg?.color || "var(--cz-accent)"} / 0.1)`,
                      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                    }}>
                      <Icon size={20} style={{ color: `hsl(${cfg?.color || "var(--cz-accent)"})` }} />
                    </div>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 600, color: "hsl(var(--cz-text-primary))" }}>{ch.name}</div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "hsl(var(--cz-text-muted))", marginTop: 3 }}>
                        <span>{cfg?.label}</span><span style={{ opacity: 0.4 }}>·</span>
                        <span>{ch.content_formats.map(f => formatLabels[f] || f).join(", ")}</span><span style={{ opacity: 0.4 }}>·</span>
                        <span>{ch.languages.map(l => l.toUpperCase()).join(", ")}</span>
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <button onClick={() => startEdit(ch)} title="Редактировать"
                      style={{
                        width: 36, height: 36, borderRadius: "var(--cz-radius-md)",
                        backgroundColor: "transparent", border: "1px solid hsl(var(--cz-border-subtle))",
                        cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                        color: "hsl(var(--cz-text-muted))", transition: "all 0.2s",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = "hsl(var(--cz-primary) / 0.1)";
                        e.currentTarget.style.borderColor = "hsl(var(--cz-primary))";
                        e.currentTarget.style.color = "hsl(var(--cz-primary))";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = "transparent";
                        e.currentTarget.style.borderColor = "hsl(var(--cz-border-subtle))";
                        e.currentTarget.style.color = "hsl(var(--cz-text-muted))";
                      }}
                    >
                      <Pencil size={14} />
                    </button>
                    <CzBadge variant={ch.is_active ? "success" : "default"}>{ch.is_active ? "Активен" : "Выкл"}</CzBadge>
                  </div>
                </div>
                {/* ToV preview */}
                {ch.tone_of_voice && (
                  <div style={{
                    padding: "10px 20px 14px", borderTop: "1px solid hsl(var(--cz-border-subtle) / 0.5)",
                    fontSize: 12, color: "hsl(var(--cz-text-muted))", lineHeight: 1.5,
                  }}>
                    <strong style={{ color: "hsl(var(--cz-text-secondary))" }}>ToV:</strong>{" "}
                    {ch.tone_of_voice.length > 120 ? ch.tone_of_voice.substring(0, 120) + "..." : ch.tone_of_voice}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
