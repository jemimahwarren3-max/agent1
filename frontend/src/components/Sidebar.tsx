"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  Search,
  Database,
  Microscope,
  Mail,
  Megaphone,
  CheckSquare,
  Inbox,
  BarChart3,
  Link2,
  Settings,
} from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/agent", label: "AI Agent", icon: Bot },
  { href: "/discover", label: "Discover Leads", icon: Search },
  { href: "/leads", label: "Lead Database", icon: Database },
  { href: "/research", label: "Research Centre", icon: Microscope },
  { href: "/templates", label: "Email Templates", icon: Mail },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/approvals", label: "Approval Queue", icon: CheckSquare },
  { href: "/inbox", label: "Inbox and Replies", icon: Inbox },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/integrations", label: "Google Integrations", icon: Link2 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-navy-700 bg-navy-900 px-3 py-6">
      <div className="mb-8 px-3">
        <p className="text-sm font-semibold tracking-wide text-white">Haki Systems</p>
        <p className="text-xs text-white/50">AI Prospecting Platform</p>
      </div>
      <nav className="flex-1 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-accent-500/15 text-accent-400"
                  : "text-white/70 hover:bg-white/5 hover:text-white"
              )}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
