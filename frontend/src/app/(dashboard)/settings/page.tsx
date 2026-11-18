"use client";

import { useEffect, useState } from "react";
import { api, ApiError, AuditLogEntry, CompanyProfile, CurrentUser } from "@/lib/api";

const EMPTY_INVITE = { email: "", full_name: "", password: "", role: "member" };

export default function SettingsPage() {
  const [me, setMe] = useState<CurrentUser | null>(null);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [profileForm, setProfileForm] = useState<Partial<CompanyProfile>>({});
  const [users, setUsers] = useState<CurrentUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [invite, setInvite] = useState(EMPTY_INVITE);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const isAdmin = me?.role === "admin";

  const load = async () => {
    try {
      const [meData, profileData] = await Promise.all([api.me(), api.companyProfile()]);
      setMe(meData);
      setProfile(profileData);
      setProfileForm(profileData);
      if (meData.role === "admin") {
        const [usersData, auditData] = await Promise.all([api.users(), api.auditLogs()]);
        setUsers(usersData);
        setAuditLogs(auditData);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load settings");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const saveProfile = async () => {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await api.updateCompanyProfile(profileForm);
      setProfile(updated);
      setNotice("Company profile updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const submitInvite = async () => {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await api.inviteUser(invite);
      setNotice(`Added ${invite.full_name} as ${invite.role}.`);
      setInvite(EMPTY_INVITE);
      setUsers(await api.users());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add team member");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="text-sm text-white/50">
          Company profile, team, and the audit log of every mutation taken in this workspace.
        </p>
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>}
      {notice && <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300">{notice}</div>}

      {me && (
        <div className="rounded-lg border border-navy-700 bg-navy-900 p-4 text-sm text-white/70">
          Signed in as <span className="text-white">{me.full_name}</span> —{" "}
          <span className="rounded bg-accent-500/15 px-2 py-0.5 text-[11px] text-accent-400">{me.role}</span>
        </div>
      )}

      <div className="rounded-lg border border-navy-700 bg-navy-900 p-4">
        <h2 className="mb-3 text-sm font-semibold text-white">Company profile</h2>
        {profile === null && <p className="text-sm text-white/50">Loading…</p>}
        {profile && (
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              disabled={!isAdmin}
              placeholder="Company name"
              value={profileForm.company_name ?? ""}
              onChange={(e) => setProfileForm({ ...profileForm, company_name: e.target.value })}
              className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30 disabled:opacity-50"
            />
            <input
              disabled={!isAdmin}
              placeholder="Website"
              value={profileForm.website ?? ""}
              onChange={(e) => setProfileForm({ ...profileForm, website: e.target.value })}
              className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30 disabled:opacity-50"
            />
            <textarea
              disabled={!isAdmin}
              placeholder="Description"
              value={profileForm.description ?? ""}
              onChange={(e) => setProfileForm({ ...profileForm, description: e.target.value })}
              rows={3}
              className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30 disabled:opacity-50 sm:col-span-2"
            />
            <textarea
              disabled={!isAdmin}
              placeholder="Outreach messaging notes"
              value={profileForm.outreach_messaging_notes ?? ""}
              onChange={(e) => setProfileForm({ ...profileForm, outreach_messaging_notes: e.target.value })}
              rows={3}
              className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30 disabled:opacity-50 sm:col-span-2"
            />
          </div>
        )}
        {isAdmin && profile && (
          <button
            onClick={saveProfile}
            disabled={saving}
            className="mt-3 rounded-md bg-accent-500 px-4 py-2 text-xs font-medium text-navy-950 hover:bg-accent-400 disabled:opacity-40"
          >
            {saving ? "Saving…" : "Save profile"}
          </button>
        )}
        {!isAdmin && <p className="mt-3 text-xs text-white/40">Only an admin can edit the company profile.</p>}
      </div>

      {isAdmin && (
        <div className="rounded-lg border border-navy-700 bg-navy-900 p-4">
          <h2 className="mb-3 text-sm font-semibold text-white">Team ({users.length})</h2>
          <div className="mb-4 space-y-2">
            {users.map((user) => (
              <div key={user.id} className="flex items-center justify-between text-sm text-white/70">
                <span>
                  {user.full_name} <span className="text-white/40">({user.email})</span>
                </span>
                <span className="rounded bg-white/10 px-2 py-0.5 text-[11px] text-white/60">{user.role}</span>
              </div>
            ))}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <input
              placeholder="Full name"
              value={invite.full_name}
              onChange={(e) => setInvite({ ...invite, full_name: e.target.value })}
              className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30"
            />
            <input
              placeholder="Email"
              value={invite.email}
              onChange={(e) => setInvite({ ...invite, email: e.target.value })}
              className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30"
            />
            <input
              placeholder="Temporary password"
              type="password"
              value={invite.password}
              onChange={(e) => setInvite({ ...invite, password: e.target.value })}
              className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white placeholder:text-white/30"
            />
            <select
              value={invite.role}
              onChange={(e) => setInvite({ ...invite, role: e.target.value })}
              className="rounded-md border border-navy-700 bg-navy-950 px-3 py-2 text-sm text-white"
            >
              <option value="member">Member</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button
            onClick={submitInvite}
            disabled={saving || !invite.email || !invite.full_name || !invite.password}
            className="mt-3 rounded-md border border-navy-700 px-4 py-2 text-xs text-white/80 hover:bg-white/5 disabled:opacity-40"
          >
            Add team member
          </button>
        </div>
      )}

      {isAdmin && (
        <div className="rounded-lg border border-navy-700 bg-navy-900 p-4">
          <h2 className="mb-3 text-sm font-semibold text-white">Audit log</h2>
          {auditLogs.length === 0 && <p className="text-sm text-white/40">No actions logged yet.</p>}
          <div className="space-y-2">
            {auditLogs.map((log) => (
              <div key={log.id} className="flex items-center justify-between border-t border-navy-700 py-2 text-xs text-white/60 first:border-t-0">
                <span>
                  <span className="text-white/80">{log.action}</span> {log.entity_type}
                  {log.entity_id ? ` (${log.entity_id.slice(0, 8)})` : ""}
                </span>
                <span className="text-white/30">{new Date(log.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
