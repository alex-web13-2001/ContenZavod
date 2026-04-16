"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { CzCard, CzBadge } from "@/components/ui-system";
import {
  FolderOpen,
  Plus,
  Send,
  Globe,
  Video,
  ChevronRight,
  Sparkles,
  X,
} from "lucide-react";
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

const platformIcons: Record<string, { icon: typeof Send; label: string }> = {
  telegram: { icon: Send, label: "Telegram" },
  website: { icon: Globe, label: "Сайт" },
  youtube: { icon: Video, label: "YouTube" },
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  // Create form state
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

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

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
      setFormName("");
      setFormDescription("");
      setFormTopic("");
      setFormAudience("");
      fetchProjects();
    } finally {
      setCreating(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "24px",
              fontWeight: 700,
              color: `hsl(var(--cz-text-primary))`,
              letterSpacing: "-0.02em",
            }}
          >
            Проекты
          </h1>
          <p
            style={{
              fontSize: "14px",
              color: `hsl(var(--cz-text-muted))`,
              marginTop: "4px",
            }}
          >
            Тематические медиа-проекты с каналами публикации
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 16px",
            fontSize: "13px",
            fontWeight: 600,
            borderRadius: "var(--cz-radius-md)",
            backgroundColor: `hsl(var(--cz-accent))`,
            color: "white",
            border: "none",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
        >
          <Plus size={14} />
          Создать проект
        </button>
      </div>

      {/* Create form modal */}
      {showCreate && (
        <CzCard>
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <h3
                style={{
                  fontSize: "16px",
                  fontWeight: 600,
                  color: `hsl(var(--cz-text-primary))`,
                }}
              >
                Новый проект
              </h3>
              <button
                onClick={() => setShowCreate(false)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: `hsl(var(--cz-text-muted))`,
                }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: `hsl(var(--cz-text-secondary))`,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  Название *
                </label>
                <input
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="CyprusNews"
                  style={{
                    padding: "8px 12px",
                    fontSize: "13px",
                    borderRadius: "var(--cz-radius-md)",
                    border: `1px solid hsl(var(--cz-border))`,
                    backgroundColor: `hsl(var(--cz-bg-surface))`,
                    color: `hsl(var(--cz-text-primary))`,
                    outline: "none",
                  }}
                />
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: `hsl(var(--cz-text-secondary))`,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  Описание
                </label>
                <input
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  placeholder="Новостной медиа-проект"
                  style={{
                    padding: "8px 12px",
                    fontSize: "13px",
                    borderRadius: "var(--cz-radius-md)",
                    border: `1px solid hsl(var(--cz-border))`,
                    backgroundColor: `hsl(var(--cz-bg-surface))`,
                    color: `hsl(var(--cz-text-primary))`,
                    outline: "none",
                  }}
                />
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: `hsl(var(--cz-text-secondary))`,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Тематика — что публикуем (для AI-отбора)
              </label>
              <textarea
                value={formTopic}
                onChange={(e) => setFormTopic(e.target.value)}
                placeholder="Экономика, политика, бизнес, визы, налоги Кипра. НЕ: спорт, светская хроника."
                rows={3}
                style={{
                  padding: "8px 12px",
                  fontSize: "13px",
                  borderRadius: "var(--cz-radius-md)",
                  border: `1px solid hsl(var(--cz-border))`,
                  backgroundColor: `hsl(var(--cz-bg-surface))`,
                  color: `hsl(var(--cz-text-primary))`,
                  outline: "none",
                  resize: "vertical",
                  fontFamily: "inherit",
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: `hsl(var(--cz-text-secondary))`,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Целевая аудитория
              </label>
              <textarea
                value={formAudience}
                onChange={(e) => setFormAudience(e.target.value)}
                placeholder="Русскоязычные предприниматели 30-55 лет, инвесторы на Кипре"
                rows={2}
                style={{
                  padding: "8px 12px",
                  fontSize: "13px",
                  borderRadius: "var(--cz-radius-md)",
                  border: `1px solid hsl(var(--cz-border))`,
                  backgroundColor: `hsl(var(--cz-bg-surface))`,
                  color: `hsl(var(--cz-text-primary))`,
                  outline: "none",
                  resize: "vertical",
                  fontFamily: "inherit",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
              <button
                onClick={() => setShowCreate(false)}
                style={{
                  padding: "8px 16px",
                  fontSize: "13px",
                  fontWeight: 500,
                  borderRadius: "var(--cz-radius-md)",
                  backgroundColor: "transparent",
                  color: `hsl(var(--cz-text-secondary))`,
                  border: `1px solid hsl(var(--cz-border))`,
                  cursor: "pointer",
                }}
              >
                Отмена
              </button>
              <button
                onClick={handleCreate}
                disabled={creating || !formName.trim()}
                style={{
                  padding: "8px 20px",
                  fontSize: "13px",
                  fontWeight: 600,
                  borderRadius: "var(--cz-radius-md)",
                  backgroundColor: `hsl(var(--cz-accent))`,
                  color: "white",
                  border: "none",
                  cursor: creating ? "not-allowed" : "pointer",
                  opacity: creating || !formName.trim() ? 0.6 : 1,
                }}
              >
                {creating ? "Создаю..." : "Создать"}
              </button>
            </div>
          </div>
        </CzCard>
      )}

      {/* Projects list */}
      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton" style={{ height: "120px" }} />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <CzCard>
          <div style={{ textAlign: "center", padding: "64px 24px" }}>
            <FolderOpen
              size={48}
              style={{
                color: `hsl(var(--cz-text-muted))`,
                margin: "0 auto 16px",
              }}
            />
            <h3
              style={{
                fontSize: "16px",
                fontWeight: 600,
                color: `hsl(var(--cz-text-secondary))`,
              }}
            >
              Нет проектов
            </h3>
            <p
              style={{
                fontSize: "13px",
                color: `hsl(var(--cz-text-muted))`,
                marginTop: "6px",
              }}
            >
              Создайте первый проект, чтобы начать управлять контентом
            </p>
          </div>
        </CzCard>
      ) : (
        <div
          className="stagger-children"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
            gap: "16px",
          }}
        >
          {projects.map((p) => (
            <Link
              key={p.id}
              href={`/projects/${p.id}`}
              style={{ textDecoration: "none" }}
            >
              <CzCard interactive padding="md">
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                    height: "100%",
                  }}
                >
                  {/* Project header */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                      }}
                    >
                      <div
                        style={{
                          width: "40px",
                          height: "40px",
                          borderRadius: "var(--cz-radius-md)",
                          background: `linear-gradient(135deg, hsl(var(--cz-primary)), hsl(var(--cz-accent)))`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "white",
                          fontSize: "16px",
                          fontWeight: 700,
                          flexShrink: 0,
                        }}
                      >
                        {p.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div
                          style={{
                            fontSize: "15px",
                            fontWeight: 600,
                            color: `hsl(var(--cz-text-primary))`,
                          }}
                        >
                          {p.name}
                        </div>
                        {p.description && (
                          <div
                            style={{
                              fontSize: "12px",
                              color: `hsl(var(--cz-text-muted))`,
                              marginTop: "2px",
                            }}
                          >
                            {p.description}
                          </div>
                        )}
                      </div>
                    </div>
                    <ChevronRight
                      size={16}
                      style={{ color: `hsl(var(--cz-text-muted))`, flexShrink: 0 }}
                    />
                  </div>

                  {/* Stats row */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "16px",
                      marginTop: "auto",
                      paddingTop: "8px",
                      borderTop: `1px solid hsl(var(--cz-border-subtle))`,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        fontSize: "12px",
                        color: `hsl(var(--cz-text-muted))`,
                      }}
                    >
                      <Send size={12} />
                      {p.channel_count} каналов
                    </div>

                    {p.recommendation_count > 0 && (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          fontSize: "12px",
                          color: `hsl(var(--cz-success))`,
                          fontWeight: 600,
                        }}
                      >
                        <Sparkles size={12} />
                        {p.recommendation_count} рекомендаций
                      </div>
                    )}

                    <CzBadge variant={p.is_active ? "success" : "default"}>
                      {p.is_active ? "Активен" : "Неактивен"}
                    </CzBadge>
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
