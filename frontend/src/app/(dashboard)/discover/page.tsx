"use client";

import { useEffect, useState } from "react";
import { api, ApiError, DiscoveryJob, DiscoveryStartParams } from "@/lib/api";
import { JobProgress } from "@/components/JobProgress";

const EMPTY: DiscoveryStartParams = {
  country: "Zimbabwe",
  city: "",
  industry: "",
  business_type: "",
  keywords: "",
  services: "",
  num_leads: 20,
};

export default function DiscoverPage() {
  const [form, setForm] = useState<DiscoveryStartParams>(EMPTY);
  const [jobs, setJobs] = useState<DiscoveryJob[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const loadJobs = async () => {
    try {
      setJobs(await api.discoveryJobs());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load jobs");
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const field = (key: keyof DiscoveryStartParams, value: string) =>
    setForm((f) => ({ ...f, [key]: key === "num_leads" ? Number(value) : value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const job = await api.startDiscovery(form);
      setActiveJobId(job.id);
      await loadJobs();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start discovery");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Discover Leads</h1>
        <p className="text-sm text-white/50">
          Describe the businesses to find. The system searches, crawls each site, extracts
          publicly-listed details, qualifies the lead, and saves the results — running in the
          background so you can leave this page.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>
      )}

      <form onSubmit={submit} className="grid grid-cols-1 gap-4 rounded-lg border border-navy-700 bg-navy-900 p-5 md:grid-cols-2">
        <Field label="Country" value={form.country ?? ""} onChange={(v) => field("country", v)} />
        <Field label="City / region" value={form.city ?? ""} onChange={(v) => field("city", v)} />
        <Field label="Industry" value={form.industry ?? ""} onChange={(v) => field("industry", v)} placeholder="Hospitality" />
        <Field label="Business type" value={form.business_type ?? ""} onChange={(v) => field("business_type", v)} placeholder="Hotels and lodges" />
        <Field label="Keywords" value={form.keywords ?? ""} onChange={(v) => field("keywords", v)} placeholder="booking automation" />
        <Field label="Services to promote" value={form.services ?? ""} onChange={(v) => field("services", v)} placeholder="Website development, AI booking" />
        <Field label="Number of leads" type="number" value={String(form.num_leads ?? 20)} onChange={(v) => field("num_leads", v)} />
        <div className="flex items-end">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50"
          >
            {submitting ? "Starting…" : "Start discovery"}
          </button>
        </div>
      </form>

      <p className="text-xs text-white/40">
        Note: discovery needs a Gemini API key and a search provider configured on the backend. Without
        them a job will finish with an error explaining what to set — see docs/GOOGLE_CLOUD_SETUP.md.
      </p>

      {activeJobId && <JobProgress jobId={activeJobId} onChange={loadJobs} />}

      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-white/80">Recent jobs</h2>
        {jobs.length === 0 && <p className="text-sm text-white/40">No discovery jobs yet.</p>}
        {jobs.map((j) => (
          <button
            key={j.id}
            onClick={() => setActiveJobId(j.id)}
            className="flex w-full items-center justify-between rounded-lg border border-navy-700 bg-navy-900 px-4 py-3 text-left hover:bg-white/5"
          >
            <span className="text-sm text-white/80">
              {String(j.search_params.industry ?? "—")} · {String(j.search_params.city ?? j.search_params.country ?? "")}
            </span>
            <span className="text-xs text-white/50">
              {j.status} · {j.discovered_count} found / {j.qualified_count} qualified
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-white/60">{label}</label>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white outline-none focus:border-accent-500"
      />
    </div>
  );
}
