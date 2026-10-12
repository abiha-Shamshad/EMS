"use client";

import { useState, type FormEvent } from "react";

import { Card, PageHeader } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { label } from "@/lib/format";

type Answer = { intent: string; answered: boolean; text: string; data: unknown[]; sources: string[] };
type Turn = { q: string; a?: Answer; error?: string };

const SUGGESTIONS = ["Who is on leave today?", "Which leave requests are pending?", "Who came late today?", "Who is online now?",
  "Work summary for me today", "What is the leave policy?"];

/** Screen 30 - HR Agent query and work summary (API-035). Rule-based: answers come from EMS records, with sources; nothing is guessed. */
export default function HrAgentPage() {
  const [q, setQ] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);

  async function ask(question: string) {
    if (question.trim().length < 3) return;
    setBusy(true);
    setQ("");
    setTurns((t) => [...t, { q: question }]);
    try {
      const a = await post<Answer>("/hr-agent/ask", { question });
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, a } : x)));
    } catch (e) {
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, error: (e as ApiError).message } : x)));
    } finally {
      setBusy(false);
    }
  }
  const submit = (e: FormEvent) => { e.preventDefault(); void ask(q); };

  return (
    <>
      <PageHeader title="HR Agent" subtitle="Answers come from EMS records and list their sources. No AI model; only the question type is logged, never your words." />
      <Card>
        <div className="chat" style={{ minHeight: 280 }}>
          {turns.length === 0 && <p className="muted">Ask about leave, lateness, who is online, someone&apos;s work summary or a company policy.</p>}
          {turns.map((t, i) => (
            <div key={i} className="stack-sm">
              <div className="bubble me">{t.q}</div>
              {t.error && <div className="alert error">{t.error}</div>}
              {t.a && (
                <div className="bubble">
                  <div className="row gap-sm" style={{ marginBottom: 6 }}>
                    <span className={`badge ${t.a.answered ? "success" : "warning"}`}>{t.a.answered ? label(t.a.intent) : "Not answered"}</span>
                  </div>
                  <div style={{ whiteSpace: "pre-wrap" }}>{t.a.text}</div>
                  {t.a.sources.length > 0 && <div className="muted small" style={{ marginTop: 6 }}>Sources: {t.a.sources.map((s) => s.length > 20 ? s.slice(0, 8) : s).join(", ")}</div>}
                </div>
              )}
              {!t.a && !t.error && <div className="bubble muted">Looking it up…</div>}
            </div>
          ))}
        </div>
        <form onSubmit={submit} className="row gap" style={{ marginTop: 16 }}>
          <input className="input grow" maxLength={300} placeholder="Ask a question…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Question" />
          <button className="btn" disabled={busy || q.trim().length < 3}>Ask</button>
        </form>
        <div className="row gap wrap" style={{ marginTop: 12 }}>
          {SUGGESTIONS.map((s) => <button key={s} className="btn sm ghost" disabled={busy} onClick={() => void ask(s)}>{s}</button>)}
        </div>
      </Card>
    </>
  );
}
