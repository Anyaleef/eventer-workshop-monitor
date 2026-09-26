# Claude Code workshop monitor

![Status](https://img.shields.io/badge/status-active-brightgreen)
![Use](https://img.shields.io/badge/use-personal%20only-orange)

Personal monitor for the two Claude Code for Everyone cohorts and their activity listings during Technion AI Days. This repository documents my own workflow and is not intended for public use.

## What it checks

- **Registration availability:** Checks each active cohort's registration page. A newly opened place triggers a 🟢 alert, or 🔵 if both cohorts open. When registration is closed, the bot sends a 🔴 status message. Unchanged availability is reported at most once per hour.
- **New activity links:** Checks the AI Days activity list for another Claude Code for Everyone registration link. A genuinely new link triggers one 🟠 message containing the activity title, short description, and registration link. Existing links and previously announced links are ignored. No activity-list message is sent when nothing new appears.
- **End dates:** Cohort 1 stops being checked on October 11, 2026; cohort 2 on October 13, 2026. A scheduled run sends a one-time end notice for each cohort on its end date. The activity-list check continues through October 22 and stops on October 23. All dates use Israel time.

## Runs

- **Scheduled:** The main GitHub Actions workflow is configured to run every five minutes. GitHub may delay or skip scheduled runs, so the configured interval is not a guarantee.
- **Manual:** In **Actions → Check Eventer workshops → Run workflow**, each run sends the full current availability status for active cohorts, even if nothing changed. Manual runs do not scan the activity list, send end notices, or change the scheduled monitor's saved state.
- **Schedule probe:** The separate hourly probe records when GitHub starts a scheduled run. It does not check registration or send Telegram messages.

## Private configuration

Telegram delivery uses the repository secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Scheduled runs record confirmed statuses and announced activity links in `monitor_state.json` to avoid duplicate alerts. Incomplete page checks fail rather than being treated as unchanged availability.
