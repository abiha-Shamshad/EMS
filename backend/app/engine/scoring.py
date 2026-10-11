"""Prospect scoring against an ideal-customer profile (proposed path: backend/app/hunter/scoring.py).
Deterministic: every point has a reason the user can see."""

WEIGHTS = {"industry_match": 30, "country_match": 15, "has_contact_page": 10, "has_public_email": 15,
           "size_signal": 15, "tech_match": 15}


def score(prospect: dict, icp: dict) -> tuple[int, list[str]]:
    s, reasons = 0, []
    text = (prospect.get("text") or "").lower()
    kws = [k.lower() for k in icp.get("industry_keywords", [])]
    hits = [k for k in kws if k in text]
    if hits:
        s += WEIGHTS["industry_match"]; reasons.append("industry keywords: " + ", ".join(hits[:3]))
    if icp.get("countries") and prospect.get("country") in icp["countries"]:
        s += WEIGHTS["country_match"]; reasons.append("country " + prospect["country"])
    if prospect.get("has_contact_page"):
        s += WEIGHTS["has_contact_page"]; reasons.append("contact page found")
    if prospect.get("public_emails"):
        s += WEIGHTS["has_public_email"]; reasons.append("public business email listed")
    if prospect.get("team_size_hint") and icp.get("min_team_size") and prospect["team_size_hint"] >= icp["min_team_size"]:
        s += WEIGHTS["size_signal"]; reasons.append(f"team size hint {prospect['team_size_hint']}")
    tech = set(t.lower() for t in prospect.get("tech", [])) & set(t.lower() for t in icp.get("tech", []))
    if tech:
        s += WEIGHTS["tech_match"]; reasons.append("uses " + ", ".join(sorted(tech)))
    return min(s, 100), reasons
