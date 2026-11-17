"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, ApiError, Integration } from "@/lib/api";

export default function IntegrationsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-white/50">Loading…</p>}>
      <IntegrationsPageContent />
    </Suspense>
  );
}

function IntegrationsPageContent() {
  const [integrations, setIntegrations] = useState<Integration[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const searchParams = useSearchParams();

  const load = async () => {
    try {
      setIntegrations(await api.integrations());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load integrations");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const connect = async () => {
    setBusy(true);
    setError(null);
    try {
      const { authorize_url } = await api.googleAuthorizeUrl();
      window.location.href = authorize_url;
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Failed to start Google sign-in"
      );
      setBusy(false);
    }
  };

  const disconnect = async (integration: Integration) => {
    setBusy(true);
    setError(null);
    try {
      await api.disconnectIntegration(integration.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to disconnect");
    } finally {
      setBusy(false);
    }
  };

  const google = integrations?.find((i) => i.provider === "google_workspace");
  const connected = google?.status === "connected";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Google Integrations</h1>
        <p className="text-sm text-white/50">
          Connect a Google account to send campaign emails through Gmail and monitor replies.
          Sheets/Drive scopes are requested too but not yet used by any feature.
        </p>
      </div>

      {searchParams.get("connected") === "1" && (
        <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300">
          Google account connected.
        </div>
      )}
      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>}

      {integrations === null && <p className="text-sm text-white/50">Loading…</p>}

      {integrations !== null && (
        <div className="rounded-lg border border-navy-700 bg-navy-900 p-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-white">Google Workspace</p>
              <p className="text-xs text-white/50">
                {connected
                  ? `Connected as ${google?.connected_account_email}`
                  : "Not connected — Gmail sending and reply monitoring are unavailable until you connect."}
              </p>
              {connected && google && google.scopes.length > 0 && (
                <p className="mt-1 text-xs text-white/30">{google.scopes.join(", ")}</p>
              )}
            </div>
            {connected ? (
              <button
                disabled={busy}
                onClick={() => google && disconnect(google)}
                className="shrink-0 rounded-md border border-red-500/30 px-4 py-2 text-xs text-red-300 hover:bg-red-500/10 disabled:opacity-40"
              >
                Disconnect
              </button>
            ) : (
              <button
                disabled={busy}
                onClick={connect}
                className="shrink-0 rounded-md bg-accent-500 px-4 py-2 text-xs font-medium text-navy-950 hover:bg-accent-400 disabled:opacity-40"
              >
                {busy ? "Redirecting…" : "Connect Google account"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
