"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

type Lead = Record<string, unknown>;

export default function OverviewPage() {
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .leads()
      .then(setLeads)
      .catch((err: ApiError) => setError(err.message));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Overview</h1>
        <p className="text-sm text-white/50">Live numbers from the lead database.</p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          Could not reach the API: {error}. Is the backend running at the configured
          NEXT_PUBLIC_API_URL?
        </div>
      )}

      {!error && leads === null && (
        <div className="rounded-lg border border-navy-700 bg-navy-900 p-4 text-sm text-white/50">
          Loading…
        </div>
      )}

      {leads !== null && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Total leads" value={leads.length} />
          <StatCard
            label="Qualified"
            value={leads.filter((l) => l.status === "qualified").length}
          />
          <StatCard label="Sent" value={leads.filter((l) => l.status === "sent").length} />
          <StatCard
            label="Unsubscribed"
            value={leads.filter((l) => l.is_unsubscribed).length}
          />
        </div>
      )}

      {leads !== null && leads.length === 0 && (
        <div className="rounded-lg border border-navy-700 bg-navy-900 p-6 text-sm text-white/50">
          No leads yet. Start a discovery job from the <strong>Discover Leads</strong> page once
          that phase is built, or add a lead manually from the Lead Database page.
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-navy-700 bg-navy-900 p-4">
      <p className="text-xs text-white/50">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}
