"use client";

import React, { useState } from "react";
import { CzCard, CzBadge, CzButton, CzEmptyState, CzSkeletonTable, CzChip, CzChipGroup } from "@/components/ui-system";
import { Sparkles, Zap, ExternalLink, Check, X, Inbox, PenTool, CheckCircle2, Archive, Send } from "lucide-react";
import { Material, Adaptation, Channel, PipelineCounts, categoryLabels, formatLabels, renderMarkdownToHtml } from "./types";
import { PipelineNav, type PipelineStatus } from "./PipelineNav";
import { InboxCard, PublishedCard, RejectedCard, InProgressCardHeader } from "./PipelineCards";
import { PublishDialog } from "./PublishDialog";

const LANG_OPTIONS: { code: string; flag: string; label: string }[] = [
  { code: "ru", flag: "🇷🇺", label: "RU" }, { code: "en", flag: "🇬🇧", label: "EN" },
  { code: "el", flag: "🇬🇷", label: "EL" }, { code: "de", flag: "🇩🇪", label: "DE" },
  { code: "uk", flag: "🇺🇦", label: "UA" }, { code: "es", flag: "🇪🇸", label: "ES" },
  { code: "fr", flag: "🇫🇷", label: "FR" }, { code: "zh", flag: "🇨🇳", label: "ZH" },
];

/* ────────── AdaptationCard (reused in "in_progress") ────────── */
function AdaptationCard({
  ad, expandedId, onToggleExpand, onAction,
}: {
  ad: Adaptation; expandedId: string | null;
  onToggleExpand: (id: string | null) => void;
  onAction: (id: string, action: "approved" | "rejected") => void;
}) {
  const isExpanded = expandedId === ad.id;

  /* Status badge config */
  const STATUS_UI: Record<string, { bg: string; color: string; label: string; pulse?: boolean }> = {
    draft: { bg: "hsl(var(--cz-warning) / 0.12)", color: "hsl(var(--cz-warning))", label: "Черновик" },
    approved: { bg: "hsl(var(--cz-accent) / 0.15)", color: "hsl(var(--cz-accent))", label: "⏳ Публикуется...", pulse: true },
    published: { bg: "hsl(var(--cz-success) / 0.12)", color: "hsl(var(--cz-success))", label: "✅ Опубликовано" },
    rejected: { bg: "hsl(var(--cz-error) / 0.12)", color: "hsl(var(--cz-error))", label: "Отклонён" },
  };
  const sui = STATUS_UI[ad.status] || STATUS_UI.draft;

  return (
    <div className="cz-card-inner" style={{
      padding: "16px 20px", borderRadius: 12,
      backgroundColor: "hsl(var(--cz-bg-surface))", border: "1px solid hsl(var(--cz-border))",
      opacity: ad.status === "rejected" ? 0.5 : 1,
      transition: "opacity 0.3s ease",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>{ad.channel_name || "Канал"}</span>
          <CzBadge variant="info">{formatLabels[ad.content_format] || ad.content_format}</CzBadge>
          <span style={{ fontSize: 13, fontWeight: 600 }}>
            {LANG_OPTIONS.find(l => l.code === ad.language)?.flag} {ad.language.toUpperCase()}
          </span>
          <span style={{
            padding: "3px 10px", fontSize: 11, fontWeight: 700, borderRadius: 6,
            backgroundColor: sui.bg, color: sui.color,
            animation: sui.pulse ? "cz-pulse 1.5s ease-in-out infinite" : undefined,
          }}>{sui.label}</span>
        </div>
        <button onClick={() => onToggleExpand(isExpanded ? null : ad.id)} style={{
          background: "none", border: "none", cursor: "pointer", fontSize: 12,
          color: "hsl(var(--cz-text-muted))", padding: "4px 8px", borderRadius: 4,
        }}>{isExpanded ? "▲ Свернуть" : "▼ Развернуть"}</button>
      </div>

      {isExpanded && (
        <>
          {ad.headline && <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 6, color: "hsl(var(--cz-text-primary))" }}>{ad.headline}</div>}
          <div style={{
            fontSize: 14, lineHeight: 1.65, color: "hsl(var(--cz-text-secondary))",
            maxHeight: 320, overflowY: "auto", paddingRight: 8,
          }} dangerouslySetInnerHTML={{ __html: renderMarkdownToHtml(ad.body) }} />
          {ad.status === "draft" && (
            <div style={{ display: "flex", gap: 10, marginTop: 12, justifyContent: "flex-end", alignItems: "center" }}>
              <button onClick={() => onAction(ad.id, "rejected")} style={{
                display: "flex", alignItems: "center", gap: 5, padding: "7px 14px", borderRadius: 7,
                border: "1px solid hsl(var(--cz-border) / 0.5)", cursor: "pointer", fontSize: 13, fontWeight: 600,
                backgroundColor: "transparent", color: "hsl(var(--cz-text-muted))",
              }}><X size={14} /> Отклонить</button>
              <button onClick={() => onAction(ad.id, "approved")} style={{
                display: "flex", alignItems: "center", gap: 5, padding: "7px 16px", borderRadius: 7,
                border: "none", cursor: "pointer", fontSize: 13, fontWeight: 700,
                backgroundColor: "hsl(var(--cz-success))", color: "white",
              }}><Check size={14} /> Одобрить и опубликовать</button>
            </div>
          )}
          {ad.status === "approved" && (
            <div style={{ marginTop: 12, padding: "8px 14px", borderRadius: 8, backgroundColor: "hsl(var(--cz-accent) / 0.08)", fontSize: 13, color: "hsl(var(--cz-accent))", fontWeight: 600, textAlign: "center" }}>
              ⏳ Отправляется в канал...
            </div>
          )}
          {ad.status === "published" && (
            <div style={{ marginTop: 12, padding: "8px 14px", borderRadius: 8, backgroundColor: "hsl(var(--cz-success) / 0.08)", fontSize: 13, color: "hsl(var(--cz-success))", fontWeight: 600, textAlign: "center" }}>
              ✅ Успешно опубликовано в канал
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ────────── Empty state config ────────── */
const EMPTY_STATES: Record<PipelineStatus, { icon: React.ReactNode; title: string; text: string }> = {
  inbox: { icon: <Inbox size={56} />, title: "Нет входящих", text: "Новые рекомендации появятся после AI-оценки" },
  in_progress: { icon: <PenTool size={56} />, title: "Нет новостей в работе", text: "Перейдите во «Входящие» и возьмите новость в работу" },
  published: { icon: <CheckCircle2 size={56} />, title: "Ничего не опубликовано", text: "Публикации появятся здесь после одобрения адаптаций" },
  rejected: { icon: <Archive size={56} />, title: "Нет отклонённых", text: "Отклонённые новости будут здесь" },
};

/* ────────── Main Tab ────────── */
interface RecommendationsTabProps {
  materials: Material[];
  adaptations: Record<string, Adaptation[]>;
  channels: Channel[];
  loading: boolean;
  onlyRecommended: boolean;
  setOnlyRecommended: (v: boolean) => void;
  categoryFilter: string;
  setCategoryFilter: (v: string) => void;
  availableCategories: { category: string; count: number }[];
  onAdaptationAction: (id: string, action: "approved" | "rejected") => void;
  onGenerateFormat: (materialId: string, channelId: string, fmt: string, lang: string) => void;
  generatingFormats: Record<string, boolean>;
  pipelineStatus: PipelineStatus;
  setPipelineStatus: (s: PipelineStatus) => void;
  pipelineCounts: PipelineCounts;
  dateFrom: string;
  setDateFrom: (v: string) => void;
  onPipelineAction: (scoreId: string, newStatus: PipelineStatus) => void;
  exitingCards?: Set<string>;
  publishDialogScoreId: string | null;
  onOpenPublishDialog: (scoreId: string) => void;
  onClosePublishDialog: () => void;
  onBatchPublish: (scoreId: string, adaptationIds: string[]) => void;
  publishingBatch?: boolean;
  onGenerateCover?: (materialId: string) => void;
  generatingCovers?: Record<string, boolean>;
}

export function RecommendationsTab({
  materials, adaptations, channels, loading,
  onlyRecommended, setOnlyRecommended,
  categoryFilter, setCategoryFilter, availableCategories,
  onAdaptationAction, onGenerateFormat, generatingFormats,
  pipelineStatus, setPipelineStatus, pipelineCounts,
  dateFrom, setDateFrom, onPipelineAction, exitingCards,
  publishDialogScoreId, onOpenPublishDialog, onClosePublishDialog, onBatchPublish, publishingBatch,
  onGenerateCover, generatingCovers,
}: RecommendationsTabProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const empty = EMPTY_STATES[pipelineStatus];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Pipeline navigation */}
      <PipelineNav
        active={pipelineStatus} counts={pipelineCounts}
        dateFrom={dateFrom}
        onChangeStatus={setPipelineStatus} onChangeDate={setDateFrom}
      />

      {/* Filter bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, color: "hsl(var(--cz-text-secondary))", cursor: "pointer" }}>
          <input type="checkbox" checked={onlyRecommended} onChange={(e) => setOnlyRecommended(e.target.checked)}
            style={{ accentColor: "hsl(var(--cz-primary))", width: 18, height: 18 }} />
          Только рекомендованные
        </label>
        <span style={{ fontSize: 14, color: "hsl(var(--cz-text-muted))" }}>{materials.length} материалов</span>
      </div>

      {/* Category chips */}
      {availableCategories.length > 0 && (
        <div style={{ marginBottom: 0 }}>
          <CzChipGroup>
            <CzChip label="Все" active={!categoryFilter} onClick={() => setCategoryFilter("")} />
            {availableCategories.map((cat) => {
              const info = categoryLabels[cat.category];
              return (
                <CzChip key={cat.category} active={categoryFilter === cat.category}
                  label={`${info?.emoji || "📰"} ${info?.label || cat.category}`}
                  count={cat.count}
                  onClick={() => setCategoryFilter(categoryFilter === cat.category ? "" : cat.category)} />
              );
            })}
          </CzChipGroup>
        </div>
      )}

      {/* Material cards — stage-specific rendering */}
      {loading ? (
        <CzSkeletonTable rows={3} />
      ) : materials.length === 0 ? (
        <CzEmptyState icon={empty.icon} title={empty.title} text={empty.text} />
      ) : (
        <div className="stagger-children" style={{ display: "flex", flexDirection: "column", gap: pipelineStatus === "rejected" ? 6 : 20 }}>
          {materials.map((m) => {
            const isExiting = exitingCards?.has(m.id);
            /* ── INBOX ── */
            if (pipelineStatus === "inbox") {
              return <div key={m.id} className={isExiting ? "cz-card-exiting" : ""}><InboxCard m={m}
                onTake={(id) => onPipelineAction(id, "in_progress")}
                onReject={(id) => onPipelineAction(id, "rejected")} /></div>;
            }

            /* ── PUBLISHED ── */
            if (pipelineStatus === "published") {
              return <PublishedCard key={m.id} m={m} />;
            }

            /* ── REJECTED ── */
            if (pipelineStatus === "rejected") {
              return <div key={m.id} className={isExiting ? "cz-card-exiting" : ""}><RejectedCard m={m}
                onRestore={(id) => onPipelineAction(id, "inbox")} /></div>;
            }

            /* ── IN_PROGRESS — full card with adaptations ── */
            const materialId = m.material_id || m.id;
            const matAdapts = adaptations[materialId] || [];
            const generatingItems: { key: string; channelId: string; format: string; lang: string; channelName: string }[] = [];
            Object.keys(generatingFormats).forEach((gk) => {
              if (!generatingFormats[gk] || !gk.startsWith(`${materialId}::`)) return;
              const parts = gk.split("::");
              if (parts.length !== 4) return;
              const ch = channels.find((c) => c.id === parts[1]);
              generatingItems.push({ key: gk, channelId: parts[1], format: parts[2], lang: parts[3], channelName: ch?.name || "Канал" });
            });
            const totalCount = matAdapts.length + generatingItems.length;
            const hasDrafts = matAdapts.some(a => a.status === "draft");

            return (
              <div key={m.id} className={isExiting ? "cz-card-exiting" : ""}>
              <CzCard padding="lg">
                <InProgressCardHeader m={m} onGenerateCover={onGenerateCover} generatingCover={generatingCovers?.[m.material_id || m.id]} />

                {/* Adaptations block */}
                <div style={{ padding: 16, borderRadius: 12, backgroundColor: "hsl(var(--cz-bg-base) / 0.5)", border: "1px solid hsl(var(--cz-border) / 0.5)" }}>
                  <div style={{ marginBottom: 12, fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", color: "hsl(var(--cz-text-muted))" }}>
                    ✍️ Каналы и адаптации {totalCount > 0 && `(${totalCount})`}
                  </div>

                  {totalCount > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      {matAdapts.map((ad) => (
                        <AdaptationCard key={ad.id} ad={ad} expandedId={expandedId}
                          onToggleExpand={setExpandedId} onAction={onAdaptationAction} />
                      ))}
                      {/* Skeleton cards for generating */}
                      {generatingItems.map((gi) => {
                        const langOpt = LANG_OPTIONS.find((l) => l.code === gi.lang);
                        return (
                          <div key={gi.key} style={{
                            padding: "14px 18px", borderRadius: 10,
                            backgroundColor: "hsl(var(--cz-bg-surface))",
                            border: "1px dashed hsl(var(--cz-accent) / 0.4)",
                            animation: "cz-pulse 2s ease-in-out infinite",
                          }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                              <span style={{ fontSize: 14, fontWeight: 600 }}>{gi.channelName}</span>
                              <CzBadge variant="info">{formatLabels[gi.format] || gi.format}</CzBadge>
                              <span style={{ fontSize: 13, fontWeight: 600 }}>{langOpt?.flag} {gi.lang.toUpperCase()}</span>
                              <span style={{ padding: "3px 10px", fontSize: 11, fontWeight: 700, borderRadius: 5, backgroundColor: "hsl(var(--cz-accent) / 0.12)", color: "hsl(var(--cz-accent))" }}>⏳ AI генерирует...</span>
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                              <div style={{ height: 16, width: "70%", borderRadius: 5, backgroundColor: "hsl(var(--cz-border) / 0.4)" }} />
                              <div style={{ height: 12, width: "100%", borderRadius: 4, backgroundColor: "hsl(var(--cz-border) / 0.25)" }} />
                              <div style={{ height: 12, width: "85%", borderRadius: 4, backgroundColor: "hsl(var(--cz-border) / 0.2)" }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div style={{ padding: 16, textAlign: "center", color: "hsl(var(--cz-text-muted))", fontSize: 14 }}>
                      ⏳ AI готовит адаптации для каналов...
                    </div>
                  )}

                  {/* Add format / language buttons */}
                  {(() => {
                    const existingKeys = new Set<string>();
                    matAdapts.forEach((ad) => existingKeys.add(`${ad.channel_id}::${ad.content_format}::${ad.language}`));
                    const channelIds = [...new Set(matAdapts.map((ad) => ad.channel_id))];
                    const fmtBtns: React.ReactNode[] = [];
                    const lngBtns: React.ReactNode[] = [];
                    channelIds.forEach((chId) => {
                      const ch = channels.find((c) => c.id === chId);
                      if (!ch) return;
                      ch.content_formats.forEach((fmt) => {
                        const pLang = ch.languages[0] || "ru";
                        if (existingKeys.has(`${chId}::${fmt}::${pLang}`)) return;
                        const gk = `${materialId}::${chId}::${fmt}::${pLang}`;
                        if (generatingFormats[gk]) return;
                        fmtBtns.push(
                          <CzButton key={gk} variant="outline" size="sm" icon={<Sparkles size={13} />}
                            onClick={() => onGenerateFormat(materialId, chId, fmt, pLang)}>
                            {`${ch.name}: ${formatLabels[fmt] || fmt}`}
                          </CzButton>
                        );
                      });
                      if (ch.languages.length > 1) {
                        const uFmts = [...new Set(matAdapts.filter((a) => a.channel_id === chId).map((a) => a.content_format))];
                        uFmts.forEach((fmt) => {
                          ch.languages.forEach((lang) => {
                            if (existingKeys.has(`${chId}::${fmt}::${lang}`)) return;
                            const gk = `${materialId}::${chId}::${fmt}::${lang}`;
                            if (generatingFormats[gk]) return;
                            const lo = LANG_OPTIONS.find((l) => l.code === lang);
                            lngBtns.push(
                              <CzButton key={gk} variant="outline" size="sm" icon={<Sparkles size={13} />}
                                onClick={() => onGenerateFormat(materialId, chId, fmt, lang)}>
                                {`${lo?.flag || ""} ${lang.toUpperCase()}: ${formatLabels[fmt] || fmt}`}
                              </CzButton>
                            );
                          });
                        });
                      }
                    });
                    if (!fmtBtns.length && !lngBtns.length) return null;
                    return (
                      <div style={{ marginTop: 12, paddingTop: 10, borderTop: "1px dashed hsl(var(--cz-border) / 0.3)" }}>
                        {fmtBtns.length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", marginBottom: lngBtns.length > 0 ? 6 : 0 }}>
                            <span style={{ fontSize: 11, fontWeight: 700, color: "hsl(var(--cz-text-muted))", textTransform: "uppercase", letterSpacing: "0.03em" }}>+ формат</span>
                            {fmtBtns}
                          </div>
                        )}
                        {lngBtns.length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
                            <span style={{ fontSize: 11, fontWeight: 700, color: "hsl(var(--cz-text-muted))", textTransform: "uppercase", letterSpacing: "0.03em" }}>🌐 язык</span>
                            {lngBtns}
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>

                {/* ── ЕДИНАЯ КНОПКА ПУБЛИКАЦИИ ── */}
                {hasDrafts && (
                  <div style={{
                    display: "flex", justifyContent: "flex-end", alignItems: "center",
                    marginTop: 16, paddingTop: 16, gap: 12,
                    borderTop: "1px solid hsl(var(--cz-border) / 0.2)",
                  }}>
                    <CzButton variant="ghost" size="sm"
                      onClick={() => onPipelineAction(m.id, "inbox")}
                      style={{ flexShrink: 0 }}>
                      ↩️ Вернуть
                    </CzButton>
                    <CzButton variant="success" size="md"
                      onClick={() => onOpenPublishDialog(m.id)}
                      icon={<Send size={15} />}
                      style={{ flexShrink: 0 }}>
                      Опубликовать
                    </CzButton>
                  </div>
                )}
              </CzCard>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Publish Dialog ── */}
      {(() => {
        if (!publishDialogScoreId) return null;
        const m = materials.find(mat => mat.id === publishDialogScoreId);
        if (!m) return null;
        const materialId = m.material_id || m.id;
        const matAdapts = adaptations[materialId] || [];
        const title = m.headline_ru || m.material_title || m.title || "Без заголовка";
        return (
          <PublishDialog
            open={true}
            onClose={onClosePublishDialog}
            adaptations={matAdapts}
            materialTitle={title}
            onPublish={(ids) => onBatchPublish(publishDialogScoreId, ids)}
            publishing={publishingBatch}
          />
        );
      })()}
    </div>
  );
}
