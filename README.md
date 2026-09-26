# Eventer workshop availability monitor

The monitor checks two Eventer workshop pages for a visible ordering option:

| Workshop | Page |
| --- | --- |
| Claude Code for Everyone, first cohort | https://www.eventer.co.il/t242f |
| Claude Code for Everyone, second cohort | https://www.eventer.co.il/rmh2f |

## Test a run

In **Actions → Check Eventer workshops → Run workflow**, leave `check_only` checked to inspect both page statuses without sending Telegram or saving state. The log reports `sold_out`, `open`, or `unknown`. To test the Telegram connection, check `test_telegram`; this sends one test message without checking Eventer or changing availability state.

The repository secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are required for a normal run. They are never written to the repository.

## Automatic checks and notifications

The main workflow is scheduled every five minutes. Cohort 1 is checked through October 10, 2026, and cohort 2 through October 12, 2026. Each check stops at 00:00 Israel time on the following date (October 11 and October 13, respectively). From October 11 onward, messages mention only cohort 2. From October 13 onward, no Eventer pages are checked and no availability messages are sent; scheduled runs exit after a quick date check.

When one cohort opens, the bot sends a 🟢 message with that cohort's link. When both open at the same check, it sends a 🔵 message with both links. When all monitored cohorts are closed, it sends a 🔴 message with their links. If registration remains open without a new opening, the bot reports that it is still open. Telegram messages use Markdown for bold headings. A confirmed change sends a message immediately; unchanged status sends at most one message per hour. The latest confirmed statuses and time of the last unchanged message are saved in `monitor_state.json`. Incomplete checks fail the run and do not send an unchanged message or save partial statuses.

The independent `Schedule probe (hourly)` workflow is scheduled at minute 13 of each hour in Israel time. It only records its event type and UTC time in the run log; it does not check Eventer or send Telegram. An Actions run with `event=schedule` confirms that GitHub started an automatic run. A manual run does not confirm this.

GitHub can delay or drop scheduled runs, so a short opening may be missed even though the schedule is set to every five minutes. Confirm actual execution by inspecting the `event=schedule` runs. In inactive public repositories GitHub can disable scheduled workflows after 60 days. To stop checking, disable the main workflow in Actions or remove its `schedule` block.
