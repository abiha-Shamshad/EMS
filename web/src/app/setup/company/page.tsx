"use client";

import { useRouter } from "next/navigation";

import { CompanySettingsForm, type Org } from "@/components/forms/CompanySettingsForm";
import { Steps } from "@/components/Steps";
import { Async, Card, NoAccess } from "@/components/ui";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

/** Screen 05 - company setup (API-010). */
export default function CompanySetupPage() {
  const router = useRouter();
  const { can, me } = useSession();
  const org = useApi<Org>("/org");
  if (!can("members.manage")) return <NoAccess message="Only the CEO and HR complete company setup." />;
  return (
    <>
      <Steps current={2} />
      <Card title="Set up your company" subtitle="Working hours decide lateness, attendance and break allowances. You can change them later.">
        <Async state={org}>
          {(o) => (
            <CompanySettingsForm org={o} submitLabel="Save and continue" onSaved={() => router.push("/setup/invite")}
              onSkip={() => router.push(`/dashboards/${me.dashboard}`)} />
          )}
        </Async>
      </Card>
    </>
  );
}
