from playwright.async_api import async_playwright
from datetime import datetime
import os
import json
import asyncio

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

async def scrape_ranking_options(page, output_dir, timestamp):
    """Scrape ranking options from the prepared page and save to JSON."""
    if not page:
        print("Cannot scrape: Page is not prepared.")
        return None

    try:
        ranking_options = await save_ranking_options_to_json(page, output_dir, timestamp)
        return ranking_options
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        await save_html_content(page, output_dir, timestamp, filename_prefix="bwf_tournaments_error")
        await save_screenshot(page, output_dir, timestamp, suffix="_error")
        return None


async def extract_match_card_text(page, output_dir, timestamp):
    """Extract structured text from match-card elements and save to JSON."""
    try:
        match_cards = await page.query_selector_all('div.match-card')
        if not match_cards:
            print("No match cards found.")
            html_content = await page.content()
            with open(f"{output_dir}/debug_page_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            return None

        match_card_data = []
        for card in match_cards:
            card_data = {}

            # Match Name
            match_name_el = await card.query_selector('span.match-name')
            if match_name_el:
                match_name = (await match_name_el.inner_text()).strip()
                card_data["Match_Name"] = match_name

            # Team 1 Players and Country
            team1_wrapper = await card.query_selector('div.participant-wrapper:nth-child(1)')
            if team1_wrapper:
                players = await team1_wrapper.query_selector_all('a.participant-name')
                player_names = [(await p.inner_text()).strip() for p in players]
                if player_names:
                    card_data["Team_1_Players"] = player_names
                seeding = await team1_wrapper.query_selector('span')
                if seeding:
                    seeding_text = (await seeding.inner_text()).strip()
                    if seeding_text:
                        card_data["Team_1_Seeding"] = seeding_text
                # Extract Team 1 Country
                team1_flag = await team1_wrapper.query_selector('div.flags-wrapper img')
                if team1_flag:
                    country_code = (await team1_flag.get_attribute('alt')).strip()
                    if country_code:
                        card_data["Team_1_Country"] = country_code

            # Separator
            separator_el = await card.query_selector('div.separator')
            if separator_el:
                separator = (await separator_el.inner_text()).strip()
                card_data["Separator"] = separator

            # Team 2 Players and Country
            team2_wrapper = await card.query_selector('div.participant-wrapper:nth-child(3)')
            if team2_wrapper:
                players = await team2_wrapper.query_selector_all('a.participant-name')
                player_names = [(await p.inner_text()).strip() for p in players]
                if player_names:
                    card_data["Team_2_Players"] = player_names
                # Extract Team 2 Country
                team2_flag = await team2_wrapper.query_selector('div.flags-wrapper img')
                if team2_flag:
                    country_code = (await team2_flag.get_attribute('alt')).strip()
                    if country_code:
                        card_data["Team_2_Country"] = country_code

            # Scores
            score_sets = await card.query_selector_all('div.game-score-set')
            scores = []
            for set_el in score_sets:
                points = await set_el.query_selector_all('span.set-points')
                if len(points) == 2:
                    score = f"{(await points[0].inner_text()).strip()}-{(await points[1].inner_text()).strip()}"
                    scores.append(score)
            if scores:
                card_data["Scores"] = scores

            # Schedule
            schedule_el = await card.query_selector('div.schedule-module')
            if schedule_el:
                date = await schedule_el.query_selector('span:nth-child(1)')
                status = await schedule_el.query_selector('span.schedule-status')
                time = await schedule_el.query_selector('span.schedule-date')
                if date:
                    card_data["Date"] = (await date.inner_text()).strip()
                if status:
                    card_data["Status"] = (await status.inner_text()).strip()
                if time:
                    card_data["Time"] = (await time.inner_text()).strip()

            # Footer Details and Stadium
            footer_labels = await card.query_selector_all('span.footer-label')
            for i, label in enumerate(footer_labels):
                label_text = (await label.inner_text()).strip()
                if i == 0:
                    card_data["Category"] = label_text
                elif i == 1:
                    card_data["Round"] = label_text
                elif i == 2:
                    card_data["Court"] = label_text

            # Extract Stadium from court-header
            court_header = await card.query_selector('xpath=ancestor::div[contains(@class, "court-wrapper")]//div[contains(@class, "court-header")]')
            if court_header:
                stadium_el = await court_header.query_selector('span.venue-name')
                if stadium_el:
                    stadium_name = (await stadium_el.inner_text()).strip()
                    if stadium_name:
                        card_data["Stadium"] = stadium_name

            duration = await card.query_selector('span.footer-match-time')
            if duration:
                card_data["Duration"] = (await duration.inner_text()).strip()

            if card_data:
                match_card_data.append(card_data)

        if not match_card_data:
            print("No data extracted from match cards.")
            return None

        output_file = f"{output_dir}/match_card_text_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(match_card_data, f, indent=2)
        print(f"Match card text saved to {output_file}")
        return match_card_data

    except Exception as e:
        print(f"Failed to extract match card text: {str(e)}")
        html_content = await page.content()
        with open(f"{output_dir}/debug_page_{timestamp}.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        return None
    
async def extract_schedule_links(page, output_dir):
    """Extract all schedule links from the days-tabs element and save to JSON."""
    try:
        # Generate timestamp for the output file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Query the ul element with id="ajaxTabsResults"
        tabs_container = await page.query_selector('ul#ajaxTabsResults.content-tabs.days-tabs')
        if not tabs_container:
            print("No schedule tabs found with id='ajaxTabsResults'.")
            return None

        # Query all <a> tags within the ul
        link_elements = await tabs_container.query_selector_all('a')
        if not link_elements:
            print("No links found in schedule tabs.")
            return None

        # Extract href attributes
        links = []
        for link_el in link_elements:
            href = await link_el.get_attribute('href')
            if href:
                links.append(href.strip())

        if not links:
            print("No valid links extracted from schedule tabs.")
            return None

        # Save links to JSON
        output_file = f"{output_dir}/schedule_links_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(links, f, indent=2)
        print(f"Schedule links saved to {output_file}")

        return links

    except Exception as e:
        print(f"Failed to extract schedule links: {str(e)}")
        return None

    
async def initialize_browser():
    """Initialize Playwright browser with realistic context."""
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
            'button:text("Agree"), [role="button"][aria-label*="cookie"]',
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

async def switch_to_list_view(page):
    """Switch the page to List View by clicking the List View label."""
    try:
        list_view_button = await page.wait_for_selector(
            'label:has-text("List View")',
            timeout=10000
        )
        if list_view_button:
            await list_view_button.click()
            print("Switched to List View.")
            await page.wait_for_timeout(1000)
        else:
            print("List View button not found, proceeding anyway.")
    except Exception as e:
        print(f"Failed to switch to List View (non-critical): {str(e)}")

async def save_ranking_options_to_json(page, output_dir, timestamp):
    """Extract and save ranking dropdown options to JSON."""
    try:
        await page.wait_for_load_state('networkidle')
        selectors = [
            'div.select div.v-select__slot:has(> label:has-text("Ranking"))',
            'label:has-text("Ranking")',
            'div.v-select__slot',
            'role=combobox[name=/Ranking/i]'
        ]
        dropdown = None
        for selector in selectors:
            try:
                dropdown = await page.wait_for_selector(selector, timeout=30000)
                if dropdown:
                    print(f"Dropdown found with selector: {selector}")
                    break
            except:
                continue

        if not dropdown:
            print("Ranking dropdown not found with any selector.")
            html_content = await page.content()
            with open(f"{output_dir}/debug_page_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            elements = await page.query_selector_all('*:has-text("Ranking")')
            for i, el in enumerate(elements):
                outer_html = await el.evaluate('el => el.outerHTML')
                print(f"Element {i} with 'Ranking': {outer_html}")
            return None

        await dropdown.click()
        await page.wait_for_timeout(1000)
        dropdown_container = await page.query_selector('div.v-menu__content')
        if dropdown_container:
            container_html = await dropdown_container.evaluate('el => el.outerHTML')
            with open(f"{output_dir}/dropdown_html_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(container_html)
            print(f"Dropdown HTML saved to {output_dir}/dropdown_html_{timestamp}.html")

        options = await page.query_selector_all('div.v-list-item__title')
        if not options:
            print("No dropdown options found with primary selector, trying fallback.")
            options = await page.query_selector_all('div.v-list-item, option, [role="option"]')

        ranking_options = []
        seen = set()
        for option in options:
            text = await option.inner_text()
            text = text.strip()
            if text and text not in seen:
                ranking_options.append(text)
                seen.add(text)

        if not ranking_options:
            print("No ranking options extracted.")
            return None

        output_file = f"{output_dir}/ranking_options_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(ranking_options, f, indent=2)
        print(f"Ranking options saved to {output_file}")
        return ranking_options

    except Exception as e:
        print(f"Failed to extract or save ranking options: {str(e)}")
        html_content = await page.content()
        with open(f"{output_dir}/debug_page_{timestamp}.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        return None

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

async def match_card_text(url):
    p, browser, context, page, timestamp = await prepare_page(url)
    if not page:
        print("Preparation failed, cannot proceed with scraping.")
        if p:
            await p.stop()
        return

    try:
        await switch_to_list_view(page)
        await save_html_content(page,  "output",timestamp, "listview")
        await save_screenshot(page,  "output",timestamp, "listview")
        await extract_match_card_text(page, "output", timestamp)
    finally:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if p:
            await p.stop()

async def schedule_links(url):
    p, browser, context, page, timestamp = await prepare_page(url)
    if not page:
        print("Preparation failed, cannot proceed with scraping.")
        if p:
            await p.stop()
        return

    try:
        # await switch_to_list_view(page)
        await save_html_content(page,  "output",timestamp, "listview")
        await save_screenshot(page,  "output",timestamp, "listview")
        await extract_schedule_links(page, "output")
    finally:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if p:
            await p.stop()



async def main():
    url = "https://bwfworldtour.bwfbadminton.com/tournament/5222/petronas-malaysia-open-2025/results/2025-01-07"
    await match_card_text(url)

    # url = "https://bwfworldtour.bwfbadminton.com/tournament/5225/toyota-thailand-open-2025/results/2025-05-14"
    # await match_card_text(url)

    # url = "https://bwfworldtour.bwfbadminton.com/tournament/5224/perodua-malaysia-masters-2025/results/2025-05-20"
    # await schedule_links(url)


if __name__ == "__main__":
    asyncio.run(main())