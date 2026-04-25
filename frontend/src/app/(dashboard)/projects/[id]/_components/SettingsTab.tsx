"use client";

import React, { useState } from "react";
import { CzButton } from "@/components/ui-system";
import { Pencil, Save } from "lucide-react";
import { Project } from "./types";

interface SettingsTabProps {
  project: Project;
  onSave: (form: { name: string; description: string; topic_guidelines: string; target_audience: string }) => Promise<void>;
}

export function SettingsTab({ project, onSave }: SettingsTabProps) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: project.name,
    description: project.description,
    topic_guidelines: project.topic_guidelines,
    target_audience: project.target_audience,
  });

  const startEdit = () => {
    setForm({
      name: project.name, description: project.description,
      topic_guidelines: project.topic_guidelines, target_audience: project.target_audience,
    });
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try { await onSave(form); setEditing(false); } finally { setSaving(false); }
  };

  const fields: { key: keyof typeof form; label: string; placeholder: string; rows: number }[] = [
    { key: "name", label: "Название проекта", placeholder: "", rows: 0 },
    { key: "description", label: "Описание", placeholder: "", rows: 2 },
    { key: "topic_guidelines", label: "Тематика (Topic Guidelines)", placeholder: "Опишите тематику проекта, ключевые темы...", rows: 4 },
    { key: "target_audience", label: "Целевая аудитория", placeholder: "Кто читает? Возраст, интересы, язык, география...", rows: 3 },
  ];

  return (
    <div className="cz-flex-col" style={{ gap: 16 }}>
      <div className="cz-glass-panel animate-page-in">
        <div className="cz-flex-col" style={{ gap: 20 }}>
          {/* Header */}
          <div className="cz-flex-between cz-items-center">
            <h3 className="cz-text-lg cz-font-semibold">Настройки проекта</h3>
            {!editing ? (
              <CzButton onClick={startEdit} icon={<Pencil size={13} />} size="sm">Редактировать</CzButton>
            ) : (
              <div className="cz-flex cz-gap-8">
                <CzButton variant="ghost" onClick={() => setEditing(false)}>Отмена</CzButton>
                <CzButton onClick={handleSave} disabled={saving} icon={<Save size={13} />}>
                  {saving ? "..." : "Сохранить"}
                </CzButton>
              </div>
            )}
          </div>

          {/* Fields */}
          {fields.map((field) => (
            <div key={field.key} className="cz-form-group">
              <label className="cz-form-label">{field.label}</label>
              {editing ? (
                field.rows === 0 ? (
                  <input type="text" className="cz-input focus-ring"
                    value={form[field.key]} onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} />
                ) : (
                  <textarea className="cz-textarea focus-ring" rows={field.rows} placeholder={field.placeholder}
                    value={form[field.key]} onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} />
                )
              ) : (
                <div className="cz-field-display">
                  {(project as unknown as Record<string, string>)[field.key] || "Не задано"}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
