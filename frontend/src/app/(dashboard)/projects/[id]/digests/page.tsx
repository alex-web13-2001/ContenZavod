"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import Link from "next/link";
import {
  ArrowLeft, Plus, Sparkles, Play, Download, Trash2, Loader2,
  RefreshCw, Clock, CheckCircle2, XCircle, FileText, Film,Video,
} from "lucide-react";

/* ── Types ─────────────────────────────────────── */

interface Digest {
  id: string; title: string; script_text: string | null; language: string;
  material_ids: string[]; revid_status: string; video_url: string | null;
  thumbnail_url: string | null; duration_seconds: number | null;
  error_message: string | null; created_at: string; updated_at: string;
  config: Record<string, unknown>;
}

interface Material {
  id: string; material_id: string; material_title: string;
  headline_ru: string | null; summary_ru: string | null;
  relevance_score: number; hype_score: number;
  editorial_status: string;
}

/* ── Helpers ───────────────────────────────────── */

const STATUS_CFG: Record<string, { label: string; color: string; spinning?: boolean }> = {
  draft:              { label: "Черновик",          color: "#888" },
  script_generating:  { label: "ИИ пишет скрипт…", color: "#e8a735", spinning: true },
  script_ready:       { label: "Скрипт готов",      color: "#4ade80" },
  rendering:          { label: "Рендер видео…",     color: "#60a5fa", spinning: true },
  ready:              { label: "Готово",             color: "#4ade80" },
  failed:             { label: "Ошибка",            color: "#f87171" },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_CFG[status] || STATUS_CFG.draft;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, color: s.color, fontWeight: 500 }}>
      {s.spinning
        ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
        : status === "failed" ? <XCircle size={14} />
        : status === "ready" || status === "script_ready" ? <CheckCircle2 size={14} />
        : <FileText size={14} />}
      {s.label}
    </span>
  );
}

const wc = (t: string) => t.trim().split(/\s+/).filter(Boolean).length;
const estSec = (t: string) => Math.round(wc(t) / 2.5);

/* ── Page ──────────────────────────────────────── */

export default function DigestsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [digests, setDigests] = useState<Digest[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [mats, setMats] = useState<Material[]>([]);
  const [matsLoading, setMatsLoading] = useState(false);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [creating, setCreating] = useState(false);
  const [detail, setDetail] = useState<Digest | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  // ── Video settings (persisted to localStorage) ──
  const SETTINGS_KEY = `cz_video_settings_${projectId}`;
  const defaultSettings = {
    // Avatar
    avatarUrl: "https://cdn.revid.ai/uploads/1777969137819-image.png",
    avatarImageModel: "good" as string,
    removeBackground: true,
    // Voice
    voiceId: "Qvbf0AoA7UZSgJUp8Ba5",
    voiceSpeed: 1,
    voiceLanguage: "ru" as string,
    // Media
    mediaType: "stock-video" as string,
    mediaDensity: "medium" as string,
    mediaImageModel: "good" as string,
    videoModel: "base" as string,
    bRollType: "fullscreen" as string,
    placeAvatarInContext: true,
    // Captions
    captionsEnabled: true,
    captionsPreset: "Hormozi" as string,
    captionsPosition: "bottom" as string,
    // Music
    musicEnabled: false,
    // Format
    aspectRatio: "9 / 16" as string,
    disableAudio: true,
    // Provided media
    providedMedia: [] as { url: string; title: string; type: string }[],
  };
  type VideoSettings = typeof defaultSettings;

  const [vs, setVsRaw] = useState<VideoSettings>(() => {
    if (typeof window === "undefined") return defaultSettings;
    try {
      const saved = localStorage.getItem(SETTINGS_KEY);
      return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
    } catch { return defaultSettings; }
  });

  const setVs = (patch: Partial<VideoSettings>) => {
    setVsRaw(prev => {
      const next = { ...prev, ...patch };
      try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  };

  /* ── Fetch ─────────────────────────────────── */

  const fetchDigests = useCallback(async () => {
    try {
      const d = await api.get<{ items: Digest[] }>(`/digests?project_id=${projectId}`);
      setDigests(d.items);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [projectId]);

  const fetchMaterials = useCallback(async () => {
    setMatsLoading(true);
    try {
      const [prog, pub] = await Promise.all([
        api.get<{ items: Material[] }>(`/projects/${projectId}/recommendations?per_page=50&pipeline_status=in_progress`),
        api.get<{ items: Material[] }>(`/projects/${projectId}/recommendations?per_page=50&pipeline_status=published`),
      ]);
      setMats([...prog.items, ...pub.items]);
    } catch (e) { console.error(e); }
    finally { setMatsLoading(false); }
  }, [projectId]);

  const loadDetail = useCallback(async (id: string) => {
    try {
      const full = await api.get<Digest>(`/digests/${id}`);
      setDetail(full);
    } catch (e) {
      console.error("Failed to load digest detail", e);
      // Fallback: use list data
      const fromList = digests.find(d => d.id === id);
      if (fromList) setDetail(fromList);
    }
  }, [digests]);

  useEffect(() => { fetchDigests(); }, [fetchDigests]);

  /* ── Actions ───────────────────────────────── */

  const handleCreate = async () => {
    if (!title.trim() || sel.size === 0) return;
    setCreating(true);
    try {
      const ids = Array.from(sel).map(id => { const m = mats.find(x => x.id === id); return m?.material_id || id; });
      const d = await api.post<Digest>("/digests", { title: title.trim(), project_id: projectId, material_ids: ids });
      setShowCreate(false); setTitle(""); setSel(new Set()); setDetail(d); fetchDigests();
    } catch (e) { console.error(e); }
    finally { setCreating(false); }
  };

  const pollDigest = async (id: string, check: (d: Digest) => boolean, interval: number, max: number) => {
    for (let i = 0; i < max; i++) {
      await new Promise(r => setTimeout(r, interval));
      const d = await api.get<Digest>(`/digests/${id}`);
      setDetail(d);
      if (!check(d)) { fetchDigests(); return; }
    }
    fetchDigests();
  };

  const genScript = async (id: string) => {
    const u = await api.post<Digest>(`/digests/${id}/generate-script`);
    setDetail(u); fetchDigests();
    pollDigest(id, d => d.revid_status === "script_generating", 3000, 20);
  };

  const saveScript = async (id: string) => {
    const u = await api.patch<Digest>(`/digests/${id}/script`, { script_text: draft });
    setDetail(u); setEditing(false); fetchDigests();
  };

  const render = async (id: string) => {
    const u = await api.post<Digest>(`/digests/${id}/render`, { render_config: vs });
    setDetail(u); fetchDigests();
    pollDigest(id, d => d.revid_status === "rendering", 8000, 60);
  };

  const del = async (id: string) => {
    if (!confirm("Удалить дайджест?")) return;
    await api.delete(`/digests/${id}`); setDetail(null); fetchDigests();
  };

  const toggle = (id: string) => setSel(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const matTitle = (m: Material) => m.headline_ru || m.material_title || "Без названия";

  /* ── Render ─────────────────────────────────── */
  return (
    <div className="cz-page">
      <Link href={`/projects/${projectId}`} className="cz-breadcrumb-link"><ArrowLeft size={14} /> Проект</Link>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: "linear-gradient(135deg,#9333ea,#ec4899)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff" }}>
            <Film size={22} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Видео-Дайджесты</h1>
            <p style={{ fontSize: 13, color: "var(--cz-text-muted)", margin: 0 }}>AI-аватар зачитывает новости</p>
          </div>
        </div>
        <button className="cz-btn cz-btn-primary" onClick={() => { const d = new Date(); setTitle(`Дайджест — ${d.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" })}`); setShowCreate(true); fetchMaterials(); }} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Plus size={16} /> Создать дайджест
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: detail ? "380px 1fr" : "1fr", gap: 20 }}>
        {/* Left list */}
        <div>
          {loading ? <div style={{ textAlign: "center", padding: 40 }}><Loader2 size={24} style={{ animation: "spin 1s linear infinite" }} /></div>
          : digests.length === 0 ? (
            <div className="cz-card" style={{ textAlign: "center", padding: 40 }}>
              <Video size={48} style={{ color: "var(--cz-text-muted)", marginBottom: 16 }} />
              <p style={{ color: "var(--cz-text-muted)" }}>Нет дайджестов</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {digests.map(d => (
                <div key={d.id} className="cz-card" onClick={() => loadDetail(d.id)} style={{
                  cursor: "pointer", padding: "14px 16px",
                  borderLeft: detail?.id === d.id ? "3px solid hsl(var(--cz-primary))" : "3px solid transparent",
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <div><h3 style={{ fontSize: 14, fontWeight: 600, margin: 0, marginBottom: 4 }}>{d.title}</h3><StatusBadge status={d.revid_status} /></div>
                    {d.video_url && <Play size={20} style={{ color: "#4ade80" }} />}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--cz-text-muted)", marginTop: 6 }}>
                    <Clock size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />
                    {new Date(d.created_at).toLocaleDateString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                    {d.duration_seconds ? ` · ${d.duration_seconds}с` : ""}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right detail */}
        {detail && (
          <div className="cz-card" style={{ padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
              <div><h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>{detail.title}</h2><StatusBadge status={detail.revid_status} /></div>
              <button onClick={() => del(detail.id)} className="cz-btn cz-btn-ghost" style={{ color: "#f87171" }}><Trash2 size={16} /></button>
            </div>

            {detail.error_message && <div style={{ padding: "10px 14px", borderRadius: 8, background: "rgba(248,113,113,0.1)", color: "#f87171", fontSize: 13, marginBottom: 16 }}>⚠ {detail.error_message}</div>}

            {/* Script */}
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>📝 Скрипт</h3>
                <div style={{ display: "flex", gap: 6 }}>
                  {!detail.script_text && detail.revid_status !== "script_generating" && <button className="cz-btn cz-btn-sm cz-btn-primary" onClick={() => genScript(detail.id)} style={{ display: "flex", alignItems: "center", gap: 4 }}><Sparkles size={14} /> Генерировать ИИ</button>}
                  {detail.script_text && !editing && <>
                    <button className="cz-btn cz-btn-sm cz-btn-ghost" onClick={() => { setEditing(true); setDraft(detail.script_text || ""); }}>Редактировать</button>
                    <button className="cz-btn cz-btn-sm cz-btn-ghost" onClick={() => genScript(detail.id)} style={{ display: "flex", alignItems: "center", gap: 4 }}><RefreshCw size={12} /> Перегенерировать</button>
                  </>}
                </div>
              </div>
              {detail.revid_status === "script_generating" ? <div style={{ textAlign: "center", padding: 30, color: "var(--cz-text-muted)" }}><Loader2 size={24} style={{ animation: "spin 1s linear infinite", marginBottom: 8 }} /><p style={{ fontSize: 13 }}>ИИ генерирует скрипт…</p></div>
              : editing ? <div>
                  <textarea value={draft} onChange={e => setDraft(e.target.value)} style={{ width: "100%", minHeight: 200, padding: 12, borderRadius: 8, border: "1px solid var(--cz-border)", background: "var(--cz-surface-1)", color: "var(--cz-text)", fontSize: 14, lineHeight: 1.6, resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }} />
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
                    <span style={{ fontSize: 12, color: "var(--cz-text-muted)" }}>{wc(draft)} слов · ~{estSec(draft)} сек</span>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button className="cz-btn cz-btn-sm cz-btn-ghost" onClick={() => setEditing(false)}>Отмена</button>
                      <button className="cz-btn cz-btn-sm cz-btn-primary" onClick={() => saveScript(detail.id)}>Сохранить</button>
                    </div>
                  </div>
                </div>
              : detail.script_text ? <div style={{ padding: 14, borderRadius: 8, background: "var(--cz-surface-1)", fontSize: 14, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
                  {detail.script_text}
                  <div style={{ marginTop: 10, fontSize: 12, color: "var(--cz-text-muted)" }}>{wc(detail.script_text)} слов · ~{estSec(detail.script_text)} сек</div>
                </div>
              : <p style={{ fontSize: 13, color: "var(--cz-text-muted)" }}>Скрипт ещё не создан.</p>}
            </div>

            {/* ── Video Settings Panel ── */}
            {detail.script_text && detail.revid_status !== "script_generating" && !detail.video_url && detail.revid_status !== "rendering" && (() => {
              const S = { lbl: { fontSize: 11, fontWeight: 600, color: "var(--cz-text-muted)", display: "block", marginBottom: 4 } as const, inp: { width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid var(--cz-border)", background: "var(--cz-bg)", color: "var(--cz-text)", fontSize: 12, boxSizing: "border-box" as const }, sel: { width: "100%", padding: "7px 8px", borderRadius: 6, border: "1px solid var(--cz-border)", background: "var(--cz-bg)", color: "var(--cz-text)", fontSize: 12 }, chk: { width: 16, height: 16, accentColor: "#9333ea" }, sec: { fontSize: 12, fontWeight: 700, color: "var(--cz-text)", padding: "8px 0 4px", borderTop: "1px solid var(--cz-border)", marginTop: 2 } };
              return (
              <div style={{ marginBottom: 20 }}>
                <details open style={{ borderRadius: 10, border: "1px solid var(--cz-border)", overflow: "hidden" }}>
                  <summary style={{ cursor: "pointer", fontSize: 14, fontWeight: 600, padding: "12px 16px", background: "var(--cz-surface-1)", userSelect: "none" }}>
                    ⚙️ Настройки видео
                  </summary>
                  <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>

                    {/* ── AVATAR ── */}
                    <div style={S.sec}>👤 Аватар</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 10 }}>
                      <div>
                        <label style={S.lbl}>Avatar URL</label>
                        <input value={vs.avatarUrl} onChange={e => setVs({ avatarUrl: e.target.value })} style={S.inp} />
                      </div>
                      <div>
                        <label style={S.lbl}>Quality</label>
                        <select value={vs.avatarImageModel} onChange={e => setVs({ avatarImageModel: e.target.value })} style={S.sel}>
                          <option value="cheap">Cheap</option>
                          <option value="good">Good</option>
                          <option value="ultra">Ultra</option>
                        </select>
                      </div>
                      <div style={{ display: "flex", alignItems: "end", paddingBottom: 2 }}>
                        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer", whiteSpace: "nowrap" }}>
                          <input type="checkbox" checked={vs.removeBackground} onChange={e => setVs({ removeBackground: e.target.checked })} style={S.chk} />
                          ✂️ Remove BG
                        </label>
                      </div>
                    </div>

                    {/* ── VOICE ── */}
                    <div style={S.sec}>🎙️ Голос</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 10 }}>
                      <div>
                        <label style={S.lbl}>Voice ID</label>
                        <input value={vs.voiceId} onChange={e => setVs({ voiceId: e.target.value })} style={S.inp} />
                      </div>
                      <div>
                        <label style={S.lbl}>Скорость: {vs.voiceSpeed}x</label>
                        <input type="range" min="0.5" max="2" step="0.1" value={vs.voiceSpeed} onChange={e => setVs({ voiceSpeed: parseFloat(e.target.value) })}
                          style={{ width: 100, accentColor: "#9333ea" }} />
                      </div>
                      <div>
                        <label style={S.lbl}>Язык</label>
                        <select value={vs.voiceLanguage} onChange={e => setVs({ voiceLanguage: e.target.value })} style={S.sel}>
                          <option value="ru">Русский</option>
                          <option value="en">English</option>
                          <option value="el">Ελληνικά</option>
                          <option value="de">Deutsch</option>
                          <option value="fr">Français</option>
                          <option value="es">Español</option>
                          <option value="tr">Türkçe</option>
                        </select>
                      </div>
                    </div>

                    {/* ── MEDIA ── */}
                    <div style={S.sec}>🎬 Медиа / B-Roll</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr", gap: 8 }}>
                      <div>
                        <label style={S.lbl}>Тип медиа</label>
                        <select value={vs.mediaType} onChange={e => setVs({ mediaType: e.target.value })} style={S.sel}>
                          <option value="stock-video">Stock Video</option>
                          <option value="stock-image">Stock Image</option>
                          <option value="ai-image">AI Image</option>
                          <option value="ai-video">AI Video</option>
                          <option value="provided">Только мои</option>
                        </select>
                      </div>
                      <div>
                        <label style={S.lbl}>Плотность</label>
                        <select value={vs.mediaDensity} onChange={e => setVs({ mediaDensity: e.target.value })} style={S.sel}>
                          <option value="none">None</option>
                          <option value="low">Low</option>
                          <option value="medium">Medium</option>
                          <option value="high">High</option>
                        </select>
                      </div>
                      <div>
                        <label style={S.lbl}>Image Model</label>
                        <select value={vs.mediaImageModel} onChange={e => setVs({ mediaImageModel: e.target.value })} style={S.sel}>
                          <option value="cheap">Cheap</option>
                          <option value="good">Good</option>
                          <option value="ultra">Ultra</option>
                        </select>
                      </div>
                      <div>
                        <label style={S.lbl}>Video Model</label>
                        <select value={vs.videoModel} onChange={e => setVs({ videoModel: e.target.value })} style={S.sel}>
                          <option value="base">Base</option>
                          <option value="pro">Pro</option>
                        </select>
                      </div>
                      <div>
                        <label style={S.lbl}>B-Roll</label>
                        <select value={vs.bRollType} onChange={e => setVs({ bRollType: e.target.value })} style={S.sel}>
                          <option value="fullscreen">Fullscreen</option>
                          <option value="split-screen">Split Screen</option>
                        </select>
                      </div>
                    </div>
                    <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer" }}>
                      <input type="checkbox" checked={vs.placeAvatarInContext} onChange={e => setVs({ placeAvatarInContext: e.target.checked })} style={S.chk} />
                      Аватар в контексте видео (Place Avatar in Context)
                    </label>

                    {/* ── CAPTIONS + MUSIC + FORMAT ── */}
                    <div style={S.sec}>💬 Субтитры · 🎵 Музыка · 📐 Формат</div>
                    <div style={{ display: "grid", gridTemplateColumns: "auto 1fr 1fr auto auto 1fr auto", gap: 10, alignItems: "end" }}>
                      <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer", paddingBottom: 2 }}>
                        <input type="checkbox" checked={vs.captionsEnabled} onChange={e => setVs({ captionsEnabled: e.target.checked })} style={S.chk} />
                        Субтитры
                      </label>
                      <div>
                        <label style={S.lbl}>Preset</label>
                        <select value={vs.captionsPreset} onChange={e => setVs({ captionsPreset: e.target.value })} style={S.sel} disabled={!vs.captionsEnabled}>
                          <option value="Hormozi">Hormozi</option>
                          <option value="Ali Abdaal">Ali Abdaal</option>
                          <option value="Beast">Beast</option>
                          <option value="Wrap 1">Wrap 1</option>
                          <option value="Wrap 2">Wrap 2</option>
                          <option value="Classic Pop">Classic Pop</option>
                          <option value="Faceless">Faceless</option>
                        </select>
                      </div>
                      <div>
                        <label style={S.lbl}>Позиция</label>
                        <select value={vs.captionsPosition} onChange={e => setVs({ captionsPosition: e.target.value })} style={S.sel} disabled={!vs.captionsEnabled}>
                          <option value="top">Top</option>
                          <option value="bottom">Bottom</option>
                        </select>
                      </div>
                      <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer", paddingBottom: 2 }}>
                        <input type="checkbox" checked={vs.musicEnabled} onChange={e => setVs({ musicEnabled: e.target.checked })} style={S.chk} />
                        🎵 Музыка
                      </label>
                      <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer", paddingBottom: 2 }}>
                        <input type="checkbox" checked={vs.disableAudio} onChange={e => setVs({ disableAudio: e.target.checked })} style={S.chk} />
                        🔇 Без аудио
                      </label>
                      <div>
                        <label style={S.lbl}>Aspect Ratio</label>
                        <select value={vs.aspectRatio} onChange={e => setVs({ aspectRatio: e.target.value })} style={S.sel}>
                          <option value="9 / 16">9:16 (Vertical)</option>
                          <option value="16 / 9">16:9 (Horizontal)</option>
                          <option value="1 / 1">1:1 (Square)</option>
                          <option value="4 / 5">4:5 (Portrait)</option>
                        </select>
                      </div>
                    </div>

                    {/* ── PROVIDED MEDIA ── */}
                    <div style={S.sec}>🖼️ Свои медиа ({vs.providedMedia.length})</div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: 11, color: "var(--cz-text-muted)" }}>{vs.providedMedia.length === 0 ? "Не добавлены" : `${vs.providedMedia.length} файлов`}</span>
                      <button className="cz-btn cz-btn-sm cz-btn-ghost" onClick={() => setVs({ providedMedia: [...vs.providedMedia, { url: "", title: "", type: "image" }] })} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <Plus size={14} /> Добавить
                      </button>
                    </div>
                    {vs.providedMedia.length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                        {vs.providedMedia.map((m, i) => (
                          <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto auto", gap: 5, padding: 7, borderRadius: 6, background: "var(--cz-surface-1)", border: "1px solid var(--cz-border)", alignItems: "center" }}>
                            <input placeholder="URL" value={m.url}
                              onChange={e => setVs({ providedMedia: vs.providedMedia.map((x, j) => j === i ? { ...x, url: e.target.value } : x) })}
                              style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid var(--cz-border)", background: "var(--cz-bg)", color: "var(--cz-text)", fontSize: 11 }} />
                            <input placeholder="Title (англ.)" value={m.title}
                              onChange={e => setVs({ providedMedia: vs.providedMedia.map((x, j) => j === i ? { ...x, title: e.target.value } : x) })}
                              style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid var(--cz-border)", background: "var(--cz-bg)", color: "var(--cz-text)", fontSize: 11 }} />
                            <select value={m.type}
                              onChange={e => setVs({ providedMedia: vs.providedMedia.map((x, j) => j === i ? { ...x, type: e.target.value } : x) })}
                              style={{ padding: "4px 5px", borderRadius: 4, border: "1px solid var(--cz-border)", background: "var(--cz-bg)", color: "var(--cz-text)", fontSize: 10 }}>
                              <option value="image">Img</option>
                              <option value="video">Vid</option>
                            </select>
                            <button onClick={() => setVs({ providedMedia: vs.providedMedia.filter((_, j) => j !== i) })}
                              style={{ padding: 2, background: "none", border: "none", cursor: "pointer", color: "#f87171" }}>
                              <Trash2 size={12} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    <p style={{ fontSize: 10, color: "var(--cz-text-muted)", margin: 0, textAlign: "right" }}>💾 Все настройки сохранены автоматически</p>
                  </div>
                </details>
              </div>
              );
            })()}

            {/* Video */}
            {detail.video_url ? <div style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>🎬 Видео</h3>
              <video src={detail.video_url} controls style={{ width: "100%", maxHeight: 500, borderRadius: 10, background: "#000" }} />
              <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                <a href={detail.video_url} target="_blank" rel="noopener noreferrer" className="cz-btn cz-btn-sm cz-btn-primary" style={{ display: "flex", alignItems: "center", gap: 4, textDecoration: "none" }}><Download size={14} /> Скачать</a>
              </div>
            </div>
            : detail.revid_status === "rendering" ? <div style={{ textAlign: "center", padding: 40, color: "var(--cz-text-muted)" }}><Loader2 size={32} style={{ animation: "spin 1s linear infinite", marginBottom: 12 }} /><p style={{ fontWeight: 600 }}>Рендер видео…</p><p style={{ fontSize: 13 }}>1-3 минуты</p></div>
            : detail.script_text && detail.revid_status !== "script_generating" ? <button className="cz-btn cz-btn-primary" onClick={() => render(detail.id)} style={{ display: "flex", alignItems: "center", gap: 6, width: "100%", justifyContent: "center", padding: "12px 0" }}><Film size={18} /> Создать видео</button>
            : null}

            {/* ReVid API Preview */}
            {detail.script_text && (
              <details style={{ marginTop: 16 }}>
                <summary style={{ cursor: "pointer", fontSize: 13, fontWeight: 600, color: "var(--cz-text-muted)", padding: "8px 0", userSelect: "none" }}>
                  🔧 ReVid API запрос (preview)
                </summary>
                <pre style={{
                  marginTop: 8, padding: 14, borderRadius: 10, background: "rgba(0,0,0,0.4)",
                  border: "1px solid var(--cz-border)", fontSize: 12, lineHeight: 1.5,
                  color: "#a5f3b4", overflow: "auto", maxHeight: 400, whiteSpace: "pre-wrap",
                  wordBreak: "break-word", fontFamily: "'SF Mono', 'Fira Code', 'Consolas', monospace",
                }}>
{JSON.stringify({
  endpoint: "POST https://www.revid.ai/api/public/v3/render",
  body: {
    workflow: "avatar-to-video",
    source: { text: detail.script_text },
    media: {
      type: vs.mediaType,
      density: vs.mediaDensity,
      imageModel: vs.mediaImageModel,
      videoModel: vs.videoModel,
      bRollType: vs.bRollType,
      placeAvatarInContext: vs.placeAvatarInContext,
      ...(vs.providedMedia.length > 0 ? { provided: vs.providedMedia } : {}),
    },
    voice: {
      enabled: true,
      voiceId: vs.voiceId,
      speed: vs.voiceSpeed,
      useLegacyModel: false,
      language: vs.voiceLanguage,
    },
    captions: { enabled: vs.captionsEnabled, preset: vs.captionsPreset, position: vs.captionsPosition },
    music: { enabled: vs.musicEnabled },
    avatar: {
      enabled: true,
      url: vs.avatarUrl,
      mimeType: "image/png",
      imageModel: vs.avatarImageModel,
      removeBackground: vs.removeBackground,
    },
    options: { disableAudio: vs.disableAudio },
    metadata: null,
    aspectRatio: vs.aspectRatio,
  },
}, null, 2)}
                </pre>
              </details>
            )}

            <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--cz-border)" }}>
              <p style={{ fontSize: 13, color: "var(--cz-text-muted)", margin: 0 }}>Новости в дайджесте: {detail.material_ids?.length || 0}</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Create modal ── */}
      {showCreate && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }} onClick={() => setShowCreate(false)}>
          <div onClick={e => e.stopPropagation()} style={{
            width: 620, maxHeight: "85vh", display: "flex", flexDirection: "column",
            background: "var(--cz-surface-2, #1a1a2e)", border: "1px solid var(--cz-border)",
            borderRadius: 16, overflow: "hidden",
          }}>
            {/* Modal header */}
            <div style={{ padding: "20px 24px 0", flexShrink: 0 }}>
              <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 16px" }}>🎬 Новый видео-дайджест</h2>
              <label style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, display: "block", color: "var(--cz-text-muted)" }}>Название</label>
              <input type="text" value={title} onChange={e => setTitle(e.target.value)} placeholder="Дайджест новостей Кипра — 4 мая"
                style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: "1px solid var(--cz-border)", background: "var(--cz-surface-1)", color: "var(--cz-text)", fontSize: 14, boxSizing: "border-box", marginBottom: 16, outline: "none" }} />

              {/* Selected counter */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--cz-text-muted)" }}>Новости для дайджеста</span>
                {sel.size > 0 && <span style={{ fontSize: 12, fontWeight: 700, color: "#4ade80", background: "rgba(74,222,128,0.15)", padding: "3px 10px", borderRadius: 20 }}>✓ Выбрано: {sel.size}</span>}
              </div>
            </div>

            {/* Material list */}
            <div style={{ flex: 1, overflowY: "auto", padding: "0 24px", minHeight: 0 }}>
              {matsLoading ? (
                <div style={{ textAlign: "center", padding: 40 }}><Loader2 size={24} style={{ animation: "spin 1s linear infinite" }} /></div>
              ) : mats.length === 0 ? (
                <p style={{ fontSize: 13, color: "var(--cz-text-muted)", padding: 20, textAlign: "center" }}>Нет отобранных материалов. Сначала отберите новости в разделе «В работе».</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {mats.map(m => {
                    const isSelected = sel.has(m.id);
                    return (
                      <div key={m.id} onClick={() => toggle(m.id)} style={{
                        display: "flex", alignItems: "center", gap: 12, padding: "12px 14px",
                        borderRadius: 10, cursor: "pointer", transition: "all 0.15s",
                        background: isSelected ? "rgba(96,165,250,0.12)" : "rgba(255,255,255,0.03)",
                        border: isSelected ? "1px solid rgba(96,165,250,0.4)" : "1px solid transparent",
                      }}>
                        {/* Checkbox */}
                        <div style={{
                          width: 22, height: 22, borderRadius: 6, flexShrink: 0,
                          border: isSelected ? "2px solid #60a5fa" : "2px solid #555",
                          background: isSelected ? "#60a5fa" : "transparent",
                          display: "flex", alignItems: "center", justifyContent: "center",
                          transition: "all 0.15s",
                        }}>
                          {isSelected && <CheckCircle2 size={14} color="#fff" />}
                        </div>
                        {/* Content */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 14, fontWeight: 500, color: "var(--cz-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {matTitle(m)}
                          </div>
                          {m.summary_ru && <div style={{ fontSize: 12, color: "var(--cz-text-muted)", marginTop: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.summary_ru}</div>}
                          <div style={{ fontSize: 11, color: "#888", marginTop: 3 }}>
                            Рел: {m.relevance_score} · Хайп: {m.hype_score}
                            {m.editorial_status === "published" && <span style={{ marginLeft: 8, color: "#4ade80" }}>● опубликовано</span>}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Modal footer */}
            <div style={{ padding: "16px 24px", borderTop: "1px solid var(--cz-border)", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
              <span style={{ fontSize: 12, color: "var(--cz-text-muted)" }}>{mats.length} новостей доступно</span>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="cz-btn cz-btn-ghost" onClick={() => setShowCreate(false)}>Отмена</button>
                <button className="cz-btn cz-btn-primary" onClick={handleCreate}
                  disabled={creating || !title.trim() || sel.size === 0}
                  style={{ display: "flex", alignItems: "center", gap: 6, opacity: (!title.trim() || sel.size === 0) ? 0.4 : 1 }}>
                  {creating ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Plus size={14} />}
                  Создать ({sel.size})
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
