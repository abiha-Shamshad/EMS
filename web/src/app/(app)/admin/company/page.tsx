"use client";

import { CompanySettingsForm, type Org } from "@/components/forms/CompanySettingsForm";
import { Async, Card, NoAccess, PageHeader, useToast } from "@/components/ui";
import { label } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

/** Company settings (API-010) and the read-only facts other screens depend on. */
export default function CompanySettingsPage() {
  const toast = useToast();
  const { can } = useSession();
  const org = useApi<Org>("/org");
  if (!can("members.manage")) return <NoAccess message="Only the CEO and HR can change company settings." />;
  return (
    <>
      <PageHeader title="Company settings" subtitle="Working hours drive lateness, attendance, auto check-out and break allowances." />
      <Async state={org}>
        {(o) => (
          <div className="grid grid-3">
            <Card title="Details and working hours" className="span-2">
              <CompanySettingsForm key={o.version} org={o} submitLabel="Save settings" onSaved={() => { toast("Settings saved"); org.reload(); }} />
            </Card>
            <Card title="Company">
              <dl className="kv" style={{ gridTemplateColumns: "130px 1fr" }}>
                <dt>Address</dt><dd className="mono">{o.slug}</dd>
                <dt>Country</dt><dd>{o.country}</dd>
                <dt>Currency</dt><dd>{o.base_currency}</dd>
                <dt>Setup</dt><dd>{label(o.setup_state)}</dd>
                <dt>Break allowance</dt><dd>{o.daily_break_allowance_minutes} min / day</dd>
                <dt>Monitoring notice</dt><dd>Version {o.room_policy_version}</dd>
                <dt>Live screen view</dt><dd>{o.live_view_enabled ? "On" : "Off (pending legal review, OD-02)"}</dd>
              </dl>
              <p className="muted small" style={{ marginTop: 12 }}>Break allowance and grace can also be changed by publishing an attendance policy in Policies &amp; rules.</p>
            </Card>
          </div>
        )}
      </Async>
    </>
  );
}
