"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileText } from "lucide-react";

interface Material {
  id: string;
  title: string;
  original_url: string;
  status: string;
  word_count: number | null;
  scraped_at: string;
  created_at: string;
}

const statusConfig: Record<string, { label: string; color: string }> = {
  new: { label: "Новый", color: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
  classified: { label: "Классифицирован", color: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
  adapted: { label: "Адаптирован", color: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  published: { label: "Опубликован", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  rejected: { label: "Отклонён", color: "bg-red-500/10 text-red-400 border-red-500/20" },
};

export default function MaterialsPage() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const fetchMaterials = async (status?: string) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (status && status !== "all") params.set("status", status);
      const data = await api.get<{ items: Material[]; total: number }>(`/materials?${params}`);
      setMaterials(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMaterials(statusFilter); }, [statusFilter]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Материалы</h1>
          <p className="text-zinc-500 mt-1">{total} материалов</p>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48 bg-zinc-800 border-zinc-700 text-zinc-100">
            <SelectValue placeholder="Все статусы" />
          </SelectTrigger>
          <SelectContent className="bg-zinc-800 border-zinc-700">
            <SelectItem value="all">Все статусы</SelectItem>
            <SelectItem value="new">Новый</SelectItem>
            <SelectItem value="classified">Классифицирован</SelectItem>
            <SelectItem value="adapted">Адаптирован</SelectItem>
            <SelectItem value="published">Опубликован</SelectItem>
            <SelectItem value="rejected">Отклонён</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Card key={i} className="bg-zinc-900/50 border-zinc-800 animate-pulse">
              <CardContent className="p-4 h-20" />
            </Card>
          ))}
        </div>
      ) : materials.length === 0 ? (
        <Card className="bg-zinc-900/50 border-zinc-800 border-dashed">
          <CardContent className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-zinc-600 mb-4" />
            <h3 className="text-lg font-medium text-zinc-300">Нет материалов</h3>
            <p className="text-zinc-500 mt-1">
              Материалы появятся после парсинга источников
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {materials.map((material) => {
            const sc = statusConfig[material.status] || statusConfig.new;
            return (
              <Card
                key={material.id}
                className="bg-zinc-900/50 border-zinc-800 hover:border-zinc-700 transition-colors cursor-pointer"
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-zinc-200 truncate">
                        {material.title}
                      </h3>
                      <p className="text-xs text-zinc-500 truncate mt-1">
                        {material.original_url}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      {material.word_count && (
                        <span className="text-xs text-zinc-500">
                          {material.word_count} слов
                        </span>
                      )}
                      <Badge variant="outline" className={`text-xs ${sc.color}`}>
                        {sc.label}
                      </Badge>
                      <span className="text-xs text-zinc-600">
                        {new Date(material.created_at).toLocaleDateString("ru")}
                      </span>
                    </div>
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
