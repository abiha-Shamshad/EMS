import type { ReactNode } from "react";

import { Logo } from "./icons";

/** Screen 01 layout: brand panel on the left, form on the right (the panel hides on small screens). */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="auth">
      <div className="auth-hero">
        <div className="row gap">
          <Logo size={44} />
          <div>
            <b style={{ fontSize: 26, letterSpacing: "-0.02em" }}>EMS</b>
            <div style={{ color: "#9aa3d6", fontSize: 13 }}>Employee Management System</div>
          </div>
        </div>
        <div className="stack" style={{ marginTop: 48 }}>
          <span className="eyebrow" style={{ color: "#8b93ff" }}>One workspace. Every team.</span>
          <h1>Work better, <em>together.</em></h1>
          <p>Bring your people, projects and leads into one clear view of the work that matters.</p>
          <div className="auth-chips"><span>People &amp; HR</span><span>Projects</span><span>Insights</span></div>
        </div>
      </div>
      <div className="auth-form">
        <div className="inner">{children}</div>
      </div>
    </div>
  );
}

export function AuthHeading({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <div className="stack-sm">
      {eyebrow && <span className="eyebrow">● {eyebrow}</span>}
      <h1 className="h1" style={{ fontSize: 30 }}>{title}</h1>
      {children && <p className="muted">{children}</p>}
    </div>
  );
}
