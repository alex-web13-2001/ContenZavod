"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CzCard, CzBadge, CzSelect } from "@/components/ui-system";
import { FileText } from "lucide-react";

interface Material {
  id: string;
  title: string;
  original_url: string;
  status: string;
  word_count: number | null;
  created_at: string;
}

const statusConfig: Record<string, { label: string; variant: "default" | "success" | "warning" | "error" | "info" }> = {
  new: { label: "Новый", variant: "info" },
  classified: { label: "Классифицирован", variant: "default" },
  adapted: { label: "Адаптирован", variant: "warning" },
  published: { label: "Опубликован", variant: "success" },
  rejected: { label: "Отклонён", variant: "error" },
};

const statusOptions = [
  { value: "all", label: "Все статусы" },
  { value: "new", label: "Новый" },
  { value: "classified", label: "Классифицирован" },
  { value: "adapted", label: "Адаптирован" },
  { value: "published", label: "Опубликован" },
  { value: "rejected", label: "Отклонён" },
];

export default function MaterialsPage() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");

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
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, color: `hsl(var(--cz-text-primary))`, letterSpacing: "-0.02em" }}>Материалы</h1>
          <p style={{ fontSize: "14px", color: `hsl(var(--cz-text-muted))`, marginTop: "4px" }}>{total} материалов</p>
        </div>
        <div style={{ width: "200px" }}>
          <CzSelect value={statusFilter} onChange={setStatusFilter} options={statusOptions} />
        </div>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton" style={{ height: "64px" }} />)}
        </div>
      ) : materials.length === 0 ? (
        <CzCard>
          <div style={{ textAlign: "center", padding: "48px 24px" }}>
            <FileText size={48} style={{ color: `hsl(var(--cz-text-muted))`, margin: "0 auto 16px" }} />
            <h3 style={{ fontSize: "16px", fontWeight: 600, color: `hsl(var(--cz-text-secondary))` }}>Нет материалов</h3>
            <p style={{ fontSize: "13px", color: `hsl(var(--cz-text-muted))`, marginTop: "6px" }}>Материалы появятся после парсинга источников</p>
          </div>
        </CzCard>
      ) : (
        <div className="stagger-children" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {materials.map((m) => {
            const sc = statusConfig[m.status] || statusConfig.new;
            return (
              <CzCard key={m.id} interactive padding="sm">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", padding: "4px 0" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: "14px", fontWeight: 500, color: `hsl(var(--cz-text-primary))`, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {m.title}
                    </div>
                    <div style={{ fontSize: "12px", color: `hsl(var(--cz-text-muted))`, marginTop: "2px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {m.original_url}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", flexShrink: 0 }}>
                    {m.word_count && (
                      <span style={{ fontSize: "12px", color: `hsl(var(--cz-text-muted))` }}>{m.word_count} слов</span>
                    )}
                    <CzBadge variant={sc.variant}>{sc.label}</CzBadge>
                    <span style={{ fontSize: "12px", color: `hsl(var(--cz-text-muted))`, whiteSpace: "nowrap" }}>
                      {new Date(m.created_at).toLocaleDateString("ru")}
                    </span>
                  </div>
                </div>
              </CzCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
