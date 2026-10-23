"""Changes to items. Every change is written to the item's log."""

from . import dates
from .store import OPEN_STATUSES, PlannerError, TYPE_LABELS


def _log(store, item, text, touch=True):
    ts = dates.stamp(store.now())
    item.setdefault("log", []).append({"at": ts, "text": text})
    if touch:
        item["last_update"] = ts


def _project_and_company(store, project, company):
    if project:
        pid = store.resolve("project", project)
        return pid, store.project(pid)["company"]
    if company:
        cid = store.resolve("company", company)
        only = [p for p in store.projects if p["company"] == cid]
        return (only[0]["id"] if len(only) == 1 else None), cid
    return None, None


def add(store, title, type="task", project=None, company=None, due=None, planned=None,
        waiting_on=None, channel=None, priority="normal", status=None, note=None,
        link=None, blocks=(), meeting=None, followup=None):
    if type not in TYPE_LABELS:
        raise PlannerError(f"type must be one of {list(TYPE_LABELS)}")
    pid, cid = _project_and_company(store, project, company)
    if not cid:
        raise PlannerError("say which project (or at least which company) this belongs to")
    person = store.resolve("person", waiting_on) if waiting_on else None
    now = store.now()
    item = {
        "id": store.new_id(pid),
        "title": title.strip(),
        "type": type,
        "company": cid,
        "project": pid,
        "status": None,
        "priority": priority,
        "due": store.parse_date(due),
        "planned_day": store.parse_date(planned),
        "waiting_on": person,
        "channel": store.resolve("channel", channel) if channel else (store.default_channel(person, pid) if person else None),
        "next_followup": None,
        "blocks": [store.item(b)["id"] for b in blocks],
        "meeting": meeting,
        "notes": [],
        "links": [],
        "subtasks": [],
        "slips": [],
        "log": [],
        "created": dates.stamp(now),
        "last_update": dates.stamp(now),
        "last_prompted": None,
        "closed": None,
    }
    if status:
        item["status"] = status
    elif person:
        item["status"] = "waiting"
    elif not pid:
        item["status"] = "inbox"
    elif item["planned_day"]:
        item["status"] = "planned"
    else:
        item["status"] = "inbox"
    if item["status"] == "waiting":
        item["next_followup"] = store.parse_date(followup) or store.next_followup(item)
    if note:
        item["notes"].append({"at": dates.stamp(now), "text": note})
    if link:
        item["links"].append(link)
    who = f", waiting on {store.person(person)['name']}" if person else ""
    _log(store, item, f"Created ({TYPE_LABELS[type]}{who})")
    store.save_item(item)
    return item


def update(store, iid, title=None, type=None, project=None, company=None, due=None, planned=None,
           waiting_on=None, channel=None, priority=None, status=None, followup=None,
           blocks=None, meeting=None, note=None, link=None, subtask=None, subtask_done=None,
           text=None):
    """Change fields. Pass "none" to clear a date. Returns the item."""
    item = store.item(iid)
    changes = []
    today = store.today()

    def setf(field, value, label=None, show=None):
        if value is not None and item.get(field) != value:
            item[field] = value
            changes.append(f"{label or field} → {show(value) if show else value}")

    setf("title", title.strip() if title else None, "title")
    setf("type", type, "type", lambda v: TYPE_LABELS[v])
    if project or company:
        pid, cid = _project_and_company(store, project, company)
        if pid != item.get("project") or cid != item["company"]:
            item["project"], item["company"] = pid, cid
            changes.append(f"project → {store.project(pid)['name'] if pid else store.company(cid)['name']}")
    if due is not None:
        new = store.parse_date(due)
        if new != item.get("due"):
            item["due"] = new
            changes.append(f"due → {dates.fmt(new)}")
    if planned is not None:
        new, old = store.parse_date(planned), item.get("planned_day")
        if new != old:
            item["planned_day"] = new
            if old and new and new > old:
                item.setdefault("slips", []).append(today.isoformat())
                changes.append(f"moved {dates.fmt(old)} → {dates.fmt(new)} (slipped)")
            else:
                changes.append(f"planned → {dates.fmt(new)}")
            if new and item["status"] == "inbox" and item.get("project"):
                item["status"] = "planned"
    if waiting_on is not None:
        if waiting_on.lower() in ("none", "clear", "-"):
            item["waiting_on"] = None
            if item["status"] == "waiting" and not status:
                status = "in_progress"
        else:
            pid = store.resolve("person", waiting_on)
            if pid != item.get("waiting_on"):
                item["waiting_on"] = pid
                changes.append(f"waiting on → {store.person(pid)['name']}")
                if not channel:
                    item["channel"] = store.default_channel(pid, item.get("project"))
                if item["status"] == "waiting" and followup is None:
                    item["next_followup"] = store.next_followup(item)
                status = status or "waiting"
    if channel is not None:
        setf("channel", store.resolve("channel", channel), "channel")
    setf("priority", priority, "priority")
    if blocks is not None:
        item["blocks"] = [store.item(b)["id"] for b in blocks]
        changes.append("blocks → " + (", ".join(item["blocks"]) or "nothing"))
    setf("meeting", meeting, "meeting")
    if status is not None and status != item["status"]:
        set_status(store, item, status, changes)
    if followup is not None:
        new = store.parse_date(followup)
        if new != item.get("next_followup"):
            item["next_followup"] = new
            changes.append(f"next follow-up → {dates.fmt(new)}")
    elif item["status"] == "waiting" and due is not None:
        # A new due date can pull the next chase earlier, never later.
        item["next_followup"] = min(item["next_followup"], store.next_followup(item))
    if note:
        item.setdefault("notes", []).append({"at": dates.stamp(store.now()), "text": note})
        changes.append(f"note: {note}")
    if link:
        item.setdefault("links", []).append(link)
        changes.append(f"link: {link}")
    if subtask:
        item.setdefault("subtasks", []).append({"text": subtask, "done": False})
        changes.append(f"sub-step: {subtask}")
    if subtask_done is not None:
        try:
            st = item["subtasks"][int(subtask_done) - 1]
        except (IndexError, ValueError, KeyError):
            raise PlannerError(f"no sub-step {subtask_done}")
        st["done"] = True
        changes.append(f"sub-step done: {st['text']}")
    if text:
        changes.append(text)
    if not changes:
        return item
    _log(store, item, "; ".join(changes))
    store.save_item(item)
    return item


def set_status(store, item, status, changes):
    if status not in ("inbox", "planned", "in_progress", "waiting", "done", "dropped"):
        raise PlannerError(f"unknown status {status}")
    item["status"] = status
    item["closed"] = store.today().isoformat() if status in ("done", "dropped") else None
    if status == "waiting":
        item["next_followup"] = item.get("next_followup") or store.next_followup(item)
    else:
        item["next_followup"] = None
    changes.append(f"status → {status.replace('_', ' ')}")


def log(store, iid, text):
    """A plain update ('Saad says Thursday', 'no change'). Resets the stale timer."""
    item = store.item(iid)
    _log(store, item, text)
    store.save_item(item)
    return item


def done(store, iid, note=None):
    return update(store, iid, status="done", text=note)


def drop(store, iid, reason):
    if not reason:
        raise PlannerError("say why it's being dropped")
    return update(store, iid, status="dropped", text=f"dropped: {reason}")


def chased(store, iid, note=None):
    """You sent the follow-up. Schedules the next one by cadence."""
    item = store.item(iid)
    if item["status"] != "waiting":
        raise PlannerError(f"{item['id']} isn't waiting on anyone")
    item["next_followup"] = store.next_followup(item)
    ch = store.channel(item["channel"])["name"] if item.get("channel") else "?"
    _log(store, item, f"Follow-up sent via {ch}; next {dates.fmt(item['next_followup'])}" + (f" — {note}" if note else ""))
    store.save_item(item)
    return item


def mark_prompted(store, items):
    """Record that the brief asked about these, without counting as an update."""
    ts = dates.stamp(store.now())
    for item in items:
        item["last_prompted"] = ts
        store.save_item(item)


def roll(store, iid, to=None):
    """Not done today: move to `to` (default next working day) and count a slip."""
    item = store.item(iid)
    if item["status"] not in OPEN_STATUSES:
        raise PlannerError(f"{item['id']} is {item['status']}")
    target = store.parse_date(to) if to else store.cal.add(store.today(), 1).isoformat()
    old = item.get("planned_day")
    item["planned_day"] = target
    item.setdefault("slips", []).append(store.today().isoformat())
    if item["status"] == "inbox" and item.get("project"):
        item["status"] = "planned"
    _log(store, item, f"rolled {dates.fmt(old) if old else 'unplanned'} → {dates.fmt(target)} (slipped)")
    store.save_item(item)
    return item


def archive(store):
    """Move items closed more than archive_after_weeks ago to data/archive/."""
    weeks = store.settings.get("archive_after_weeks", 8)
    cutoff = store.today().toordinal() - weeks * 7
    moved = []
    for item in list(store.items().values()):
        if item.get("closed") and dates.to_date(item["closed"]).toordinal() < cutoff:
            src = store.items_dir / f"{item['id']}.json"
            src.replace(store.base / "data" / "archive" / src.name)
            del store.items()[item["id"]]
            moved.append(item["id"])
    return moved
