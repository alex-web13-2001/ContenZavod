"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CzButton, CzInput, CzSelect, CzCard, CzBadge, CzDialog } from "@/components/ui-system";
import { Plus, Pencil, Trash2, Send, MessageCircle, Video, Globe } from "lucide-react";
import { toast } from "sonner";

interface Channel {
  id: string;
  name: string;
  channel_type: string;
  config: Record<string, unknown>;
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
  const [form, setForm] = useState({ name: "", channel_type: "telegram" });

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
      setForm({ name: "", channel_type: "telegram" });
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
    setForm({ name: ch.name, channel_type: ch.channel_type });
    setDialogOpen(true);
  };

  const openNew = () => {
    setEditingId(null);
    setForm({ name: "", channel_type: "telegram" });
    setDialogOpen(true);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, color: `hsl(var(--cz-text-primary))`, letterSpacing: "-0.02em" }}>Каналы публикации</h1>
          <p style={{ fontSize: "14px", color: `hsl(var(--cz-text-muted))`, marginTop: "4px" }}>Управление каналами дистрибуции</p>
        </div>
        <CzButton onClick={openNew} icon={<Plus size={16} />}>Добавить</CzButton>
      </div>

      <CzDialog open={dialogOpen} onClose={() => setDialogOpen(false)} title={editingId ? "Редактировать канал" : "Новый канал"}>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <CzInput label="Название" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="Название канала" />
          <CzSelect label="Тип канала" value={form.channel_type} onChange={(v) => setForm({ ...form, channel_type: v })} options={typeOptions} />
          <CzButton type="submit" fullWidth size="lg">{editingId ? "Сохранить" : "Создать"}</CzButton>
        </form>
      </CzDialog>

      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "16px" }}>
          {[1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: "140px" }} />)}
        </div>
      ) : channels.length === 0 ? (
        <CzCard>
          <div style={{ textAlign: "center", padding: "48px 24px" }}>
            <Send size={48} style={{ color: `hsl(var(--cz-text-muted))`, margin: "0 auto 16px" }} />
            <h3 style={{ fontSize: "16px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))` }}>Нет каналов</h3>
            <p style={{ fontSize: "13px", color: `hsl(var(--cz-text-muted))`, marginTop: "6px" }}>Добавьте канал публикации</p>
            <div style={{ marginTop: "20px" }}>
              <CzButton onClick={openNew} icon={<Plus size={16} />}>Добавить канал</CzButton>
            </div>
          </div>
        </CzCard>
      ) : (
        <div className="stagger-children" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "16px" }}>
          {channels.map((ch) => {
            const Icon = typeIcons[ch.channel_type] || Send;
            return (
              <CzCard key={ch.id} interactive>
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
                      <div style={{ fontSize: "14px", fontWeight: 600, color: `hsl(var(--cz-text-primary))` }}>{ch.name}</div>
                      <CzBadge variant={ch.is_active ? "success" : "default"}>
                        {ch.is_active ? "Активен" : "Выключен"}
                      </CzBadge>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "4px" }}>
                    <CzButton variant="ghost" size="sm" onClick={() => openEdit(ch)} icon={<Pencil size={14} />} />
                    <CzButton variant="ghost" size="sm" onClick={() => handleDelete(ch.id)} icon={<Trash2 size={14} />} />
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "12px", color: `hsl(var(--cz-text-muted))` }}>
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
