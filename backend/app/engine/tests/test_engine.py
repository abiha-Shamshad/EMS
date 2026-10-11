import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from engine import rules, presence, leakage, robots, scoring, hr_agent
import urllib.robotparser

UTC = timezone.utc


class RulesTests(unittest.TestCase):
    D = {"trigger": "deal.stale",
         "when": {"all": [{"fact": "deal.days_since_activity", "op": "gte", "value": 14},
                          {"any": [{"fact": "deal.stage", "op": "in", "value": ["proposal", "negotiation"]}]}]},
         "then": [{"action": "notify", "to": "owner", "template": "deal_stale"},
                  {"action": "create_task", "assign": "owner", "title": "Follow up: {deal.title}", "due_in_hours": 24}]}

    def test_RUL_01_match_and_render(self):
        r = rules.run(self.D, {"deal.days_since_activity": 15, "deal.stage": "proposal", "deal.title": "Website rebuild"})
        self.assertTrue(r["matched"]); self.assertEqual(r["actions"][1]["title"], "Follow up: Website rebuild")
        self.assertEqual(len(r["trace"]), 2)

    def test_RUL_02_no_match_traces_all_conditions(self):
        r = rules.run(self.D, {"deal.days_since_activity": 3, "deal.stage": "proposal"})
        self.assertFalse(r["matched"]); self.assertEqual(r["actions"], []); self.assertEqual(len(r["trace"]), 2)

    def test_RUL_03_rejects_unknown_fact_op_action_and_depth(self):
        bad = [dict(self.D, when={"fact": "deal.secret", "op": "eq", "value": 1}),
               dict(self.D, when={"fact": "deal.stage", "op": "regex", "value": ".*"}),
               dict(self.D, then=[{"action": "run_python", "code": "x"}]),
               dict(self.D, when={"all": [{"all": [{"all": [{"fact": "deal.stage", "op": "eq", "value": "new"}]}]}]}),
               dict(self.D, extra=1)]
        for b in bad:
            with self.assertRaises(rules.RuleError):
                rules.validate(b)

    def test_RUL_04_missing_fact_is_false_not_error(self):
        self.assertFalse(rules.run(self.D, {})["matched"])


class PresenceTests(unittest.TestCase):
    def test_PRS_01_segments_with_idle_break_and_offline_gap(self):
        t0 = datetime(2026, 10, 12, 4, 0, tzinfo=UTC)     # 09:00 PKT
        hb = [{"at": t0 + timedelta(seconds=30 * i), "state": "active"} for i in range(20)]          # 10 min active
        hb += [{"at": t0 + timedelta(minutes=10, seconds=30 * i), "state": "idle"} for i in range(10)]  # 5 min idle
        hb += [{"at": t0 + timedelta(minutes=15, seconds=30 * i), "state": "active", "on_break": True} for i in range(30)]  # 15 min break
        hb += [{"at": t0 + timedelta(minutes=60), "state": "active"}]          # gap 30 -> 60 min
        segs = presence.segments(hb, t0 + timedelta(minutes=61))
        tot = presence.totals(segs)
        self.assertEqual(tot["active"], 11)      # 10 + final 1 minute
        self.assertEqual(tot["idle"], 5)
        self.assertEqual(tot["on_break"], 15)    # 14.5 min of heartbeats + 30 s before the gap
        self.assertEqual(tot["offline"], 30)      # 30:00 -> 60:00; totals sum to the 61-minute session

    def test_PRS_02_current_presence_offline_after_90s(self):
        now = datetime(2026, 10, 12, 5, 0, tzinfo=UTC)
        self.assertEqual(presence.current_presence(now - timedelta(seconds=91), "active", False, now), "offline")
        self.assertEqual(presence.current_presence(now - timedelta(seconds=30), "idle", False, now), "idle")
        self.assertEqual(presence.current_presence(now - timedelta(seconds=30), "active", True, now), "on_break")


class LeakageTests(unittest.TestCase):
    today = date(2026, 10, 12)
    projects = {"p1": {"id": "p1", "billing_type": "hourly", "hourly_rate": "40.00", "currency": "USD", "client_id": "c1"},
                "p2": {"id": "p2", "billing_type": "fixed", "budget_amount": "3000.00", "currency": "USD", "client_id": "c2"}}

    def test_LEK_01_unbilled_time_only_old_billable_uninvoiced_hourly(self):
        entries = [{"project_id": "p1", "minutes": 180, "billable": True, "invoice_id": None, "date": date(2026, 10, 1)},
                   {"project_id": "p1", "minutes": 60, "billable": True, "invoice_id": None, "date": date(2026, 10, 10)},   # too recent
                   {"project_id": "p1", "minutes": 60, "billable": False, "invoice_id": None, "date": date(2026, 10, 1)},
                   {"project_id": "p1", "minutes": 60, "billable": True, "invoice_id": "i9", "date": date(2026, 10, 1)},
                   {"project_id": "p2", "minutes": 600, "billable": True, "invoice_id": None, "date": date(2026, 10, 1)}]
        f = leakage.unbilled_time(entries, self.projects, self.today)
        self.assertEqual(len(f), 1); self.assertEqual(f[0]["amount_at_risk"], Decimal("120.00"))
        self.assertEqual(f[0]["fingerprint"], "unbilled_time:p1:2026-10-12")

    def test_LEK_02_overdue_invoice_net_of_payments(self):
        inv = [{"id": "i1", "number": "INV-2026-1048", "amount": "8400.00", "currency": "USD", "status": "partially_paid", "due_on": date(2026, 10, 1)},
               {"id": "i2", "number": "INV-2026-1049", "amount": "500.00", "currency": "USD", "status": "sent", "due_on": date(2026, 10, 20)}]
        f = leakage.overdue_invoices(inv, [{"invoice_id": "i1", "amount": "2400.00"}], self.today)
        self.assertEqual([x["amount_at_risk"] for x in f], [Decimal("6000.00")]); self.assertEqual(f[0]["evidence"]["days_overdue"], 11)

    def test_LEK_03_stale_deal_weighted(self):
        d = [{"id": "d1", "stage": "proposal", "amount": "5000", "currency": "USD", "last_activity_on": date(2026, 9, 25)},
             {"id": "d2", "stage": "won", "amount": "9000", "currency": "USD", "last_activity_on": date(2026, 8, 1)}]
        f = leakage.stale_deals(d, self.today)
        self.assertEqual(len(f), 1); self.assertEqual(f[0]["amount_at_risk"], Decimal("2500.00"))

    def test_LEK_04_won_follow_through(self):
        deals = [{"id": "dw1", "stage": "won", "won_on": date(2026, 10, 5), "amount": "4000", "currency": "USD"},
                 {"id": "dw2", "stage": "won", "won_on": date(2026, 8, 1), "amount": "7000", "currency": "USD"}]
        clients = [{"id": "c9", "origin_deal_id": "dw2"}]
        projects = {"p9": {"id": "p9", "client_id": "c9", "billing_type": "fixed"}}
        f = leakage.won_follow_through(deals, clients, projects, [], self.today)
        self.assertEqual(sorted(x["kind"] for x in f), ["won_without_invoice", "won_without_project"])

    def test_LEK_05_over_budget(self):
        entries = [{"project_id": "p2", "user_id": "u1", "minutes": 6000}]          # 100 h x 28 = 2800 >= 90% of 3000
        f = leakage.over_budget(self.projects, entries, {"u1": "28.00"})
        self.assertEqual(len(f), 1); self.assertEqual(f[0]["amount_at_risk"], Decimal("0.00")); self.assertEqual(f[0]["evidence"]["ratio"], "0.93")

    def test_LEK_06_idle_threshold(self):
        f = leakage.idle_paid_time({"u1": {"idle": 61, "active": 400}, "u2": {"idle": 60}}, {"u1": "6.00"}, self.today, "USD")
        self.assertEqual([x["entity_id"] for x in f], ["u1"]); self.assertEqual(f[0]["amount_at_risk"], Decimal("6.10"))


class RobotsTests(unittest.TestCase):
    TXT = "User-agent: *\nDisallow: /team\nAllow: /team/contact\n\nUser-agent: EMSHunter\nDisallow: /private\nAllow: /private/press$\n"

    def test_ROB_01_longest_match_wins_where_stdlib_differs(self):
        g = robots.parse(self.TXT)
        self.assertTrue(robots.allowed(g, "OtherBot", "/team/contact"))
        rp = urllib.robotparser.RobotFileParser(); rp.parse(self.TXT.splitlines())
        self.assertFalse(rp.can_fetch("OtherBot", "https://x.example/team/contact"))   # documents the stdlib difference

    def test_ROB_02_specific_group_replaces_star(self):
        g = robots.parse(self.TXT)
        self.assertTrue(robots.allowed(g, "emshunter", "/team"))           # star group not merged into a matching group
        self.assertFalse(robots.allowed(g, "EMSHunter", "/private/x"))
        self.assertTrue(robots.allowed(g, "EMSHunter", "/private/press"))
        self.assertFalse(robots.allowed(g, "EMSHunter", "/private/press/2"))

    def test_ROB_03_status_handling(self):
        self.assertEqual(robots.decision_for_status(404), "allow_all")
        self.assertEqual(robots.decision_for_status(503), "disallow_all")
        self.assertEqual(robots.decision_for_status(None), "disallow_all")


class ScoringTests(unittest.TestCase):
    def test_SCO_01_reasons_explain_points(self):
        s, reasons = scoring.score({"text": "We are a digital marketing agency in Lahore", "country": "PK", "has_contact_page": True,
                                    "public_emails": ["info@x.example"], "tech": ["WordPress"]},
                                   {"industry_keywords": ["marketing agency"], "countries": ["PK"], "tech": ["wordpress"]})
        self.assertEqual(s, 85); self.assertEqual(len(reasons), 5)


class FakeRepo(hr_agent.Repo):
    def leave_on(self, day): return [{"user_id": "u2", "name": "Andleeb", "kind": "annual", "request_id": "lr1"}] if day == date(2026, 10, 12) else []
    def pending_leave(self): return [{"request_id": "lr2", "name": "Rabia", "days": 2, "kind": "casual"}]
    def late_on(self, day, g): return [{"user_id": "u3", "name": "Subhan", "minutes_late": 25, "session_id": "ws3"}]
    def online_now(self): return [{"user_id": "u1", "name": "Abiha", "presence": "active", "task": "Auth API"}]
    def day_totals(self, uid, day): return {"active": 412, "idle": 38, "on_break": 45, "tasks": [{"title": "Auth API", "minutes": 300}], "session_ids": ["ws1"]} if uid == "u1" else {}
    def find_person(self, text): return {"user_id": "u1", "name": "Abiha"} if "abiha" in text else None
    def policy(self, topic): return {"topic": "leave", "text": "18 annual days per year.", "version": 2} if topic == "leave" else None


class HrAgentTests(unittest.TestCase):
    today = date(2026, 10, 12); hr = {"user_id": "hr1", "role": "hr"}; emp = {"user_id": "u9", "role": "employee"}

    def test_AGT_01_answers_with_sources(self):
        a = hr_agent.answer("Who is on leave today?", self.hr, FakeRepo(), self.today)
        self.assertTrue(a["answered"]); self.assertEqual(a["sources"], ["lr1"]); self.assertIn("Andleeb", a["text"])

    def test_AGT_02_unknown_question_never_guesses(self):
        a = hr_agent.answer("What will our revenue be next year?", self.hr, FakeRepo(), self.today)
        self.assertFalse(a["answered"]); self.assertEqual(a["intent"], "unknown"); self.assertEqual(a["sources"], [])

    def test_AGT_03_employee_cannot_see_team_or_others(self):
        self.assertFalse(hr_agent.answer("Who came late today?", self.emp, FakeRepo(), self.today)["answered"])
        self.assertFalse(hr_agent.answer("Work summary for Abiha yesterday", self.emp, FakeRepo(), self.today)["answered"])

    def test_AGT_04_work_summary_and_policy(self):
        a = hr_agent.answer("work summary for abiha yesterday", self.hr, FakeRepo(), self.today)
        self.assertIn("active 412 min", a["text"]); self.assertEqual(a["sources"], ["ws1"])
        p = hr_agent.answer("What is the leave policy?", self.emp, FakeRepo(), self.today)
        self.assertTrue(p["answered"]); self.assertIn("v2", p["text"])

    def test_AGT_05_missing_policy_is_stated(self):
        a = hr_agent.answer("What is the attendance rule for late arrival?", self.emp, FakeRepo(), self.today)
        self.assertEqual(a["intent"], "policy")          # policy intent is checked before lateness
        self.assertFalse(a["answered"]); self.assertIn("No attendance policy", a["text"])


if __name__ == "__main__":
    unittest.main()
