"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CzButton, CzInput, CzSelect, CzCard, CzBadge, CzDialog, CzPageHeader, CzEmptyState, CzSkeletonGrid } from "@/components/ui-system";
import { Plus, Pencil, Trash2, Send, MessageCircle, Video, Globe } from "lucide-react";
import { toast } from "sonner";

interface Channel {
  id: string;
  name: string;
  channel_type: string;
  config: Record<string, unknown>;
  editorial_guidelines?: string;
  target_audience?: string;
  is_active: boolean;
  created_at: string;
}

const typeIcons: Record<string, React.ElementType> = { telegram: MessageCircle, youtube: Video, website: Globe };
const typeLabels: Record<string, string> = { telegram: "Telegram", youtube: "YouTube", website: "Веб-сайт" };
const typeOptions = [
  { value: "telegram", label: "Telegram" },
  { value: "youtube", label: "YouTube" },
  { value: "website", label: "Веб-сайт" },
];

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ 
    name: "", 
    channel_type: "telegram",
    editorial_guidelines: "",
    target_audience: ""
  });

  const fetchChannels = async () => {
    try {
      const data = await api.get<{ items: Channel[] }>("/channels");
      setChannels(data.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchChannels(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.patch(`/channels/${editingId}`, form);
        toast.success("Канал обновлён");
      } else {
        await api.post("/channels", { ...form, is_active: true, config: {} });
        toast.success("Канал добавлен");
      }
      setDialogOpen(false);
      setEditingId(null);
      setForm({ name: "", channel_type: "telegram", editorial_guidelines: "", target_audience: "" });
      fetchChannels();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить канал?")) return;
    try {
      await api.delete(`/channels/${id}`);
      toast.success("Удалено");
      fetchChannels();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const openEdit = (ch: Channel) => {
    setEditingId(ch.id);
    setForm({ 
      name: ch.name, 
      channel_type: ch.channel_type,
      editorial_guidelines: ch.editorial_guidelines || "",
      target_audience: ch.target_audience || ""
    });
    setDialogOpen(true);
  };

  const openNew = () => {
    setEditingId(null);
    setForm({ name: "", channel_type: "telegram", editorial_guidelines: "", target_audience: "" });
    setDialogOpen(true);
  };

  return (
    <div className="cz-page">
      <CzPageHeader title="Каналы публикации" subtitle="Управление каналами дистрибуции">
        <CzButton onClick={openNew} icon={<Plus size={16} />}>Добавить</CzButton>
      </CzPageHeader>

      <CzDialog open={dialogOpen} onClose={() => setDialogOpen(false)} title={editingId ? "Редактировать канал" : "Новый канал"}>
        <form onSubmit={handleSubmit} className="cz-form">
          <CzInput label="Название" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="Название канала" />
          <CzSelect label="Тип канала" value={form.channel_type} onChange={(v) => setForm({ ...form, channel_type: v })} options={typeOptions} />
          <CzInput 
            label="Целевая аудитория (AI контекст)" 
            value={form.target_audience} 
            onChange={(e) => setForm({ ...form, target_audience: e.target.value })} 
            placeholder="Опишите, кто читает этот канал (напр. Tech entrepreneurs in Cyprus)"
          />
          <div className="cz-form-group">
            <label className="cz-form-label">Редакционная политика (AI инструкции)</label>
            <textarea 
              value={form.editorial_guidelines}
              onChange={(e) => setForm({ ...form, editorial_guidelines: e.target.value })}
              placeholder="Инструкции для ИИ редактора: что публиковать, о чем умалчивать, стиль..."
              style={{
                width: "100%", padding: "10px", fontSize: "14px", borderRadius: "var(--cz-radius-md)",
                border: "1px solid hsl(var(--cz-border))", minHeight: "80px", 
                backgroundColor: "hsl(var(--cz-bg-input))", color: "hsl(var(--cz-text-primary))",
                fontFamily: "var(--cz-font-sans)", resize: "vertical",
              }}
            />
          </div>
          <CzButton type="submit" fullWidth size="lg">{editingId ? "Сохранить" : "Создать"}</CzButton>
        </form>
      </CzDialog>

      {loading ? (
        <CzSkeletonGrid count={3} />
      ) : channels.length === 0 ? (
        <CzEmptyState
          icon={<Send size={48} />}
          title="Нет каналов"
          text="Добавьте канал публикации"
          action={<CzButton onClick={openNew} icon={<Plus size={16} />}>Добавить канал</CzButton>}
        />
      ) : (
        <div className="cz-card-grid stagger-children">
          {channels.map((ch) => {
            const Icon = typeIcons[ch.channel_type] || Send;
            return (
              <CzCard key={ch.id} interactive>
                <div className="cz-flex-between cz-items-start" style={{ marginBottom: 12 }}>
                  <div className="cz-flex cz-items-center cz-gap-12">
                    <div className="cz-icon-box">
                      <Icon size={20} />
                    </div>
                    <div>
                      <div className="cz-text-lg cz-font-semibold">{ch.name}</div>
                      <CzBadge variant={ch.is_active ? "success" : "default"}>
                        {ch.is_active ? "Активен" : "Выключен"}
                      </CzBadge>
                    </div>
                  </div>
                  <div className="cz-table-actions">
                    <CzButton variant="ghost" size="sm" onClick={() => openEdit(ch)} icon={<Pencil size={14} />} />
                    <CzButton variant="ghost" size="sm" onClick={() => handleDelete(ch.id)} icon={<Trash2 size={14} />} />
                  </div>
                </div>
                <div className="cz-flex cz-items-center cz-gap-12 cz-text-sm cz-text-muted">
                  <span>{typeLabels[ch.channel_type]}</span>
                  <span>{new Date(ch.created_at).toLocaleDateString("ru")}</span>
                </div>
              </CzCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
