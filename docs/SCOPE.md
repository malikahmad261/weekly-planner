# Weekly Planner — Scope & Process Flows (v0.1, draft for review)

> Status: **Approved (v1.0).** Your decisions are recorded in
> [Section 9](#9-decisions). The build plan is in [BUILD_PLAN.md](BUILD_PLAN.md).

---

## 1. Goal

One place to hold every task, deliverable and follow-up across your three
companies, with **Claude chat as the only interface**. You talk to Claude to
add and update things, and Claude makes sure nothing is forgotten:

- **Every Friday:** Claude walks you through planning next week.
- **Every morning:** Claude tells you which follow-ups to send today, drafts them for you, and asks for updates you haven't given.
- **Anytime:** you tell Claude about a new task, an update or a detail in plain language, and it files it.

### Out of scope for v1
- Integrations with Google Calendar, Notion Calendar, Slack or email. Claude does not read or send anything there. You paste in or describe what matters.
- Claude sending messages for you. It drafts them and you send them.
- Other users. This is a personal system; your team never sees it.
- A visual app. A read-only view can come later if chat isn't enough.

---

## 2. The structure Claude keeps track of

```
Company ──< Project ──< Item ──< Update log
                         │
                         └── Person (owner / waiting on)
```

| Company | Projects | Shape of the work |
|---|---|---|
| **Inspiring Vacations** | 1 (general) | One weekly recurring meeting, very few tasks |
| **Salam** | 1 (general), more if needed | Many meetings, few tasks |
| **MarketLytics** | 27 client projects + 5 internal workstreams (16 active right now) | Some meetings, heavy client and team communication over 2 Slack workspaces and email |

**People** are stored once and reused: name, company, role (team member or
client), and their usual channel (**Analytics Huddle** Slack for clients,
**MarketLytics** Slack for the internal team, email, **Teams** for Salam,
or **IV's own Slack**). This lets Claude say
*"Message Ali on Analytics Huddle"*
without you having to repeat it.

**Meetings** are tagged by company, not by calendar. So the Inspiring Vacations
meeting that sits on your Salam calendar is still counted as Inspiring
Vacations.

### 2.1 An item

Everything you track is an **item**. Each item has a type:

| Type | Meaning | Example |
|---|---|---|
| **Task** | Something you do | "Review Q4 media plan" |
| **Deliverable** | Something due to someone outside, by a date | "Send Acme the revised proposal by Wed" |
| **Follow-up** | Something you're waiting on from someone else | "Waiting on Sara for the creatives" |
| **Meeting prep** | Something tied to a specific meeting | "Prepare agenda for Salam ops sync" |

| Field | Required? | Notes |
|---|---|---|
| Title | Yes | |
| Company / project | Yes | Claude guesses from context and asks only if unsure |
| Type | Yes | Claude infers it |
| Due date | Deliverables: yes. Others: optional | "Wed", "end of week" and "before the Acme call" all work |
| Planned day | Set during Friday planning | The day you intend to work on it, separate from the due date |
| Owner / waiting on | Follow-ups: yes | A person from the People list |
| Channel | Follow-ups | Defaults to that person's usual channel |
| Next follow-up date | Follow-ups | Set automatically from the cadence (see §5) |
| Priority | Optional | High / normal. Kept simple on purpose |
| Status | Yes | See §2.2 |
| Notes, links, sub-steps | Optional | Added anytime |
| Update log | Automatic | Every change, with the date, in plain English |
| Last updated | Automatic | Used to find stale items |

### 2.2 Status lifecycle

```
Inbox ──► Planned ──► In progress ──► Done
                 │          │
                 │          └──► Waiting on (someone) ──► back to In progress / Done
                 └──────────────────────────────────────► Dropped (with a reason)
```

- **Inbox:** captured, but missing something or not planned yet. Friday planning empties it.
- **Waiting on:** the ball is in someone else's court. Each item in this state always has a next follow-up date.
- Nothing is deleted. Done and Dropped items stay in the log for the weekly review.

---

## 3. Flow A — Adding a task or deliverable (anytime)

1. **You say it in plain language.**
   *"Acme wants the revised proposal by Wednesday, and I need Sara's numbers first."*
2. **Claude parses it** into one or more items. In this case:
   - Deliverable: *Send revised proposal to Acme*, MarketLytics / Acme, due Wed.
   - Follow-up: *Get numbers from Sara*, waiting on Sara, needed by Mon, linked to the deliverable.
3. **Claude asks only about what's missing or ambiguous**, in one short message (*"Is this the Acme SEO project or Acme Ads?"*). If you don't answer, the item goes to **Inbox** rather than being lost.
4. **Claude confirms back in one line per item** so you can correct it straight away.
5. **Bulk add:** paste a list, Slack thread, email or meeting notes and say *"pull out the action items."* Claude lists what it found and you confirm before anything is saved.

---

## 4. Flow B — Updating and adding details (anytime)

| You say | Claude does |
|---|---|
| "Acme proposal sent" | Marks it Done, logs the date |
| "Sara says she'll have the numbers Thursday" | Logs the update, moves the follow-up date to Thursday, warns you that this now clashes with the Wednesday deliverable |
| "Push the media plan review to next week" | Changes the planned day, logs that it slipped |
| "Add to Acme proposal: use the v3 pricing sheet, link …" | Adds the note or link to the item |
| "Drop the Beta audit, client paused it" | Marks it Dropped with that reason |
| "What's open on Acme?" / "What am I waiting on from Sara?" | Answers from the data |
| "Break the website launch into steps" | Proposes sub-steps for you to confirm |

**Rules:**
- Every change is written to the item's **update log** with the date, so the history is always visible.
- If Claude can't tell which item you mean, it shows the 2–3 closest matches and asks you to pick one.
- Saying *"no change"* or *"still waiting"* is a valid update. It resets the stale timer (see §5).

---

## 5. Flow C — Follow-ups and the "get an update" loop

Follow-ups are the core of the system.

### 5.1 How a follow-up is created
- Automatically, when you hand something off (*"asked Bilal to fix the tracking"*) or when you're waiting on something (*"waiting on client approval"*).
- Manually, by asking (*"remind me to chase Acme on Thursday"*).

### 5.2 Default cadence (adjustable per item or per person)

| Waiting on | First follow-up | Then every |
|---|---|---|
| Internal team member | 2 working days | 2 working days |
| Client | 3 working days | 3 working days |
| Has a hard due date | 1 working day before the due date, whichever comes first | Daily once overdue |

### 5.3 The loop

```
Follow-up is due
     │
     ▼
Morning brief: "Chase Sara for the Acme numbers" + draft message
     │
     ├── You reply with an update ("Sara sent them") ───► Done, or next date set
     │
     ├── You reply "sent the chaser" ───► Next follow-up date set by cadence
     │
     └── You say nothing ───► Next morning it's marked
                              "⚠ No update since <date> — what happened?"
                              It stays at the top until you answer.
```

### 5.4 Stale items
Any open item with **no update for 10 working days** (adjustable) gets flagged
in the morning brief as *"needs an update"*, even if it isn't a follow-up. This
covers tasks that quietly stall.

---

## 6. Flow D — The morning brief (every working day)

Claude sends this at **10:00 Pakistan time, Monday to Friday**. It's kept short enough to
read in two minutes.

1. **⚠ No answer yet.** Items Claude asked about in an earlier brief that you haven't updated. These stay at the top until you answer (§5.3).
2. **Follow-ups to send today.** Grouped by channel (Analytics Huddle, MarketLytics Slack, Email, Teams, IV Slack) so you can work through one app at a time. Each one has a **draft message** you can copy.
3. **Needs an update.** Stale items (§5.4), phrased as direct questions you can answer in one line each.
4. **Due today and overdue.** Deliverables first.
5. **Today.** Meetings and their prep, plus what the Friday plan put on today.
6. **Heads-up.** Anything due tomorrow, clashes (a follow-up that lands after the deliverable it blocks), and a missing weekly plan.

Then you reply in one message (*"1, 2, 4 sent. Sara: Thursday. Beta: drop it"*)
and Claude applies all of it.

**End-of-day check at 17:00, Monday to Friday:** a 30-second close-out. *"Here's
what was planned today. What got done?"* Anything not done rolls forward
automatically.

---

## 7. Flow E — Friday weekly planning

Takes about 20–30 minutes. Claude leads it step by step and you answer.

1. **Review this week.**
   Claude shows what got done, what slipped (and how many times), and what's still waiting on others, grouped by company.
2. **Empty the inbox.**
   Every Inbox item gets a project, a type and either a planned day, *"later"* or *"drop."*
3. **Load next week's meetings.**
   You paste or list next week's meetings from Notion Calendar. Claude tags each one by company and asks: *"Does any of these need prep or a follow-up afterwards?"*
4. **Go through each company, smallest first.**
   - Inspiring Vacations: weekly meeting prep and any open items (about 1 minute).
   - Salam: meeting prep and the few tasks.
   - MarketLytics: each client project in turn. *"What's due? What are you waiting on? Anything new from Slack or email this week?"*
5. **Set the week's priorities.**
   Up to 3 top outcomes for the week, across all companies.
6. **Assign work to days.**
   Claude proposes a day-by-day plan that puts less work on meeting-heavy days and puts deliverables before their due dates. You adjust it.
7. **Schedule follow-ups.**
   Claude lists every Waiting-on item with its next follow-up date for the week.
8. **Output: the weekly plan.**
   One summary covering top 3 priorities, the day-by-day plan, deliverables due and follow-ups by day. It's saved and used by every morning brief.

If you miss Friday, Claude reminds you on Saturday or Monday morning and offers a
shorter 10-minute version.

---

## 8. Alerts Claude raises

| Alert | When | Where |
|---|---|---|
| Follow-up due | On the date | Morning brief §1 |
| No answer to a follow-up prompt | Next working day, then daily | Morning brief §2, at the top |
| Stale item | 10 working days without an update | Morning brief §2 |
| Deliverable due tomorrow / today / overdue | As it happens | Morning brief §3 and §5 |
| Item slipped 2+ times | During Friday review | Friday step 1 |
| Overloaded day | A day with too much planned for its meeting load | Friday step 6 |
| Weekly planning reminder | Friday 12:00 | Its own session |
| Weekly planning not done | Next working morning | Top of the morning brief |

---

## 9. Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Where Claude runs | **Claude Code (web + mobile app).** Data lives in a GitHub repo; scheduled tasks start the briefs and send a push notification. |
| 2 | Morning brief | **10:00 Asia/Karachi, Mon–Fri** |
| 3 | Friday planning reminder | **12:00 Asia/Karachi, Friday** |
| 4 | Follow-up cadence | Defaults in §5.2 kept. **Stale threshold: 10 working days.** |
| 5 | End-of-day check | **Yes, 17:00 Asia/Karachi, Mon–Fri** |
| 6 | Slack workspaces | **Analytics Huddle** = clients · **MarketLytics** = internal team |
| 7 | Team and projects | Seeded from your lists (see BUILD_PLAN.md §3). Client contacts are added the first time you mention them. |
| 8 | Repo | **New repository**, `weekly-planner` (private) |
| 9 | "by Ted" projects | Ted is a partner. Each project has its own client contact. |
| 10 | Active projects | 16 active (11 client + 5 internal). The other 16 are *paused*. |
| 11 | Other channels | Austell uses email. Salam uses Teams and email. Inspiring Vacations has its own Slack. |
