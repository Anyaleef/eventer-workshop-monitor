"""Check two Eventer workshops and send a Telegram alert on a new opening."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright


WORKSHOPS = {
    "t242f": ("Claude Code for Everyone – מחזור ראשון", "https://www.eventer.co.il/t242f"),
    "rmh2f": ("Claude Code for Everyone – מחזור שני", "https://www.eventer.co.il/rmh2f"),
}
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


def send_telegram(name, url):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    message = f"נראה שנפתחה אפשרות להזמין מקום בסדנה:\n{name}\n{url}\n\nבדקי את העמוד לפני שהמקום נתפס."
    payload = urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, method="POST")
    with urlopen(request, timeout=20) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram did not accept the alert")


def load_state():
    if not STATE_FILE.exists():
        return {}
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("monitor_state.json must contain a JSON object")
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="Report status without sending alerts or saving state")
    args = parser.parse_args()
    if not args.check_only and not (os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")):
        parser.error("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in GitHub Actions secrets first")

    state = load_state()
    failed = False
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for key, (name, url) in WORKSHOPS.items():
                try:
                    status = check_page(browser, url)
                    print(f"{key}: {status}", flush=True)
                    if status == "unknown":
                        failed = True
                        continue
                    if args.check_only:
                        continue
                    if status == "open" and state.get(key) != "open":
                        send_telegram(name, url)
                        print(f"{key}: Telegram alert sent", flush=True)
                    state[key] = status
                except Exception as exc:
                    print(f"{key}: check or notification failed: {exc}", file=sys.stderr, flush=True)
                    failed = True
        finally:
            browser.close()

    if not args.check_only:
        temp = STATE_FILE.with_suffix(".json.tmp")
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(STATE_FILE)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
