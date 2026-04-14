"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CzButton, CzInput, CzSelect, CzCard, CzBadge, CzDialog } from "@/components/ui-system";
import { Plus, Pencil, Trash2, Radio, Globe, Rss, Zap, Users } from "lucide-react";
import { toast } from "sonner";

interface Source {
  id: string;
  name: string;
  url: string;
  source_type: string;
  is_active: boolean;
  error_count: number;
  last_scraped_at: string | null;
  created_at: string;
}

const typeIcons: Record<string, React.ElementType> = { rss: Rss, website: Globe, api: Zap, social: Users };
const typeLabels: Record<string, string> = { rss: "RSS", website: "Сайт", api: "API", social: "Соцсети" };
const typeOptions = [
  { value: "rss", label: "RSS" },
  { value: "website", label: "Сайт" },
  { value: "api", label: "API" },
  { value: "social", label: "Соцсети" },
];

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", url: "", source_type: "rss" });

  const fetchSources = async () => {
    try {
      const data = await api.get<{ items: Source[] }>("/sources");
      setSources(data.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSources(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.patch(`/sources/${editingId}`, form);
        toast.success("Источник обновлён");
      } else {
        await api.post("/sources", { ...form, is_active: true });
        toast.success("Источник добавлен");
      }
      setDialogOpen(false);
      setEditingId(null);
      setForm({ name: "", url: "", source_type: "rss" });
      fetchSources();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить источник?")) return;
    try {
      await api.delete(`/sources/${id}`);
      toast.success("Удалено");
      fetchSources();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const openEdit = (s: Source) => {
    setEditingId(s.id);
    setForm({ name: s.name, url: s.url, source_type: s.source_type });
    setDialogOpen(true);
  };

  const openNew = () => {
    setEditingId(null);
    setForm({ name: "", url: "", source_type: "rss" });
    setDialogOpen(true);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, color: `hsl(var(--cz-text-primary))`, letterSpacing: "-0.02em" }}>Источники</h1>
          <p style={{ fontSize: "14px", color: `hsl(var(--cz-text-muted))`, marginTop: "4px" }}>Управление источниками контента</p>
        </div>
        <CzButton onClick={openNew} icon={<Plus size={16} />}>Добавить</CzButton>
      </div>

      <CzDialog open={dialogOpen} onClose={() => setDialogOpen(false)} title={editingId ? "Редактировать источник" : "Новый источник"}>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <CzInput label="Название" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="Название источника" />
          <CzInput label="URL" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} required placeholder="https://..." />
          <CzSelect label="Тип" value={form.source_type} onChange={(v) => setForm({ ...form, source_type: v })} options={typeOptions} />
          <CzButton type="submit" fullWidth size="lg">{editingId ? "Сохранить" : "Создать"}</CzButton>
        </form>
      </CzDialog>

      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "16px" }}>
          {[1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: "140px" }} />)}
        </div>
      ) : sources.length === 0 ? (
        <CzCard>
          <div style={{ textAlign: "center", padding: "48px 24px" }}>
            <Radio size={48} style={{ color: `hsl(var(--cz-text-muted))`, margin: "0 auto 16px" }} />
            <h3 style={{ fontSize: "16px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))` }}>Нет источников</h3>
            <p style={{ fontSize: "13px", color: `hsl(var(--cz-text-muted))`, marginTop: "6px" }}>Добавьте первый источник контента</p>
            <div style={{ marginTop: "20px" }}>
              <CzButton onClick={openNew} icon={<Plus size={16} />}>Добавить источник</CzButton>
            </div>
          </div>
        </CzCard>
      ) : (
        <div className="stagger-children" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "16px" }}>
          {sources.map((source) => {
            const Icon = typeIcons[source.source_type] || Globe;
            return (
              <CzCard key={source.id} interactive>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "12px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div
                      style={{
                        width: "40px",
                        height: "40px",
                        borderRadius: "var(--cz-radius-md)",
                        backgroundColor: `hsl(var(--cz-bg-overlay))`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <Icon size={20} style={{ color: `hsl(var(--cz-text-muted))` }} />
                    </div>
                    <div>
                      <div style={{ fontSize: "14px", fontWeight: 600, color: `hsl(var(--cz-text-primary))` }}>{source.name}</div>
                      <CzBadge variant={source.is_active ? "success" : "default"}>
                        {source.is_active ? "Активен" : "Выключен"}
                      </CzBadge>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "4px" }}>
                    <CzButton variant="ghost" size="sm" onClick={() => openEdit(source)} icon={<Pencil size={14} />} />
                    <CzButton variant="ghost" size="sm" onClick={() => handleDelete(source.id)} icon={<Trash2 size={14} />} />
                  </div>
                </div>
                <p style={{ fontSize: "12px", color: `hsl(var(--cz-text-muted))`, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{source.url}</p>
                <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "12px", fontSize: "12px", color: `hsl(var(--cz-text-muted))` }}>
                  <span>{typeLabels[source.source_type]}</span>
                  {source.error_count > 0 && <span style={{ color: `hsl(var(--cz-error))` }}>{source.error_count} ошибок</span>}
                </div>
              </CzCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
