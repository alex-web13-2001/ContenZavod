"use client";

import React, { useState, useMemo } from "react";
import { CzButton, CzDialog } from "@/components/ui-system";
import { Check, Send, Globe } from "lucide-react";
import { Adaptation, formatLabels } from "./types";

const LANG_OPTIONS: { code: string; flag: string; label: string }[] = [
  { code: "ru", flag: "🇷🇺", label: "Русский" },
  { code: "en", flag: "🇬🇧", label: "English" },
  { code: "el", flag: "🇬🇷", label: "Ελληνικά" },
  { code: "de", flag: "🇩🇪", label: "Deutsch" },
  { code: "uk", flag: "🇺🇦", label: "Українська" },
  { code: "es", flag: "🇪🇸", label: "Español" },
  { code: "fr", flag: "🇫🇷", label: "Français" },
  { code: "zh", flag: "🇨🇳", label: "中文" },
];

interface PublishDialogProps {
  open: boolean;
  onClose: () => void;
  adaptations: Adaptation[];
  materialTitle: string;
  onPublish: (adaptationIds: string[]) => void;
  publishing?: boolean;
}

export function PublishDialog({
  open, onClose, adaptations, materialTitle, onPublish, publishing,
}: PublishDialogProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Group adaptations by format → languages
  const grouped = useMemo(() => {
    const map: Record<string, Adaptation[]> = {};
    for (const ad of adaptations) {
      // Only show publishable (draft) adaptations
      if (ad.status !== "draft") continue;
      const key = ad.content_format;
      if (!map[key]) map[key] = [];
      map[key].push(ad);
    }
    return map;
  }, [adaptations]);

  const toggleItem = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    const allIds = adaptations.filter(a => a.status === "draft").map(a => a.id);
    if (selected.size === allIds.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(allIds));
    }
  };

  const handlePublish = () => {
    if (selected.size === 0) return;
    onPublish(Array.from(selected));
  };

  const draftCount = adaptations.filter(a => a.status === "draft").length;

  return (
    <CzDialog open={open} onClose={onClose} title="Публикация материала" maxWidth="560px">
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Material title */}
        <div style={{
          padding: "12px 16px", borderRadius: 10,
          backgroundColor: "hsl(var(--cz-bg-surface))",
          border: "1px solid hsl(var(--cz-border))",
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "hsl(var(--cz-text-muted))", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Материал
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: "hsl(var(--cz-text-primary))", lineHeight: 1.4 }}>
            {materialTitle}
          </div>
        </div>

        {/* Select all */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: "hsl(var(--cz-text-primary))" }}>
            <Globe size={16} style={{ verticalAlign: "middle", marginRight: 6 }} />
            Выберите что публиковать
          </span>
          <button onClick={toggleAll} style={{
            background: "none", border: "none", cursor: "pointer",
            fontSize: 13, fontWeight: 600, color: "hsl(var(--cz-primary))",
            padding: "4px 8px", borderRadius: 6,
          }}>
            {selected.size === draftCount ? "Снять все" : "Выбрать все"}
          </button>
        </div>

        {/* Format groups */}
        {Object.keys(grouped).length === 0 ? (
          <div style={{ textAlign: "center", padding: 24, color: "hsl(var(--cz-text-muted))", fontSize: 14 }}>
            Нет доступных адаптаций для публикации
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {Object.entries(grouped).map(([format, ads]) => (
              <div key={format} style={{
                padding: "14px 16px", borderRadius: 10,
                backgroundColor: "hsl(var(--cz-bg-surface))",
                border: "1px solid hsl(var(--cz-border))",
              }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, color: "hsl(var(--cz-text-primary))", textTransform: "uppercase", letterSpacing: "0.03em" }}>
                  📝 {formatLabels[format] || format}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {ads.map((ad) => {
                    const lang = LANG_OPTIONS.find(l => l.code === ad.language);
                    const isSelected = selected.has(ad.id);
                    return (
                      <button key={ad.id} onClick={() => toggleItem(ad.id)} style={{
                        display: "flex", alignItems: "center", gap: 8,
                        padding: "8px 14px", borderRadius: 8,
                        border: isSelected
                          ? "2px solid hsl(var(--cz-success))"
                          : "1px solid hsl(var(--cz-border))",
                        backgroundColor: isSelected
                          ? "hsl(var(--cz-success) / 0.1)"
                          : "transparent",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}>
                        <span style={{
                          width: 20, height: 20, borderRadius: 5,
                          display: "flex", alignItems: "center", justifyContent: "center",
                          backgroundColor: isSelected ? "hsl(var(--cz-success))" : "transparent",
                          border: isSelected ? "none" : "2px solid hsl(var(--cz-border))",
                          transition: "all 0.15s ease",
                        }}>
                          {isSelected && <Check size={12} color="white" />}
                        </span>
                        <span style={{ fontSize: 18 }}>{lang?.flag || "🏳️"}</span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "hsl(var(--cz-text-primary))" }}>
                          {lang?.label || ad.language.toUpperCase()}
                        </span>
                        <span style={{ fontSize: 11, color: "hsl(var(--cz-text-muted))" }}>
                          {ad.channel_name || ""}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Already published */}
        {adaptations.some(a => a.status === "published") && (
          <div style={{
            padding: "10px 14px", borderRadius: 8,
            backgroundColor: "hsl(var(--cz-success) / 0.06)",
            fontSize: 13, color: "hsl(var(--cz-success))", fontWeight: 600,
          }}>
            ✅ Уже опубликовано: {adaptations.filter(a => a.status === "published").map(a => {
              const lang = LANG_OPTIONS.find(l => l.code === a.language);
              return `${lang?.flag || ""} ${formatLabels[a.content_format] || a.content_format}`;
            }).join(", ")}
          </div>
        )}

        {/* Actions */}
        <div style={{
          display: "flex", gap: 12, justifyContent: "flex-end",
          alignItems: "center", paddingTop: 12,
          borderTop: "1px solid hsl(var(--cz-border) / 0.2)",
        }}>
          <CzButton variant="ghost" size="md" onClick={onClose} style={{ flexShrink: 0 }}>
            Отмена
          </CzButton>
          <CzButton
            variant="success"
            size="md"
            icon={<Send size={14} />}
            onClick={handlePublish}
            disabled={selected.size === 0 || publishing}
            loading={publishing}
            style={{ flexShrink: 0, minWidth: 160 }}
          >
            {publishing ? "Публикуем..." : `Опубликовать (${selected.size})`}
          </CzButton>
        </div>
      </div>
    </CzDialog>
  );
}
