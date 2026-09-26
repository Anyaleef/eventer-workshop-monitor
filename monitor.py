"""Check two Eventer workshops and report changes and hourly status to Telegram."""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright


WORKSHOPS = {
    "t242f": ("Claude Code for Everyone – מחזור ראשון", "https://www.eventer.co.il/t242f"),
    "rmh2f": ("Claude Code for Everyone – מחזור שני", "https://www.eventer.co.il/rmh2f"),
}
END_DATES = {
    "t242f": date(2026, 10, 11),  # Stop at midnight, Israel time.
    "rmh2f": date(2026, 10, 13),
}
ISRAEL_TIME = ZoneInfo("Asia/Jerusalem")
STATE_FILE = Path("monitor_state.json")
SOLD_OUT = 'h2[ng-if*="purchaseFrameSoldOutMsg"]'
ORDER_BUTTON = '[rnd-id="navigate_to_transaction"]'


def visible(locator):
    return any(locator.nth(i).is_visible() for i in range(locator.count()))


def check_page(browser, url):
    page = browser.new_page(locale="he-IL")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=35_000)
        page.locator("h1.descriptionHeader").first.wait_for(state="visible", timeout=25_000)
        # Angular renders the sold-out banner and checkout after the shell loads.
        page.wait_for_timeout(2_000)
        if visible(page.locator(SOLD_OUT)):
            return "sold_out"

        # The checkout form is in the DOM even when the event is sold out.
        # Visibility, rather than mere existence, is the useful signal.
        if visible(page.locator(ORDER_BUTTON)):
            return "open"

        # An alternate Eventer registration button can be used instead.
        for role in ("button", "link"):
            candidate = page.get_by_role(
                role, name=re.compile(r"^(?:הזמן עכשיו|להזמנה|להרשמה|הירשמו עכשיו|רכישת כרטיסים)$")
            )
            if visible(candidate):
                return "open"
        return "unknown"
    finally:
        page.close()


def send_telegram_text(message):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    payload = urlencode({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode("utf-8")
    request = Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, method="POST")
    with urlopen(request, timeout=20) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram did not accept the alert")


def availability_message(statuses, changes):
    first_url = WORKSHOPS["t242f"][1]
    second_url = WORKSHOPS["rmh2f"][1]
    opened = [key for key in statuses if changes.get(key) == "open"]
    if len(opened) == 2:
        return ("🔵 *נפתחו מקומות הרשמה חדשים!*\n"
                "ניתן להירשם לשני המחזורים של Claude Code for Everyone\n"
                f"- מחזור 1: {first_url}\n- מחזור 2: {second_url}")
    if len(opened) == 1:
        key = opened[0]
        cohort = 1 if key == "t242f" else 2
        return ("🟢 *נפתח מקום הרשמה חדש!*\n"
                f"ניתן להירשם למחזור {cohort} של Claude Code for Everyone\n"
                f"{WORKSHOPS[key][1]}")
    if all(status == "sold_out" for status in statuses.values()):
        if len(statuses) == 1:
            key = next(iter(statuses))
            cohort = 1 if key == "t242f" else 2
            return ("🔴 *אין מקומות הרשמה פנויים*\n"
                    f"מחזור {cohort} של Claude Code for Everyone סגור להרשמה.\n"
                    f"- מחזור {cohort}: {WORKSHOPS[key][1]}")
        return ("🔴 *אין מקומות הרשמה פנויים*\n"
                "שני המחזורים של Claude Code for Everyone סגורים להרשמה.\n"
                f"- מחזור 1: {first_url}\n- מחזור 2: {second_url}")

    # An unchanged open page must not be reported as newly opened or closed.
    open_keys = [key for key in statuses if statuses[key] == "open"]
    if len(open_keys) == 2:
        return ("🔵 *ההרשמה עדיין פתוחה*\n"
                "ניתן להירשם לשני המחזורים של Claude Code for Everyone\n"
                f"- מחזור 1: {first_url}\n- מחזור 2: {second_url}")
    key = open_keys[0]
    cohort = 1 if key == "t242f" else 2
    return ("🟢 *ההרשמה עדיין פתוחה*\n"
            f"ניתן להירשם למחזור {cohort} של Claude Code for Everyone\n"
            f"{WORKSHOPS[key][1]}")


def hourly_notice_due(state, now):
    previous = state.get("_last_no_change_message_at")
    if not previous:
        return True
    try:
        return now - datetime.fromisoformat(previous) >= timedelta(hours=1)
    except (TypeError, ValueError):
        return True


def load_state():
    if not STATE_FILE.exists():
        return {}
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("monitor_state.json must contain a JSON object")
    return state


def active_workshops(today):
    return {key: workshop for key, workshop in WORKSHOPS.items() if today < END_DATES[key]}


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--manual", action="store_true", help="Always send the full status without changing automatic monitoring state")
    mode.add_argument("--check-only", action="store_true", help="Report status without sending alerts or saving state")
    mode.add_argument("--test-telegram", action="store_true", help="Send one test message without checking Eventer")
    args = parser.parse_args()
    if args.test_telegram:
        if not (os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")):
            parser.error("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in GitHub Actions secrets first")
        send_telegram_text("🔵 בדיקת התראות Eventer: החיבור לטלגרם פועל.")
        print("Telegram test message sent", flush=True)
        return

    workshops = active_workshops(datetime.now(ISRAEL_TIME).date())
    if not workshops:
        print("Monitoring period finished; no pages checked or messages sent", flush=True)
        return
    if not args.check_only and not (os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")):
        parser.error("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in GitHub Actions secrets first")

    state = load_state()
    failed = False
    statuses = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for key, (name, url) in workshops.items():
                if datetime.now(ISRAEL_TIME).date() >= END_DATES[key]:
                    print(f"{key}: monitoring period finished", flush=True)
                    continue
                try:
                    status = check_page(browser, url)
                    print(f"{key}: {status}", flush=True)
                    if status not in ("open", "sold_out"):
                        failed = True
                        continue
                    statuses[key] = status
                except Exception as exc:
                    print(f"{key}: check or notification failed: {exc}", file=sys.stderr, flush=True)
                    failed = True
        finally:
            browser.close()

    # An incomplete check must never be reported as "no change" or saved.
    if failed:
        sys.exit(1)
    if not statuses:
        return

    if args.manual:
        changes = {key: status for key, status in statuses.items() if state.get(key) != status}
        send_telegram_text(availability_message(statuses, changes))
        print("Telegram full manual status sent; automatic state unchanged", flush=True)
        return

    if not args.check_only:
        changes = {key: status for key, status in statuses.items() if state.get(key) != status}
        now = datetime.now(timezone.utc)
        if changes:
            send_telegram_text(availability_message(statuses, changes))
            print("Telegram change alert sent", flush=True)
        elif hourly_notice_due(state, now):
            send_telegram_text(availability_message(statuses, changes))
            state["_last_no_change_message_at"] = now.isoformat()
            print("Telegram no-change status sent", flush=True)
        state.update(statuses)
        temp = STATE_FILE.with_suffix(".json.tmp")
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(STATE_FILE)


if __name__ == "__main__":
    main()
