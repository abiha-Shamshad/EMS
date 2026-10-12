"use client";

import { useRouter } from "next/navigation";

import { InviteForm } from "@/components/forms/InviteForm";
import { Steps } from "@/components/Steps";
import { Card, NoAccess } from "@/components/ui";
import { get, patch } from "@/lib/api";
import { useSession } from "@/lib/session";

/** Screen 06 - invite the team (API-011). "Skip for now" marks setup active (API-010 setup_state). */
export default function InviteTeamPage() {
  const router = useRouter();
  const { can, me } = useSession();
  if (!can("members.manage")) return <NoAccess message="Only the CEO and HR can invite people." />;

  async function skip() {
    try {
      const org = await get<{ version: number }>("/org");
      await patch("/org", { expected_version: org.version, setup_state: "active" });
    } finally {
      router.push(`/dashboards/${me.dashboard}`);
    }
  }

  return (
    <>
      <Steps current={3} />
      <Card title="Invite your team" subtitle="Add teammates by email and pick their role. You can invite more people any time from Users & roles."
        actions={<button className="btn ghost sm" onClick={() => void skip()}>Skip for now</button>}>
        <InviteForm isCeo={me.active_org.role === "ceo"} />
      </Card>
      <div className="row end"><button className="btn" onClick={() => router.push(`/dashboards/${me.dashboard}`)}>Continue to dashboard</button></div>
    </>
  );
}
