"""Alert when a new Claude Code workshop registration link appears on AI Days."""

import html
import os
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from monitor import WORKSHOPS, load_state, save_state, send_telegram_text

AI_DAYS_URL = "https://aidays.technion.ac.il/"
TITLE_PATTERN = re.compile(r"סדנה\s+מעשית.*Claude\s+Code\s+for\s+Everyone", re.IGNORECASE)
REGISTER_PATTERN = re.compile(r"הרשמה|לרכישה|כרטיסים")
STATE_KEY = "_ai_days_seen_links"


def canonical_link(url):
    """Ignore marketing parameters and cosmetic URL variants, but keep meaningful queries."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    hostname = parts.hostname.lower().removeprefix("www.")
    query = urlencode(sorted((key, value) for key, value in parse_qsl(parts.query)
                           if not key.lower().startswith("utm_") and key.lower() not in
                           ("fbclid", "gclid", "mc_cid", "mc_eid")))
    return urlunsplit(("https", hostname, parts.path.rstrip("/") or "/", query, ""))


def find_registration_links(browser):
    page = browser.new_page(locale="he-IL")
    try:
        page.goto(AI_DAYS_URL, wait_until="domcontentloaded", timeout=35_000)
        headings = page.locator("main h3").filter(has_text=TITLE_PATTERN)
        headings.first.wait_for(state="visible", timeout=25_000)
        activities = []
        for heading in headings.all():
            card = heading.locator(
                "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' group ')][1]"
            )
            title = heading.inner_text().strip()
            summary = card.locator("h3 + div p").first.inner_text().strip()
            card.get_by_role("button", name="פרטים נוספים").click()
            for link in card.locator("a[href]").all():
                if not REGISTER_PATTERN.search(link.inner_text()):
                    continue
                url = urljoin(page.url, link.get_attribute("href"))
                if canonical_link(url):
                    activities.append((title, summary, url))
        return activities
    finally:
        page.close()


def alert_message(title, summary, url):
    # The website controls these fields. HTML escaping prevents malformed Telegram markup.
    return ("🟠<b>עדכון חשוב!</b>\n"
            "נמצא קישור חדש עבור Claude Code for Everyone ברשימת הפעילויות של ימי AI:\n\n"
            f"<b>{html.escape(title)}</b>\n"
            f"{html.escape(summary)}\n"
            f"{html.escape(url)}")


def main():
    if not (os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")):
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in GitHub Actions secrets first")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            activities = find_registration_links(browser)
        finally:
            browser.close()

    state = load_state()
    seen = set(state.get(STATE_KEY, []))
    known = {canonical_link(url) for _, url in WORKSHOPS.values()} | seen
    print(f"AI Days: found {len(activities)} matching registration links", flush=True)
    for title, summary, url in activities:
        key = canonical_link(url)
        if key in known:
            continue
        send_telegram_text(alert_message(title, summary, url), parse_mode="HTML")
        seen.add(key)
        known.add(key)
        state[STATE_KEY] = sorted(seen)
        save_state(state)  # Commit after each successful message, even if a later alert fails.
        print(f"AI Days: new registration link sent: {url}", flush=True)


if __name__ == "__main__":
    main()
