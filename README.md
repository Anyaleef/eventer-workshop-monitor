# Eventer workshop availability monitor

This project checks two Eventer workshop pages for a **visible** ordering option. It sends a Telegram message when a workshop changes to open, and sends another only if it first becomes sold out and later reopens. A failed or unclear page load never counts as an opening.

## 1. Test the page checks

Open **Actions → Check Eventer workshops → Run workflow**, leave `check_only` checked, then inspect the run log. The run log reports `sold_out`, `open`, or `unknown` for each page. The test sends no Telegram message and saves no state.

## 2. Set up Telegram

1. In Telegram, message **@BotFather** with `/newbot` and follow its instructions. Keep the token private.
2. Open a direct chat with your new bot and send `/start` or any message.
3. In your own browser, visit `https://api.telegram.org/bot<TOKEN>/getUpdates`, replacing `<TOKEN>` with your bot token. Find `message.chat.id` in the response. Do not paste the token or chat ID into this repository or into a public conversation.
4. In GitHub, open **Settings → Secrets and variables → Actions → New repository secret**. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` separately.
5. Run the workflow manually with `check_only` **unchecked**. An alert is sent immediately if a place is currently open. If both pages are sold out, this run only saves the initial statuses.
6. To verify the Telegram connection, run the workflow with `test_telegram` checked. It sends one test message to the configured chat, even if `check_only` remains checked. It does not alter availability state.

## 3. Automatic checks

The repository is public and the workflow checks both pages at minute 2, 7, 12, etc. of every hour (UTC). Scheduled runs send Telegram only when an event becomes open. The latest confirmed status is saved in `monitor_state.json` to avoid repeated alerts. The bot token and chat ID stay in GitHub Actions secrets and are never written to the repository.

GitHub can delay or skip scheduled runs, so a short opening between checks can be missed. GitHub disables scheduled workflows in inactive public repositories after 60 days. To stop checking, remove the `schedule` section from `.github/workflows/monitor.yml` or disable the workflow from the Actions tab.
