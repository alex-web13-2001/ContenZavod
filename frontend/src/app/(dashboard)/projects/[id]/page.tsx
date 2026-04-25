"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { CzPageHeader, CzTabs, CzSkeleton, useToast } from "@/components/ui-system";
import { ArrowLeft, Sparkles, Send, Settings } from "lucide-react";
import Link from "next/link";

import { Project, Channel, Material, Adaptation, PipelineCounts } from "./_components/types";
import { RecommendationsTab } from "./_components/RecommendationsTab";
import { ChannelsTab } from "./_components/ChannelsTab";
import { SettingsTab } from "./_components/SettingsTab";

const TAB_OPTIONS = [
  { key: "recommendations" as const, label: "Рекомендации", icon: Sparkles },
  { key: "channels" as const, label: "Каналы", icon: Send },
  { key: "settings" as const, label: "Настройки", icon: Settings },
];

export type PipelineStatus = "inbox" | "in_progress" | "published" | "rejected";

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [adaptations, setAdaptations] = useState<Record<string, Adaptation[]>>({});
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"recommendations" | "channels" | "settings">("recommendations");
  const [onlyRecommended, setOnlyRecommended] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [availableCategories, setAvailableCategories] = useState<{ category: string; count: number }[]>([]);
  const [generatingFormats, setGeneratingFormats] = useState<Record<string, boolean>>({});
  const [exitingCards, setExitingCards] = useState<Set<string>>(new Set());
  const initialLoadDone = useRef(false);
  const { showToast } = useToast();

  // Pipeline state
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>("inbox");
  const [pipelineCounts, setPipelineCounts] = useState<PipelineCounts>({ inbox: 0, in_progress: 0, published: 0, rejected: 0 });
  const [dateFrom, setDateFrom] = useState<string>("");

  /* ────── Data fetching ────── */
  const fetchProject = useCallback(async () => {
    try { setProject(await api.get<Project>(`/projects/${projectId}`)); } catch (e) { console.error(e); }
  }, [projectId]);

  const fetchChannels = useCallback(async () => {
    try {
      const data = await api.get<{ items: Channel[] }>(`/channels?project_id=${projectId}`);
      setChannels(data.items);
    } catch (e) { console.error(e); }
  }, [projectId]);

  const fetchRecommendationsAndAdaptations = useCallback(async (opts?: { silent?: boolean }) => {
    // Only show loading skeleton on the very first load
    if (!opts?.silent && !initialLoadDone.current) setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("per_page", "50");
      params.set("recommended_only", onlyRecommended ? "true" : "false");
      params.set("pipeline_status", pipelineStatus);
      if (categoryFilter) params.set("category", categoryFilter);
      if (dateFrom) params.set("date_from", dateFrom);

      const [recsData, adapData, catsData] = await Promise.all([
        api.get<{ items: Material[]; total: number; pipeline_counts: PipelineCounts }>(`/projects/${projectId}/recommendations?${params}`),
        // Only fetch adaptations for in_progress tab (others don't need them)
        pipelineStatus === "in_progress"
          ? api.get<{ items: Adaptation[] }>(`/adaptations?project_id=${projectId}&per_page=200`)
          : Promise.resolve({ items: [] as Adaptation[] }),
        api.get<{ category: string; count: number }[]>(`/projects/${projectId}/categories`),
      ]);

      setMaterials(recsData.items.map((m) => ({
        ...m,
        title: m.material_title || "Untitled",
        original_url: m.material_url || "",
        project_relevance_score: m.relevance_score,
        project_hype_score: m.hype_score,
        project_explanation: m.explanation,
      })));
      setPipelineCounts(recsData.pipeline_counts);
      setAvailableCategories(catsData);

      const grouped: Record<string, Adaptation[]> = {};
      for (const a of adapData.items) {
        if (!grouped[a.material_id]) grouped[a.material_id] = [];
        grouped[a.material_id].push(a);
      }
      setAdaptations(grouped);
      initialLoadDone.current = true;
    } finally { setLoading(false); }
  }, [projectId, onlyRecommended, categoryFilter, pipelineStatus, dateFrom]);

  /* ────── Actions ────── */
  const handleAdaptationAction = async (adaptationId: string, action: "approved" | "rejected") => {
    // Optimistic update: immediately reflect status in UI without re-fetching
    setAdaptations((prev) => {
      const next = { ...prev };
      for (const matId of Object.keys(next)) {
        next[matId] = next[matId].map((a) =>
          a.id === adaptationId ? { ...a, status: action } : a
        );
      }
      return next;
    });
    try {
      await api.patch(`/adaptations/${adaptationId}`, { status: action });
      if (action === "approved") {
        showToast("📤 Публикация запущена...", "info");
        // Poll for completion
        setTimeout(async () => {
          await fetchRecommendationsAndAdaptations({ silent: true });
          showToast("✅ Опубликовано!", "success");
        }, 3000);
      } else {
        showToast("Адаптация отклонена", "info");
        setTimeout(() => fetchRecommendationsAndAdaptations({ silent: true }), 1500);
      }
    } catch (e) {
      console.error(e);
      showToast("Ошибка при обновлении", "error");
      fetchRecommendationsAndAdaptations({ silent: true });
    }
  };

  const handlePipelineAction = async (scoreId: string, newStatus: PipelineStatus) => {
    // Animate card exit
    setExitingCards((prev) => new Set(prev).add(scoreId));

    const TOAST_MESSAGES: Record<string, { msg: string; variant: "success" | "info" }> = {
      in_progress: { msg: "✅ Взято в работу — AI генерирует адаптации...", variant: "success" },
      rejected: { msg: "🗑 Материал отклонён", variant: "info" },
      inbox: { msg: "↩️ Материал возвращён во Входящие", variant: "success" },
    };

    // Wait for exit animation, then remove from state
    setTimeout(() => {
      setMaterials((prev) => prev.filter((m) => m.id !== scoreId));
      setExitingCards((prev) => { const next = new Set(prev); next.delete(scoreId); return next; });
      setPipelineCounts((prev) => ({
        ...prev,
        [pipelineStatus]: Math.max(0, prev[pipelineStatus] - 1),
        [newStatus]: prev[newStatus] + 1,
      }));

      const t = TOAST_MESSAGES[newStatus];
      if (t) showToast(t.msg, t.variant);
    }, 400);

    try {
      await api.patch(`/projects/${projectId}/recommendations/${scoreId}/status`, { status: newStatus });
      setTimeout(() => fetchRecommendationsAndAdaptations({ silent: true }), 2000);
    } catch (e) {
      console.error(e);
      showToast("Ошибка при перемещении", "error");
      setExitingCards((prev) => { const next = new Set(prev); next.delete(scoreId); return next; });
      fetchRecommendationsAndAdaptations({ silent: true });
    }
  };

  /* ────── Batch Publish (new flow) ────── */
  const [publishDialogScoreId, setPublishDialogScoreId] = useState<string | null>(null);
  const [publishingBatch, setPublishingBatch] = useState(false);
  const [generatingCovers, setGeneratingCovers] = useState<Record<string, boolean>>({});

  const handleOpenPublishDialog = (scoreId: string) => {
    setPublishDialogScoreId(scoreId);
  };

  const handleBatchPublish = async (scoreId: string, adaptationIds: string[]) => {
    setPublishingBatch(true);
    try {
      const resp = await api.post<{ editorial_status: string }>(`/projects/${projectId}/recommendations/${scoreId}/publish-batch`, {
        adaptation_ids: adaptationIds,
      });

      setPublishDialogScoreId(null);

      // Mark published adaptations optimistically
      setAdaptations((prev) => {
        const next = { ...prev };
        for (const matId of Object.keys(next)) {
          next[matId] = next[matId].map((a) =>
            adaptationIds.includes(a.id) ? { ...a, status: "approved" } : a
          );
        }
        return next;
      });

      // If backend says material moved to 'published' (all adaptations done),
      // animate card exit from in_progress
      if (resp.editorial_status === "published") {
        setExitingCards((prev) => new Set(prev).add(scoreId));
        setTimeout(() => {
          setMaterials((prev) => prev.filter((m) => m.id !== scoreId));
          setExitingCards((prev) => { const next = new Set(prev); next.delete(scoreId); return next; });
          setPipelineCounts((prev) => ({
            ...prev,
            in_progress: Math.max(0, prev.in_progress - 1),
            published: prev.published + 1,
          }));
        }, 400);
      }

      showToast(`📤 Опубликовано (${adaptationIds.length}) — отправляется в каналы`, "success");

      // Sync to get updated state
      setTimeout(() => fetchRecommendationsAndAdaptations({ silent: true }), 3000);
    } catch (e) {
      console.error(e);
      showToast("Ошибка при публикации", "error");
    } finally {
      setPublishingBatch(false);
    }
  };

  /* ────── Cover Image Generation (per adaptation) ────── */
  const handleGenerateCover = async (adaptationId: string) => {
    setGeneratingCovers((prev) => ({ ...prev, [adaptationId]: true }));

    // Optimistic UI: immediately show "generating" in adaptation state
    setAdaptations((prev) => {
      const next = { ...prev };
      for (const matId of Object.keys(next)) {
        next[matId] = next[matId].map((a) =>
          a.id === adaptationId ? { ...a, cover_status: "generating" } : a
        );
      }
      return next;
    });

    try {
      await api.post(`/projects/${projectId}/adaptations/${adaptationId}/generate-cover`);
      showToast("🎨 Генерация обложки запущена", "info");

      // Poll by directly fetching adaptations from API
      const pollCover = async (attempt: number) => {
        if (attempt > 40) {
          setGeneratingCovers((prev) => ({ ...prev, [adaptationId]: false }));
          showToast("⏳ Генерация обложки заняла слишком долго", "error");
          return;
        }

        await new Promise((r) => setTimeout(r, 5000));

        try {
          // Fetch fresh adaptations directly from API
          const data = await api.get<{ items: Adaptation[] }>(
            `/adaptations?project_id=${projectId}&per_page=200`
          );
          const freshAd = data.items.find((a) => a.id === adaptationId);

          if (freshAd?.cover_status === "ready" || freshAd?.cover_status === "error") {
            // Update adaptations state with fresh data
            const grouped: Record<string, Adaptation[]> = {};
            for (const a of data.items) {
              if (!grouped[a.material_id]) grouped[a.material_id] = [];
              grouped[a.material_id].push(a);
            }
            setAdaptations(grouped);
            setGeneratingCovers((prev) => ({ ...prev, [adaptationId]: false }));

            if (freshAd.cover_status === "ready") {
              showToast("✅ Обложка готова!", "success");
            } else {
              showToast("❌ Ошибка генерации обложки", "error");
            }
          } else {
            // Not ready yet — continue polling
            pollCover(attempt + 1);
          }
        } catch {
          pollCover(attempt + 1);
        }
      };

      pollCover(0);
    } catch (e) {
      console.error(e);
      setGeneratingCovers((prev) => ({ ...prev, [adaptationId]: false }));
      // Revert optimistic update
      setAdaptations((prev) => {
        const next = { ...prev };
        for (const matId of Object.keys(next)) {
          next[matId] = next[matId].map((a) =>
            a.id === adaptationId ? { ...a, cover_status: null } : a
          );
        }
        return next;
      });
      showToast("Ошибка запуска генерации обложки", "error");
    }
  };

  const handleGenerateFormat = async (materialId: string, channelId: string, contentFormat: string, language: string = "ru") => {
    const key = `${materialId}::${channelId}::${contentFormat}::${language}`;
    setGeneratingFormats((prev) => ({ ...prev, [key]: true }));

    const pollUntilReady = (attempts: number) => {
      if (attempts <= 0) { setGeneratingFormats((p) => ({ ...p, [key]: false })); return; }
      setTimeout(async () => {
        await fetchRecommendationsAndAdaptations({ silent: true });
        // Check if adaptation now exists in the data — if so, clear skeleton
        // We re-read from the latest state via a callback
        setAdaptations((current) => {
          const matAdapts = current[materialId] || [];
          const found = matAdapts.some((a) => a.channel_id === channelId && a.content_format === contentFormat && a.language === language);
          if (found) {
            setGeneratingFormats((p) => ({ ...p, [key]: false }));
          } else {
            pollUntilReady(attempts - 1);
          }
          return current; // no mutation
        });
      }, 4000);
    };

    try {
      await api.post("/adaptations/generate", { material_id: materialId, channel_id: channelId, content_format: contentFormat, language });
      // Poll until adaptation appears (max ~6 attempts = ~24 seconds)
      pollUntilReady(6);
    } catch (e: unknown) {
      const err = e as { status?: number };
      if (err?.status === 409) {
        // Adaptation already exists — refresh to show it, then remove skeleton
        await fetchRecommendationsAndAdaptations({ silent: true });
      } else {
        console.error(e);
      }
      setGeneratingFormats((p) => ({ ...p, [key]: false }));
    }
  };

  const handleCreateChannel = async (form: { name: string; channel_type: string; content_formats: string[]; tone_of_voice: string; formatting_rules: string; languages: string[]; bot_token: string; chat_id: string; endpoints: Record<string, string> }) => {
    const { bot_token, chat_id, endpoints, ...rest } = form;
    // Build per-language endpoints config
    const endpointsCfg: Record<string, { chat_id: string }> = {};
    Object.entries(endpoints).forEach(([lang, cid]) => { if (cid) endpointsCfg[lang] = { chat_id: cid }; });
    const config: Record<string, unknown> = { bot_token, chat_id };
    if (Object.keys(endpointsCfg).length > 0) config.endpoints = endpointsCfg;
    await api.post("/channels", { ...rest, project_id: projectId, config });
    fetchChannels();
  };

  const handleSaveChannel = async (channelId: string, form: { name: string; channel_type: string; content_formats: string[]; tone_of_voice: string; formatting_rules: string; languages: string[]; bot_token: string; chat_id: string; endpoints: Record<string, string>; is_active?: boolean }) => {
    const { bot_token, chat_id, endpoints, ...rest } = form;
    // Build per-language endpoints config
    const endpointsCfg: Record<string, { chat_id: string }> = {};
    Object.entries(endpoints).forEach(([lang, cid]) => { if (cid) endpointsCfg[lang] = { chat_id: cid }; });
    const config: Record<string, unknown> = { bot_token, chat_id };
    if (Object.keys(endpointsCfg).length > 0) config.endpoints = endpointsCfg;
    await api.patch(`/channels/${channelId}`, { ...rest, config });
    fetchChannels();
  };

  const handleDeleteChannel = async (channelId: string) => {
    await api.delete(`/channels/${channelId}`);
    fetchChannels();
  };

  const handleSaveProject = async (form: { name: string; description: string; topic_guidelines: string; target_audience: string }) => {
    await api.patch(`/projects/${projectId}`, form);
    fetchProject();
  };

  /* ────── Effects ────── */
  useEffect(() => { fetchProject(); fetchChannels(); }, [fetchProject, fetchChannels]);
  useEffect(() => { if (tab === "recommendations") fetchRecommendationsAndAdaptations(); }, [tab, fetchRecommendationsAndAdaptations]);

  /* ────── Render ────── */
  if (!project) {
    return (
      <div className="cz-page">
        <CzSkeleton variant="card" count={3} />
      </div>
    );
  }

  return (
    <div className="cz-page">
      {/* Breadcrumb */}
      <Link href="/projects" className="cz-breadcrumb-link">
        <ArrowLeft size={14} /> Проекты
      </Link>

      {/* Header */}
      <CzPageHeader title={project.name} subtitle={project.description}>
        <div className="cz-flex-center cz-flex-shrink-0" style={{
          width: 44, height: 44, borderRadius: "var(--cz-radius-md)",
          background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
          color: "white", fontSize: 18, fontWeight: 700,
        }}>
          {project.name.charAt(0).toUpperCase()}
        </div>
      </CzPageHeader>

      {/* Tabs */}
      <CzTabs tabs={TAB_OPTIONS.map(t => ({ id: t.key, label: t.label, icon: <t.icon size={16} /> }))}
        activeTab={tab} onChange={(k) => setTab(k as typeof tab)} />

      {/* Tab content */}
      {tab === "recommendations" && (
        <RecommendationsTab
          materials={materials} adaptations={adaptations} channels={channels} loading={loading}
          onlyRecommended={onlyRecommended} setOnlyRecommended={setOnlyRecommended}
          categoryFilter={categoryFilter} setCategoryFilter={setCategoryFilter}
          availableCategories={availableCategories}
          onAdaptationAction={handleAdaptationAction}
          onGenerateFormat={handleGenerateFormat}
          generatingFormats={generatingFormats}
          pipelineStatus={pipelineStatus}
          setPipelineStatus={setPipelineStatus}
          pipelineCounts={pipelineCounts}
          dateFrom={dateFrom}
          setDateFrom={setDateFrom}
          onPipelineAction={handlePipelineAction}
          exitingCards={exitingCards}
          publishDialogScoreId={publishDialogScoreId}
          onOpenPublishDialog={handleOpenPublishDialog}
          onClosePublishDialog={() => setPublishDialogScoreId(null)}
          onBatchPublish={handleBatchPublish}
          publishingBatch={publishingBatch}
          onGenerateCover={handleGenerateCover}
          generatingCovers={generatingCovers}
        />
      )}

      {tab === "channels" && (
        <ChannelsTab
          channels={channels} projectId={projectId}
          onCreateChannel={handleCreateChannel}
          onSaveChannel={handleSaveChannel}
          onDeleteChannel={handleDeleteChannel}
        />
      )}

      {tab === "settings" && <SettingsTab project={project} onSave={handleSaveProject} />}
    </div>
  );
}
