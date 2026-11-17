"use client";

import { useEffect, useState } from "react";
import { api, ApiError, EmailTemplate, TemplateInput } from "@/lib/api";

const CATEGORIES = [
  "general_introduction",
  "website_development",
  "ai_automation",
  "ai_customer_support",
  "workflow_automation",
  "custom_software",
  "industry_specific",
  "follow_up",
];

const EMPTY_FORM: TemplateInput = {
  name: "",
  category: CATEGORIES[0],
  subject: "",
  body: "",
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<EmailTemplate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [form, setForm] = useState<TemplateInput>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      setTemplates(await api.templates());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load templates");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const startEdit = (template: EmailTemplate) => {
    setEditingId(template.id);
    setForm({
      name: template.name,
      category: template.category,
      subject: template.subject,
      body: template.body,
    });
  };

  const resetForm = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
  };

  const submit = async () => {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      if (editingId) {
        await api.updateTemplate(editingId, form);
        setNotice(`Updated "${form.name}".`);
      } else {
        await api.createTemplate(form);
        setNotice(`Created "${form.name}".`);
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const toggleApproved = async (template: EmailTemplate) => {
    setBusyId(template.id);
    try {
      await api.updateTemplate(template.id, { is_approved: !template.is_approved });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (template: EmailTemplate) => {
    setBusyId(template.id);
    try {
      await api.deleteTemplate(template.id);
      if (editingId === template.id) resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Email Templates</h1>
        <p className="text-sm text-white/50">
          Reusable subject/body pairs by category. A template must be approved before it&apos;s
          safe to use as a starting point for outreach drafts.
        </p>
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>}
      {notice && <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300">{notice}</div>}

      <div className="rounded-lg border border-navy-700 bg-navy-900 p-4">
        <h2 className="mb-3 text-sm font-semibold text-white">
          {editingId ? "Edit template" : "New template"}
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30"
          />
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white"
          >
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
          <input
            placeholder="Subject"
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30 sm:col-span-2"
          />
          <textarea
            placeholder="Body"
            value={form.body}
            onChange={(e) => setForm({ ...form, body: e.target.value })}
            rows={6}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30 sm:col-span-2"
          />
        </div>
        <div className="mt-3 flex gap-2">
          <button
            onClick={submit}
            disabled={saving || !form.name || !form.subject || !form.body}
            className="rounded-md bg-accent-500 px-4 py-2 text-xs font-medium text-navy-950 hover:bg-accent-400 disabled:opacity-40"
          >
            {saving ? "Saving…" : editingId ? "Save changes" : "Create template"}
          </button>
          {editingId && (
            <button
              onClick={resetForm}
              className="rounded-md border border-navy-700 px-4 py-2 text-xs text-white/70 hover:bg-white/5"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {templates === null && <p className="text-sm text-white/50">Loading…</p>}
      {templates !== null && templates.length === 0 && (
        <p className="text-sm text-white/40">No templates yet — create one above.</p>
      )}

      <div className="space-y-3">
        {templates?.map((template) => (
          <div key={template.id} className="rounded-lg border border-navy-700 bg-navy-900 p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{template.name}</p>
                <p className="text-xs text-white/50">{template.subject}</p>
                <span className="mt-2 inline-block rounded bg-accent-500/15 px-2 py-0.5 text-[11px] text-accent-400">
                  {template.category}
                </span>
                <span
                  className={`ml-2 inline-block rounded px-2 py-0.5 text-[11px] ${
                    template.is_approved ? "bg-green-500/15 text-green-300" : "bg-white/10 text-white/50"
                  }`}
                >
                  {template.is_approved ? "approved" : "unapproved"}
                </span>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  disabled={busyId === template.id}
                  onClick={() => toggleApproved(template)}
                  className="rounded-md border border-navy-700 px-3 py-1 text-xs text-white/80 hover:bg-white/5 disabled:opacity-40"
                >
                  {template.is_approved ? "Unapprove" : "Approve"}
                </button>
                <button
                  onClick={() => startEdit(template)}
                  className="rounded-md border border-navy-700 px-3 py-1 text-xs text-white/80 hover:bg-white/5"
                >
                  Edit
                </button>
                <button
                  disabled={busyId === template.id}
                  onClick={() => remove(template)}
                  className="rounded-md border border-red-500/30 px-3 py-1 text-xs text-red-300 hover:bg-red-500/10 disabled:opacity-40"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
