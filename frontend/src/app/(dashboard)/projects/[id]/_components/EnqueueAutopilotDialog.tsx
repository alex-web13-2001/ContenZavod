"use client";

import React, { useEffect, useMemo, useState } from "react";
import { CzButton, CzDialog } from "@/components/ui-system";
import { Zap } from "lucide-react";
import { Channel, formatLabels } from "./types";

const FORMAT_ICONS: Record<string, string> = {
  flash: "⚡",
  short_post: "📝",
  longread: "📊",
  video_script: "🎬",
  digest: "📰",
};

interface EnqueueAutopilotDialogProps {
  open: boolean;
  onClose: () => void;
  channels: Channel[];
  materialTitle: string;
  /** AI-recommended format from classifier metadata, if any. */
  suggestedFormat?: string | null;
  onEnqueue: (channelId: string, contentFormat: string, language: string) => Promise<void>;
  submitting?: boolean;
}

export function EnqueueAutopilotDialog({
  open, onClose, channels, materialTitle, suggestedFormat,
  onEnqueue, submitting,
}: EnqueueAutopilotDialogProps) {
  // Only active TG channels are eligible for autopilot
  const eligibleChannels = useMemo(
    () => channels.filter((c) => c.is_active && c.channel_type === "telegram"),
    [channels],
  );

  const [channelId, setChannelId] = useState<string>("");
  const [contentFormat, setContentFormat] = useState<string>("");
  const [language, setLanguage] = useState<string>("");

  // Selected channel object
  const channel = useMemo(
    () => eligibleChannels.find((c) => c.id === channelId) || null,
    [eligibleChannels, channelId],
  );

  // Reset state when dialog opens
  useEffect(() => {
    if (!open) return;
    const first = eligibleChannels[0];
    setChannelId(first?.id || "");
    setContentFormat("");
    setLanguage("");
  }, [open, eligibleChannels]);

  // When channel changes, pick a sensible default format and language
  useEffect(() => {
    if (!channel) return;
    const formats = channel.content_formats || ["short_post"];
    // Prefer AI-suggested format if it's in the channel's allowed list
    const preferred =
      suggestedFormat && formats.includes(suggestedFormat) ? suggestedFormat : formats[0];
    setContentFormat(preferred);
    setLanguage(channel.languages?.[0] || "ru");
  }, [channel, suggestedFormat]);

  const canSubmit = !!channelId && !!contentFormat && !!language && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    await onEnqueue(channelId, contentFormat, language);
  };

  return (
    <CzDialog
      open={open}
      onClose={onClose}
      title="⚡ Поставить в очередь автопилота"
      maxWidth="520px"
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        {/* Material */}
        <div>
          <label className="cz-form-label">Материал</label>
          <div
            style={{
              padding: "10px 12px",
              backgroundColor: "hsl(var(--cz-bg-elevated) / 0.6)",
              border: "1px solid hsl(var(--cz-border-subtle))",
              borderRadius: 10,
              fontSize: 14,
              color: "hsl(var(--cz-text-secondary))",
              lineHeight: 1.4,
            }}
          >
            {materialTitle}
          </div>
        </div>

        {/* Channel select */}
        <div>
          <label className="cz-form-label">Канал</label>
          {eligibleChannels.length === 0 ? (
            <div
              style={{
                padding: "10px 12px",
                fontSize: 13,
                color: "hsl(var(--cz-warning))",
                backgroundColor: "hsl(var(--cz-warning) / 0.08)",
                border: "1px solid hsl(var(--cz-warning) / 0.2)",
                borderRadius: 10,
              }}
            >
              Нет активных Telegram-каналов в этом проекте. Создайте канал или включите его.
            </div>
          ) : (
            <select
              className="cz-input focus-ring"
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              disabled={submitting}
            >
              {eligibleChannels.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({(c.languages || []).join(", ").toUpperCase() || "ru"})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Format select — depends on channel */}
        {channel && (
          <div>
            <label className="cz-form-label">Формат</label>
            <select
              className="cz-input focus-ring"
              value={contentFormat}
              onChange={(e) => setContentFormat(e.target.value)}
              disabled={submitting}
            >
              {(channel.content_formats || ["short_post"]).map((fmt) => {
                const isSuggested = suggestedFormat === fmt;
                const icon = FORMAT_ICONS[fmt] || "•";
                const label = formatLabels[fmt] || fmt;
                return (
                  <option key={fmt} value={fmt}>
                    {icon} {label}{isSuggested ? " · AI рекомендует" : ""}
                  </option>
                );
              })}
            </select>
          </div>
        )}

        {/* Language select — depends on channel */}
        {channel && (channel.languages?.length ?? 0) > 1 && (
          <div>
            <label className="cz-form-label">Язык</label>
            <select
              className="cz-input focus-ring"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={submitting}
            >
              {(channel.languages || ["ru"]).map((lang) => (
                <option key={lang} value={lang}>
                  {lang.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: 10,
            marginTop: 4,
          }}
        >
          <CzButton variant="ghost" onClick={onClose} disabled={submitting}>
            Отмена
          </CzButton>
          <CzButton
            variant="primary"
            onClick={handleSubmit}
            disabled={!canSubmit}
            icon={<Zap size={14} />}
            loading={submitting}
          >
            В очередь
          </CzButton>
        </div>
      </div>
    </CzDialog>
  );
}
