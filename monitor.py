#!/usr/bin/env python3
"""
ToyzzShop product monitor.
Scrapes all pages of a category (sorted by newest first), diffs against
saved state, and sends a Telegram notification when new products appear.
"""

import re
import json
import os
import sys
import time
import urllib.parse
import urllib.request

# ── Configuration ────────────────────────────────────────────────────────────
BASE_URL     = "https://toyzzshop.bg/katalog/f/b/pokemon?product_list_order=created_at"
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE_FILE   = "state/products.json"
MAX_PAGES    = 20
# ─────────────────────────────────────────────────────────────────────────────


def page_url(n: int) -> str:
    """Return the URL for page n (1-based). Page 1 has no &p= param."""
    if n == 1:
        return BASE_URL
    # Append page param cleanly regardless of existing query string
    sep = "&" if "?" in BASE_URL else "?"
    return f"{BASE_URL}{sep}p={n}"


def fetch(url: str, retries: int = 3) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            print(f"  [fetch] attempt {attempt} failed for {url}: {exc}", file=sys.stderr)
            if attempt < retries:
                time.sleep(5 * attempt)
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


def parse_products(html: str) -> dict[str, str]:
    """
    Extract product {url: name} pairs from raw HTML.
    Product links look like:
      <a href="https://toyzzshop.bg/some-slug" ...>Product Name</a>
    We identify them by being single-path-segment toyzzshop.bg URLs
    that appear inside a product-list container.
    """
    products = {}

    # Match all anchor tags that point to a single-slug toyzzshop.bg product page
    pattern = re.compile(
        r'<a\b[^>]*\bhref="(https://toyzzshop\.bg/[A-Za-z0-9\-]+)"[^>]*>'
        r'(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    for m in pattern.finditer(html):
        href = m.group(1).strip()
        inner = m.group(2).strip()

        # Must be exactly one path segment (no extra slashes)
        path = urllib.parse.urlparse(href).path.strip("/")
        if "/" in path or not path:
            continue

        # Skip obvious non-product pages
        if path in {"katalog", "kontakti", "dostavka", "plashtane"}:
            continue

        # Strip HTML tags from inner text to get the name
        name = re.sub(r"<[^>]+>", " ", inner)
        name = re.sub(r"\s+", " ", name).strip()

        # Drop entries that look like navigation / UI chrome (too short or contain БГН/лв)
        if len(name) < 4:
            continue

        # Keep only the first occurrence (anchors repeat for image + text)
        if href not in products and name:
            products[href] = name

    return products


def has_next_page(html: str, current_page: int) -> bool:
    """Return True if the HTML contains a link to the next page number."""
    next_p = current_page + 1
    return f"p={next_p}" in html or f"?p={next_p}" in html


def scrape_all() -> dict[str, str]:
    all_products: dict[str, str] = {}

    for page_num in range(1, MAX_PAGES + 1):
        url = page_url(page_num)
        print(f"  Fetching page {page_num}: {url}")
        html = fetch(url)

        page_products = parse_products(html)
        print(f"    → {len(page_products)} products found on page {page_num}")
        all_products.update(page_products)

        if not has_next_page(html, page_num):
            print(f"  No page {page_num + 1} found — stopping.")
            break

        time.sleep(1)  # be polite

    return all_products


def load_state() -> dict[str, str]:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(products: dict[str, str]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def send_telegram(message: str) -> None:
    encoded = urllib.parse.quote(message, safe="")
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        f"?chat_id={TELEGRAM_CHAT_ID}&text={encoded}&parse_mode=HTML"
    )
    with urllib.request.urlopen(url, timeout=15) as resp:
        result = json.loads(resp.read())
        if not result.get("ok"):
            raise RuntimeError(f"Telegram error: {result}")
    print("  Telegram notification sent.")


def main() -> None:
    print("=== ToyzzShop Monitor ===")

    print("Scraping catalog...")
    current = scrape_all()
    print(f"Total products found: {len(current)}")

    previous = load_state()
    is_first_run = not previous
    print(f"Previous state: {len(previous)} products  |  First run: {is_first_run}")

    new_items = {url: name for url, name in current.items() if url not in previous}
    print(f"New products detected: {len(new_items)}")

    # Always save updated state
    save_state(current)
    print("State saved.")

    if new_items and not is_first_run:
        count = len(new_items)
        lines = [f"🎮 <b>{count} new Pokémon item{'s' if count != 1 else ''} on ToyzzShop!</b>\n"]
        for url, name in list(new_items.items())[:20]:   # cap at 20 to stay within Telegram limits
            lines.append(f"• {name}")
            lines.append(f"  {url}")
        if count > 20:
            lines.append(f"\n…and {count - 20} more.")
        message = "\n".join(lines)
        print("Sending Telegram notification...")
        send_telegram(message)
    elif is_first_run:
        print("First run — state saved, no notification sent.")
    else:
        print("No new products — nothing to notify.")

    print("Done.")


if __name__ == "__main__":
    main()
