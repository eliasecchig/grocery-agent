"""Automated store API reconnaissance via headless Playwright.

Usage:
    uv run --with playwright python scripts/auto_recon.py <store_url> [username] [password]
    # First time only: uv run --with playwright playwright install chromium
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "docs"
OUTPUT_DIR.mkdir(exist_ok=True)

STORE_URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STORE_GRAPHQL_URL", "").replace("/graphql", "")
USERNAME = sys.argv[2] if len(sys.argv) > 2 else ""
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else ""
STORE_HOSTNAME = urlparse(STORE_URL).hostname or ""

captured_requests: list[dict] = []


def capture_request(request):
    parsed = urlparse(request.url)
    if STORE_HOSTNAME not in (parsed.hostname or ""):
        return
    entry = {
        "method": request.method,
        "url": request.url,
        "path": parsed.path,
        "headers": dict(request.headers),
        "post_data": request.post_data,
        "resource_type": request.resource_type,
    }
    captured_requests.append(entry)


def capture_response(response):
    parsed = urlparse(response.url)
    if STORE_HOSTNAME not in (parsed.hostname or ""):
        return
    for req in reversed(captured_requests):
        if req["url"] == response.url and "status" not in req:
            req["status"] = response.status
            req["response_headers"] = dict(response.headers)
            break


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="it-IT",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        page.on("request", capture_request)
        page.on("response", capture_response)

        print("=== Step 1: Loading homepage ===")
        await page.goto(STORE_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        print(f"  Title: {await page.title()}")
        print(f"  URL: {page.url}")
        print(f"  Captured {len(captured_requests)} requests so far")

        # Take screenshot
        await page.screenshot(path=str(OUTPUT_DIR / "01_homepage.png"))

        # Look for login link/button
        print("\n=== Step 2: Finding login ===")
        login_selectors = [
            'a[href*="login"]', 'a[href*="accedi"]', 'a[href*="auth"]',
            'button:has-text("Accedi")', 'a:has-text("Accedi")',
            'button:has-text("Login")', 'a:has-text("Login")',
            'a:has-text("Entra")', 'button:has-text("Entra")',
            '[class*="login"]', '[class*="account"]', '[class*="user"]',
            'a[href*="account"]',
        ]
        login_found = False
        for sel in login_selectors:
            try:
                elem = page.locator(sel).first
                if await elem.is_visible(timeout=2000):
                    print(f"  Found login element: {sel}")
                    text = await elem.text_content()
                    href = await elem.get_attribute("href") or ""
                    print(f"  Text: {text}, href: {href}")
                    await elem.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=str(OUTPUT_DIR / "02_login_page.png"))
                    login_found = True
                    print(f"  Navigated to: {page.url}")
                    break
            except Exception:
                continue

        if not login_found:
            print("  Could not find login link. Dumping page content...")
            content = await page.content()
            (OUTPUT_DIR / "homepage.html").write_text(content)

        # Try to log in
        if USERNAME and PASSWORD:
            print("\n=== Step 3: Logging in ===")
            email_selectors = [
                'input[type="email"]', 'input[name="email"]', 'input[name="username"]',
                'input[id="email"]', 'input[id="username"]', 'input[placeholder*="email"]',
                'input[placeholder*="Email"]', 'input[type="text"]',
            ]
            pass_selectors = [
                'input[type="password"]', 'input[name="password"]',
                'input[id="password"]',
            ]
            submit_selectors = [
                'button[type="submit"]', 'input[type="submit"]',
                'button:has-text("Accedi")', 'button:has-text("Login")',
                'button:has-text("Entra")', 'button:has-text("Invia")',
            ]

            email_filled = False
            for sel in email_selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.is_visible(timeout=2000):
                        await elem.fill(USERNAME)
                        email_filled = True
                        print(f"  Filled email with selector: {sel}")
                        break
                except Exception:
                    continue

            pass_filled = False
            for sel in pass_selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.is_visible(timeout=2000):
                        await elem.fill(PASSWORD)
                        pass_filled = True
                        print(f"  Filled password with selector: {sel}")
                        break
                except Exception:
                    continue

            if email_filled and pass_filled:
                await page.screenshot(path=str(OUTPUT_DIR / "03_login_filled.png"))
                for sel in submit_selectors:
                    try:
                        elem = page.locator(sel).first
                        if await elem.is_visible(timeout=2000):
                            await elem.click()
                            print(f"  Clicked submit: {sel}")
                            break
                    except Exception:
                        continue

                await page.wait_for_timeout(5000)
                await page.screenshot(path=str(OUTPUT_DIR / "04_after_login.png"))
                print(f"  After login URL: {page.url}")
                print(f"  After login title: {await page.title()}")

                # Check cookies
                cookies = await context.cookies()
                print(f"  Cookies: {len(cookies)}")
                for c in cookies:
                    if STORE_HOSTNAME in c.get("domain", ""):
                        print(f"    {c['name']}: {c['value'][:30]}...")
            else:
                print(f"  Email filled: {email_filled}, Password filled: {pass_filled}")
                content = await page.content()
                (OUTPUT_DIR / "login_page.html").write_text(content)

        # Try searching for products
        print("\n=== Step 4: Searching products ===")
        search_selectors = [
            'input[type="search"]', 'input[name="q"]', 'input[name="search"]',
            'input[placeholder*="Cerca"]', 'input[placeholder*="cerca"]',
            'input[placeholder*="Search"]', '[class*="search"] input',
            'input[id*="search"]',
        ]
        for sel in search_selectors:
            try:
                elem = page.locator(sel).first
                if await elem.is_visible(timeout=2000):
                    await elem.fill("latte")
                    await elem.press("Enter")
                    print(f"  Searched 'latte' with selector: {sel}")
                    await page.wait_for_timeout(5000)
                    await page.screenshot(path=str(OUTPUT_DIR / "05_search_results.png"))
                    print(f"  Search URL: {page.url}")
                    break
            except Exception:
                continue

        # Try to find and click a product
        print("\n=== Step 5: Product detail ===")
        product_selectors = [
            '[class*="product"] a', '[class*="item"] a',
            '[class*="card"] a', '.product-list a',
        ]
        for sel in product_selectors:
            try:
                elem = page.locator(sel).first
                if await elem.is_visible(timeout=2000):
                    await elem.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=str(OUTPUT_DIR / "06_product_detail.png"))
                    print(f"  Product page URL: {page.url}")
                    break
            except Exception:
                continue

        # Try to add to cart
        print("\n=== Step 6: Add to cart ===")
        add_selectors = [
            'button:has-text("Aggiungi")', 'button:has-text("Carrello")',
            'button:has-text("Add")', '[class*="add-to-cart"]',
            'button[class*="cart"]', 'button[class*="add"]',
        ]
        for sel in add_selectors:
            try:
                elem = page.locator(sel).first
                if await elem.is_visible(timeout=2000):
                    await elem.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=str(OUTPUT_DIR / "07_after_add_to_cart.png"))
                    print(f"  Clicked add-to-cart: {sel}")
                    break
            except Exception:
                continue

        # Try to view cart
        print("\n=== Step 7: View cart ===")
        cart_selectors = [
            'a[href*="cart"]', 'a[href*="carrello"]',
            'button:has-text("Carrello")', '[class*="cart"] a',
            'a:has-text("Carrello")',
        ]
        for sel in cart_selectors:
            try:
                elem = page.locator(sel).first
                if await elem.is_visible(timeout=2000):
                    await elem.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=str(OUTPUT_DIR / "08_cart.png"))
                    print(f"  Cart URL: {page.url}")
                    break
            except Exception:
                continue

        # Try order history
        print("\n=== Step 8: Order history ===")
        history_selectors = [
            'a[href*="order"]', 'a[href*="ordini"]', 'a[href*="storico"]',
            'a:has-text("Ordini")', 'a:has-text("Storico")',
            'a[href*="account"]', 'a:has-text("Account")',
            'a[href*="profilo"]',
        ]
        for sel in history_selectors:
            try:
                elem = page.locator(sel).first
                if await elem.is_visible(timeout=2000):
                    await elem.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path=str(OUTPUT_DIR / "09_orders.png"))
                    print(f"  Orders URL: {page.url}")
                    break
            except Exception:
                continue

        await browser.close()

    # Analyze captured requests
    print(f"\n=== RESULTS: {len(captured_requests)} total requests captured ===\n")

    api_requests = [
        r for r in captured_requests
        if r["resource_type"] in ("xhr", "fetch")
        or r["method"] != "GET"
        or "/api/" in r["url"]
        or "json" in r.get("response_headers", {}).get("content-type", "")
    ]

    print(f"API/XHR requests: {len(api_requests)}\n")
    for req in api_requests:
        status = req.get("status", "?")
        print(f"  {req['method']:6s} {status} {req['path']}")
        if req.get("post_data"):
            print(f"         POST data: {req['post_data'][:200]}")

    # Save full capture
    output = {
        "total_requests": len(captured_requests),
        "api_requests": api_requests,
        "all_paths": sorted({r["path"] for r in captured_requests}),
    }
    (OUTPUT_DIR / "recon_results.json").write_text(json.dumps(output, indent=2, default=str))
    print("\nFull results saved to docs/recon_results.json")
    print("Screenshots saved to docs/*.png")


if __name__ == "__main__":
    asyncio.run(main())
