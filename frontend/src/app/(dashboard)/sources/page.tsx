"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CzButton, CzInput, CzSelect, CzCard, CzBadge, CzDialog, CzPageHeader, CzEmptyState, CzSkeletonGrid } from "@/components/ui-system";
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
    <div className="cz-page">
      <CzPageHeader title="Источники" subtitle="Управление источниками контента">
        <CzButton onClick={openNew} icon={<Plus size={16} />}>Добавить</CzButton>
      </CzPageHeader>

      <CzDialog open={dialogOpen} onClose={() => setDialogOpen(false)} title={editingId ? "Редактировать источник" : "Новый источник"}>
        <form onSubmit={handleSubmit} className="cz-form">
          <CzInput label="Название" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="Название источника" />
          <CzInput label="URL" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} required placeholder="https://..." />
          <CzSelect label="Тип" value={form.source_type} onChange={(v) => setForm({ ...form, source_type: v })} options={typeOptions} />
          <CzButton type="submit" fullWidth size="lg">{editingId ? "Сохранить" : "Создать"}</CzButton>
        </form>
      </CzDialog>

      {loading ? (
        <CzSkeletonGrid count={3} />
      ) : sources.length === 0 ? (
        <CzEmptyState
          icon={<Radio size={48} />}
          title="Нет источников"
          text="Добавьте первый источник контента"
          action={<CzButton onClick={openNew} icon={<Plus size={16} />}>Добавить источник</CzButton>}
        />
      ) : (
        <div className="cz-card-grid stagger-children">
          {sources.map((source) => {
            const Icon = typeIcons[source.source_type] || Globe;
            return (
              <CzCard key={source.id} interactive>
                <div className="cz-flex-between cz-items-start" style={{ marginBottom: 12 }}>
                  <div className="cz-flex cz-items-center cz-gap-12">
                    <div className="cz-icon-box">
                      <Icon size={20} />
                    </div>
                    <div>
                      <div className="cz-text-lg cz-font-semibold">{source.name}</div>
                      <CzBadge variant={source.is_active ? "success" : "default"}>
                        {source.is_active ? "Активен" : "Выключен"}
                      </CzBadge>
                    </div>
                  </div>
                  <div className="cz-table-actions">
                    <CzButton variant="ghost" size="sm" onClick={() => openEdit(source)} icon={<Pencil size={14} />} />
                    <CzButton variant="ghost" size="sm" onClick={() => handleDelete(source.id)} icon={<Trash2 size={14} />} />
                  </div>
                </div>
                <p className="cz-text-sm cz-text-muted cz-truncate">{source.url}</p>
                <div className="cz-flex cz-items-center cz-gap-12 cz-text-sm cz-text-muted" style={{ marginTop: 12 }}>
                  <span>{typeLabels[source.source_type]}</span>
                  {source.error_count > 0 && <span className="cz-text-error">{source.error_count} ошибок</span>}
                </div>
              </CzCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
