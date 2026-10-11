"""HR Agent: rule-based question answering over EMS data (proposed path: backend/app/agent/hr_agent.py).

No language model and no external API. A question is matched to one intent by patterns; the intent runs a fixed
query through the repository interface; the answer is a template filled with real records and lists its sources.
If no intent matches, the agent says so and lists what it can answer. It never guesses.
"""
import re
from datetime import date, timedelta

PRIVILEGED = {"ceo", "coo", "hr"}


class Repo:
    """Interface implemented by the backend with SQL; tests use an in-memory fake. All methods are org-scoped."""
    def leave_on(self, day): ...                 # -> [{"user_id","name","kind","request_id"}]
    def pending_leave(self): ...                 # -> [{"request_id","name","days","kind"}]
    def late_on(self, day, grace_minutes): ...   # -> [{"user_id","name","minutes_late","session_id"}]
    def online_now(self): ...                    # -> [{"user_id","name","presence","task"}]
    def day_totals(self, user_id, day): ...      # -> {"active":m,"idle":m,"on_break":m,"tasks":[{"title","minutes"}],"session_ids":[...]}
    def find_person(self, text): ...             # -> {"user_id","name"} | None
    def policy(self, topic): ...                 # -> {"topic","text","version"} | None


def _day(q: str, today: date) -> date:
    if "yesterday" in q:
        return today - timedelta(days=1)
    if "tomorrow" in q:
        return today + timedelta(days=1)
    m = re.search(r"(\d{4}-\d{2}-\d{2})", q)
    return date.fromisoformat(m.group(1)) if m else today


INTENTS = [   # order matters: policy questions are checked first so "late arrival rule" is not read as a lateness query
    ("policy", re.compile(r"\b(policy|rule|rules|allowed|how many (days|leaves))\b")),
    ("who_on_leave", re.compile(r"\b(who|anyone)\b.*\b(on leave|off|absent|leave)\b")),
    ("pending_leave", re.compile(r"\b(pending|waiting|approve)\b.*\bleave\b|\bleave\b.*\b(pending|requests?)\b")),
    ("late_arrivals", re.compile(r"\b(late|came late|late arrivals?)\b")),
    ("online_now", re.compile(r"\b(online|working now|who is in|active now)\b")),
    ("work_summary", re.compile(r"\b(summary|what did|worked on|work report)\b")),
]
CAPABILITIES = ["Who is on leave today?", "Which leave requests are pending?", "Who came late today?",
                "Who is online now?", "Work summary for <name> yesterday", "What is the leave policy?"]


def classify(question: str) -> str | None:
    q = question.lower()
    for name, pat in INTENTS:
        if pat.search(q):
            return name
    return None


def answer(question: str, asker: dict, repo: Repo, today: date, grace_minutes: int = 10) -> dict:
    """asker = {"user_id","role"}. Returns {"intent","answered","text","data","sources"}."""
    q = question.lower()
    intent = classify(question)
    if intent is None:
        return {"intent": "unknown", "answered": False,
                "text": "I can't answer that from EMS records. I can answer: " + "; ".join(CAPABILITIES),
                "data": [], "sources": []}
    privileged = asker["role"] in PRIVILEGED
    day = _day(q, today)

    if intent in ("who_on_leave", "pending_leave", "late_arrivals", "online_now") and not privileged and asker["role"] != "manager":
        return {"intent": intent, "answered": False, "text": "Only HR, managers and leadership can see team attendance.", "data": [], "sources": []}

    if intent == "who_on_leave":
        rows = repo.leave_on(day)
        text = f"{len(rows)} on leave on {day.isoformat()}" + (": " + ", ".join(f"{r['name']} ({r['kind']})" for r in rows) if rows else ".")
        return {"intent": intent, "answered": True, "text": text, "data": rows, "sources": [r["request_id"] for r in rows]}
    if intent == "pending_leave":
        rows = repo.pending_leave()
        text = f"{len(rows)} leave request(s) waiting for a decision" + (": " + ", ".join(f"{r['name']} {r['days']}d {r['kind']}" for r in rows) if rows else ".")
        return {"intent": intent, "answered": True, "text": text, "data": rows, "sources": [r["request_id"] for r in rows]}
    if intent == "late_arrivals":
        rows = repo.late_on(day, grace_minutes)
        text = f"{len(rows)} late on {day.isoformat()} (after {grace_minutes} min grace)" + (": " + ", ".join(f"{r['name']} {r['minutes_late']} min" for r in rows) if rows else ".")
        return {"intent": intent, "answered": True, "text": text, "data": rows, "sources": [r["session_id"] for r in rows]}
    if intent == "online_now":
        rows = repo.online_now()
        text = f"{len(rows)} online now" + (": " + ", ".join(f"{r['name']} ({r['presence']})" for r in rows) if rows else ".")
        return {"intent": intent, "answered": True, "text": text, "data": rows, "sources": [r["user_id"] for r in rows]}
    if intent == "work_summary":
        person = repo.find_person(q) or ({"user_id": asker["user_id"], "name": "you"} if re.search(r"\b(my|me|i)\b", q) else None)
        if person is None:
            return {"intent": intent, "answered": False, "text": "Name the person, for example: work summary for Abiha yesterday.", "data": [], "sources": []}
        if person["user_id"] != asker["user_id"] and not privileged and asker["role"] != "manager":
            return {"intent": intent, "answered": False, "text": "You can only see your own work summary.", "data": [], "sources": []}
        t = repo.day_totals(person["user_id"], day)
        if not t or not t.get("session_ids"):
            return {"intent": intent, "answered": True, "text": f"No work session recorded for {person['name']} on {day.isoformat()}.", "data": [], "sources": []}
        tasks = ", ".join(f"{x['title']} ({x['minutes']} min)" for x in t.get("tasks", [])) or "no task selected"
        text = (f"{person['name']} on {day.isoformat()}: active {t.get('active', 0)} min, idle {t.get('idle', 0)} min, "
                f"breaks {t.get('on_break', 0)} min. Tasks: {tasks}.")
        return {"intent": intent, "answered": True, "text": text, "data": [t], "sources": t["session_ids"]}
    if intent == "policy":
        topic = "leave" if "leave" in q else "attendance" if ("late" in q or "attendance" in q) else "general"
        p = repo.policy(topic)
        if not p:
            return {"intent": intent, "answered": False, "text": f"No {topic} policy has been published in EMS yet.", "data": [], "sources": []}
        return {"intent": intent, "answered": True, "text": f"{p['topic'].title()} policy (v{p['version']}): {p['text']}", "data": [p], "sources": [f"policy:{p['topic']}:v{p['version']}"]}
