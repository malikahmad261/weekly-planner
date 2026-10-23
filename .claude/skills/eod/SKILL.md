---
name: eod
description: End-of-day check at 17:00 Mon–Fri. Asks what got done from today's plan and rolls the rest forward. Use when the scheduled task fires or the user says they're wrapping up.
---

# End-of-day check

Keep this to about 30 seconds of the user's time.

1. Run `scripts/sync.sh start`, then `python3 -m planner eod`.
2. Show the list and ask: *"What got done? Anything not listed is rolled to tomorrow. Anything new to capture?"*
3. When the user replies:
   - Mark done items with `done`.
   - Roll the unfinished items with `roll ID…` (to the next working day by default, or `--to` if they name a day).
   - Capture anything new they mention, following the adding rules in `CLAUDE.md`.
   - Save with `scripts/sync.sh "End of day <date>"`.
4. Confirm in one short block. If any item has now slipped 2+ times, ask whether it should be re-planned, broken into steps or dropped.

If the user doesn't reply, do nothing. Tomorrow's brief still shows the open
items, and Friday's review shows what slipped.

If the list is empty, just ask: *"Anything to capture before you log off?"*
