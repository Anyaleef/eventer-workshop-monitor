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

The main workflow is scheduled every five minutes. A confirmed change sends a Telegram message immediately: 🟢 means registration opened, 🔴 means it closed, and the message includes the direct link to every affected workshop page. If neither page changed, 🔵 reports both current statuses at most once an hour. The latest confirmed statuses and time of the last unchanged message are saved in `monitor_state.json`. Incomplete checks fail the run and do not send a misleading unchanged message or save partial statuses.

The independent `Schedule probe (hourly)` workflow is scheduled at minute 13 of each hour in Israel time. It only records its event type and UTC time in the run log; it does not check Eventer or send Telegram. An Actions run with `event=schedule` confirms that GitHub started an automatic run. A manual run does not confirm this.

GitHub can delay or drop scheduled runs, so a short opening may be missed. Until a run with `event=schedule` appears, automatic checking is not verified. In inactive public repositories GitHub can disable scheduled workflows after 60 days. To stop checking, disable the main workflow in Actions or remove its `schedule` block.
