"""Lead Hunter crawler (spec Section 14, DEC-010, TASK-012). Runs in the worker, never in the API.

Per domain: suppression check, then `/robots.txt` (4xx -> allowed, 5xx or network error -> do not crawl, at most
500 KiB, longest match wins - engine/robots.py), then at most 5 pages (home, about, services, contact, careers).
1 request per 5 seconds per domain, 10-second timeout, HTML only, 2 MB per page. Domains are crawled round-robin, so a
hunt takes about (pages + 1) x 5 seconds plus fetch time instead of that per domain.

Only company name, public role addresses (info@, sales@, contact@, hello@ on the site's own domain), technology tags,
a country hint, a team-size hint, the source URL and the score are kept. Page text is used for scoring and discarded;
personal names, personal emails and phone numbers are never stored. Every fetch decision is written to crawl_log.
"""
import logging
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.crm import suppression
from app.engine import robots, scoring
from app.platform import events
from app.platform.db import Db, jsonb

log = logging.getLogger("ems.hunter")

ROBOTS_AGENT = "EMS-LeadHunter"
PAGES = ["/", "/about", "/services", "/contact", "/careers"]
REQUEST_GAP_SECONDS, TIMEOUT_SECONDS, MAX_PAGE_BYTES = 5.0, 10.0, 2_000_000
ROLE_LOCALS = {"info", "sales", "contact", "hello"}
BLOCKED_DOMAINS = ("linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "bing.com")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}")
_TEAM = re.compile(r"\b(\d{1,5})\s*\+?\s*(?:employees|people|team members|staff|experts|professionals|specialists)\b", re.I)
TECH_SIGNATURES = {
    "wordpress": ("wp-content", "wp-includes"), "shopify": ("cdn.shopify.com", "shopify.theme"), "wix": ("wixstatic.com", "wix.com"),
    "squarespace": ("squarespace.com",), "webflow": ("webflow.com", "data-wf-site"), "next.js": ("/_next/",),
    "react": ("data-reactroot", "react-dom"), "hubspot": ("js.hs-scripts.com", "hubspot"), "google analytics": ("gtag(", "google-analytics.com"),
    "magento": ("mage/cookies", "magento"), "drupal": ("drupal.settings", "/sites/default/files"), "angular": ("ng-version",),
}
TECH_LABELS = {"wordpress": "WordPress", "shopify": "Shopify", "wix": "Wix", "squarespace": "Squarespace", "webflow": "Webflow",
               "next.js": "Next.js", "react": "React", "hubspot": "HubSpot", "google analytics": "Google Analytics",
               "magento": "Magento", "drupal": "Drupal", "angular": "Angular"}
GENERIC_TLDS = {"com", "org", "net", "io", "co", "ai", "app", "dev", "me", "tv", "ly", "biz", "info", "example", "test", "local"}
COUNTRY_NAMES = {
    "PK": "pakistan", "IN": "india", "AE": "united arab emirates", "SA": "saudi arabia", "GB": "united kingdom", "US": "united states",
    "CA": "canada", "AU": "australia", "DE": "germany", "FR": "france", "NL": "netherlands", "SG": "singapore", "MY": "malaysia",
    "TR": "turkey", "QA": "qatar", "BD": "bangladesh", "EG": "egypt", "NG": "nigeria", "KE": "kenya", "ZA": "south africa",
}


def blocked(domain: str) -> bool:
    """Social networks and search engines are never crawled (Section 14.1 rule 1)."""
    d = domain.lower()
    return any(d == b or d.endswith("." + b) for b in BLOCKED_DOMAINS) or ".google." in f".{d}"     # google.com, google.com.pk, www.google.de


@dataclass
class Page:
    status: int | None                 # None: network error or timeout
    html: str | None = None            # only for 2xx text/html within the size cap


Fetch = Callable[[str], Page]


def http_fetch(user_agent: str) -> Fetch:
    """Real fetcher: 10 s timeout, at most 3 redirects, HTML only (and robots.txt), 2 MB cap (the body is streamed and cut)."""
    def fetch(url: str) -> Page:
        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True, max_redirects=3,
                              headers={"User-Agent": user_agent, "Accept": "text/html,text/plain"}) as client, \
                    client.stream("GET", url) as r:
                ctype = r.headers.get("content-type", "").lower()
                wanted = url.endswith("/robots.txt") or "text/html" in ctype
                if not (200 <= r.status_code < 300) or not wanted:
                    return Page(r.status_code)
                body = bytearray()
                for chunk in r.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_PAGE_BYTES:
                        return Page(r.status_code)            # over the cap: not parsed
                return Page(r.status_code, body.decode(r.encoding or "utf-8", errors="replace"))
        except httpx.HTTPError:
            return Page(None)
    return fetch


@dataclass
class DomainCrawl:
    domain: str
    scheme: str = "https"
    groups: list | None = None         # parsed robots.txt; None until fetched
    stop: bool = False
    pages: list[str] = field(default_factory=list)
    fetched: list[tuple[str, str]] = field(default_factory=list)     # (url, html)
    last_request: float = 0.0

    @property
    def pending(self) -> bool:
        """robots.txt still to fetch, or pages left to fetch."""
        return not self.stop and (self.groups is None or bool(self.pages))


def extract(domain: str, fetched: list[tuple[str, str]]) -> dict[str, Any]:
    """Signals from the fetched pages. Returns what is stored plus `text` (for scoring only, never stored)."""
    texts, tech, emails, team, name = [], set(), set(), 0, None
    has_contact = False
    for url, html in fetched:
        soup = BeautifulSoup(html, "html.parser")
        lowered = html.lower()
        tech |= {t for t, sigs in TECH_SIGNATURES.items() if any(s in lowered for s in sigs)}
        if name is None:
            og = soup.find("meta", attrs={"property": "og:site_name"})
            title = og.get("content") if og and og.get("content") else (soup.title.string if soup.title and soup.title.string else None)
            if title:
                name = re.split(r"\s+[|\-–—:]\s+", title.strip())[0].strip()[:120] or None
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        texts.append(text)
        if url.rstrip("/").endswith("/contact") or soup.find("a", href=re.compile(r"contact", re.I)):
            has_contact = True
        for e in _EMAIL.findall(html):
            local, _, host = e.lower().partition("@")
            if local in ROLE_LOCALS and (host == domain or host.endswith("." + domain)):
                emails.add(f"{local}@{host}")
        team = max([team, *(int(n) for n in _TEAM.findall(text))])
    joined = " ".join(texts).lower()
    tld = domain.rsplit(".", 1)[-1]
    country = tld.upper() if len(tld) == 2 and tld not in GENERIC_TLDS else None
    if country is None:
        named = [c for c, n in COUNTRY_NAMES.items() if re.search(rf"\b{n}\b", joined)]
        country = named[0] if len(named) == 1 else None
    return {"company_name": name or domain, "public_emails": sorted(emails), "tech": sorted(tech), "country": country,
            "has_contact_page": has_contact, "team_size_hint": team or None, "text": joined}


class Crawler:
    """One hunt. `fetch` and `sleep` are injectable so tests run without network or real waiting."""

    def __init__(self, db_factory, org_id: uuid.UUID, hunt: dict[str, Any], fetch: Fetch, sleep=time.sleep, clock=time.monotonic):
        self.db_factory, self.org_id, self.hunt = db_factory, org_id, hunt
        self.fetch, self.sleep, self.clock = fetch, sleep, clock
        self.max_pages = int(hunt["seeds"].get("max_pages_per_domain", len(PAGES)))
        self.stats = {"domains": 0, "fetched_pages": 0, "robots_disallowed": 0, "unreachable": 0, "prospects": 0,
                      "already_in_crm": 0, "suppressed": 0}

    # --------------------------------------------------------------------------------------- helpers
    def _log(self, db: Db, url: str, decision: str, status: int | None) -> None:
        db.execute("INSERT INTO ems.crawl_log (org_id, hunt_id, url, robots_decision, http_status) VALUES (:org, :h, :u, :d, :s)",
                   org=self.org_id, h=self.hunt["id"], u=url[:2000], d=decision, s=status)

    def _paced(self, dc: DomainCrawl, url: str) -> Page:
        wait = REQUEST_GAP_SECONDS - (self.clock() - dc.last_request)
        if dc.last_request and wait > 0:
            self.sleep(wait)
        page = self.fetch(url)
        dc.last_request = self.clock()
        return page

    def _save_progress(self, status: str) -> None:
        with self.db_factory() as db:
            db.set_context(self.org_id, None)
            db.execute("UPDATE ems.hunts SET status = :st, stats = CAST(:stats AS jsonb) || jsonb_build_object('heartbeat_at', now()) "
                       "WHERE id = :h", st=status, stats=jsonb(self.stats), h=self.hunt["id"])

    # --------------------------------------------------------------------------------------- steps
    def _robots(self, db: Db, dc: DomainCrawl) -> None:
        page = self._paced(dc, f"https://{dc.domain}/robots.txt")
        if page.status is None:                               # no TLS / unreachable over https: try plain http once
            dc.scheme = "http"
            page = self._paced(dc, f"http://{dc.domain}/robots.txt")
        decision = robots.decision_for_status(page.status)
        if decision == "disallow_all":
            self._log(db, f"{dc.scheme}://{dc.domain}/robots.txt", "unreachable_blocked", page.status)
            self.stats["unreachable"] += 1
            dc.stop = True
            return
        dc.groups = robots.parse(page.html or "") if decision == "parse" else []
        dc.pages = PAGES[: self.max_pages]

    def _next_page(self, db: Db, dc: DomainCrawl) -> None:
        path = dc.pages.pop(0)
        url = f"{dc.scheme}://{dc.domain}{path}"
        if not robots.allowed(dc.groups, ROBOTS_AGENT, path):
            self._log(db, url, "disallowed", None)
            self.stats["robots_disallowed"] += 1
            return
        page = self._paced(dc, url)
        self._log(db, url, "allowed", page.status)
        if page.html is not None:
            dc.fetched.append((url, page.html))
            self.stats["fetched_pages"] += 1

    def _finish(self, db: Db, dc: DomainCrawl) -> None:
        if not dc.fetched:
            return
        signals = extract(dc.domain, dc.fetched)
        icp = self.hunt["icp"]
        score, reasons = scoring.score(signals, icp)
        keywords = [k.lower() for k in icp.get("industry_keywords", [])]
        source = next((u for u, h in dc.fetched if any(k in h.lower() for k in keywords)), dc.fetched[0][0])
        stored = {k: signals[k] for k in ("tech", "country", "has_contact_page", "team_size_hint")}
        prospect_id = db.scalar(
            "INSERT INTO ems.prospects (id, org_id, hunt_id, domain, company_name, public_emails, signals, score, score_reasons, "
            "source_url, fetched_at) "
            "VALUES (:id, :org, :h, :d, :n, :e, CAST(:sig AS jsonb), :sc, CAST(:r AS jsonb), :src, now()) "
            "ON CONFLICT (org_id, domain) DO UPDATE SET hunt_id = EXCLUDED.hunt_id, company_name = EXCLUDED.company_name, "
            "public_emails = EXCLUDED.public_emails, signals = EXCLUDED.signals, score = EXCLUDED.score, score_reasons = EXCLUDED.score_reasons, "
            "source_url = EXCLUDED.source_url, fetched_at = EXCLUDED.fetched_at RETURNING id",
            id=uuid.uuid4(), org=self.org_id, h=self.hunt["id"], d=dc.domain, n=signals["company_name"], e=signals["public_emails"],
            sig=jsonb(stored), sc=score, r=jsonb(reasons), src=source)
        self.stats["prospects"] += 1
        events.emit(db, self.org_id, "prospect.scored", {
            "prospect_id": str(prospect_id), "hunt_id": str(self.hunt["id"]), "hunt_owner_id": str(self.hunt["created_by"]),
            "domain": dc.domain, "company_name": signals["company_name"], "prospect.score": score,
            "prospect.has_public_email": bool(signals["public_emails"]), "prospect.country": signals["country"]})

    # --------------------------------------------------------------------------------------- run
    def run(self) -> dict[str, Any]:
        domains = list(dict.fromkeys(d.lower() for d in self.hunt["seeds"].get("domains", [])))
        self.stats["domains"] = len(domains)
        crawls = []
        with self.db_factory() as db:
            db.set_context(self.org_id, None)
            for d in domains:
                if blocked(d) or suppression.is_suppressed(db, domain=d):
                    self.stats["suppressed"] += 1
                elif db.scalar("SELECT 1 FROM ems.companies WHERE domain = :d", d=d):
                    self.stats["already_in_crm"] += 1
                else:
                    crawls.append(DomainCrawl(d))
        self._save_progress("running")
        while any(dc.pending for dc in crawls):
            for dc in [dc for dc in crawls if dc.pending]:         # round-robin: one request per domain per pass
                with self.db_factory() as db:
                    db.set_context(self.org_id, None)
                    if dc.groups is None:
                        self._robots(db, dc)
                    else:
                        self._next_page(db, dc)
                    if not dc.stop and not dc.pending:
                        self._finish(db, dc)
            self._save_progress("running")
        self._save_progress("completed")
        return self.stats
