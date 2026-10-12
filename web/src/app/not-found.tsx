import Link from "next/link";

/** Screen 49 (404). */
export default function NotFound() {
  return (
    <div className="notfound">
      <div className="stack" style={{ alignItems: "center" }}>
        <div className="code-big">404</div>
        <h1 className="h2">This page doesn&apos;t exist</h1>
        <p className="muted">The link may be old, or the record was removed. Records in another company also show as not found.</p>
        <Link className="btn" href="/">Go to my dashboard</Link>
      </div>
    </div>
  );
}
