import asyncio
import os
import json
import random
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup
import re

async def scrape_bwf(url, output_dir="output"):
    """Scrape badminton match data from BWF World Tour website.
    
    Args:
        url (str): URL of the BWF tournament results page
        output_dir (str): Directory to save output files
    
    Returns:
        list: List of match data dictionaries, or None if scraping fails
    """
    # Configuration
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    async with async_playwright() as p:
        # Initialize browser with randomized user-agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0"
        ]
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={"width": random.randint(1200, 1400), "height": random.randint(700, 900)},
            java_script_enabled=True,
            locale="en-US"
        )
        page = await context.new_page()
        await stealth_async(page)

        # Set HTTP headers
        await page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive"
        })

        try:
            # Navigate to page
            await asyncio.sleep(random.uniform(2, 5))  # Random delay
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(30000)  # Wait for Cloudflare

            # Handle cookie consent
            try:
                await page.click('button:has-text("Accept"), [id*="cookie"], [class*="cookie"]', timeout=5000)
                print("Clicked cookie consent button.")
            except:
                print("No cookie consent button found.")

            # Check for CAPTCHA
            try:
                captcha = await page.query_selector('[id*="captcha"], [class*="captcha"]')
                if captcha:
                    print("Warning: CAPTCHA detected. Manual intervention may be required.")
            except:
                pass

            # Check for block page
            title = await page.title()
            print(f"Page Title: {title}")
            if "blocked" in title.lower() or "cloudflare" in title.lower():
                print("Warning: Page title suggests a Cloudflare block.")

            # Click List View
            try:
                list_view_selector = '#switchListView, input[name="corporateSwitch"][value="listView"]'
                await page.wait_for_selector(list_view_selector, timeout=15000)
                await page.click(list_view_selector)
                print("Clicked List View radio input.")
                await page.wait_for_timeout(5000)
            except Exception as e:
                print(f"Failed to click List View radio input: {str(e)}")
                try:
                    label_selector = 'label[for="switchListView"], label:has-text("List View")'
                    await page.wait_for_selector(label_selector, timeout=10000)
                    await page.click(label_selector)
                    print("Clicked List View label as fallback.")
                    await page.wait_for_timeout(5000)
                except Exception as e2:
                    print(f"Failed to click List View label: {str(e2)}")

            # Save screenshot
            screenshot_path = os.path.join(output_dir, f"screenshot_{timestamp}.png")
            await page.screenshot(path=screenshot_path)
            print(f"Saved screenshot to {screenshot_path}")

            # Get and save HTML
            html_content = await page.content()
            html_filename = os.path.join(output_dir, f"bwf_results_{timestamp}.html")
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved HTML to {html_filename}")

            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")

            # Check for Cloudflare block
            block_text = soup.find(string=re.compile("cloudflare|blocked|ray id", re.I))
            if block_text:
                print(f"Error: HTML contains Cloudflare block page. Block text: {block_text[:100]}...")
                match_cards = soup.select("div.match-card")
                if match_cards:
                    print("Found partial match data despite block. Attempting to extract.")
                else:
                    print("No match data found in block page.")
                    return None

            # Extract tournament name
            tournament_elem = soup.select_one("div.page-hero-header-text h2")
            tournament_name = tournament_elem.get_text(strip=True) if tournament_elem else None
            print(f"Tournament Name: {tournament_name if tournament_name else 'Not found'}")

            # Extract and format event date
            event_date_elem = soup.select_one("div.col-md-6.schedule-header span.event-date")
            event_date = None
            if event_date_elem:
                date_str = event_date_elem.get_text(strip=True)
                try:
                    # Parse date from format "Saturday, May 17, 2025"
                    parsed_date = datetime.strptime(date_str, "%A, %B %d, %Y")
                    # Convert to YYYY-MM-DD for Supabase
                    event_date = parsed_date.strftime("%Y-%m-%d")
                except ValueError as e:
                    print(f"Failed to parse date '{date_str}': {str(e)}")
            print(f"Event Date: {event_date if event_date else 'Not found'}")

            # Extract match data
            matches = []
            current_court = None
            current_venue = None

            elements = soup.select("div.court-header, div.match-card")
            for elem in elements:
                if elem.has_attr("class") and "court-header" in elem["class"]:
                    # Update court and venue
                    court_elem = elem.select_one("h3")
                    venue_elem = elem.select_one("span.venue-name")
                    current_court = court_elem.get_text(strip=True) if court_elem else None
                    current_venue = venue_elem.get_text(strip=True) if venue_elem else None
                    print(f"Found court header: {current_court}, Venue: {current_venue}")

                elif elem.has_attr("class") and "match-card" in elem["class"]:
                    # Initialize match data
                    match_data = {
                        "tournament_name": tournament_name,
                        "date": event_date,
                        "court": current_court,
                        "venue": current_venue,
                        "winner": None,
                        "category": None,      # First footer label (e.g., MD)
                        "round": None,         # Second footer label (e.g., SF)
                        "schedule_status": None,  # Schedule status (e.g., Starts)
                        "schedule_date": None    # Schedule date (e.g., 12:00 PM)
                    }

                    # Extract match number
                    match_name_elem = elem.select_one("span.match-name")
                    match_data["match_number"] = match_name_elem.get_text(strip=True) if match_name_elem else "Unknown Match"

                    # Extract team names, country codes, status badges, and winner
                    participant_wrappers = elem.select("div.participant-wrapper")
                    match_data["team1"] = []
                    match_data["team2"] = []
                    if len(participant_wrappers) >= 2:
                        # Team 1
                        for name_elem in participant_wrappers[0].select("a.participant-name"):
                            player_name = name_elem.get_text(strip=True)
                            country_code = name_elem.get("data-country-code", None)
                            status_badge_elem = participant_wrappers[0].select_one("span.status-badge")
                            status_badge = status_badge_elem.get_text(strip=True) if status_badge_elem else None
                            match_data["team1"].append({
                                "name": player_name,
                                "country_code": country_code,
                                "status_badge": status_badge
                            })
                        # Team 2
                        for name_elem in participant_wrappers[1].select("a.participant-name"):
                            player_name = name_elem.get_text(strip=True)
                            country_code = name_elem.get("data-country-code", None)
                            status_badge_elem = participant_wrappers[1].select_one("span.status-badge")
                            status_badge = status_badge_elem.get_text(strip=True) if status_badge_elem else None
                            match_data["team2"].append({
                                "name": player_name,
                                "country_code": country_code,
                                "status_badge": status_badge
                            })

                        # Check for winner
                        if participant_wrappers[0].select_one("div.winner-dot"):
                            match_data["winner"] = "team1"
                        elif participant_wrappers[1].select_one("div.winner-dot"):
                            match_data["winner"] = "team2"

                    # If no status badge in participant wrappers, check match-card level and infer team
                    if not any(p["status_badge"] for team in (match_data["team1"], match_data["team2"]) for p in team):
                        status_badge_elem = elem.select_one("span.status-badge")
                        if status_badge_elem:
                            status_badge = status_badge_elem.get_text(strip=True)
                            # Infer team based on scores (e.g., team with "0" or fewer sets may have retired)
                            scores = []
                            for set_elem in elem.select("div.game-score-set"):
                                points = set_elem.select("span.set-points")
                                if len(points) == 2:
                                    scores.append({
                                        "team1": points[0].get_text(strip=True),
                                        "team2": points[1].get_text(strip=True)
                                    })
                            # If last set has a "0" score, assign status to that team
                            if scores and scores[-1]["team1"] == "0":
                                for player in match_data["team1"]:
                                    player["status_badge"] = status_badge
                            elif scores and scores[-1]["team2"] == "0":
                                for player in match_data["team2"]:
                                    player["status_badge"] = status_badge
                            # If no clear score indicator, assign to team2 as a fallback
                            else:
                                for player in match_data["team2"]:
                                    player["status_badge"] = status_badge

                    # Extract scores
                    match_data["scores"] = []
                    for set_elem in elem.select("div.game-score-set"):
                        points = set_elem.select("span.set-points")
                        if len(points) == 2:
                            match_data["scores"].append({
                                "team1": points[0].get_text(strip=True),
                                "team2": points[1].get_text(strip=True)
                            })

                    # Extract footer labels and map to category and round
                    footer_labels = elem.select("div.court-details-wrapper span.footer-label")
                    footer_label_list = [label.get_text(strip=True) for label in footer_labels]
                    if footer_label_list:
                        # First label -> category
                        if len(footer_label_list) >= 1:
                            match_data["category"] = footer_label_list[0]
                        # Second label -> round
                        if len(footer_label_list) >= 2:
                            match_data["round"] = footer_label_list[1]
                        # Third label (e.g., Court 1) is ignored
                        print(f"Footer labels for {match_data['match_number']}: {footer_label_list}")

                    # Extract schedule status and date
                    schedule_status_elem = elem.select_one("span.schedule-status")
                    schedule_date_elem = elem.select_one("span.schedule-date")
                    match_data["schedule_status"] = schedule_status_elem.get_text(strip=True) if schedule_status_elem else None
                    match_data["schedule_date"] = schedule_date_elem.get_text(strip=True) if schedule_date_elem else None
                    if match_data["schedule_status"] or match_data["schedule_date"]:
                        print(f"Schedule for {match_data['match_number']}: Status={match_data['schedule_status']}, Date={match_data['schedule_date']}")

                    matches.append(match_data)

            # Output results
            if matches:
                print("\nMatch Data Found:")
                for match in matches:
                    print(f"\n{match['match_number']}:")
                    print(f"Tournament: {match['tournament_name']}")
                    print(f"Date: {match['date']}")
                    print(f"Court: {match['court']}")
                    print(f"Venue: {match['venue']}")
                    if match["winner"]:
                        print(f"Winner: {match['winner']}")
                    print(f"Category: {match['category']}")
                    print(f"Round: {match['round']}")
                    print(f"Schedule Status: {match['schedule_status']}")
                    print(f"Schedule Date: {match['schedule_date']}")
                    print("Team 1: " + ", ".join(
                        f"{p['name']} ({p['country_code']})" + (f" [{p['status_badge']}]" if p['status_badge'] else "")
                        for p in match['team1']
                    ))
                    print("Team 2: " + ", ".join(
                        f"{p['name']} ({p['country_code']})" + (f" [{p['status_badge']}]" if p['status_badge'] else "")
                        for p in match['team2']
                    ))
                    print("Scores:")
                    for i, score in enumerate(match['scores'], 1):
                        print(f"  Set {i}: Team 1 ({score['team1']}) - Team 2 ({score['team2']})")

                # Save to JSON
                json_filename = os.path.join(output_dir, f"match_data_{timestamp}.json")
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(matches, f, ensure_ascii=False, indent=2)
                print(f"\nSaved match data to {json_filename}")
            else:
                print("\nNo match data found. Check the saved HTML and screenshot for changes in structure or missing results.")

            return matches

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            html_content = await page.content()
            html_filename = os.path.join(output_dir, f"bwf_results_error_{timestamp}.html")
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved error HTML to {html_filename}")
            await page.screenshot(path=os.path.join(output_dir, f"screenshot_error_{timestamp}.png"))
            return None

        finally:
            await context.close()
            await browser.close()