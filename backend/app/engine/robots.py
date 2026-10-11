"""RFC 9309 robots.txt evaluation (proposed path: backend/app/hunter/robots.py).

Python's urllib.robotparser applies the first matching rule, not the longest match required by RFC 9309
(checked in the audit sandbox), so Lead Hunter uses this module instead.
"""
import re

MAX_BYTES = 512_000


def parse(text: str) -> list[dict]:
    """Return groups: [{"agents": [...lowercase], "rules": [("allow"|"disallow", pattern)]}]."""
    groups, current, last_was_agent = [], None, False
    for raw in text.encode()[:MAX_BYTES].decode(errors="ignore").splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if not last_was_agent:
                current = {"agents": [], "rules": []}
                groups.append(current)
            current["agents"].append(value.lower())
            last_was_agent = True
        elif key in ("allow", "disallow") and current is not None:
            if value:
                current["rules"].append((key, value))
            last_was_agent = False
        else:
            last_was_agent = False
    return groups


def _to_regex(pattern: str) -> re.Pattern:
    anchored = pattern.endswith("$")
    body = re.escape(pattern[:-1] if anchored else pattern).replace(r"\*", ".*")
    return re.compile("^" + body + ("$" if anchored else ""))


def allowed(groups: list[dict], user_agent_token: str, path: str) -> bool:
    ua = user_agent_token.lower()
    rules = [r for g in groups if ua in g["agents"] for r in g["rules"]]
    if not any(ua in g["agents"] for g in groups):
        rules = [r for g in groups if "*" in g["agents"] for r in g["rules"]]
    best = None   # (length, is_allow)
    for kind, pattern in rules:
        if _to_regex(pattern).match(path):
            cand = (len(pattern), kind == "allow")
            if best is None or cand > best:      # longer wins; on equal length allow (True) wins
                best = cand
    return True if best is None else best[1]


def decision_for_status(status: int | None) -> str:
    """RFC 9309 section 2.3.1: 4xx = no restrictions; 5xx or network error = complete disallow."""
    if status is None or 500 <= status <= 599:
        return "disallow_all"
    if 400 <= status <= 499:
        return "allow_all"
    return "parse"
