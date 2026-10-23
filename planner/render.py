"""Markdown output: briefs, reviews, plans and the views/ files."""

from datetime import timedelta

from . import dates, queries as q
from .store import OPEN_STATUSES, TYPE_LABELS

fmt = dates.fmt
D = dates.to_date
CHANNEL_ORDER = ["analytics-huddle", "marketlytics-slack", "ml-email", "salam-teams", "salam-email", "iv-slack"]


def where(store, item):
    if item.get("project"):
        p = store.project(item["project"])
        c = store.company(p["company"])
        return p["name"] if p["company"] == "ml" else c["name"]
    return f"{store.company(item['company'])['name']} (no project)"


def line(store, item, show_where=True, show_status=False):
    bits = [f"**{item['title']}**"]
    if show_where:
        bits.append(where(store, item))
    if item.get("type") not in ("task",):
        bits.append(TYPE_LABELS[item["type"]].lower())
    if item.get("waiting_on"):
        bits.append(f"waiting on {store.person(item['waiting_on'])['name']}")
    if item.get("due"):
        overdue = D(item["due"]) < store.today() and item["status"] in OPEN_STATUSES
        bits.append(("**OVERDUE** " if overdue else "") + f"due {fmt(item['due'])}")
    if item.get("planned_day"):
        bits.append(f"planned {fmt(item['planned_day'])}")
    if show_status:
        bits.append(item["status"].replace("_", " "))
    if item.get("priority") == "high":
        bits.append("⚑ high")
    open_steps = [s for s in item.get("subtasks", []) if not s["done"]]
    if item.get("subtasks"):
        bits.append(f"{len(item['subtasks']) - len(open_steps)}/{len(item['subtasks'])} steps")
    return " · ".join(bits) + f" `{item['id']}`"


def last_log(item):
    e = item["log"][-1]
    return f"{fmt(e['at'])}: {e['text']}"


def detail(store, item):
    out = [f"## {item['title']}  `{item['id']}`",
           f"- {TYPE_LABELS[item['type']]} · {where(store, item)} · status **{item['status'].replace('_', ' ')}** · priority {item.get('priority', 'normal')}"]
    for label, field in (("Due", "due"), ("Planned", "planned_day"), ("Next follow-up", "next_followup"), ("Closed", "closed")):
        if item.get(field):
            out.append(f"- {label}: {fmt(item[field])}")
    if item.get("waiting_on"):
        ch = store.channel(item["channel"])["name"] if item.get("channel") else "?"
        out.append(f"- Waiting on: {store.person(item['waiting_on'])['name']} via {ch} (chased {q.chase_count(item)}×)")
    if item.get("blocks"):
        out.append("- Blocks: " + ", ".join(f"{store.items()[b]['title']} `{b}`" for b in item["blocks"] if b in store.items()))
    if item.get("slips"):
        out.append(f"- Slipped {len(item['slips'])}×")
    if item.get("subtasks"):
        out.append("- Steps:")
        out += [f"  {n}. [{'x' if s['done'] else ' '}] {s['text']}" for n, s in enumerate(item["subtasks"], 1)]
    if item.get("notes"):
        out.append("- Notes:")
        out += [f"  - {fmt(n['at'])}: {n['text']}" for n in item["notes"]]
    if item.get("links"):
        out.append("- Links: " + " · ".join(item["links"]))
    out.append("- Log:")
    out += [f"  - {e['at'].replace('T', ' ')} — {e['text']}" for e in item["log"]]
    return "\n".join(out)


def _meetings_on(store, day):
    return [m for m in store.meetings(dates.week_id(day)) if m["date"] == day.isoformat()]


def _meeting_line(store, m):
    t = f"{m['time']} " if m.get("time") else ""
    return f"{t}{m['title']} ({store.company(m['company'])['name']}) `{m['id']}`"


def brief(store, day=None, mark=False):
    day = day or store.today()
    n = 0
    out = [f"# Morning brief — {fmt(day)}", ""]
    shown, prompted = set(), []

    def num():
        nonlocal n
        n += 1
        return n

    unans = sorted(q.unanswered(store, day), key=lambda i: i["last_prompted"])
    fups = [i for i in q.followups_due(store, day) if i["id"] not in {u["id"] for u in unans}]
    stale = [i for i in q.stale(store, day) if i["id"] not in {x["id"] for x in unans + fups}]
    due = [i for i in q.due_by(store, day) if i["id"] not in {x["id"] for x in unans + fups}]
    out.append(f"_{len(unans)} unanswered · {_n(len(fups), 'follow-up')} · {len(stale)} need an update · {len(due)} due/overdue_")

    if unans:
        out += ["", "## ⚠ No answer yet — what happened?"]
        for i in unans:
            out.append(f"{num()}. {line(store, i)} — asked {fmt(i['last_prompted'])}, no update since {fmt(i['last_update'])}")
            prompted.append(i)

    if fups:
        out += ["", "## Follow-ups to send"]
        by_ch = {}
        for i in fups:
            by_ch.setdefault(i.get("channel") or "?", []).append(i)
        for ch in sorted(by_ch, key=lambda c: CHANNEL_ORDER.index(c) if c in CHANNEL_ORDER else 99):
            out.append(f"### {store.channel(ch)['name'] if store.channel(ch) else 'Channel not set'}")
            for i in by_ch[ch]:
                who = store.person(i["waiting_on"])["name"]
                k = q.chase_count(i)
                extra = f" · chase #{k + 1}" if k else ""
                need = f" · needed by {fmt(i['due'])}" if i.get("due") else ""
                out.append(f"{num()}. **{who}** — {i['title']} ({where(store, i)}){need}{extra} `{i['id']}`")
                out.append(f"   _Last: {last_log(i)}_")
                prompted.append(i)

    if stale:
        limit = store.settings.get("stale_after_working_days", 10)
        out += ["", f"## Needs an update (nothing logged in {limit}+ working days)"]
        for i in stale:
            out.append(f"{num()}. {line(store, i)} — last update {fmt(i['last_update'])}")
            prompted.append(i)

    if due:
        out += ["", "## Due today & overdue"]
        for i in due:
            out.append(f"{num()}. {line(store, i)}")
    shown = {i["id"] for i in unans + fups + stale + due}

    meetings = _meetings_on(store, day)
    planned = [i for i in q.planned_on(store, day) if i["id"] not in shown]
    if meetings or planned:
        out += ["", "## Today"]
        if meetings:
            out.append("**Meetings**")
            for m in meetings:
                prep = [i for i in q.open_items(store) if i.get("meeting") == m["id"]]
                out.append(f"- {_meeting_line(store, m)}" + ("".join(f"\n  - prep: {line(store, p, False)}" for p in prep)))
        if planned:
            out.append("**Planned**")
            for i in planned:
                out.append(f"{num()}. {line(store, i)}")

    heads = []
    nxt = store.cal.add(day, 1)
    for i in q.due_on(store, nxt):
        heads.append(f"Due {fmt(nxt)}: {line(store, i)}")
    for w, b in q.clashes(store):
        heads.append(f"Clash: **{w['title']}** won't land before **{b['title']}** is due {fmt(b['due'])} `{w['id']}`")
    if not store.plan(dates.week_id(day)):
        heads.append("No plan for this week yet. Run `/plan` for the 10-minute catch-up.")
    if heads:
        out += ["", "## Heads-up"] + [f"- {h}" for h in heads]

    if n == 0 and not meetings and not heads:
        out += ["", "Nothing needs you this morning."]
    if mark:
        from . import ops
        ops.mark_prompted(store, prompted)
    return "\n".join(out)


def eod(store, day=None):
    day = day or store.today()
    n = 0
    out = [f"# End of day — {fmt(day)}"]
    planned = q.planned_on(store, day)
    due = [i for i in q.due_on(store, day) if i not in planned]
    done = q.closed_between(store, day, day, "done")
    if planned:
        out += ["", "## Planned for today — what got done?"]
        for i in planned:
            n += 1
            out.append(f"{n}. {line(store, i)}")
    if due:
        out += ["", "## Due today, still open"]
        for i in due:
            n += 1
            out.append(f"{n}. {line(store, i)}")
    if done:
        out += ["", "## Done today ✓"] + [f"- {line(store, i)}" for i in done]
    if not (planned or due or done):
        out += ["", "Nothing was planned for today."]
    out += ["", "_Anything not done rolls to the next working day unless you say otherwise._"]
    return "\n".join(out)


def _n(count, word):
    return f"{count} {word}{'' if count == 1 else 's'}"


def _week_range(store, wid):
    monday = dates.week_monday(wid)
    days = store.cal.week_days(monday)
    return monday, monday + timedelta(days=6), days


def review(store, wid):
    monday, sunday, days = _week_range(store, wid)
    out = [f"# Week review — {wid} ({fmt(days[0])} – {fmt(days[-1])})"]
    done = q.closed_between(store, monday, sunday, "done")
    out += ["", f"## Done ({len(done)})"]
    for c in store.companies:
        mine = [i for i in done if i["company"] == c["id"]]
        if mine:
            out.append(f"**{c['name']}**")
            out += [f"- {line(store, i, c['id'] == 'ml')}" for i in mine]
    if not done:
        out.append("- Nothing marked done.")
    dropped = q.closed_between(store, monday, sunday, "dropped")
    if dropped:
        out += ["", "## Dropped"] + [f"- {line(store, i)} — {i['log'][-1]['text']}" for i in dropped]
    slipped = [i for i in q.slipped_between(store, monday, sunday) if i["status"] in OPEN_STATUSES]
    if slipped:
        out += ["", "## Slipped"]
        out += [f"- {'⚠ ' if len(i['slips']) >= 2 else ''}{line(store, i)} — slipped {len(i['slips'])}×" for i in slipped]
    waiting = [i for i in q.open_items(store) if i["status"] == "waiting"]
    if waiting:
        out += ["", "## Waiting on others"]
        people = sorted({i["waiting_on"] for i in waiting}, key=lambda p: store.person(p)["name"])
        for p in people:
            out.append(f"**{store.person(p)['name']}**")
            out += [f"- {line(store, i)} · next chase {fmt(i['next_followup'])}" for i in waiting if i["waiting_on"] == p]
    inbox = [i for i in q.open_items(store) if i["status"] == "inbox"]
    out += ["", f"## Inbox ({len(inbox)}) — each needs a project, a day, 'later' or 'drop'"]
    out += [f"- {line(store, i)}" for i in inbox] or ["- Empty ✓"]
    out += ["", "## Open by project"]
    for c in store.companies:
        out.append(f"**{c['name']}**")
        for p in [p for p in store.projects if p["company"] == c["id"]]:
            items = [i for i in q.open_items(store) if i.get("project") == p["id"]]
            if p["status"] != "active" and not items:
                continue
            tag = "" if p["status"] == "active" else " _(paused)_"
            out.append(f"- {p['name']}{tag}: " + (f"{len(items)} open" if items else "nothing open — anything new?"))
    return "\n".join(out)


def week_plan(store, wid):
    monday, sunday, days = _week_range(store, wid)
    plan = store.plan(wid) or {}
    meetings = store.meetings(wid)
    threshold = store.settings.get("overload_threshold_per_day", 8)
    out = [f"# Plan — {wid} ({fmt(days[0])} – {fmt(days[-1])})"]
    out += ["", "## Priorities"]
    out += [f"{n}. {p}" for n, p in enumerate(plan.get("priorities", []), 1)] or ["- Not set yet"]
    out += ["", "## Day by day"]
    for d in days:
        ms = [m for m in meetings if m["date"] == d.isoformat()]
        work = q.planned_on(store, d)
        chase = [i for i in q.open_items(store) if i["status"] == "waiting" and i.get("next_followup") == d.isoformat()]
        due = [i for i in q.due_on(store, d) if i not in work and i not in chase]
        load = len(ms) + len(work)
        flag = " ⚠ overloaded" if load > threshold else ""
        out.append(f"### {fmt(d)} — {_n(len(ms), 'meeting')} · {_n(len(work), 'item')}{flag}")
        out += [f"- 📅 {_meeting_line(store, m)}" for m in ms]
        out += [f"- {line(store, i)}" for i in work]
        out += [f"- ⏰ due: {line(store, i)}" for i in due]
        out += [f"- ↩ chase {store.person(i['waiting_on'])['name']}: {i['title']} `{i['id']}`" for i in chase]
        if not (ms or work or due or chase):
            out.append("- Free")
    unscheduled = [i for i in q.due_between(store, monday, sunday)
                   if i["status"] != "waiting" and not (i.get("planned_day") and days[0] <= D(i["planned_day"]) <= D(i["due"]))]
    if unscheduled:
        out += ["", "## Due this week but not scheduled before the due date"] + [f"- {line(store, i)}" for i in unscheduled]
    if plan.get("notes"):
        out += ["", "## Notes", plan["notes"]]
    return "\n".join(out)


def open_view(store):
    out = ["# Open items", "", f"_Generated {fmt(store.today())} by the planner. Don't edit — ask Claude instead._"]
    for c in store.companies:
        items = [i for i in q.open_items(store) if i["company"] == c["id"]]
        out += ["", f"## {c['name']} ({len(items)})"]
        for p in [p for p in store.projects if p["company"] == c["id"]] + [None]:
            mine = [i for i in items if i.get("project") == (p["id"] if p else None)]
            if not mine:
                continue
            out.append(f"### {p['name'] if p else 'No project yet'}")
            out += [f"- {line(store, i, False, True)}" for i in sorted(mine, key=lambda i: (i.get('due') or '9999', i['title']))]
    return "\n".join(out) + "\n"


def write_views(store):
    views = store.base / "views"
    views.mkdir(exist_ok=True)
    today = store.today()
    this = dates.week_id(today)
    body = [week_plan(store, this)]
    nxt = dates.week_id(today + timedelta(days=7))
    if today.weekday() >= 4 and store.plan(nxt):
        body.append(week_plan(store, nxt))
    head = f"_Generated {fmt(today)} by the planner. Don't edit — ask Claude instead._\n\n"
    (views / "THIS_WEEK.md").write_text(head + "\n\n---\n\n".join(body) + "\n", encoding="utf-8")
    (views / "OPEN.md").write_text(open_view(store), encoding="utf-8")
