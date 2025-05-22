from datetime import datetime
import os

async def initialize_browser():
    """Initialize Playwright browser with realistic context."""
    from playwright.async_api import async_playwright
    try:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Jakarta"
        )
        page = await context.new_page()
        return p, browser, context, page
    except Exception as e:
        print(f"Failed to initialize browser: {str(e)}")
        return None, None, None, None

async def prepare_page(url, output_dir="output"):
    """Prepare the browser and page for scraping, handling navigation, cookies, and CAPTCHAs."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)

    p, browser, context, page = await initialize_browser()
    if not page:
        print("Failed to initialize browser for scraping.")
        return None, None, None, None, timestamp

    try:
        if not await navigate_to_page(page, url):
            raise Exception("Navigation to page failed.")

        await page.wait_for_load_state('networkidle')
        await page.screenshot(path=f"{output_dir}/debug_screenshot_{timestamp}.png")
        title = await page.title()
        print(f"Page title: {title}")

        if "Cloudflare" in title:
            print("Cloudflare protection detected.")
            return None, None, None, None, timestamp

        await handle_cookie_consent(page)

        if await check_captcha(page):
            print("Scraping stopped due to CAPTCHA detection.")
            await page.screenshot(path=f"{output_dir}/captcha_screenshot_{timestamp}.png")
            return None, None, None, None, timestamp

        return p, browser, context, page, timestamp

    except Exception as e:
        print(f"Error during preparation: {str(e)}")
        if page:
            await save_html_content(page, output_dir, timestamp, filename_prefix="bwf_tournaments_error")
            await save_screenshot(page, output_dir, timestamp, suffix="_error")
        return None, None, None, None, timestamp

async def navigate_to_page(page, url):
    """Navigate to the specified URL and verify successful load."""
    print(f"Navigating to {url}")
    response = await page.goto(url)
    if response and response.ok:
        print("Page loaded successfully")
        return True
    print(f"Failed to load page: {response.status if response else 'No response'}")
    return False

async def handle_cookie_consent(page):
    """Handle cookie consent popup if present."""
    try:
        cookie_button = await page.wait_for_selector(
            'button#accept-cookies, button.accept, [id*="cookie"] button, '
            'button[class*="consent"], button:text("Accept"), button:text("Allow"), '
            'button:text(" Agree"), [role="button"][aria-label*="cookie"]',
            timeout=10000
        )
        if cookie_button:
            await cookie_button.click()
            print("Cookie consent accepted.")
            await page.wait_for_timeout(1000)
        else:
            print("Cookie consent button not found, proceeding anyway.")
    except Exception as e:
        print(f"Failed to handle cookie consent (non-critical): {str(e)}")

async def check_captcha(page):
    """Check for CAPTCHA or Cloudflare protection."""
    captcha_indicators = [
        'text="Please complete the security check"',
        '[title="Cloudflare"]',
        'form#challenge-form',
        'iframe[src*="captcha"]'
    ]
    for indicator in captcha_indicators:
        try:
            if await page.query_selector(indicator):
                print(f"CAPTCHA detected: {indicator}")
                return True
        except Exception as e:
            print(f"Error checking CAPTCHA indicator {indicator}: {str(e)}")
    return False

async def save_screenshot(page, output_dir, timestamp, suffix=""):
    """Save a screenshot of the current page."""
    try:
        await page.screenshot(path=f"{output_dir}/screenshot_{timestamp}{suffix}.png")
    except Exception as e:
        print(f"Failed to save screenshot: {str(e)}")

async def save_html_content(page, output_dir, timestamp, filename_prefix="page"):
    """Save the current page HTML content."""
    try:
        html_content = await page.content()
        with open(f"{output_dir}/{filename_prefix}_{timestamp}.html", "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"Failed to save HTML content: {str(e)}")

