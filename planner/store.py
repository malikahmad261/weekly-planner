"""Loading, saving and validating the planner's JSON files."""

import difflib
import json
import os
import re
import secrets
from pathlib import Path

from . import dates

TYPES = ["task", "deliverable", "followup", "prep"]
TYPE_LABELS = {"task": "Task", "deliverable": "Deliverable", "followup": "Follow-up", "prep": "Meeting prep"}
STATUSES = ["inbox", "planned", "in_progress", "waiting", "done", "dropped"]
OPEN_STATUSES = ["inbox", "planned", "in_progress", "waiting"]
PRIORITIES = ["high", "normal"]
ROLES = ["team", "colleague", "client", "partner"]


class PlannerError(Exception):
    pass


def root():
    return Path(os.environ.get("PLANNER_ROOT", Path(__file__).resolve().parent.parent))


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class Store:
    def __init__(self, base=None):
        self.base = Path(base or root())
        cfg = self.base / "config"
        self.settings = read_json(cfg / "settings.json", {})
        self.companies = read_json(cfg / "companies.json", [])
        self.channels = read_json(cfg / "channels.json", [])
        self.projects = read_json(cfg / "projects.json", [])
        self.people = read_json(cfg / "people.json", [])
        self.cal = dates.Calendar(
            self.settings.get("working_days", ["mon", "tue", "wed", "thu", "fri"]),
            read_json(cfg / "holidays.json", []),
        )
        self._items = None

    # ---- time -------------------------------------------------------------
    def now(self):
        return dates.now(self.settings.get("timezone", "Asia/Karachi"))

    def today(self):
        return self.now().date()

    def parse_date(self, expr):
        if expr is None or str(expr).lower() in ("none", "clear", "-", ""):
            return None
        return dates.parse(expr, self.today(), self.cal).isoformat()

    # ---- lookups ----------------------------------------------------------
    def by_id(self, records, rid):
        return next((r for r in records if r["id"] == rid), None)

    def company(self, cid):
        return self.by_id(self.companies, cid)

    def project(self, pid):
        return self.by_id(self.projects, pid)

    def person(self, pid):
        return self.by_id(self.people, pid)

    def channel(self, cid):
        return self.by_id(self.channels, cid)

    def resolve(self, kind, text):
        """Match an id or name (exact, then unique partial, then fuzzy)."""
        records = {"company": self.companies, "project": self.projects,
                   "person": self.people, "channel": self.channels}[kind]
        if text is None:
            return None
        t = text.strip().lower()
        for r in records:
            if r["id"] == t or r["name"].lower() == t:
                return r["id"]
        hits = [r for r in records if t in r["id"] or t in r["name"].lower()]
        if kind == "project" and len(hits) > 1:  # prefer active projects when ambiguous
            active = [r for r in hits if r.get("status") == "active"]
            hits = active if len(active) == 1 else hits
        if len(hits) == 1:
            return hits[0]["id"]
        if not hits:
            close = difflib.get_close_matches(t, [r["name"].lower() for r in records], n=3, cutoff=0.75)
            hits = [r for r in records if r["name"].lower() in close]
            if len(hits) == 1:
                return hits[0]["id"]
        if hits:
            raise PlannerError(f"'{text}' could be {kind}: " + ", ".join(f"{r['name']} ({r['id']})" for r in hits))
        raise PlannerError(f"no {kind} matches '{text}'")

    def save_config(self, name):
        write_json(self.base / "config" / f"{name}.json", getattr(self, name))

    # ---- items ------------------------------------------------------------
    @property
    def items_dir(self):
        return self.base / "data" / "items"

    def items(self):
        if self._items is None:
            self._items = {}
            for p in sorted(self.items_dir.glob("*.json")):
                item = read_json(p)
                self._items[item["id"]] = item
        return self._items

    def item(self, iid):
        items = self.items()
        if iid in items:
            return items[iid]
        hits = [k for k in items if k.endswith(iid) or k.startswith(iid)]
        if len(hits) == 1:
            return items[hits[0]]
        raise PlannerError(f"no item with id '{iid}'" + (f" (did you mean: {', '.join(hits)})" if hits else ""))

    def new_id(self, project):
        prefix = project or "inbox"
        while True:
            iid = f"{prefix}-{secrets.token_hex(2)}"
            if iid not in self.items() and not (self.base / "data" / "archive" / f"{iid}.json").exists():
                return iid

    def save_item(self, item):
        errors = self.validate_item(item)
        if errors:
            raise PlannerError(f"{item.get('id')}: " + "; ".join(errors))
        write_json(self.items_dir / f"{item['id']}.json", item)
        self.items()[item["id"]] = item

    def validate_item(self, it):
        e = []
        for f in ("id", "title", "type", "company", "status", "created", "last_update", "log"):
            if not it.get(f):
                e.append(f"missing {f}")
        if it.get("type") not in TYPES:
            e.append(f"type must be one of {TYPES}")
        if it.get("status") not in STATUSES:
            e.append(f"status must be one of {STATUSES}")
        if it.get("priority", "normal") not in PRIORITIES:
            e.append(f"priority must be one of {PRIORITIES}")
        if it.get("company") and not self.company(it["company"]):
            e.append(f"unknown company {it['company']}")
        if it.get("project"):
            p = self.project(it["project"])
            if not p:
                e.append(f"unknown project {it['project']}")
            elif p["company"] != it.get("company"):
                e.append("company doesn't match project")
        elif it.get("status") not in ("inbox", "done", "dropped"):
            e.append("an item without a project must stay in inbox")
        for f in ("due", "planned_day", "next_followup", "closed"):
            if it.get(f):
                try:
                    dates.to_date(it[f])
                except ValueError:
                    e.append(f"{f} is not a date")
        if it.get("waiting_on") and not self.person(it["waiting_on"]):
            e.append(f"unknown person {it['waiting_on']}")
        if it.get("channel") and not self.channel(it["channel"]):
            e.append(f"unknown channel {it['channel']}")
        if it.get("status") == "waiting":
            if not it.get("waiting_on"):
                e.append("waiting items need waiting_on")
            if not it.get("next_followup"):
                e.append("waiting items need next_followup")
        if it.get("type") == "deliverable" and it.get("status") not in ("inbox", "done", "dropped") and not it.get("due"):
            e.append("deliverables need a due date")
        for b in it.get("blocks", []):
            if b not in self.items() and b != it.get("id"):
                e.append(f"blocks unknown item {b}")
        return e

    # ---- meetings and plans -----------------------------------------------
    def meetings_path(self, wid):
        return self.base / "data" / "meetings" / f"{wid}.json"

    def meetings(self, wid):
        return read_json(self.meetings_path(wid), [])

    def save_meetings(self, wid, meetings):
        meetings.sort(key=lambda m: (m["date"], m.get("time") or ""))
        write_json(self.meetings_path(wid), meetings)

    def plan_path(self, wid):
        return self.base / "data" / "plans" / f"{wid}.json"

    def plan(self, wid):
        return read_json(self.plan_path(wid))

    def save_plan(self, wid, plan):
        write_json(self.plan_path(wid), plan)

    # ---- follow-up rules --------------------------------------------------
    def cadence_for(self, person_id):
        cad = self.settings.get("followup_cadence_working_days", {})
        person = self.person(person_id) if person_id else None
        role = person["role"] if person else "client"
        return cad.get(role, 3)

    def next_followup(self, item, from_day=None):
        """When to chase next, counted from from_day (default today).

        Cadence by role, but never later than N working days before a hard
        due date, and daily once the due date has passed. Always at least the
        next working day, so a chase sent today isn't repeated today.
        """
        today = from_day or self.today()
        soonest = self.cal.add(today, 1)
        target = self.cal.add(today, self.cadence_for(item.get("waiting_on")))
        if item.get("due"):
            due = dates.to_date(item["due"])
            lead = self.cal.add(due, -self.settings.get("followup_lead_before_due_working_days", 1))
            target = min(target, max(lead, soonest))
        return max(target, soonest).isoformat()

    def default_channel(self, person_id, project_id):
        person = self.person(person_id) if person_id else None
        if person and person.get("channel"):
            return person["channel"]
        project = self.project(project_id) if project_id else None
        return project["default_channel"] if project else None
