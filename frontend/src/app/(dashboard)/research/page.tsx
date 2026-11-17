"use client";

import { useEffect, useState } from "react";
import { api, ApiError, Lead } from "@/lib/api";

export default function ResearchPage() {
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = async () => {
    try {
      setLeads(await api.leads());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load leads");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const run = async (lead: Lead, action: "research" | "qualify") => {
    setBusyId(lead.id);
    setError(null);
    setNotice(null);
    try {
      if (action === "research") {
        await api.researchLead(lead.id);
        setNotice(`Researched ${lead.business_name}.`);
      } else {
        const score = await api.qualifyLead(lead.id);
        setNotice(`${lead.business_name} scored ${score.score} (${score.classification}).`);
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Research Centre</h1>
        <p className="text-sm text-white/50">
          Run website research and lead qualification on individual businesses, or review what the
          agents already found. Bulk discovery runs from the Discover Leads page.
        </p>
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>}
      {notice && <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300">{notice}</div>}

      {leads === null && <p className="text-sm text-white/50">Loading…</p>}
      {leads !== null && leads.length === 0 && (
        <p className="text-sm text-white/40">No leads yet. Start a discovery job or add a lead manually.</p>
      )}

      <div className="space-y-3">
        {leads?.map((lead) => (
          <div key={lead.id} className="rounded-lg border border-navy-700 bg-navy-900 p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{lead.business_name}</p>
                <a href={lead.website} target="_blank" className="text-xs text-accent-400 hover:underline">
                  {lead.website}
                </a>
                {lead.identified_opportunity && (
                  <p className="mt-2 text-xs text-white/60">
                    <span className="text-white/40">Opportunity:</span> {lead.identified_opportunity}
                  </p>
                )}
                {lead.recommended_service && (
                  <p className="text-xs text-white/60">
                    <span className="text-white/40">Suggested service:</span> {lead.recommended_service}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 flex-col items-end gap-2">
                <span className="rounded bg-accent-500/15 px-2 py-0.5 text-[11px] text-accent-400">{lead.status}</span>
                <div className="flex gap-2">
                  <button
                    disabled={busyId === lead.id}
                    onClick={() => run(lead, "research")}
                    className="rounded-md border border-navy-700 px-3 py-1 text-xs text-white/80 hover:bg-white/5 disabled:opacity-40"
                  >
                    {busyId === lead.id ? "Working…" : "Research"}
                  </button>
                  <button
                    disabled={busyId === lead.id}
                    onClick={() => run(lead, "qualify")}
                    className="rounded-md border border-navy-700 px-3 py-1 text-xs text-white/80 hover:bg-white/5 disabled:opacity-40"
                  >
                    Qualify
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
