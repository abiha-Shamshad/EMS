"use client";

import type { ReactNode } from "react";

import { Logo } from "@/components/icons";
import { SessionProvider } from "@/lib/session";

/** Onboarding steps 2-3 (screens 05, 06): signed in, no sidebar yet. */
export default function SetupLayout({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <div style={{ minHeight: "100vh", padding: "32px 20px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto" }} className="stack">
          <div className="row gap"><Logo /><b style={{ fontSize: 20 }}>EMS</b></div>
          {children}
        </div>
      </div>
    </SessionProvider>
  );
}
