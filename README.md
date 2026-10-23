# Weekly Planner

One place for every task, deliverable and follow-up across Inspiring Vacations,
Salam and MarketLytics. **You manage it by chatting with Claude** in the Claude
app (phone or web), in Claude Code sessions on this repo.

📄 [Scope](docs/SCOPE.md) · 🛠️ [Build plan](docs/BUILD_PLAN.md) · 📅 [This week](views/THIS_WEEK.md) · 📋 [All open items](views/OPEN.md)

## What happens on its own (Pakistan time)

| When | What |
|---|---|
| Mon–Fri 10:00 | **Morning brief:** follow-ups to send (with drafts), updates Claude is waiting on, what's due, today's meetings and plan |
| Mon–Fri 17:00 | **End of day:** what got done? The rest rolls to tomorrow |
| Fri 12:00 | **Weekly planning:** review, empty the inbox, next week's meetings, priorities, a day-by-day plan |

Each one opens a new Claude Code session and sends a notification to your
phone. Reply in that session. Number replies work: *"1, 2 sent · 3: Thursday ·
5 drop"*.

## Anytime

Open a Claude Code session on this repo and just say it:

- *"RVShare wants the revised proposal by Wed, I need Saad's numbers first"*
- *"Asked Awais to fix the GeoTrek tracking"* (this creates a follow-up and reminds you to chase him)
- *"Saad says Thursday"* · *"proposal sent"* · *"push the audit to next week"* · *"drop Beta, client paused"*
- *"What's open on Destify?"* · *"What am I waiting on from Maria?"*
- Paste a Slack thread or an email: *"pull out the action items"*
- `/brief`, `/eod` or `/plan` runs a routine on demand

## Rules it follows

- Follow-ups: team every **2** working days, clients every **3**, one working day before a hard due date, and daily once it's overdue.
- If you're asked about something and don't answer, it's flagged **⚠ No answer yet** at the top of the next brief until you do.
- Anything with no update for **10 working days** is flagged as needing an update.
- Settings are in `config/settings.json`. Ask Claude to change them.

## For Claude / developers

Conversation rules are in [`CLAUDE.md`](CLAUDE.md). The CLI is `python3 -m planner --help`
(Python 3.9+, standard library only). Tests: `python3 -m unittest`.
