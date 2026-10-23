---
name: brief
description: Morning brief. Follow-ups to send (with drafts), updates the user owes, what's due, today's plan. Runs at 10:00 Mon–Fri from a scheduled task, or whenever the user asks for their brief.
---

# Morning brief

1. Run `scripts/sync.sh start`.
2. Run `python3 -m planner brief --mark`. `--mark` records that you asked about these items, so tomorrow's brief can flag the ones the user doesn't answer. Use `--mark` only once per day. If the user asks to see the brief again, run it without `--mark`.
3. Run `scripts/sync.sh "Morning brief <date>"` to save the marks.
4. Show the brief, keeping its numbering, and make these changes:
   - Under each follow-up, add a **draft message** in a quote block, using the drafting rules in `CLAUDE.md`. Use `show ID` if you need more context.
   - Turn each item under **⚠ No answer yet** and **Needs an update** into a direct one-line question (*"Saad / Q4 numbers: did they arrive?"*).
   - Keep everything else as the CLI printed it. Don't pad it out.
5. End with one line: *"Reply by number, e.g. '1, 2 sent · 3: Thursday · 5 drop'."*
6. When the user replies, apply every part of the reply (`chased`, `log`, `update`, `done`, `drop`), save once with `scripts/sync.sh`, then confirm with one line per item.

If the brief says *"Nothing needs you this morning"*, say so in one line and
mention today's meetings, if there are any.

When this runs from the scheduled task, the user may reply hours later. Run
`scripts/sync.sh start` again before applying their reply.
