"use client";

import { useState, type FormEvent } from "react";

import { Field, FormError, Modal } from "@/components/ui";
import { ApiError, newIdempotencyKey, post } from "@/lib/api";
import { label } from "@/lib/format";

/** New contact or lead, with an optional company (API-045). The same email returns the existing contact. */
export function ContactForm({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const [f, setF] = useState({ name: "", email: "", phone: "", company: "", domain: "", source: "manual" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key] = useState(newIdempotencyKey);
  const fe = error?.fields ?? {};

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = { name: f.name, source: f.source };
    if (f.email) body.email = f.email;
    if (f.phone) body.phone = f.phone;
    if (f.company) body.company = { name: f.company, ...(f.domain ? { domain: f.domain } : {}) };
    try {
      const c = await post<{ id: string }>("/contacts", body, { idempotencyKey: key });
      onCreated(c.id);
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }

  return (
    <Modal title="New contact or lead" onClose={onClose} footer={<>
      <button className="btn ghost" onClick={onClose}>Cancel</button>
      <button className="btn" form="contact-form" disabled={busy || !f.name}>{busy ? "Saving…" : "Save contact"}</button></>}>
      <form id="contact-form" className="form-grid" onSubmit={submit} noValidate>
        <Field label="Name" error={fe.name} className="full">
          {(id, inv) => <input id={id} className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} aria-invalid={inv} autoFocus />}
        </Field>
        <Field label="Email" error={fe.email}>
          {(id, inv) => <input id={id} className="input" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} aria-invalid={inv} />}
        </Field>
        <Field label="Phone" error={fe.phone}>
          {(id, inv) => <input id={id} className="input" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} aria-invalid={inv} />}
        </Field>
        <Field label="Company" error={fe["company.name"]}>
          {(id, inv) => <input id={id} className="input" value={f.company} onChange={(e) => setF({ ...f, company: e.target.value })} aria-invalid={inv} />}
        </Field>
        <Field label="Company website" error={fe["company.domain"]} hint="e.g. northwind.example">
          {(id, inv) => <input id={id} className="input" value={f.domain} onChange={(e) => setF({ ...f, domain: e.target.value })} aria-invalid={inv} disabled={!f.company} />}
        </Field>
        <Field label="Source" error={fe.source}>
          {(id) => <select id={id} className="select" value={f.source} onChange={(e) => setF({ ...f, source: e.target.value })}>
            {["manual", "referral", "website", "import"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>}
        </Field>
        <div className="full"><FormError error={error && !Object.keys(fe).length ? error : null} /></div>
      </form>
    </Modal>
  );
}
