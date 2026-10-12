"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Card, Field, FormError, NoAccess, PageHeader } from "@/components/ui";
import { ApiError, newIdempotencyKey, post } from "@/lib/api";
import { useSession } from "@/lib/session";

const split = (s: string) => s.split(/[\s,;]+/).map((x) => x.trim()).filter(Boolean);

/** Screen 41 - search and filters: the seed websites and the ideal-customer profile for a hunt (API-055). */
export default function NewHuntPage() {
  const router = useRouter();
  const { can } = useSession();
  const [f, setF] = useState({ name: "", domains: "", keywords: "", countries: "", tech: "", min_team_size: "", pages: "5" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key] = useState(newIdempotencyKey);
  if (!can("hunter.use")) return <NoAccess message="Only leadership and managers can use the Lead Hunter." />;
  const domains = split(f.domains);
  const fe = error?.fields ?? {};

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const icp: Record<string, unknown> = { industry_keywords: f.keywords.split(",").map((x) => x.trim()).filter(Boolean),
        countries: split(f.countries).map((c) => c.toUpperCase()), tech: split(f.tech).map((t) => t.toLowerCase()) };
      if (f.min_team_size) icp.min_team_size = Number(f.min_team_size);
      const res = await post<{ hunt_id: string }>("/hunts", { name: f.name, seeds: { domains }, icp, max_pages_per_domain: Number(f.pages) }, { idempotencyKey: key });
      router.push(`/hunter/${res.hunt_id}`);
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="New hunt" subtitle="Only websites you supply are crawled. Social networks and search engines are never crawled." />
      <Card>
        <form className="form-grid" onSubmit={submit} noValidate>
          <Field label="Hunt name" error={fe.name} className="full">{(id, inv) => <input id={id} className="input" maxLength={120} value={f.name}
            onChange={(e) => setF({ ...f, name: e.target.value })} aria-invalid={inv} placeholder="e.g. Lahore marketing agencies" />}</Field>
          <Field label={`Company websites (${domains.length}/200)`} error={fe["seeds.domains"]} hint="One per line, or separated by commas. e.g. brightpixel.example" className="full">
            {(id, inv) => <textarea id={id} className="textarea" style={{ minHeight: 140 }} value={f.domains} onChange={(e) => setF({ ...f, domains: e.target.value })} aria-invalid={inv} />}</Field>
          <Field label="Industry keywords" error={fe["icp.industry_keywords"]} hint="Comma separated, e.g. marketing agency, digital agency" className="full">
            {(id, inv) => <input id={id} className="input" value={f.keywords} onChange={(e) => setF({ ...f, keywords: e.target.value })} aria-invalid={inv} />}</Field>
          <Field label="Countries" error={fe["icp.countries"]} hint="2-letter codes, e.g. PK, AE">
            {(id, inv) => <input id={id} className="input" value={f.countries} onChange={(e) => setF({ ...f, countries: e.target.value })} aria-invalid={inv} />}</Field>
          <Field label="Technologies" error={fe["icp.tech"]} hint="e.g. wordpress, shopify">
            {(id, inv) => <input id={id} className="input" value={f.tech} onChange={(e) => setF({ ...f, tech: e.target.value })} aria-invalid={inv} />}</Field>
          <Field label="Minimum team size" error={fe["icp.min_team_size"]}>
            {(id, inv) => <input id={id} className="input" type="number" min={1} value={f.min_team_size} onChange={(e) => setF({ ...f, min_team_size: e.target.value })} aria-invalid={inv} />}</Field>
          <Field label="Pages per site" error={fe.max_pages_per_domain} hint="Home, about, services, contact, careers">
            {(id) => <select id={id} className="select" value={f.pages} onChange={(e) => setF({ ...f, pages: e.target.value })}>
              {[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select>}</Field>
          <div className="full stack-sm">
            <p className="muted small">Each site&apos;s robots.txt is read first and obeyed; one request every 5 seconds per site; only company name, role addresses
              (info@, sales@, contact@, hello@), technology tags and a score are kept. No personal names, emails or phone numbers.</p>
            <FormError error={error && !Object.keys(fe).length ? error : null} />
            <div className="row end"><button className="btn" disabled={busy || !f.name || domains.length === 0 || domains.length > 200}>{busy ? "Starting…" : "Start hunt"}</button></div>
          </div>
        </form>
      </Card>
    </>
  );
}
