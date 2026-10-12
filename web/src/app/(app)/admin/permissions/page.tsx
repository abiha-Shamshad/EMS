"use client";

import { Async, Card, PageHeader } from "@/components/ui";
import { label } from "@/lib/format";
import { useApi } from "@/lib/useApi";

type Matrix = { roles: string[]; matrix: Record<string, string[]>; team_scope: Record<string, string[]> };

const MEANING: Record<string, string> = {
  "room.view_live": "Open the live room and view screens", "room.self": "Check in, breaks, own screen views", "hr.manage": "Directory, attendance, reports",
  "leave.decide": "Approve leave and breaks", "projects.manage": "Create and manage all projects", "crm.manage": "Contacts, deals, Win",
  "finance.manage": "Invoices, payments, cost rates", "hunter.use": "Lead Hunter", "rules.manage": "Automation rules", "members.manage": "Invite, roles, company settings",
  "leakage.read": "See leakage findings", "leakage.resolve": "Resolve leakage findings", "dashboards.all": "Read every role's dashboard data (API)",
};

/** Screen 48 - role permission matrix (API-016). Release 1 has seven fixed roles; custom roles are Release 2. */
export default function PermissionsPage() {
  const m = useApi<Matrix>("/roles/permissions");
  return (
    <>
      <PageHeader title="Role permissions" subtitle="What each of the seven roles can do. “Team” means the manager's direct reports only." />
      <Card flush>
        <Async state={m}>
          {(d) => (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Permission</th>{d.roles.map((r) => <th key={r} style={{ textAlign: "center" }}>{label(r)}</th>)}</tr></thead>
              <tbody>{Object.entries(d.matrix).map(([perm, roles]) => (
                <tr key={perm}>
                  <td><b className="mono">{perm}</b><div className="muted small">{MEANING[perm] ?? ""}</div></td>
                  {d.roles.map((r) => (
                    <td key={r} style={{ textAlign: "center" }}>
                      {roles.includes(r) ? (d.team_scope[perm]?.includes(r) ? <span className="badge warning">Team</span> : <span className="badge success">✓</span>) : <span className="muted">—</span>}
                    </td>
                  ))}
                </tr>
              ))}</tbody>
            </table></div>
          )}
        </Async>
      </Card>
    </>
  );
}
