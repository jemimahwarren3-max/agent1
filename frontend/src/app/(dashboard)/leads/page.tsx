"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

type Lead = {
  id: string;
  business_name: string;
  website: string;
  country: string | null;
  city: string | null;
  industry: string | null;
  status: string;
  is_unsubscribed: boolean;
};

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .leads()
      .then((data) => setLeads(data as Lead[]))
      .catch((err: ApiError) => setError(err.message));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Lead Database</h1>
        <p className="text-sm text-white/50">
          Full CRUD, bulk actions, CSV import/export land in Phase 4 once discovery and research
          are wired in. This view already reads and lists real leads from Postgres.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          Could not load leads: {error}
        </div>
      )}

      {!error && leads === null && (
        <div className="rounded-lg border border-navy-700 bg-navy-900 p-4 text-sm text-white/50">
          Loading…
        </div>
      )}

      {leads !== null && leads.length === 0 && (
        <div className="rounded-lg border border-navy-700 bg-navy-900 p-6 text-sm text-white/50">
          No leads yet.
        </div>
      )}

      {leads !== null && leads.length > 0 && (
        <table className="w-full overflow-hidden rounded-lg border border-navy-700 text-left text-sm">
          <thead className="bg-navy-900 text-white/50">
            <tr>
              <th className="px-4 py-2">Business</th>
              <th className="px-4 py-2">Website</th>
              <th className="px-4 py-2">Location</th>
              <th className="px-4 py-2">Industry</th>
              <th className="px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr key={lead.id} className="border-t border-navy-700 text-white/80">
                <td className="px-4 py-2">{lead.business_name}</td>
                <td className="px-4 py-2">
                  <a href={lead.website} target="_blank" className="text-accent-400 hover:underline">
                    {lead.website}
                  </a>
                </td>
                <td className="px-4 py-2">
                  {[lead.city, lead.country].filter(Boolean).join(", ") || "—"}
                </td>
                <td className="px-4 py-2">{lead.industry ?? "—"}</td>
                <td className="px-4 py-2">
                  <span className="rounded bg-accent-500/15 px-2 py-0.5 text-xs text-accent-400">
                    {lead.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
