"use client";

import { useEffect, useState } from "react";
import { api, ApiError, DiscoveryJob } from "@/lib/api";
import { Pause, Play, Square } from "lucide-react";

const ACTIVE = new Set(["pending", "running"]);
const STATUS_COLORS: Record<string, string> = {
  pending: "text-white/60",
  running: "text-accent-400",
  paused: "text-yellow-400",
  completed: "text-green-400",
  failed: "text-red-400",
  cancelled: "text-white/40",
};

export function JobProgress({ jobId, onChange }: { jobId: string; onChange?: () => void }) {
  const [job, setJob] = useState<DiscoveryJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const data = await api.discoveryJob(jobId);
        if (!active) return;
        setJob(data);
        onChange?.();
        if (ACTIVE.has(data.status) || data.status === "paused") {
          timer = setTimeout(poll, 2500);
        }
      } catch (err) {
        if (active) setError(err instanceof ApiError ? err.message : "Failed to load job");
      }
    }
    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [jobId, onChange]);

  if (error) {
    return <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>;
  }
  if (!job) {
    return <div className="rounded-lg border border-navy-700 bg-navy-900 p-4 text-sm text-white/50">Loading job…</div>;
  }

  const act = async (fn: (id: string) => Promise<DiscoveryJob>) => {
    try {
      setJob(await fn(job.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed");
    }
  };

  const canPause = job.status === "running" || job.status === "pending";
  const canResume = job.status === "paused";
  const canCancel = !["completed", "cancelled", "failed"].includes(job.status);

  return (
    <div className="space-y-4 rounded-lg border border-navy-700 bg-navy-900 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-white/40">Discovery job</p>
          <p className={`text-sm font-semibold uppercase tracking-wide ${STATUS_COLORS[job.status]}`}>
            {job.status}
          </p>
        </div>
        <div className="flex gap-2">
          {canPause && (
            <button onClick={() => act(api.pauseDiscovery)} className="flex items-center gap-1 rounded-md border border-navy-700 px-3 py-1.5 text-xs text-white/80 hover:bg-white/5">
              <Pause size={13} /> Pause
            </button>
          )}
          {canResume && (
            <button onClick={() => act(api.resumeDiscovery)} className="flex items-center gap-1 rounded-md border border-navy-700 px-3 py-1.5 text-xs text-white/80 hover:bg-white/5">
              <Play size={13} /> Resume
            </button>
          )}
          {canCancel && (
            <button onClick={() => act(api.cancelDiscovery)} className="flex items-center gap-1 rounded-md border border-red-500/30 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/10">
              <Square size={13} /> Cancel
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat label="Discovered" value={job.discovered_count} />
        <Stat label="Researched" value={job.researched_count} />
        <Stat label="Qualified" value={job.qualified_count} />
        <Stat label="Duplicates" value={job.duplicate_count} />
        <Stat label="Failed" value={job.failed_count} />
      </div>

      {job.error_message && (
        <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
          {job.error_message}
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-navy-800 bg-navy-950 p-3">
      <p className="text-[11px] text-white/40">{label}</p>
      <p className="mt-0.5 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
