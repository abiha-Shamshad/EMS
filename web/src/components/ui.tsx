"use client";

import Link from "next/link";
import { createContext, useCallback, useContext, useEffect, useId, useState, type ReactNode } from "react";

import { ApiError } from "@/lib/api";
import { label } from "@/lib/format";

import { Icon } from "./icons";

// ------------------------------------------------------------------------------------------------ page structure
export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1 className="h1">{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="row gap wrap">{actions}</div>}
    </div>
  );
}

export function Card({ title, subtitle, actions, children, flush, className = "" }: {
  title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; flush?: boolean; className?: string;
}) {
  return (
    <section className={`card ${flush ? "flush" : ""} ${className}`}>
      {(title || actions) && (
        <div className="card-head">
          <div>
            {title && <h2 className="h3">{title}</h2>}
            {subtitle && <p className="muted small">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

// ------------------------------------------------------------------------------------------------ states
export function Loading({ label: text = "Loading" }: { label?: string }) {
  return <div className="loading-row" role="status"><div className="spinner" aria-label={text} /></div>;
}

export function Empty({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <h3 className="h3">{title}</h3>
      {children && <p>{children}</p>}
      {action && <div style={{ marginTop: 14 }}>{action}</div>}
    </div>
  );
}

/** Error block. Permission errors explain themselves; anything retryable gets a retry button. */
export function ErrorState({ error, retry }: { error: ApiError | Error; retry?: () => void }) {
  const api = error instanceof ApiError ? error : null;
  if (api?.code === "AUTHORIZATION_DENIED") return <NoAccess message={api.message} />;
  return (
    <div className="alert error row between gap" role="alert">
      <span>{error.message}</span>
      {retry && (!api || api.retryable || api.status === 0) && <button className="btn sm ghost" onClick={retry}>Try again</button>}
    </div>
  );
}

/** Screen 49 (no access). */
export function NoAccess({ message }: { message?: string }) {
  return (
    <div className="card" style={{ textAlign: "center", padding: 48 }}>
      <div className="icon-tile" style={{ margin: "0 auto 14px" }}><Icon name="lock" /></div>
      <h2 className="h2">You don&apos;t have access to this page</h2>
      <p className="muted" style={{ marginTop: 6 }}>{message ?? "Your role does not include this area. Ask your company admin if you need it."}</p>
      <div style={{ marginTop: 18 }}><Link className="btn ghost" href="/">Back to my dashboard</Link></div>
    </div>
  );
}

/** Wraps the common load / error / content sequence. */
export function Async<T>({ state, children, empty }: {
  state: { data: T | undefined; error: ApiError | undefined; loading: boolean; reload: () => void };
  children: (data: T) => ReactNode;
  empty?: (data: T) => ReactNode | null;
}) {
  if (state.error && !state.data) return <ErrorState error={state.error} retry={state.reload} />;
  if (state.data === undefined) return <Loading />;
  const e = empty?.(state.data);
  return <>{e ?? children(state.data)}</>;
}

// ------------------------------------------------------------------------------------------------ badges
const TONE: Record<string, string> = {
  active: "success", present: "success", paid: "success", won: "success", completed: "success", approved: "success", matched: "success",
  resolved: "success", checked_in: "success", invited: "success", live: "success", customer: "success",
  idle: "warning", locked: "warning", pending: "warning", requested: "warning", partially_paid: "warning", review: "warning",
  queued: "warning", running: "warning", onboarding: "warning", late: "warning", not_checked_in: "warning", proposal: "warning",
  negotiation: "warning", planned: "primary", opportunity: "primary", qualified: "primary", sent: "primary", todo: "primary",
  on_break: "info", on_leave: "info", paused: "info", lead: "info", new: "info",
  offline: "", rejected: "danger", lost: "danger", failed: "danger", action_failed: "danger", absent_unexplained: "danger",
  at_risk: "danger", deactivated: "danger", overdue: "danger", dismissed: "", cancelled: "", churned: "danger", suppressed: "danger",
};

export function StatusBadge({ value, text }: { value: string | null | undefined; text?: string }) {
  if (!value) return <span className="muted">—</span>;
  return <span className={`badge ${TONE[value] ?? ""}`}>{text ?? label(value)}</span>;
}

// ------------------------------------------------------------------------------------------------ form fields
export function Field({ label: text, error, hint, children, className = "" }: {
  label: string; error?: string; hint?: ReactNode; children: (id: string, invalid: boolean) => ReactNode; className?: string;
}) {
  const id = useId();
  return (
    <label className={`field ${className}`} htmlFor={id}>
      <span>{text}</span>
      {children(id, Boolean(error))}
      {error ? <span className="err">{error}</span> : hint ? <small>{hint}</small> : null}
    </label>
  );
}

export function FormError({ error }: { error: ApiError | null | undefined }) {
  if (!error) return null;
  return <div className="alert error" role="alert">{error.message}</div>;
}

// ------------------------------------------------------------------------------------------------ modal + confirm (screen 50)
export function Modal({ title, subtitle, onClose, children, footer, wide }: {
  title: string; subtitle?: ReactNode; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <div>
            <h2 className="h2">{title}</h2>
            {subtitle && <p className="muted" style={{ marginTop: 4 }}>{subtitle}</p>}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="close" /></button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmDialog({ title, message, confirmLabel = "Confirm", danger, busy, error, onConfirm, onCancel, children }: {
  title: string; message: ReactNode; confirmLabel?: string; danger?: boolean; busy?: boolean; error?: ApiError | null;
  onConfirm: () => void; onCancel: () => void; children?: ReactNode;
}) {
  return (
    <Modal title={title} onClose={onCancel} footer={
      <>
        <button className="btn ghost" onClick={onCancel} disabled={busy}>Cancel</button>
        <button className={`btn ${danger ? "danger" : ""}`} onClick={onConfirm} disabled={busy}>{busy ? "Working…" : confirmLabel}</button>
      </>
    }>
      <p>{message}</p>
      {children}
      <FormError error={error} />
    </Modal>
  );
}

// ------------------------------------------------------------------------------------------------ toasts
type Toast = { id: number; text: string; kind: "ok" | "error" };
const ToastContext = createContext<(text: string, kind?: Toast["kind"]) => void>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, kind: Toast["kind"] = "ok") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text, kind }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => <div key={t.id} className={`toast ${t.kind === "error" ? "error" : ""}`}>{t.text}</div>)}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);

// ------------------------------------------------------------------------------------------------ small pieces
export function Avatar({ name, large }: { name: string; large?: boolean }) {
  const parts = name.split(/\s+/).filter(Boolean);
  const text = parts.slice(0, 2).map((p) => p[0]!.toUpperCase()).join("") || "?";
  return <span className={`avatar ${large ? "lg" : ""}`} aria-hidden="true">{text}</span>;
}

export function Progress({ ratio }: { ratio: number | null }) {
  if (ratio === null || Number.isNaN(ratio)) return <span className="muted small">No budget</span>;
  const pct = Math.min(100, Math.round(ratio * 100));
  return <div className={`progress ${ratio >= 1 ? "over" : ratio >= 0.9 ? "warn" : ""}`}><span style={{ width: `${pct}%` }} /></div>;
}

export function Tabs<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="tabs" role="tablist">
      {options.map((o) => (
        <button key={o.value} role="tab" aria-selected={o.value === value} className={`tab ${o.value === value ? "active" : ""}`}
          onClick={() => onChange(o.value)}>{o.label}</button>
      ))}
    </div>
  );
}

export function LoadMore({ cursor, onMore, busy }: { cursor: string | null | undefined; onMore: () => void; busy?: boolean }) {
  if (!cursor) return null;
  return <div className="row end" style={{ padding: 12 }}><button className="btn ghost sm" onClick={onMore} disabled={busy}>Load more</button></div>;
}
