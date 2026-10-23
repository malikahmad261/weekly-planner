---
name: plan
description: Friday weekly planning, about 20–30 minutes, led step by step. Runs from the Friday 12:00 scheduled task, or when the user asks to plan the week. Also has a 10-minute catch-up version if Friday was missed.
---

# Weekly planning

Lead it one step at a time. Ask, wait for the answer, apply it, then move on.
Save with `scripts/sync.sh` after each step, so nothing is lost if the user
stops halfway.

Start with `scripts/sync.sh start`. The week being planned is `next` when it's
Friday to Sunday, and `this` when it's Monday to Thursday (catch-up).

## Full version (Friday)

1. **Review this week.** Run `python3 -m planner review --week this` and show it in summary: wins first, then what slipped (call out ⚠ items that slipped 2+ times) and what's waiting on others. Ask if anything there needs a decision.
2. **Empty the inbox.** For each Inbox item, ask for a project (if it's missing), the type, and either a planned day, "later" (keep it, no day yet: set a project and status `planned` without a day) or "drop". Batch the questions: list them numbered and let the user answer in one message.
3. **Load next week's meetings.** Ask the user to paste next week's meetings from Notion Calendar (any format is fine). Add each one with `meeting add`, tagged by company. The Inspiring Vacations weekly meeting sits on the Salam calendar but belongs to **iv**. Then ask: *"Do any of these need prep or a follow-up afterwards?"* and add `prep` items with `--meeting ID`.
4. **Go through each company, smallest first.**
   - **Inspiring Vacations:** meeting prep and any open items. About a minute.
   - **Salam:** meeting prep and the few tasks.
   - **MarketLytics:** each **active** project in turn (`projects`, then `list --project X`). For each, ask: *"What's due? What are you waiting on? Anything new from Slack or email this week?"* Keep it brisk. Skip a project with *"nothing new"*. Ask once at the end whether any paused project has woken up, or any active one has gone quiet.
5. **Set priorities.** Ask for up to 3 outcomes for the week, then run `plan --week next --priorities "…" "…" "…"`.
6. **Assign days.** Propose a day for each open item that doesn't have one, using `update --planned`:
   - Put deliverables before their due date, leaving a buffer day where possible.
   - Put less on meeting-heavy days (count meetings from step 3).
   - Spread work across Mon–Fri. Put high-priority items early in the week.

   Show `plan --week next` and let the user adjust it. Fix any day marked ⚠ overloaded, and anything listed under *"Due this week but not scheduled"*.
7. **Follow-ups.** The plan already lists each chase under its day (↩). Ask if any should move, or if anything new is being waited on.
8. **Wrap up.** Run `archive` (this moves old closed items out of the way), then save with `scripts/sync.sh "Weekly plan <week>"`. Show the final `plan --week next` and tell the user it's also in `views/THIS_WEEK.md`.

## Catch-up version (missed Friday, about 10 minutes)

Plan the current week:
1. Do step 2 (inbox).
2. Do step 3, but only for meetings that are still ahead.
3. Do step 5 (priorities).
4. Do step 6 (days).

Skip the review and the project-by-project walkthrough.

## If the user isn't available at 12:00

The scheduled task opens this session with step 1 ready. If the user answers
later, carry on from wherever they pick up. If they say "later", reply with one
line saying you'll be here. The Monday brief flags a missing plan anyway.
