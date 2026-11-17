"use client";

import { useEffect, useState } from "react";
import { api, ApiError, Campaign, EmailReply } from "@/lib/api";

const CLASSIFICATION_STYLES: Record<string, string> = {
  interested: "bg-green-500/15 text-green-300",
  wants_meeting: "bg-green-500/15 text-green-300",
  requesting_info: "bg-accent-500/15 text-accent-400",
  not_interested: "bg-white/10 text-white/50",
  out_of_office: "bg-white/10 text-white/50",
  unsubscribe: "bg-red-500/15 text-red-300",
  other: "bg-white/10 text-white/50",
};

export default function InboxPage() {
  const [replies, setReplies] = useState<EmailReply[] | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const load = async () => {
    try {
      const [repliesData, campaignsData] = await Promise.all([api.replies(), api.campaigns()]);
      setReplies(repliesData);
      setCampaigns(campaignsData);
      if (!selectedCampaign && campaignsData.length > 0) setSelectedCampaign(campaignsData[0].id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load inbox");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sync = async () => {
    if (!selectedCampaign) return;
    setSyncing(true);
    setError(null);
    setNotice(null);
    try {
      const newReplies = await api.syncReplies(selectedCampaign);
      setNotice(
        newReplies.length > 0
          ? `Found ${newReplies.length} new repl${newReplies.length === 1 ? "y" : "ies"}.`
          : "No new replies since last check."
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Inbox and Replies</h1>
        <p className="text-sm text-white/50">
          Replies to sent campaign emails, classified by the Email Management Agent. Requires a
          connected Google integration (see Integrations) and a campaign with sent emails.
        </p>
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>}
      {notice && <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300">{notice}</div>}

      <div className="flex items-center gap-3 rounded-lg border border-navy-700 bg-navy-900 p-4">
        <select
          value={selectedCampaign}
          onChange={(e) => setSelectedCampaign(e.target.value)}
          className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white"
        >
          {campaigns.length === 0 && <option value="">No campaigns yet</option>}
          {campaigns.map((campaign) => (
            <option key={campaign.id} value={campaign.id}>
              {campaign.name}
            </option>
          ))}
        </select>
        <button
          disabled={syncing || !selectedCampaign}
          onClick={sync}
          className="rounded-md bg-accent-500 px-4 py-2 text-xs font-medium text-navy-950 hover:bg-accent-400 disabled:opacity-40"
        >
          {syncing ? "Checking Gmail…" : "Check for replies"}
        </button>
      </div>

      {replies === null && <p className="text-sm text-white/50">Loading…</p>}
      {replies !== null && replies.length === 0 && (
        <p className="text-sm text-white/40">No replies yet.</p>
      )}

      <div className="space-y-3">
        {replies?.map((reply) => (
          <div key={reply.id} className="rounded-lg border border-navy-700 bg-navy-900 p-4">
            <div className="flex items-start justify-between gap-4">
              <p className="min-w-0 text-sm text-white/80">{reply.body_snippet || "(no preview)"}</p>
              <span
                className={`shrink-0 rounded px-2 py-0.5 text-[11px] ${
                  CLASSIFICATION_STYLES[reply.classification] ?? CLASSIFICATION_STYLES.other
                }`}
              >
                {reply.classification}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
