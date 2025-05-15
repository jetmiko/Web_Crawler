import asyncio
import os
import json
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup
import re
from datetime import datetime

async def scrape_bwf():
    url = "https://bwfworldtour.bwfbadminton.com/tournament/5225/toyota-thailand-open-2025/results/2025-05-15"
    output_dir = "output"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch browser with realistic user agent and headers
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
            locale="en-US"
        )
        page = await context.new_page()
        
        # Apply stealth mode to evade bot detection
        await stealth_async(page)
        
        # Set additional headers
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
            # Random delay to mimic human behavior
            await asyncio.sleep(random.uniform(1, 3))
            
            # Navigate to page and wait for content to load
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait longer for Cloudflare or dynamic content
            await page.wait_for_timeout(25000)  # Wait 25 seconds for JavaScript challenges
            
            # Try to accept cookies if a cookie banner exists
            try:
                await page.click('button:has-text("Accept"), [id*="cookie"], [class*="cookie"]', timeout=5000)
                print("Clicked cookie consent button.")
            except:
                print("No cookie consent button found.")
            
            # Check for CAPTCHA or block page
            try:
                captcha = await page.query_selector('[id*="captcha"], [class*="captcha"]')
                if captcha:
                    print("Warning: CAPTCHA detected. Manual intervention may be required.")
            except:
                pass
            
            # Check page title to detect block
            title = await page.title()
            print(f"Page Title: {title}")
            if "blocked" in title.lower() or "cloudflare" in title.lower():
                print("Warning: Page title suggests a Cloudflare block.")
            
            # Save a screenshot for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(output_dir, f"screenshot_{timestamp}.png")
            await page.screenshot(path=screenshot_path)
            print(f"Saved screenshot to {screenshot_path}")
            
            # Get the fully rendered HTML
            html_content = await page.content()
            
            # Save HTML to output folder
            html_filename = os.path.join(output_dir, f"bwf_results_{timestamp}.html")
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved HTML to {html_filename}")
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Check for Cloudflare block page
            block_text = soup.find(string=re.compile("cloudflare|blocked|ray id", re.I))
            if block_text:
                print(f"Error: HTML contains Cloudflare block page. Block text: {block_text[:100]}...")
                # Check for partial content
                match_cards = soup.select("div.match-card")
                if match_cards:
                    print("Found partial match data despite block. Attempting to extract.")
                else:
                    print("No match data found in block page.")
                    return
            
            # Extract match data from match-card containers
            matches = []
            match_cards = soup.select("div.match-card")
            print(f"\nFound {len(match_cards)} match cards.")
            
            for i, card in enumerate(match_cards, 1):
                match_data = {"match_number": f"Match {i}"}
                
                # Extract team names
                participant_wrappers = card.select("div.participant-wrapper")
                if len(participant_wrappers) >= 2:
                    # Team 1
                    team1_names = participant_wrappers[0].select("a.participant-name")
                    match_data["team1"] = [name.get_text(strip=True) for name in team1_names]
                    
                    # Team 2
                    team2_names = participant_wrappers[1].select("a.participant-name")
                    match_data["team2"] = [name.get_text(strip=True) for name in team2_names]
                
                # Extract scores
                score_sets = card.select("div.game-score-set")
                match_data["scores"] = []
                for set_elem in score_sets:
                    points = set_elem.select("span.set-points")
                    if len(points) == 2:
                        team1_score = points[0].get_text(strip=True)
                        team2_score = points[1].get_text(strip=True)
                        match_data["scores"].append({"team1": team1_score, "team2": team2_score})
                
                matches.append(match_data)
            
            # Print and save match data
            if matches:
                print("\nMatch Data Found:")
                for match in matches:
                    print(f"\n{match['match_number']}:")
                    print(f"Team 1: {', '.join(match['team1'])}")
                    print(f"Team 2: {', '.join(match['team2'])}")
                    print("Scores:")
                    for i, score in enumerate(match['scores'], 1):
                        print(f"  Set {i}: Team 1 ({score['team1']}) - Team 2 ({score['team2']})")
                
                # Save match data to JSON file
                json_filename = os.path.join(output_dir, f"match_data_{timestamp}.json")
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(matches, f, ensure_ascii=False, indent=2)
                print(f"\nSaved match data to {json_filename}")
            else:
                print("\nNo match data found. Check the saved HTML and screenshot for changes in structure or missing results.")
                
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            # Save HTML and screenshot even on error
            html_content = await page.content()
            html_filename = os.path.join(output_dir, f"bwf_results_error_{timestamp}.html")
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved error HTML to {html_filename}")
            await page.screenshot(path=os.path.join(output_dir, f"screenshot_error_{timestamp}.png"))
            
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_bwf())