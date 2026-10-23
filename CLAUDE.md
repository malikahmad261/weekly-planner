# Weekly Planner: instructions for Claude

This repo is the user's personal planner. **You are its only interface.** The
user talks to you in plain language, from the Claude app on their phone or the
web. You turn what they say into changes made with the `planner` CLI, then
save. Full design: `docs/SCOPE.md`.

The user works across three companies (Pakistan time, Mon–Fri):
- **Inspiring Vacations (iv):** one weekly meeting, very few tasks. Comms on IV's own Slack.
- **Salam:** many meetings, few tasks. Comms on Teams and email.
- **MarketLytics (ml):** the bulk of the work. Active client projects plus internal workstreams. The internal team is on **MarketLytics** Slack, clients are on **Analytics Huddle** Slack, and Austell is on email. "by Ted" projects come through a partner, Ted, but each has its own client contact.

## Every session

1. Run `scripts/sync.sh start` before reading or changing anything.
2. After every change (or a batch of changes from one message), run `scripts/sync.sh "<short message>"`. This validates, regenerates `views/`, commits and **pushes straight to `main`**. The user has authorised data commits on `main` for this repo; don't open PRs for data. Code changes (anything in `planner/`, `tests/`, `scripts/`, `.claude/`, this file) still go on a branch with a PR.
3. If sync reports a conflict, run `scripts/sync.sh start`, re-apply the change and save again. Never hand-edit files in `data/` or `views/`; always use the CLI.

## The CLI

Run `python3 -m planner <command>`. Output is Markdown, which you can show as-is or trim.

| Need | Command |
|---|---|
| Add | `add "title" --type task\|deliverable\|followup\|prep --project X [--due D] [--planned D] [--waiting-on P] [--priority high] [--blocks ID…] [--note …] [--link …]` |
| Change | `update ID [--title] [--due D\|none] [--planned D] [--waiting-on P\|none] [--status S] [--followup D] [--note] [--link] [--subtask "…"] [--subtask-done N] [--log "…"]` |
| Plain update | `log ID "Saad says Thursday"`. "No change" counts and resets the stale timer. |
| Close | `done ID…`, `drop ID --reason "…"` |
| Follow-up sent | `chased ID… [--note]` schedules the next chase by cadence |
| Not done today | `roll ID… [--to D]` moves it and counts a slip |
| Look up | `find "words"`, `show ID`, `list [--project] [--person] [--status] [--type]` |
| Routines | `brief [--mark]`, `eod`, `review --week this`, `plan --week next [--priorities "a" "b" "c"]` |
| Meetings | `meeting add "title" --date D --time HH:MM --company C [--project P]`, `meeting list --week next`, `meeting rm ID` |
| Reference | `projects [--all]`, `project status NAME --set active\|paused`, `project add NAME …`, `people`, `person add NAME --role client --project P [--channel C]` |
| Dates | `date "next wed"` shows how a date will be read |

Dates accept: `today`, `tomorrow`, `wed` (the next Wednesday after today),
`this fri`, `next mon`, `eow`, `next week`, `eom`, `+3wd`, `in 2 days`,
`28 oct`, `28/10` (day/month), or ISO. Projects and people accept partial names
(`geotrek`, `manhole`, `moattar`).

## Adding things (SCOPE §3)

- Parse what the user says into one or more items. *"Acme wants the proposal by Wed and I need Saad's numbers first"* becomes a **deliverable** due Wed, plus a **follow-up** waiting on Saad that `--blocks` the deliverable and is due a working day before it.
- **Types:** something the user does is a *task*. Something owed to someone outside by a date is a *deliverable*. Something the user is waiting on from someone is a *follow-up* (needs `--waiting-on`). Prep for a specific meeting is *prep*.
- **Handoffs create follow-ups.** "Asked Bilal to fix tracking" becomes a follow-up waiting on Bilal. The CLI sets the channel and the next chase date.
- **Ask only about what's missing or ambiguous**, in one short message. If the user doesn't answer, save it anyway: no project means Inbox.
- **New client contacts:** the first time a client person comes up, add them with `person add NAME --role client --project P`. The channel defaults to the project's (Analytics Huddle, or email for Austell). Ask for the channel only if it's unclear.
- **Confirm each change in one line** (the CLI output line is enough), so the user can correct it straight away.
- **Bulk add:** when the user pastes a Slack thread, email or meeting notes and asks for action items, list what you found as a numbered list *first*. Add only what they confirm.

## Updating (SCOPE §4)

- Find the item with `find`. If there are several plausible matches, show the top 2–3 and ask which one. Never guess between them.
- Map phrases to commands:
  - "sent" or "done" → `done`
  - "pinged them" or "chased" → `chased`
  - "they said Thursday" → `log` plus `update --followup thu` (or `--due`)
  - "push to next week" → `update --planned "next mon"`
  - "drop it, client paused" → `drop --reason`
  - "still waiting" or "no change" → `log ID "no change"`
- If a new date makes a follow-up land after the deliverable it blocks, say so. The brief also shows this as a clash.
- If a project is paused or resumed, or a new one starts, use `project status` or `project add`.

## Follow-up drafts

When the brief lists follow-ups, write a **draft message** for each one that
the user can copy and send:
- **MarketLytics Slack (team):** 1–2 lines, casual and direct. *"Hey Saad, any update on the Q4 numbers for RVShare? Need them for the proposal going out Wed."*
- **Analytics Huddle (clients):** friendly and professional, still short. Mention the deliverable and what's needed.
- **Email (Austell, Salam):** a subject line plus 2–4 short lines.
- **Teams (Salam) and IV Slack:** short and polite.
- Use the item's log for context. On a second or later chase, acknowledge it lightly and don't nag.
- Never send anything yourself. The user sends it.

## Tone and format

- Phone-first: short lines, numbered lists the user can answer by number ("1, 3 sent. 2: Thursday").
- No preamble. Lead with what needs action.
- Use Pakistan time. The CLI already does.
