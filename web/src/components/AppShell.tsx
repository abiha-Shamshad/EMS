"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { get } from "@/lib/api";
import { label } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Permission } from "@/lib/types";
import { usePoll } from "@/lib/useApi";

import { Icon, Logo, type IconName } from "./icons";
import { Avatar } from "./ui";

type NavItem = { href: string; label: string; icon: IconName; show: (can: (p: Permission) => boolean, role: string) => boolean };

const WORKSPACE: NavItem[] = [
  { href: "/dashboards", label: "Dashboard", icon: "dashboard", show: () => true },
  { href: "/room", label: "Live room", icon: "room", show: (can) => can("room.view_live") },
  { href: "/room/me", label: "My workday", icon: "clock", show: (can) => can("room.self") },
  { href: "/hr", label: "People & HR", icon: "people", show: (can) => can("hr.manage") },
  { href: "/leave", label: "Leave", icon: "leave", show: () => true },
  { href: "/hr/agent", label: "HR Agent", icon: "agent", show: () => true },
  { href: "/projects", label: "Projects", icon: "projects", show: () => true },
  { href: "/crm", label: "CRM", icon: "crm", show: (can, role) => can("crm.manage") || role === "cfo" },
  { href: "/hunter", label: "Lead Hunter", icon: "hunter", show: (can) => can("hunter.use") },
  { href: "/automation", label: "Automations", icon: "automation", show: (can) => can("rules.manage") },
  { href: "/leakage", label: "Revenue leakage", icon: "leakage", show: (can) => can("leakage.read") },
  { href: "/finance/invoices", label: "Invoices", icon: "finance", show: (can) => can("finance.manage") },
];
const ADMIN: NavItem[] = [
  { href: "/admin/members", label: "Users & roles", icon: "people", show: (can) => can("members.manage") },
  { href: "/admin/permissions", label: "Role permissions", icon: "shield", show: () => true },
  { href: "/admin/company", label: "Company settings", icon: "admin", show: (can) => can("members.manage") },
];
const ALL = [...WORKSPACE, ...ADMIN, { href: "/notifications", label: "Notifications", icon: "bell" as IconName, show: () => true },
  { href: "/profile", label: "My profile", icon: "people" as IconName, show: () => true }];

/** The longest nav prefix of the current path is "active", so /room/me does not also light up /room. */
function activeHref(pathname: string): string | undefined {
  return ALL.map((i) => i.href).filter((h) => pathname === h || pathname.startsWith(`${h}/`)).sort((a, b) => b.length - a.length)[0];
}

export function AppShell({ children }: { children: ReactNode }) {
  const { me, can, signOut } = useSession();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [unread, setUnread] = useState(0);
  const active = activeHref(pathname);
  const current = ALL.find((i) => i.href === active);

  const loadUnread = useCallback(() => {
    get<{ unread: number }>("/notifications", { limit: 1 }).then((d) => setUnread(d.unread)).catch(() => undefined);
  }, []);
  useEffect(loadUnread, [loadUnread, pathname]);
  usePoll(loadUnread, 30_000);

  const link = (i: NavItem) => {
    const href = i.href === "/dashboards" ? `/dashboards/${me.dashboard}` : i.href;
    return (
      <Link key={i.href} href={href} className={`nav-link ${active === i.href ? "active" : ""}`} onClick={() => setOpen(false)}>
        <Icon name={i.icon} />
        {i.label}
      </Link>
    );
  };
  const admin = ADMIN.filter((i) => i.show(can, me.active_org.role));

  return (
    <div className="shell">
      <aside className={`sidebar ${open ? "open" : ""}`} aria-label="Main navigation">
        <div className="brand">
          <Logo />
          <div><b>EMS</b><small>{me.active_org.name}</small></div>
        </div>
        <div className="nav-section">Workspace</div>
        {WORKSPACE.filter((i) => i.show(can, me.active_org.role)).map(link)}
        {admin.length > 0 && <div className="nav-section">Administration</div>}
        {admin.map(link)}
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="row gap">
            <button className="icon-btn menu-toggle" onClick={() => setOpen((o) => !o)} aria-label="Open menu"><Icon name="menu" /></button>
            <div className="crumbs">
              <span>{me.active_org.name}</span>
              <span>/</span>
              <b>{current?.label ?? "EMS"}</b>
            </div>
          </div>
          <div className="row gap" style={{ position: "relative" }}>
            <Link className="icon-btn" href="/notifications" aria-label={`Notifications, ${unread} unread`}>
              <Icon name="bell" />
              {unread > 0 && <span className="count">{unread > 99 ? "99+" : unread}</span>}
            </Link>
            <button className="user-chip" onClick={() => setMenu((m) => !m)} aria-expanded={menu} aria-haspopup="menu">
              <Avatar name={me.user.name} />
              <span style={{ textAlign: "left" }}>
                <b style={{ display: "block", fontSize: 13.5 }}>{me.user.name}</b>
                <span className="muted small">{label(me.active_org.role)}</span>
              </span>
              <Icon name="chevron" size={16} />
            </button>
            {menu && (
              <div className="menu" role="menu" onMouseLeave={() => setMenu(false)}>
                <Link href="/profile" role="menuitem" onClick={() => setMenu(false)}>My profile</Link>
                <Link href="/select-company" role="menuitem" onClick={() => setMenu(false)}>Switch company</Link>
                <button role="menuitem" onClick={() => void signOut()}>Sign out</button>
              </div>
            )}
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
