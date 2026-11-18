"use client";

import { useEffect, useState } from "react";
import { api, ApiError, EmailQueueEntry, Lead } from "@/lib/api";

export default function ApprovalsPage() {
  const [items, setItems] = useState<EmailQueueEntry[] | null>(null);
  const [leadsById, setLeadsById] = useState<Record<string, Lead>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    try {
      const [queue, leads] = await Promise.all([api.emailQueue(), api.leads()]);
      setItems(queue);
      setLeadsById(Object.fromEntries(leads.map((lead) => [lead.id, lead])));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load approval queue");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const approve = async (item: EmailQueueEntry) => {
    setBusyId(item.id);
    setError(null);
    try {
      await api.approveEmail(item.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Approve failed");
    } finally {
      setBusyId(null);
    }
  };

  const reject = async (item: EmailQueueEntry) => {
    const reason = window.prompt("Reason for rejecting this email?");
    if (!reason) return;
    setBusyId(item.id);
    setError(null);
    try {
      await api.rejectEmail(item.id, reason);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reject failed");
    } finally {
      setBusyId(null);
    }
  };

  const send = async (item: EmailQueueEntry) => {
    setBusyId(item.id);
    setError(null);
    setNotice(null);
    try {
      await api.sendEmail(item.id);
      setNotice(`Sent to ${leadsById[item.lead_id]?.business_name ?? "lead"}.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Send failed");
    } finally {
      setBusyId(null);
    }
  };

  const awaitingApproval = items?.filter((i) => i.status === "awaiting_approval") ?? [];
  const approved = items?.filter((i) => i.status === "approved") ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Approval Queue</h1>
        <p className="text-sm text-white/50">
          Review drafted emails before they go out. Approving moves an email to the ready-to-send
          list below; sending requires a connected Google integration on the campaign.
        </p>
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>}
      {notice && <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300">{notice}</div>}

      {items === null && <p className="text-sm text-white/50">Loading…</p>}

      <div>
        <h2 className="mb-3 text-sm font-semibold text-white/80">
          Awaiting approval ({awaitingApproval.length})
        </h2>
        {awaitingApproval.length === 0 && items !== null && (
          <p className="text-sm text-white/40">Nothing waiting on a decision.</p>
        )}
        <div className="space-y-3">
          {awaitingApproval.map((item) => (
            <div key={item.id} className="rounded-lg border border-navy-700 bg-navy-900 p-4">
              <p className="text-sm font-semibold text-white">
                {leadsById[item.lead_id]?.business_name ?? item.lead_id}
              </p>
              <p className="mt-1 text-xs text-white/50">{item.subject}</p>
              <p className="mt-2 whitespace-pre-wrap text-xs text-white/70">{item.body}</p>
              <div className="mt-3 flex gap-2">
                <button
                  disabled={busyId === item.id}
                  onClick={() => approve(item)}
                  className="rounded-md bg-accent-500 px-3 py-1 text-xs font-medium text-navy-950 hover:bg-accent-400 disabled:opacity-40"
                >
                  Approve
                </button>
                <button
                  disabled={busyId === item.id}
                  onClick={() => reject(item)}
                  className="rounded-md border border-red-500/30 px-3 py-1 text-xs text-red-300 hover:bg-red-500/10 disabled:opacity-40"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-white/80">Ready to send ({approved.length})</h2>
        {approved.length === 0 && items !== null && (
          <p className="text-sm text-white/40">Nothing approved yet.</p>
        )}
        <div className="space-y-3">
          {approved.map((item) => (
            <div key={item.id} className="rounded-lg border border-navy-700 bg-navy-900 p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">
                    {leadsById[item.lead_id]?.business_name ?? item.lead_id}
                  </p>
                  <p className="text-xs text-white/50">{item.subject}</p>
                </div>
                <button
                  disabled={busyId === item.id}
                  onClick={() => send(item)}
                  className="shrink-0 rounded-md bg-accent-500 px-3 py-1 text-xs font-medium text-navy-950 hover:bg-accent-400 disabled:opacity-40"
                >
                  {busyId === item.id ? "Sending…" : "Send"}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
