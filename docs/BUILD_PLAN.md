# Weekly Planner — Build Plan (v1.0)

> Builds what [SCOPE.md](SCOPE.md) describes. **Status: Phases 0–3 built.**
> Phase 4 (scheduled tasks) is set up once the code is merged into `main`.

---

## 1. How it works

```
 You (Claude app on phone / web)
        │  chat
        ▼
 Claude Code session ──runs──► planner CLI (Python) ──reads/writes──► data/ (JSON files)
        ▲                                                                 │
        │ starts a session + push notification                            │ git commit + push
 Scheduled tasks (Asia/Karachi)                                           ▼
   • Morning brief   Mon–Fri 10:00                                  GitHub repo (main)
   • End of day      Mon–Fri 17:00
   • Friday planning Fri     12:00
```

- **The repo is the database.** Every change Claude makes is committed and pushed to `main` straight away, so every session (phone, web, scheduled) sees the same data. The commit history doubles as a full audit trail.
- **A small CLI does the date maths and queries.** Questions like "which follow-ups are due today?", "what's stale?" and "what's 3 working days from Thursday?" are answered by code, not by Claude estimating. Claude handles the conversation, and the CLI does the bookkeeping.
- **`CLAUDE.md` holds the rules.** It's the instruction sheet each session reads: how to capture, ask, update, draft follow-ups and commit.
- **Each routine is a skill** (`/brief`, `/eod`, `/plan`). Scheduled tasks call them, and you can also run them yourself anytime.

### Why these choices

| Choice | Reason |
|---|---|
| JSON files in git, no database | Nothing to host or pay for. Works from any Claude Code session. Readable on GitHub mobile. |
| One file per item | Two sessions open at once (for example the morning brief and a quick capture) rarely touch the same file, so git merges stay clean. |
| Python, standard library only | Already installed in Claude Code cloud sessions. No setup script, no dependencies. |
| Generated Markdown views | `views/THIS_WEEK.md` and `views/OPEN.md` can be read on GitHub without opening Claude. |

---

## 2. Repository layout

```
weekly-planner/
├── CLAUDE.md                  # Conversation rules for Claude
├── README.md                  # How to use it from your phone
├── config/
│   ├── settings.json          # timezone, working days, cadences, stale threshold, overload threshold
│   ├── companies.json         # IV, Salam, MarketLytics
│   ├── channels.json          # Analytics Huddle, MarketLytics Slack, ML email, Salam Teams/email, IV Slack
│   ├── projects.json          # one entry per project; status active/paused; default channel
│   ├── people.json            # team + client contacts, role, default channel
│   └── holidays.json          # optional non-working dates (skipped in working-day maths)
├── data/
│   ├── items/<id>.json        # one file per task / deliverable / follow-up / meeting prep
│   ├── meetings/<week>.json   # meetings, pasted in on Friday
│   ├── plans/<week>.json      # the week's priorities (e.g. 2026-W44.json)
│   └── archive/               # closed items older than 8 weeks
├── views/                     # generated, never hand-edited
│   ├── THIS_WEEK.md
│   └── OPEN.md
├── planner/                   # the CLI: python3 -m planner
│   ├── __main__.py            # commands
│   ├── store.py               # load/save/validate, name matching, follow-up rules
│   ├── dates.py               # working days, "next wed" → date
│   ├── ops.py                 # add / update / log / done / drop / chased / roll / archive
│   ├── queries.py             # due, follow-ups due, unanswered, stale, clashes, find
│   └── render.py              # brief / EOD / review / plan / views
├── scripts/sync.sh            # pull before, validate + commit + push to main after
├── tests/
└── .claude/skills/
    ├── brief/SKILL.md
    ├── eod/SKILL.md
    └── plan/SKILL.md
```

### 2.1 An item file

```json
{
  "id": "ml-rvshare-0007",
  "title": "Get Q4 numbers from Saad",
  "type": "followup",
  "company": "marketlytics",
  "project": "rvshare",
  "status": "waiting",
  "waiting_on": "saad",
  "channel": "marketlytics-slack",
  "due": "2026-10-28",
  "planned_day": null,
  "next_followup": "2026-10-27",
  "priority": "normal",
  "blocks": ["ml-rvshare-0006"],
  "notes": [],
  "links": [],
  "subtasks": [],
  "log": [
    {"at": "2026-10-23T11:02+05:00", "text": "Created: waiting on Saad for Q4 numbers"},
    {"at": "2026-10-26T10:14+05:00", "text": "Prompted in morning brief"}
  ],
  "last_update": "2026-10-23",
  "last_prompted": "2026-10-26"
}
```

The CLI uses `last_prompted` and `last_update` to find **"prompted but no answer yet"** (SCOPE §5.3) and **"stale"** (SCOPE §5.4).

---

## 3. Seed data

### Companies and channels

| Company | Channels |
|---|---|
| Inspiring Vacations | IV's own Slack |
| Salam | Teams (default) · Email |
| MarketLytics | **MarketLytics** Slack (internal team) · **Analytics Huddle** Slack (clients) · Email (Austell) |

### MarketLytics team (default channel: MarketLytics Slack)
Talha, Maria, Moattar, Motabar, Saad, Ahmed, Shiza, Zuhaid, Awais, Abbas,
Hamza, Farhan, Omair, Umar, Naveen, Nabeeha, Hussain, Adam, Tazeen, Hasnain,
Sarim.

### MarketLytics projects

| Status | Client | Internal |
|---|---|---|
| **Active** | Destify · Fenix Monthly Analytics Retainer · RVShare · Wiideman - Retainer · IQAir.com · Mr. Manhole by Ted · GeoTrek by Ted (Retainer) · Zenith Design by Ted · Austell (email) · VanWorks by Ted · PuroAir | Internal Products · Sales · Expansion · Growth · People Ops |
| **Paused** | Shamaazi · GenderGP · INE · ARM · Stipop · Campbowwow · Honey Creek Resort · Alludo · Boardroom · Sirius XM · Hollywood Mirrors · Nova Urology by Ted · Wiideman - AI · KIPP - Fenton · Sendwave Compliance - Adhoc · Zepz - AutoRek Recon | |

"By Ted" projects are tagged with Ted as the partner, but each one has its own
client contact. Client contacts start empty. The first time you mention one
(*"waiting on Jake at RVShare"*), Claude adds them with the project's channel.

## 4. Phases

Each phase ends with something you can try from your phone.

### Phase 0 — Repo and seed data
- Create the repo structure, `settings.json` with your decisions, and seed companies, projects and people.
- **Done when:** you can ask *"list my MarketLytics projects"* and *"who's on the team?"* and get correct answers.

### Phase 1 — The planner CLI
- `add`, `update`, `log`, `done`, `drop`, `find` (fuzzy match on title, project or person)
- Date parsing (*"Wed"*, *"end of week"*, *"next Monday"*), working-day maths that skips weekends and holidays, follow-up cadences (team 2, client 3, 1 day before a hard due date), stale after 10 working days
- Queries: `due`, `overdue`, `followups-due`, `unanswered`, `stale`, `open --project X`, `waiting --person X`
- `render brief | eod | review | views`
- Validation on every write, so a bad edit can't corrupt the data
- Unit tests for the date maths and queries, since these decide what lands in your brief
- **Done when:** the tests pass, and a sample dataset produces a correct morning brief.

### Phase 2 — Conversation rules (`CLAUDE.md`)
- Capture (SCOPE §3): parse, split, ask only what's missing, Inbox as the fallback, one-line confirmation, bulk "pull out the action items" from pasted Slack, email or notes.
- Updates and details (SCOPE §4): status changes, slips, notes and links, sub-steps, "no change", disambiguation when it's unclear which item you mean.
- Handoffs automatically create a follow-up with the right person, channel and date.
- Draft follow-up messages in your tone: short, friendly, Slack-style for Slack and slightly more formal for email.
- After every change: run the CLI, regenerate views, then commit and push to `main`.
- **Done when:** a 10-message test conversation (add, handoff, update, slip, drop, query) leaves the data exactly right.

### Phase 3 — Routines as skills
- `/brief` (SCOPE §6): follow-ups grouped by channel with drafts, missing updates, due and overdue, today's plan, heads-up. Takes your one-line batch reply and applies it.
- `/eod`: shows today's plan, asks what got done, rolls the rest forward and logs slips.
- `/plan` (SCOPE §7): the 8-step Friday flow, ending in `data/plans/<week>.json` and `views/THIS_WEEK.md`. Includes the shorter 10-minute catch-up version for a missed Friday.
- **Done when:** each skill runs end to end on sample data.

### Phase 4 — Scheduling and notifications
Three scheduled tasks in `Asia/Karachi`. Each one opens a fresh Claude Code session on the repo and sends you a push notification. You reply in that session.

| Task | Schedule | Runs |
|---|---|---|
| Morning brief | Mon–Fri 10:00 | `/brief` (and on Mon–Tue it says if last week's plan is missing) |
| End of day | Mon–Fri 17:00 | `/eod` |
| Friday planning | Fri 12:00 | `/plan` |

> Note: scheduled tasks set on the exact hour can be delayed by server load.
> I'll set them a few minutes early (for example 9:47) unless you want them on
> the hour.

- **Done when:** all three have fired at least once and their notifications reached your phone.

### Phase 5 — One-week pilot
- Use it for one real week, starting with a Friday plan.
- On the following Friday, tune the cadences, brief length, draft tone and anything that felt like friction.

---

## 5. Risks and how they're handled

| Risk | Mitigation |
|---|---|
| Two sessions edit at once | One file per item. Pull before every write, then push. On a conflict Claude re-reads and reapplies the change. |
| Claude misreads an item or a date | One-line confirmation after every change. Everything is in git, so any change can be undone. |
| You ignore a brief | Unanswered items get louder each day (SCOPE §5.3) and the Friday review lists them. |
| A scheduled task doesn't fire | The next brief notices the gap (for example "no EOD logged yesterday") and catches up. |
| The repo grows | Done or dropped items older than 8 weeks move to `data/archive/` during Friday planning. |

---

## 6. Status

| Phase | Status |
|---|---|
| 0 — Repo and seed data | ✅ Built |
| 1 — Planner CLI | ✅ Built, 23 tests passing |
| 2 — Conversation rules | ✅ `CLAUDE.md` |
| 3 — Routines | ✅ `/brief`, `/eod`, `/plan` |
| 4 — Scheduling | ⏳ After the code is merged into `main` |
| 5 — Pilot week | ⏳ Starts with the first Friday plan |
