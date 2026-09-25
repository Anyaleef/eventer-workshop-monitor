# Eventer workshop availability monitor

This project checks two Eventer workshop pages for a **visible** ordering option. It sends a Telegram message when a workshop changes to open, and sends another only if it first becomes sold out and later reopens. A failed or unclear page load never counts as an opening.

## 1. Test the page checks

Open **Actions → Check Eventer workshops → Run workflow**, leave `check_only` checked, then inspect the run log. Both pages currently show a sold-out message, so each should report `sold_out`. The test sends no Telegram message and saves no state.

## 2. Set up Telegram

1. In Telegram, message **@BotFather** with `/newbot` and follow its instructions. Keep the token private.
2. Open a direct chat with your new bot and send `/start` or any message.
3. In your own browser, visit `https://api.telegram.org/bot<TOKEN>/getUpdates`, replacing `<TOKEN>` with your bot token. Find `message.chat.id` in the response. Do not paste the token or chat ID into this repository or into a public conversation.
4. In GitHub, open **Settings → Secrets and variables → Actions → New repository secret**. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` separately.
5. Run the workflow manually with `check_only` **unchecked**. An alert is sent immediately if a place is currently open. If both pages are sold out, this run only saves the initial statuses.

## 3. Enable checks every five minutes

This repository was private when the monitor was prepared. GitHub Free has a monthly minute limit for private repository Actions. At five-minute intervals the monitor can exceed that limit. Make this repository **Public** under **Settings → General → Danger Zone → Change repository visibility** if you are comfortable publishing this source code and its non-sensitive availability state. GitHub Actions secrets remain separate from the code.

After the repository is public and the manual test succeeds, edit `.github/workflows/monitor.yml` on the `main` branch: remove the leading `#` and space from the two `schedule:` lines. Save the file. The schedule starts checking at minute 2, 7, 12, etc. of each hour in UTC. GitHub may delay or skip scheduled runs, so an opening between checks can be missed. Scheduled workflows in inactive public repositories can be disabled after 60 days; successful state commits count as activity only when availability changes.

The monitor writes `monitor_state.json` to the repository when a confirmed status changes. It never writes a bot token or chat ID. To stop the checks, comment out the two schedule lines again or disable the workflow from the Actions tab.
