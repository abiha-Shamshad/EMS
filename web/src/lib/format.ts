// Display helpers. Money arrives as decimal strings (DEC-011) and is never parsed into floats for arithmetic;
// timestamps arrive in UTC and are shown in the company time zone (Section 10).

export function money(value: string | null | undefined, currency = "USD"): string {
  if (value === null || value === undefined || value === "") return "—";
  const [int = "0", frac = "00"] = value.replace("-", "").split(".");
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const sign = value.startsWith("-") ? "-" : "";
  const symbol = currency === "USD" ? "$" : `${currency} `;
  return `${sign}${symbol}${grouped}.${frac.padEnd(2, "0").slice(0, 2)}`;
}

/** Exact sum of decimal-string amounts (integer cents, never floats). */
export function sumMoney(values: (string | null | undefined)[]): string {
  let cents = BigInt(0);
  for (const v of values) {
    if (!v) continue;
    const neg = v.startsWith("-");
    const [int = "0", frac = ""] = v.replace("-", "").split(".");
    const c = BigInt(int) * BigInt(100) + BigInt((frac + "00").slice(0, 2));
    cents += neg ? -c : c;
  }
  const neg = cents < BigInt(0);
  const abs = neg ? -cents : cents;
  return `${neg ? "-" : ""}${abs / BigInt(100)}.${(abs % BigInt(100)).toString().padStart(2, "0")}`;
}

export function dateTime(iso: string | null | undefined, timeZone?: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone }).format(new Date(iso));
}

export function date(value: string | null | undefined, timeZone?: string): string {
  if (!value) return "—";
  // A plain YYYY-MM-DD is a calendar date: format it without shifting time zones.
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [y, m, d] = value.split("-").map(Number) as [number, number, number];
    return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" }).format(new Date(Date.UTC(y, m - 1, d)));
  }
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone }).format(new Date(value));
}

export function time(iso: string | null | undefined, timeZone?: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-GB", { timeStyle: "short", timeZone }).format(new Date(iso));
}

export function relative(iso: string | null | undefined, now: number = Date.now()): string {
  if (!iso) return "—";
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000);
  const abs = Math.abs(seconds);
  const units: [number, Intl.RelativeTimeFormatUnit][] = [[60, "second"], [3600, "minute"], [86400, "hour"], [604800, "day"], [2629800, "week"]];
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  let prev = 1;
  for (const [limit, unit] of units) {
    if (abs < limit) return rtf.format(Math.round(seconds / prev), unit);
    prev = limit;
  }
  return rtf.format(Math.round(seconds / 2629800), "month");
}

export function minutes(total: number | null | undefined): string {
  if (total === null || total === undefined) return "—";
  const h = Math.floor(total / 60);
  const m = total % 60;
  return h ? `${h} h ${m.toString().padStart(2, "0")} min` : `${m} min`;
}

export function label(value: string | null | undefined): string {
  if (!value) return "—";
  const special: Record<string, string> = { ceo: "CEO", cto: "CTO", cfo: "CFO", coo: "COO", hr: "HR" };
  return special[value] ?? value.replace(/[_.]/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function initials(name: string | null | undefined): string {
  if (!name) return "?";
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join("");
}

export function percent(ratio: string | number | null | undefined): string {
  if (ratio === null || ratio === undefined || ratio === "") return "—";
  return `${Math.round(Number(ratio) * 100)}%`;
}

/** Today's date (YYYY-MM-DD) in a time zone. */
export function today(timeZone?: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
}
