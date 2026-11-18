"use client";

import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  Campaign,
  CampaignInput,
  EmailTemplate,
  Integration,
} from "@/lib/api";

const EMPTY_FORM: CampaignInput = {
  name: "",
  target_country: "",
  target_city: "",
  target_industry: "",
  email_template_id: "",
  integration_id: "",
  max_daily_sends: 25,
  follow_up_interval_days: 5,
  approval_mode: "manual",
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [form, setForm] = useState<CampaignInput>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    try {
      const [campaignsData, templatesData, integrationsData] = await Promise.all([
        api.campaigns(),
        api.templates(),
        api.integrations(),
      ]);
      setCampaigns(campaignsData);
      setTemplates(templatesData);
      setIntegrations(integrationsData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load campaigns");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const startEdit = (campaign: Campaign) => {
    setEditingId(campaign.id);
    setForm({
      name: campaign.name,
      target_country: campaign.target_country ?? "",
      target_city: campaign.target_city ?? "",
      target_industry: campaign.target_industry ?? "",
      email_template_id: campaign.email_template_id ?? "",
      integration_id: campaign.integration_id ?? "",
      max_daily_sends: campaign.max_daily_sends,
      follow_up_interval_days: campaign.follow_up_interval_days,
      approval_mode: campaign.approval_mode,
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
    const payload: CampaignInput = {
      ...form,
      target_country: form.target_country || null,
      target_city: form.target_city || null,
      target_industry: form.target_industry || null,
      email_template_id: form.email_template_id || null,
      integration_id: form.integration_id || null,
    };
    try {
      if (editingId) {
        await api.updateCampaign(editingId, payload);
        setNotice(`Updated "${form.name}".`);
      } else {
        await api.createCampaign(payload);
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

  const matchLeads = async (campaign: Campaign) => {
    setBusyId(campaign.id);
    setError(null);
    setNotice(null);
    try {
      const result = await api.matchCampaignLeads(campaign.id);
      setNotice(
        `Matched ${result.matched_count} lead(s) into "${campaign.name}"` +
          (result.skipped_suppressed_count > 0
            ? ` (skipped ${result.skipped_suppressed_count} suppressed).`
            : ".")
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Matching failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Campaigns</h1>
        <p className="text-sm text-white/50">
          Build a campaign, then match leads into it by target country/city/industry. Sending and
          approval happen from the Approval Queue once leads have drafted emails.
        </p>
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>}
      {notice && <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300">{notice}</div>}

      <div className="rounded-lg border border-navy-700 bg-navy-900 p-4">
        <h2 className="mb-3 text-sm font-semibold text-white">
          {editingId ? "Edit campaign" : "New campaign"}
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            placeholder="Campaign name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30 sm:col-span-2"
          />
          <input
            placeholder="Target country"
            value={form.target_country ?? ""}
            onChange={(e) => setForm({ ...form, target_country: e.target.value })}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30"
          />
          <input
            placeholder="Target city"
            value={form.target_city ?? ""}
            onChange={(e) => setForm({ ...form, target_city: e.target.value })}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30"
          />
          <input
            placeholder="Target industry"
            value={form.target_industry ?? ""}
            onChange={(e) => setForm({ ...form, target_industry: e.target.value })}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30 sm:col-span-2"
          />
          <select
            value={form.email_template_id ?? ""}
            onChange={(e) => setForm({ ...form, email_template_id: e.target.value })}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white"
          >
            <option value="">No template selected</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <select
            value={form.integration_id ?? ""}
            onChange={(e) => setForm({ ...form, integration_id: e.target.value })}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white"
          >
            <option value="">No Google account connected</option>
            {integrations
              .filter((i) => i.status === "connected")
              .map((i) => (
                <option key={i.id} value={i.id}>
                  {i.connected_account_email}
                </option>
              ))}
          </select>
          <label className="flex items-center gap-2 text-xs text-white/60">
            Max daily sends
            <input
              type="number"
              min={1}
              value={form.max_daily_sends}
              onChange={(e) => setForm({ ...form, max_daily_sends: Number(e.target.value) })}
              className="w-20 rounded-md border border-navy-700 bg-navy-950 px-2 py-1 text-sm text-white"
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-white/60">
            Follow-up after (days)
            <input
              type="number"
              min={1}
              value={form.follow_up_interval_days}
              onChange={(e) => setForm({ ...form, follow_up_interval_days: Number(e.target.value) })}
              className="w-20 rounded-md border border-navy-700 bg-navy-950 px-2 py-1 text-sm text-white"
            />
          </label>
          <select
            value={form.approval_mode}
            onChange={(e) => setForm({ ...form, approval_mode: e.target.value })}
            className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white sm:col-span-2"
          >
            <option value="manual">Manual approval</option>
            <option value="automatic">Automatic sending</option>
          </select>
        </div>
        <div className="mt-3 flex gap-2">
          <button
            onClick={submit}
            disabled={saving || !form.name}
            className="rounded-md bg-accent-500 px-4 py-2 text-xs font-medium text-navy-950 hover:bg-accent-400 disabled:opacity-40"
          >
            {saving ? "Saving…" : editingId ? "Save changes" : "Create campaign"}
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

      {campaigns === null && <p className="text-sm text-white/50">Loading…</p>}
      {campaigns !== null && campaigns.length === 0 && (
        <p className="text-sm text-white/40">No campaigns yet — create one above.</p>
      )}

      <div className="space-y-3">
        {campaigns?.map((campaign) => (
          <div key={campaign.id} className="rounded-lg border border-navy-700 bg-navy-900 p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{campaign.name}</p>
                <p className="text-xs text-white/50">
                  {[campaign.target_city, campaign.target_country, campaign.target_industry]
                    .filter(Boolean)
                    .join(" · ") || "No targeting set"}
                </p>
                <div className="mt-2 flex gap-2">
                  <span className="rounded bg-accent-500/15 px-2 py-0.5 text-[11px] text-accent-400">
                    {campaign.stage}
                  </span>
                  <span className="rounded bg-white/10 px-2 py-0.5 text-[11px] text-white/60">
                    {campaign.approval_mode}
                  </span>
                  <span className="rounded bg-white/10 px-2 py-0.5 text-[11px] text-white/60">
                    max {campaign.max_daily_sends}/day
                  </span>
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  disabled={busyId === campaign.id}
                  onClick={() => matchLeads(campaign)}
                  className="rounded-md border border-navy-700 px-3 py-1 text-xs text-white/80 hover:bg-white/5 disabled:opacity-40"
                >
                  {busyId === campaign.id ? "Matching…" : "Match leads"}
                </button>
                <button
                  onClick={() => startEdit(campaign)}
                  className="rounded-md border border-navy-700 px-3 py-1 text-xs text-white/80 hover:bg-white/5"
                >
                  Edit
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
