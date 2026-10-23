"""Read-only questions about the items. These decide what lands in each brief."""

import difflib

from . import dates
from .store import OPEN_STATUSES

D = dates.to_date


def open_items(store):
    return [i for i in store.items().values() if i["status"] in OPEN_STATUSES]


def followups_due(store, day):
    return sorted((i for i in open_items(store)
                   if i["status"] == "waiting" and i.get("next_followup") and D(i["next_followup"]) <= day),
                  key=lambda i: (i["next_followup"], i.get("due") or "9999"))


def unanswered(store, day):
    """Asked about in an earlier brief, and nothing logged since."""
    return [i for i in open_items(store)
            if i.get("last_prompted") and D(i["last_prompted"]) < day and i["last_update"] < i["last_prompted"]]


def stale(store, day):
    limit = store.settings.get("stale_after_working_days", 10)
    return sorted((i for i in open_items(store) if store.cal.between(i["last_update"], day) >= limit),
                  key=lambda i: i["last_update"])


def due_by(store, day):
    return sorted((i for i in open_items(store) if i.get("due") and D(i["due"]) <= day),
                  key=lambda i: (i["type"] != "deliverable", i["due"]))


def due_on(store, day):
    return [i for i in open_items(store) if i.get("due") and D(i["due"]) == day]


def due_between(store, a, b):
    return [i for i in open_items(store) if i.get("due") and a <= D(i["due"]) <= b]


def planned_on(store, day):
    return [i for i in open_items(store) if i.get("planned_day") and D(i["planned_day"]) == day]


def chase_count(item):
    return sum(1 for e in item.get("log", []) if e["text"].startswith("Follow-up sent"))


def clashes(store):
    """Something you're waiting on that won't arrive before the item it blocks is due."""
    out = []
    items = store.items()
    for w in open_items(store):
        for bid in w.get("blocks", []):
            b = items.get(bid)
            if not b or b["status"] not in OPEN_STATUSES or not b.get("due"):
                continue
            arrives = w.get("due") or (w.get("next_followup") if w["status"] == "waiting" else None)
            if arrives and D(arrives) >= D(b["due"]):
                out.append((w, b))
    return out


def closed_between(store, a, b, status):
    return [i for i in store.items().values()
            if i["status"] == status and i.get("closed") and a <= D(i["closed"]) <= b]


def slipped_between(store, a, b):
    return [i for i in store.items().values() if any(a <= D(s) <= b for s in i.get("slips", []))]


def find(store, query, include_closed=False, limit=5):
    q = query.lower().strip()
    scored = []
    for i in store.items().values():
        if not include_closed and i["status"] not in OPEN_STATUSES:
            continue
        project = store.project(i["project"])["name"] if i.get("project") else ""
        person = store.person(i["waiting_on"])["name"] if i.get("waiting_on") else ""
        hay = " ".join([i["title"], project, person, i["id"]]).lower()
        score = difflib.SequenceMatcher(None, q, i["title"].lower()).ratio()
        words = [w for w in q.split() if len(w) > 1]
        if words:
            score += sum(1 for w in words if w in hay) / len(words)
        if q in hay:
            score += 1
        if score > 0.5:
            scored.append((score, i))
    scored.sort(key=lambda s: -s[0])
    return [i for _, i in scored[:limit]]
