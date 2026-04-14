"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Plus, Pencil, Trash2, Globe, Rss, Zap, Users } from "lucide-react";
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

const typeIcons: Record<string, React.ElementType> = {
  rss: Rss,
  website: Globe,
  api: Zap,
  social: Users,
};

const typeLabels: Record<string, string> = {
  rss: "RSS",
  website: "Сайт",
  api: "API",
  social: "Соцсети",
};

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", url: "", source_type: "rss", is_active: true });

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
        await api.post("/sources", form);
        toast.success("Источник добавлен");
      }
      setDialogOpen(false);
      setEditingId(null);
      setForm({ name: "", url: "", source_type: "rss", is_active: true });
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

  const openEdit = (source: Source) => {
    setEditingId(source.id);
    setForm({ name: source.name, url: source.url, source_type: source.source_type, is_active: source.is_active });
    setDialogOpen(true);
  };

  const openNew = () => {
    setEditingId(null);
    setForm({ name: "", url: "", source_type: "rss", is_active: true });
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Источники</h1>
          <p className="text-zinc-500 mt-1">Управление источниками контента</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={openNew} className="bg-indigo-600 hover:bg-indigo-500">
              <Plus className="h-4 w-4 mr-2" /> Добавить
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-zinc-900 border-zinc-800">
            <DialogHeader>
              <DialogTitle className="text-zinc-100">
                {editingId ? "Редактировать источник" : "Новый источник"}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label className="text-zinc-300">Название</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="bg-zinc-800 border-zinc-700 text-zinc-100" />
              </div>
              <div className="space-y-2">
                <Label className="text-zinc-300">URL</Label>
                <Input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} required className="bg-zinc-800 border-zinc-700 text-zinc-100" />
              </div>
              <div className="space-y-2">
                <Label className="text-zinc-300">Тип</Label>
                <Select value={form.source_type} onValueChange={(v) => setForm({ ...form, source_type: v })}>
                  <SelectTrigger className="bg-zinc-800 border-zinc-700 text-zinc-100"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-zinc-800 border-zinc-700">
                    <SelectItem value="rss">RSS</SelectItem>
                    <SelectItem value="website">Сайт</SelectItem>
                    <SelectItem value="api">API</SelectItem>
                    <SelectItem value="social">Соцсети</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-3">
                <Switch checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: v })} />
                <Label className="text-zinc-300">Активен</Label>
              </div>
              <Button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-500">
                {editingId ? "Сохранить" : "Создать"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="bg-zinc-900/50 border-zinc-800 animate-pulse">
              <CardContent className="p-6 h-32" />
            </Card>
          ))}
        </div>
      ) : sources.length === 0 ? (
        <Card className="bg-zinc-900/50 border-zinc-800 border-dashed">
          <CardContent className="p-12 text-center">
            <Radio className="h-12 w-12 mx-auto text-zinc-600 mb-4" />
            <h3 className="text-lg font-medium text-zinc-300">Нет источников</h3>
            <p className="text-zinc-500 mt-1">Добавьте первый источник контента</p>
            <Button onClick={openNew} className="mt-4 bg-indigo-600 hover:bg-indigo-500">
              <Plus className="h-4 w-4 mr-2" /> Добавить источник
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sources.map((source) => {
            const Icon = typeIcons[source.source_type] || Globe;
            return (
              <Card key={source.id} className="bg-zinc-900/50 border-zinc-800 hover:border-zinc-700 transition-all group">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-zinc-800 flex items-center justify-center">
                        <Icon className="h-5 w-5 text-zinc-400" />
                      </div>
                      <div>
                        <CardTitle className="text-sm font-medium text-zinc-200">{source.name}</CardTitle>
                        <Badge variant={source.is_active ? "default" : "secondary"} className={`text-xs mt-1 ${source.is_active ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-zinc-700 text-zinc-400"}`}>
                          {source.is_active ? "Активен" : "Выключен"}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-500 hover:text-zinc-200" onClick={() => openEdit(source)}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-500 hover:text-red-400" onClick={() => handleDelete(source.id)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-xs text-zinc-500 truncate">{source.url}</p>
                  <div className="flex items-center gap-4 mt-3 text-xs text-zinc-500">
                    <span>{typeLabels[source.source_type]}</span>
                    {source.error_count > 0 && (
                      <span className="text-red-400">{source.error_count} ошибок</span>
                    )}
                    {source.last_scraped_at && (
                      <span>Парсинг: {new Date(source.last_scraped_at).toLocaleDateString("ru")}</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
