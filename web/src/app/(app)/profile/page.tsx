"use client";

import Link from "next/link";

import { Avatar, Card, PageHeader } from "@/components/ui";
import { label } from "@/lib/format";
import { useSession } from "@/lib/session";

/** Screen 14 - my profile and account (API-009). */
export default function ProfilePage() {
  const { me, signOut } = useSession();
  return (
    <>
      <PageHeader title="My profile" subtitle="Your account and what your role can do in this company" />
      <div className="grid grid-2">
        <Card title="Account">
          <div className="row gap" style={{ marginBottom: 18 }}>
            <Avatar name={me.user.name} large />
            <div>
              <h2 className="h2">{me.user.name}</h2>
              <p className="muted">{me.user.email}</p>
            </div>
          </div>
          <dl className="kv">
            <dt>Company</dt><dd>{me.active_org.name}</dd>
            <dt>Role</dt><dd>{label(me.active_org.role)}</dd>
            <dt>Time zone</dt><dd>{me.active_org.time_zone}</dd>
            <dt>Home dashboard</dt><dd><Link href={`/dashboards/${me.dashboard}`}>{label(me.dashboard)} dashboard</Link></dd>
          </dl>
        </Card>
        <Card title="Security">
          <div className="stack">
            <p className="muted">
              To change your password, use <Link href="/forgot-password">Forgot password</Link>. While email delivery is not set up for EMS,
              ask your CEO or HR to help you regain access.
            </p>
            <p className="muted">Your title, department and manager are set by HR in <b>Users &amp; roles</b>.</p>
            <div><button className="btn ghost" onClick={() => void signOut()}>Sign out of this browser</button></div>
          </div>
        </Card>
        <Card title="What your role can do" subtitle="From the role permission matrix (Section 7.2)" className="span-2">
          <div className="row gap wrap">
            {me.permissions.map((p) => <span key={p} className="badge primary">{p}</span>)}
          </div>
          <p className="muted small" style={{ marginTop: 12 }}><Link href="/admin/permissions">See every role&apos;s permissions</Link></p>
        </Card>
        <Card title="Monitoring and privacy" className="span-2">
          <p className="muted">
            While you are checked in, EMS records your presence (active, idle, locked), breaks and the task you pick. Leadership may view your shared
            screen, and your webcam if you opted in, live and never recorded; every view is shown to you in <Link href="/room/me">My workday</Link>.
            EMS never collects keystrokes, browsing history, audio or anything while you are checked out or on a break.
          </p>
        </Card>
      </div>
    </>
  );
}
