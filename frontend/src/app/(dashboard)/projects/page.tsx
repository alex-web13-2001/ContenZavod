"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { CzCard, CzBadge, CzButton, CzInput, CzDialog, CzPageHeader, CzEmptyState, CzSkeletonGrid } from "@/components/ui-system";
import { FolderOpen, Plus, Send, Sparkles, ChevronRight, Pause, Play } from "lucide-react";
import Link from "next/link";

interface Project {
  id: string;
  name: string;
  description: string;
  topic_guidelines: string;
  target_audience: string;
  is_active: boolean;
  channel_count: number;
  recommendation_count: number;
  created_at: string;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formTopic, setFormTopic] = useState("");
  const [formAudience, setFormAudience] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<{ items: Project[] }>("/projects");
      setProjects(data.items);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const [togglingId, setTogglingId] = useState<string | null>(null);

  const handleTogglePause = async (e: React.MouseEvent, p: Project) => {
    // Card is wrapped in a Link — don't navigate when clicking the button.
    e.preventDefault();
    e.stopPropagation();
    if (togglingId) return;
    setTogglingId(p.id);
    // Optimistic flip so the UI responds instantly.
    setProjects((prev) => prev.map((x) => x.id === p.id ? { ...x, is_active: !x.is_active } : x));
    try {
      await api.post(`/projects/${p.id}/${p.is_active ? "pause" : "resume"}`);
    } catch {
      // Revert on failure.
      setProjects((prev) => prev.map((x) => x.id === p.id ? { ...x, is_active: p.is_active } : x));
    } finally {
      setTogglingId(null);
    }
  };

  const handleCreate = async () => {
    if (!formName.trim()) return;
    setCreating(true);
    try {
      await api.post("/projects", {
        name: formName,
        description: formDescription,
        topic_guidelines: formTopic,
        target_audience: formAudience,
      });
      setShowCreate(false);
      setFormName(""); setFormDescription(""); setFormTopic(""); setFormAudience("");
      fetchProjects();
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="cz-page">
      <CzPageHeader title="Проекты" subtitle="Тематические медиа-проекты с каналами публикации">
        <CzButton onClick={() => setShowCreate(true)} icon={<Plus size={14} />}>Создать проект</CzButton>
      </CzPageHeader>

      {/* Create dialog */}
      <CzDialog open={showCreate} onClose={() => setShowCreate(false)} title="Новый проект">
        <div className="cz-form">
          <div className="cz-form-row">
            <CzInput label="Название *" value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="CyprusNews" />
            <CzInput label="Описание" value={formDescription} onChange={(e) => setFormDescription(e.target.value)} placeholder="Новостной медиа-проект" />
          </div>

          <div className="cz-form-group">
            <label className="cz-form-label">Тематика — что публикуем (для AI-отбора)</label>
            <textarea
              value={formTopic}
              onChange={(e) => setFormTopic(e.target.value)}
              placeholder="Экономика, политика, бизнес, визы, налоги Кипра. НЕ: спорт, светская хроника."
              rows={3}
              style={{
                padding: "8px 12px", fontSize: 13, borderRadius: "var(--cz-radius-md)",
                border: "1px solid hsl(var(--cz-border))", backgroundColor: "hsl(var(--cz-bg-surface))",
                color: "hsl(var(--cz-text-primary))", outline: "none", resize: "vertical", fontFamily: "inherit",
              }}
            />
          </div>

          <div className="cz-form-group">
            <label className="cz-form-label">Целевая аудитория</label>
            <textarea
              value={formAudience}
              onChange={(e) => setFormAudience(e.target.value)}
              placeholder="Русскоязычные предприниматели 30-55 лет, инвесторы на Кипре"
              rows={2}
              style={{
                padding: "8px 12px", fontSize: 13, borderRadius: "var(--cz-radius-md)",
                border: "1px solid hsl(var(--cz-border))", backgroundColor: "hsl(var(--cz-bg-surface))",
                color: "hsl(var(--cz-text-primary))", outline: "none", resize: "vertical", fontFamily: "inherit",
              }}
            />
          </div>

          <div className="cz-flex" style={{ justifyContent: "flex-end", gap: 8 }}>
            <CzButton variant="ghost" onClick={() => setShowCreate(false)}>Отмена</CzButton>
            <CzButton onClick={handleCreate} disabled={creating || !formName.trim()}>
              {creating ? "Создаю..." : "Создать"}
            </CzButton>
          </div>
        </div>
      </CzDialog>

      {/* Projects grid */}
      {loading ? (
        <CzSkeletonGrid count={3} />
      ) : projects.length === 0 ? (
        <CzEmptyState
          icon={<FolderOpen size={48} />}
          title="Нет проектов"
          text="Создайте первый проект, чтобы начать управлять контентом"
          action={<CzButton onClick={() => setShowCreate(true)} icon={<Plus size={14} />}>Создать проект</CzButton>}
        />
      ) : (
        <div className="cz-card-grid stagger-children" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))" }}>
          {projects.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} style={{ textDecoration: "none" }}>
              <CzCard interactive padding="md">
                <div className="cz-flex-col cz-gap-12" style={{ height: "100%" }}>
                  {/* Header */}
                  <div className="cz-flex-between cz-items-start">
                    <div className="cz-flex cz-items-center cz-gap-12">
                      <div className="cz-flex-center cz-flex-shrink-0" style={{
                        width: 40, height: 40, borderRadius: "var(--cz-radius-md)",
                        background: "linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))",
                        color: "white", fontSize: 16, fontWeight: 700,
                      }}>
                        {p.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="cz-text-lg cz-font-semibold">{p.name}</div>
                        {p.description && <div className="cz-text-sm cz-text-muted" style={{ marginTop: 2 }}>{p.description}</div>}
                      </div>
                    </div>
                    <ChevronRight size={16} className="cz-text-muted cz-flex-shrink-0" />
                  </div>

                  {/* Stats */}
                  <div className="cz-flex cz-items-center cz-gap-16" style={{
                    marginTop: "auto", paddingTop: 8, borderTop: "1px solid hsl(var(--cz-border-subtle))",
                  }}>
                    <div className="cz-flex cz-items-center cz-gap-6 cz-text-sm cz-text-muted">
                      <Send size={12} /> {p.channel_count} каналов
                    </div>
                    {p.recommendation_count > 0 && (
                      <div className="cz-flex cz-items-center cz-gap-6 cz-text-sm cz-font-semibold cz-text-success">
                        <Sparkles size={12} /> {p.recommendation_count} рекомендаций
                      </div>
                    )}
                    <CzBadge variant={p.is_active ? "success" : "default"}>
                      {p.is_active ? "Активен" : "На паузе"}
                    </CzBadge>
                    <CzButton
                      variant="ghost"
                      onClick={(e) => handleTogglePause(e, p)}
                      disabled={togglingId === p.id}
                      icon={p.is_active ? <Pause size={12} /> : <Play size={12} />}
                      style={{ marginLeft: "auto" }}
                    >
                      {p.is_active ? "Пауза" : "Запустить"}
                    </CzButton>
                  </div>
                </div>
              </CzCard>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
