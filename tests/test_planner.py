import os
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from planner import dates, ops, queries as q, render
from planner.store import PlannerError, Store

REPO = Path(__file__).resolve().parent.parent
FRI = date(2026, 10, 23)  # a Friday


class Sandbox(unittest.TestCase):
    """A throwaway copy of config/ with no items. Time is pinned via PLANNER_NOW."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        shutil.copytree(REPO / "config", self.dir / "config")
        for sub in ("items", "meetings", "plans", "archive"):
            (self.dir / "data" / sub).mkdir(parents=True)
        self.at("2026-10-23T11:00")

    def tearDown(self):
        os.environ.pop("PLANNER_NOW", None)
        shutil.rmtree(self.dir)

    def at(self, ts):
        os.environ["PLANNER_NOW"] = ts
        self.s = Store(self.dir)  # fresh store, as each CLI call would be


class DateParsing(unittest.TestCase):
    cal = dates.Calendar()

    def p(self, expr, today=FRI):
        return dates.parse(expr, today, self.cal)

    def test_weekday_is_the_next_one(self):
        self.assertEqual(self.p("wed"), date(2026, 10, 28))
        self.assertEqual(self.p("fri"), date(2026, 10, 30))  # said on a Friday: next Friday
        self.assertEqual(self.p("Wednesday", date(2026, 10, 26)), date(2026, 10, 28))

    def test_this_and_next(self):
        mon = date(2026, 10, 26)
        self.assertEqual(self.p("this fri", mon), date(2026, 10, 30))
        self.assertEqual(self.p("next mon", mon), date(2026, 11, 2))
        self.assertEqual(self.p("next week"), date(2026, 10, 26))

    def test_end_of_week(self):
        self.assertEqual(self.p("eow"), FRI)
        self.assertEqual(self.p("end of week", date(2026, 10, 24)), date(2026, 10, 30))  # Saturday
        self.assertEqual(self.p("end of next week"), date(2026, 10, 30))

    def test_relative_and_calendar_dates(self):
        self.assertEqual(self.p("+2wd"), date(2026, 10, 27))
        self.assertEqual(self.p("in 3 working days"), date(2026, 10, 28))
        self.assertEqual(self.p("in 3 days"), date(2026, 10, 26))
        self.assertEqual(self.p("28 oct"), date(2026, 10, 28))
        self.assertEqual(self.p("oct 28"), date(2026, 10, 28))
        self.assertEqual(self.p("2/11"), date(2026, 11, 2))  # day/month
        self.assertEqual(self.p("5 jan"), date(2027, 1, 5))
        self.assertEqual(self.p("eom"), date(2026, 10, 30))  # 31 Oct is a Saturday

    def test_rejects_nonsense(self):
        with self.assertRaises(ValueError):
            self.p("someday")


class WorkingDays(unittest.TestCase):
    def test_skips_weekends_and_holidays(self):
        cal = dates.Calendar(holidays=["2026-10-27"])
        self.assertEqual(cal.add(FRI, 1), date(2026, 10, 26))
        self.assertEqual(cal.add(FRI, 2), date(2026, 10, 28))
        self.assertEqual(cal.add(date(2026, 10, 28), -2), date(2026, 10, 23))
        self.assertEqual(cal.between(FRI, date(2026, 10, 30)), 4)


class FollowUps(Sandbox):
    def test_cadence_by_role(self):
        team = ops.add(self.s, "Fix tracking", project="geotrek", waiting_on="awais")
        self.assertEqual(team["next_followup"], "2026-10-27")  # 2 working days
        self.s.people.append({"id": "jake", "name": "Jake", "company": "ml", "role": "client",
                              "channel": "analytics-huddle", "projects": []})
        client = ops.add(self.s, "Approve plan", project="rvshare", waiting_on="jake")
        self.assertEqual(client["next_followup"], "2026-10-28")  # 3 working days
        self.assertEqual(client["channel"], "analytics-huddle")

    def test_due_date_pulls_the_chase_earlier(self):
        it = ops.add(self.s, "Numbers", project="rvshare", waiting_on="saad", due="tue")
        self.assertEqual(it["next_followup"], "2026-10-26")  # 1 working day before Tue

    def test_daily_once_overdue(self):
        it = ops.add(self.s, "Numbers", project="rvshare", waiting_on="saad", due="mon")
        self.at("2026-10-28T10:00")
        it = ops.chased(self.s, it["id"])
        self.assertEqual(it["next_followup"], "2026-10-29")

    def test_austell_defaults_to_email_for_new_contacts(self):
        self.assertEqual(self.s.default_channel(None, "austell"), "ml-email")


class Briefs(Sandbox):
    def test_unanswered_loop(self):
        it = ops.add(self.s, "Creatives", project="destify", waiting_on="maria")
        self.at("2026-10-27T10:00")
        self.assertIn(it["id"], [i["id"] for i in q.followups_due(self.s, self.s.today())])
        render.brief(self.s, mark=True)
        self.assertEqual(q.unanswered(self.s, self.s.today()), [])  # same day: not yet
        self.at("2026-10-28T10:00")
        self.assertEqual([i["id"] for i in q.unanswered(self.s, self.s.today())], [it["id"]])
        self.assertIn("No answer yet", render.brief(self.s))
        ops.log(self.s, it["id"], "Maria sends them today")
        self.assertEqual(q.unanswered(self.s, self.s.today()), [])

    def test_stale_after_ten_working_days(self):
        it = ops.add(self.s, "Audit", project="iqair", planned="mon")
        self.at("2026-11-05T10:00")  # 9 working days later
        self.assertEqual(q.stale(self.s, self.s.today()), [])
        self.at("2026-11-06T10:00")
        self.assertEqual([i["id"] for i in q.stale(self.s, self.s.today())], [it["id"]])
        ops.log(self.s, it["id"], "no change")
        self.assertEqual(q.stale(self.s, self.s.today()), [])

    def test_clash_when_input_arrives_too_late(self):
        d = ops.add(self.s, "Proposal", type="deliverable", project="rvshare", due="tue")
        ops.add(self.s, "Numbers", project="rvshare", waiting_on="saad", due="wed", blocks=[d["id"]])
        self.assertEqual(len(q.clashes(self.s)), 1)

    def test_brief_groups_by_channel(self):
        ops.add(self.s, "A", project="destify", waiting_on="maria")
        self.s.people.append({"id": "kim", "name": "Kim", "company": "ml", "role": "client",
                              "channel": "ml-email", "projects": ["austell"]})
        self.s.save_config("people")
        ops.add(self.s, "B", project="austell", waiting_on="kim", due="tue")
        self.at("2026-10-27T10:00")
        out = render.brief(self.s)
        self.assertLess(out.index("MarketLytics (Slack)"), out.index("Email (MarketLytics)"))
        self.assertIn("No plan for this week", out)


class Changes(Sandbox):
    def test_inbox_until_planned(self):
        it = ops.add(self.s, "Something", company="ml")
        self.assertEqual(it["status"], "inbox")
        it = ops.update(self.s, it["id"], project="sales", planned="mon")
        self.assertEqual((it["status"], it["company"]), ("planned", "ml"))

    def test_single_project_company_gets_its_project(self):
        it = ops.add(self.s, "Agenda", company="salam")
        self.assertEqual(it["project"], "salam-general")

    def test_slips_are_counted(self):
        it = ops.add(self.s, "Report", project="fenix", planned="mon")
        self.at("2026-10-26T17:00")
        ops.roll(self.s, it["id"])
        it = ops.update(self.s, it["id"], planned="next mon")
        self.assertEqual(len(it["slips"]), 2)
        self.assertIn("⚠", render.review(self.s, "2026-W44"))

    def test_deliverable_needs_due_date_once_planned(self):
        it = ops.add(self.s, "Deck", type="deliverable", project="growth")
        with self.assertRaises(PlannerError):
            ops.update(self.s, it["id"], planned="mon")

    def test_drop_needs_reason_and_done_closes(self):
        it = ops.add(self.s, "X", project="sales")
        with self.assertRaises(PlannerError):
            ops.drop(self.s, it["id"], "")
        it = ops.done(self.s, it["id"])
        self.assertEqual((it["status"], it["closed"]), ("done", "2026-10-23"))

    def test_resolve_names(self):
        self.assertEqual(self.s.resolve("project", "geotrek"), "geotrek")
        self.assertEqual(self.s.resolve("project", "Mr. Manhole"), "mr-manhole")
        self.assertEqual(self.s.resolve("person", "moattar"), "moattar")
        self.assertEqual(self.s.resolve("project", "wiideman"), "wiideman-retainer")  # active beats paused
        with self.assertRaises(PlannerError):
            self.s.resolve("project", "by ted")  # several active matches

    def test_find(self):
        it = ops.add(self.s, "Send revised proposal", project="rvshare")
        self.assertEqual(q.find(self.s, "rvshare proposal")[0]["id"], it["id"])

    def test_archive(self):
        it = ops.add(self.s, "Old", project="sales")
        ops.done(self.s, it["id"])
        self.at("2027-01-15T10:00")
        self.assertEqual(ops.archive(self.s), [it["id"]])
        self.assertTrue((self.dir / "data" / "archive" / f"{it['id']}.json").exists())


class SeedData(unittest.TestCase):
    def test_config_is_consistent(self):
        s = Store(REPO)
        ids = {c["id"] for c in s.channels}
        for p in s.projects:
            self.assertIn(p["company"], {c["id"] for c in s.companies})
            self.assertIn(p["default_channel"], ids)
        for p in s.people:
            self.assertIn(p["channel"], ids)
        self.assertEqual(len([p for p in s.projects if p["company"] == "ml" and p["status"] == "active"]), 16)
        self.assertEqual(len([p for p in s.people if p["role"] == "team"]), 21)


if __name__ == "__main__":
    unittest.main()
