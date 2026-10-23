"""planner — command line for the weekly planner.

Run `python3 -m planner --help`. Every command prints Markdown.
"""

import argparse
import json
import secrets
import sys

from . import dates, ops, queries as q, render
from .store import PlannerError, ROLES, Store, TYPE_LABELS, slug


def item_args(p, adding):
    p.add_argument("--type", choices=list(TYPE_LABELS), default="task" if adding else None)
    p.add_argument("--project", help="project id or name")
    p.add_argument("--company", help="company, when there's no project yet")
    p.add_argument("--due", help="plain-language date; 'none' clears")
    p.add_argument("--planned", help="day you'll work on it; 'none' clears")
    p.add_argument("--waiting-on", help="person; 'none' clears")
    p.add_argument("--channel")
    p.add_argument("--followup", help="override the next follow-up date")
    p.add_argument("--priority", choices=["high", "normal"], default="normal" if adding else None)
    p.add_argument("--status", choices=["inbox", "planned", "in_progress", "waiting", "done", "dropped"])
    p.add_argument("--blocks", nargs="*", help="ids of items this one blocks")
    p.add_argument("--meeting", help="meeting id (for meeting prep)")
    p.add_argument("--note")
    p.add_argument("--link")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="planner")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="add an item")
    p.add_argument("title")
    item_args(p, True)

    p = sub.add_parser("update", help="change an item")
    p.add_argument("id")
    p.add_argument("--title")
    item_args(p, False)
    p.add_argument("--subtask", help="add a sub-step")
    p.add_argument("--subtask-done", help="sub-step number to tick off")
    p.add_argument("--log", help="extra text for the log")

    p = sub.add_parser("log", help="record an update ('no change' counts)")
    p.add_argument("id")
    p.add_argument("text")
    p = sub.add_parser("done")
    p.add_argument("ids", nargs="+")
    p.add_argument("--note")
    p = sub.add_parser("drop")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    p = sub.add_parser("chased", help="you sent the follow-up")
    p.add_argument("ids", nargs="+")
    p.add_argument("--note")
    p = sub.add_parser("roll", help="not done today: move it and count a slip")
    p.add_argument("ids", nargs="+")
    p.add_argument("--to")

    p = sub.add_parser("show")
    p.add_argument("id")
    p = sub.add_parser("find")
    p.add_argument("query")
    p.add_argument("--all", action="store_true", help="include done and dropped")
    p = sub.add_parser("list")
    p.add_argument("--project")
    p.add_argument("--company")
    p.add_argument("--person")
    p.add_argument("--status")
    p.add_argument("--type")
    p.add_argument("--all", action="store_true")

    p = sub.add_parser("brief", help="morning brief")
    p.add_argument("--date")
    p.add_argument("--mark", action="store_true", help="record that these were asked about")
    p = sub.add_parser("eod", help="end-of-day check")
    p.add_argument("--date")
    p = sub.add_parser("review", help="weekly review")
    p.add_argument("--week", default="this")
    p = sub.add_parser("plan", help="show or set a week's plan")
    p.add_argument("--week", default="next")
    p.add_argument("--priorities", nargs="*")
    p.add_argument("--notes")
    p = sub.add_parser("views", help="regenerate views/")
    sub.add_parser("validate")
    sub.add_parser("archive")

    p = sub.add_parser("date", help="check how a date is read")
    p.add_argument("expr", nargs="+")
    p.add_argument("--add-working", type=int)

    p = sub.add_parser("meeting")
    msub = p.add_subparsers(dest="mcmd", required=True)
    m = msub.add_parser("add")
    m.add_argument("title")
    m.add_argument("--date", required=True)
    m.add_argument("--time")
    m.add_argument("--company", required=True)
    m.add_argument("--project")
    m = msub.add_parser("list")
    m.add_argument("--week", default="this")
    m = msub.add_parser("rm")
    m.add_argument("id")

    sub.add_parser("projects").add_argument("--all", action="store_true")
    p = sub.add_parser("project")
    p.add_argument("action", choices=["add", "status"])
    p.add_argument("name")
    p.add_argument("--company", default="ml")
    p.add_argument("--group", default="client", choices=["client", "retainer", "internal", "general"])
    p.add_argument("--channel")
    p.add_argument("--partner")
    p.add_argument("--set", choices=["active", "paused"])
    p = sub.add_parser("people")
    p.add_argument("--company")
    p.add_argument("--role")
    p = sub.add_parser("person")
    p.add_argument("action", choices=["add", "update"])
    p.add_argument("name")
    p.add_argument("--company", default="ml")
    p.add_argument("--role", choices=ROLES)
    p.add_argument("--channel")
    p.add_argument("--project", action="append")

    a = ap.parse_args(argv)
    s = Store()
    try:
        out = run(s, a)
    except (PlannerError, ValueError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    if out:
        print(out)
    return 0


def run(s, a):
    c = a.cmd
    if c == "add":
        it = ops.add(s, a.title, type=a.type, project=a.project, company=a.company, due=a.due,
                     planned=a.planned, waiting_on=a.waiting_on, channel=a.channel, priority=a.priority,
                     status=a.status, note=a.note, link=a.link, blocks=a.blocks or (), meeting=a.meeting,
                     followup=a.followup)
        return f"✓ added {render.line(s, it, show_status=True)}" + _chase_note(s, it)
    if c == "update":
        it = ops.update(s, a.id, title=a.title, type=a.type, project=a.project, company=a.company,
                        due=a.due, planned=a.planned, waiting_on=a.waiting_on, channel=a.channel,
                        priority=a.priority, status=a.status, followup=a.followup, blocks=a.blocks,
                        meeting=a.meeting, note=a.note, link=a.link, subtask=a.subtask,
                        subtask_done=a.subtask_done, text=a.log)
        return f"✓ {render.line(s, it, show_status=True)}\n  {it['log'][-1]['text']}" + _chase_note(s, it)
    if c == "log":
        it = ops.log(s, a.id, a.text)
        return f"✓ logged on {render.line(s, it)}"
    if c == "done":
        return "\n".join(f"✓ done: {render.line(s, ops.done(s, i, a.note))}" for i in a.ids)
    if c == "drop":
        return f"✓ dropped: {render.line(s, ops.drop(s, a.id, a.reason))}"
    if c == "chased":
        return "\n".join(f"✓ chased: {render.line(s, it)} · next {dates.fmt(it['next_followup'])}"
                         for it in (ops.chased(s, i, a.note) for i in a.ids))
    if c == "roll":
        return "\n".join(f"↷ {render.line(s, ops.roll(s, i, a.to))}" for i in a.ids)
    if c == "show":
        return render.detail(s, s.item(a.id))
    if c == "find":
        hits = q.find(s, a.query, a.all)
        return "\n".join(f"- {render.line(s, i, show_status=True)}" for i in hits) or "No matches."
    if c == "list":
        items = list(s.items().values()) if a.all else q.open_items(s)
        if a.project:
            pid = s.resolve("project", a.project)
            items = [i for i in items if i.get("project") == pid]
        if a.company:
            cid = s.resolve("company", a.company)
            items = [i for i in items if i["company"] == cid]
        if a.person:
            pid = s.resolve("person", a.person)
            items = [i for i in items if i.get("waiting_on") == pid]
        if a.status:
            items = [i for i in items if i["status"] == a.status]
        if a.type:
            items = [i for i in items if i["type"] == a.type]
        items.sort(key=lambda i: (i["company"], i.get("project") or "", i.get("due") or "9999"))
        return "\n".join(f"- {render.line(s, i, show_status=True)}" for i in items) or "Nothing."
    if c == "brief":
        return render.brief(s, _day(s, a.date), a.mark)
    if c == "eod":
        return render.eod(s, _day(s, a.date))
    if c == "review":
        return render.review(s, dates.resolve_week(a.week, s.today()))
    if c == "plan":
        wid = dates.resolve_week(a.week, s.today())
        if a.priorities is not None or a.notes is not None:
            plan = s.plan(wid) or {"week": wid, "created": dates.stamp(s.now())}
            if a.priorities is not None:
                if len(a.priorities) > 3:
                    raise PlannerError("keep it to 3 priorities")
                plan["priorities"] = a.priorities
            if a.notes is not None:
                plan["notes"] = a.notes
            plan["updated"] = dates.stamp(s.now())
            s.save_plan(wid, plan)
        return render.week_plan(s, wid)
    if c == "views":
        render.write_views(s)
        return "✓ views/THIS_WEEK.md and views/OPEN.md regenerated"
    if c == "validate":
        bad = [(i["id"], e) for i in s.items().values() for e in s.validate_item(i)]
        if bad:
            raise PlannerError("\n".join(f"{i}: {e}" for i, e in bad))
        return f"✓ {len(s.items())} items valid"
    if c == "archive":
        moved = ops.archive(s)
        return f"✓ archived {len(moved)} items" + ("".join(f"\n- {m}" for m in moved))
    if c == "date":
        d = dates.parse(" ".join(a.expr), s.today(), s.cal)
        if a.add_working is not None:
            d = s.cal.add(d, a.add_working)
        return f"{d.isoformat()} ({dates.fmt(d)}) · week {dates.week_id(d)} · today is {dates.fmt(s.today())}"
    if c == "meeting":
        return meeting(s, a)
    if c == "projects":
        out = []
        for co in s.companies:
            ps = [p for p in s.projects if p["company"] == co["id"] and (a.all or p["status"] == "active")]
            out.append(f"**{co['name']}**")
            for p in ps:
                n = len([i for i in q.open_items(s) if i.get("project") == p["id"]])
                bits = [p["group"], s.channel(p["default_channel"])["name"]]
                if p.get("partner"):
                    bits.append(f"via {p['partner'].title()}")
                if p["status"] != "active":
                    bits.append("paused")
                out.append(f"- {p['name']} `{p['id']}` · {' · '.join(bits)} · {n} open")
        return "\n".join(out)
    if c == "project":
        if a.action == "add":
            pid = slug(a.name)
            if s.project(pid):
                raise PlannerError(f"project {pid} exists")
            cid = s.resolve("company", a.company)
            ch = s.resolve("channel", a.channel) if a.channel else (
                "marketlytics-slack" if a.group == "internal" else
                {"ml": "analytics-huddle", "salam": "salam-teams", "iv": "iv-slack"}[cid])
            s.projects.append({"id": pid, "name": a.name, "company": cid, "group": a.group,
                               "status": a.set or "active", "partner": a.partner, "default_channel": ch})
        else:
            p = s.project(s.resolve("project", a.name))
            if not a.set:
                raise PlannerError("use --set active|paused")
            p["status"] = a.set
            pid = p["id"]
        s.save_config("projects")
        p = s.project(pid)
        return f"✓ {p['name']} `{p['id']}` · {p['status']}"
    if c == "people":
        ps = s.people
        if a.company:
            ps = [p for p in ps if p["company"] == s.resolve("company", a.company)]
        if a.role:
            ps = [p for p in ps if p["role"] == a.role]
        return "\n".join(f"- {p['name']} `{p['id']}` · {s.company(p['company'])['name']} · {p['role']} · "
                         f"{s.channel(p['channel'])['name'] if p.get('channel') else 'no channel'}"
                         + (f" · {', '.join(s.project(x)['name'] for x in p['projects'])}" if p.get("projects") else "")
                         for p in ps)
    if c == "person":
        projects = [s.resolve("project", x) for x in a.project or []]
        if a.action == "add":
            pid = slug(a.name)
            if s.person(pid):
                pid = f"{pid}-{secrets.token_hex(1)}"
            cid = s.resolve("company", a.company)
            role = a.role or "client"
            ch = s.resolve("channel", a.channel) if a.channel else (
                s.project(projects[0])["default_channel"] if projects else
                {"ml": "analytics-huddle" if role in ("client", "partner") else "marketlytics-slack",
                 "salam": "salam-teams", "iv": "iv-slack"}[cid])
            s.people.append({"id": pid, "name": a.name, "company": cid, "role": role, "channel": ch, "projects": projects})
        else:
            p = s.person(s.resolve("person", a.name))
            pid = p["id"]
            if a.role:
                p["role"] = a.role
            if a.channel:
                p["channel"] = s.resolve("channel", a.channel)
            p["projects"] = sorted(set(p.get("projects", []) + projects))
        s.save_config("people")
        p = s.person(pid)
        return f"✓ {p['name']} `{p['id']}` · {p['role']} · {s.channel(p['channel'])['name']}"
    raise PlannerError(f"unknown command {c}")


def _day(s, expr):
    return dates.parse(expr, s.today(), s.cal) if expr else s.today()


def _chase_note(s, it):
    if it["status"] == "waiting" and it.get("next_followup"):
        ch = s.channel(it["channel"])["name"] if it.get("channel") else "?"
        return f"\n  next follow-up {dates.fmt(it['next_followup'])} via {ch}"
    return ""


def meeting(s, a):
    if a.mcmd == "add":
        d = dates.parse(a.date, s.today(), s.cal)
        wid = dates.week_id(d)
        ms = s.meetings(wid)
        m = {"id": f"m-{d.strftime('%m%d')}-{secrets.token_hex(2)}", "date": d.isoformat(), "time": a.time,
             "title": a.title, "company": s.resolve("company", a.company),
             "project": s.resolve("project", a.project) if a.project else None}
        ms.append(m)
        s.save_meetings(wid, ms)
        return f"✓ {dates.fmt(d)} {render._meeting_line(s, m)}"
    if a.mcmd == "list":
        wid = dates.resolve_week(a.week, s.today())
        ms = s.meetings(wid)
        return "\n".join(f"- {dates.fmt(m['date'])} {render._meeting_line(s, m)}" for m in ms) or f"No meetings for {wid}."
    if a.mcmd == "rm":
        for path in sorted((s.base / "data" / "meetings").glob("*.json")):
            wid = path.stem
            ms = s.meetings(wid)
            keep = [m for m in ms if m["id"] != a.id]
            if len(keep) != len(ms):
                s.save_meetings(wid, keep)
                return f"✓ removed {a.id}"
        raise PlannerError(f"no meeting {a.id}")


if __name__ == "__main__":
    sys.exit(main())
