from playwright.async_api import async_playwright
import sys
import asyncio
from genlib import prepare_page, save_html_content, save_screenshot  
from supalib import save_tour_to_supabase, bwf_calendar_to_supabase, bwf_tour_to_supabase, bwf_schedule_to_supabase
from jsonlib import get_string_array_from_json, delete_files_by_extension, add_id_to_json, read_json_list, extract_number_from_filename
from datetime import datetime
import json
import asyncio
import os
import glob

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


async def extract_match_card_text(page, output_dir, timestamp, id = "01", result_file="match"):
    """Extract structured text from match-card elements and save to JSON with processed page title in each card."""
    try:
        # Extract and process page title
        full_title = (await page.title()).strip()
        # Split on " | " and take the second part; fallback to full title if no delimiter
        page_title = full_title.split(" | ")[1].strip() if " | " in full_title else full_title

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

            # Add processed page title to card data
            card_data["Tour"] = page_title
            card_data["id"] = id

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
                
                # Check if Team 1 is winner
                team1_winner_dot = await team1_wrapper.query_selector('div.winner-dot')
                card_data["Team_1_Winner"] = team1_winner_dot is not None

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
                
                # Check if Team 2 is winner
                team2_winner_dot = await team2_wrapper.query_selector('div.winner-dot')
                card_data["Team_2_Winner"] = team2_winner_dot is not None

            # Determine overall winner
            if card_data.get("Team_1_Winner"):
                card_data["Winner"] = 1
            elif card_data.get("Team_2_Winner"):
                card_data["Winner"] = 2
            else:
                card_data["Winner"] = 0

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

        output_file = f"{output_dir}/{result_file}_{id}_{timestamp}.json"
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
    

async def extract_calendar(page, output_dir, timestamp):
    """Extract structured text from tournament-card elements and save to JSON with processed page title."""
    try:
        # Extract and process page title
        full_title = (await page.title()).strip()
        # Split on " | " and take the second part; fallback to full title if no delimiter
        page_title = full_title.split(" | ")[1].strip() if " | " in full_title else full_title

        # Select the tournamentList container
        tournament_list = await page.query_selector('div.tournamentList')
        if not tournament_list:
            print("No tournament list found.")
            html_content = await page.content()
            with open(f"{output_dir}/debug_page_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            return None

        # Initialize data structure
        tournament_data = []
        current_month = None

        # Select all elements within tournamentList
        elements = await tournament_list.query_selector_all('h2.title-nolink, div.tmt-card-wrapper')

        for element in elements:
            # Check if the element is a month header
            if await element.evaluate('el => el.classList.contains("title-nolink")'):
                current_month = (await element.inner_text()).strip()
                continue

            # Process tournament card
            card_data = {"Month": current_month} if current_month else {}
            card_data["Tour"] = page_title

            # Extract link
            link_el = await element.query_selector('a')
            if link_el:
                card_data["Link"] = (await link_el.get_attribute('href')).strip()

            # Extract tournament logo
            logo_el = await element.query_selector('div.logo-wrapper img')
            if logo_el:
                card_data["Logo_URL"] = (await logo_el.get_attribute('src')).strip()

            # Extract tournament details
            details_el = await element.query_selector('div.tmt-details')
            if details_el:
                # Date
                date_el = await details_el.query_selector('div.date span')
                if date_el:
                    card_data["Date"] = (await date_el.inner_text()).strip()

                # Tournament Name
                name_el = await details_el.query_selector('span.name')
                if name_el:
                    card_data["Tournament_Name"] = (await name_el.inner_text()).strip()

                # Country and City
                country_el = await details_el.query_selector('div.country')
                if country_el:
                    country_text = (await country_el.inner_text()).strip()
                    card_data["Location"] = country_text
                    country_img = await country_el.query_selector('img')
                    if country_img:
                        card_data["Country"] = (await country_img.get_attribute('alt')).strip()

                # Category and Prize Money
                labels_el = await details_el.query_selector('div.labels[style*="margin-top"]')
                if labels_el:
                    category_el = await labels_el.query_selector('div.label-category')
                    if category_el:
                        card_data["Category"] = (await category_el.inner_text()).strip()
                    prize_el = await labels_el.query_selector('div.prize-money')
                    if prize_el:
                        card_data["Prize_Money"] = (await prize_el.inner_text()).strip()

                # Category Logo
                category_logo_el = await details_el.query_selector('div.category-logo img')
                if category_logo_el:
                    card_data["Category_Logo_URL"] = (await category_logo_el.get_attribute('src')).strip()

            # Extract header images
            header_img_desktop = await element.query_selector('div.header-img img.header-img-desktop')
            if header_img_desktop:
                card_data["Header_Image_Desktop_URL"] = (await header_img_desktop.get_attribute('src')).strip()

            header_img_mobile = await element.query_selector('div.header-img img.header-img-mobile')
            if header_img_mobile:
                card_data["Header_Image_Mobile_URL"] = (await header_img_mobile.get_attribute('src')).strip()

            # Extract Etihad logo link if present
            etihad_el = await element.query_selector('a.etihad-logo')
            if etihad_el:
                etihad_img = await etihad_el.query_selector('img')
                if etihad_img:
                    card_data["Etihad_Logo_URL"] = (await etihad_img.get_attribute('src')).strip()

            if card_data:
                tournament_data.append(card_data)

        if not tournament_data:
            print("No data extracted from tournament cards.")
            return None

        output_file = f"{output_dir}/calendar_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(tournament_data, f, indent=2)
        print(f"Tournament calendar text saved to {output_file}")
        return tournament_data

    except Exception as e:
        print(f"Failed to extract tournament calendar text: {str(e)}")
        html_content = await page.content()
        with open(f"{output_dir}/debug_page_{timestamp}.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        return None

async def extract_schedule_links(page, output_dir, id):
    """Extract all schedule links from the days-tabs element and save to JSON."""
    try:
        # Generate timestamp for the output file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Try to find the tabs container with multiple selectors
        tabs_container = None
        
        # First try: ajaxTabsResults with full class
        tabs_container = await page.query_selector('ul#ajaxTabsResults.content-tabs.days-tabs')
        if tabs_container:
            print("Found schedule tabs with id='ajaxTabsResults'")
        else:
            # Second try: ajaxTabs with content-tabs class only
            tabs_container = await page.query_selector('ul#ajaxTabs.content-tabs')
            if tabs_container:
                print("Found schedule tabs with id='ajaxTabs' (fallback)")
            else:
                # Third try: ajaxTabs without class restriction
                tabs_container = await page.query_selector('ul#ajaxTabs')
                if tabs_container:
                    print("Found schedule tabs with id='ajaxTabs' (generic fallback)")
                else:
                    # Fourth try: any ul with content-tabs class
                    tabs_container = await page.query_selector('ul.content-tabs')
                    if tabs_container:
                        print("Found schedule tabs with class 'content-tabs' (broad fallback)")
                    else:
                        print("No schedule tabs found with any of the expected selectors.")
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
        # output_file = f"{output_dir}/schedule_links_{timestamp}.json"
        output_file = f"{output_dir}/schedule_links_{id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(links, f, indent=2)
        print(f"Schedule links saved to {output_file}")
        print(f"Total links extracted: {len(links)}")
        
        return links
    
    except Exception as e:
        print(f"Failed to extract schedule links: {str(e)}")
        return None



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

async def match_card_text(url, id = "01", output = 'output', saving = False):
    p, browser, context, page, timestamp = await prepare_page(url)
    if not page:
        print("Preparation failed, cannot proceed with scraping.")
        if p:
            await p.stop()
        return

    try:
        await switch_to_list_view(page)
        await save_html_content(page, output, timestamp, "listview")
        await save_screenshot(page, output, timestamp, "listview")
        await extract_match_card_text(page, output, timestamp, id)
        # Load scraped data into Supabase
        if saving:
            # result = await save_tour_to_supabase("output")
            result = await bwf_tour_to_supabase(output)
            print(f"Supabase insertion result: {result['message']}")
    finally:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if p:
            await p.stop()

async def do_extract_calendar(url):
    p, browser, context, page, timestamp = await prepare_page(url)
    if not page:
        print("Preparation failed, cannot proceed with scraping.")
        if p:
            await p.stop()
        return

    try:
        await save_html_content(page, "output", timestamp, "calendar")
        await save_screenshot(page, "output", timestamp, "calendar")
        await extract_calendar(page, "output", timestamp)
        # Load scraped data into Supabase
        # result = await save_tour_to_supabase("output")
        # print(f"Supabase insertion result: {result['message']}")
    finally:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if p:
            await p.stop()

async def schedule_links(url, id):
    p, browser, context, page, timestamp = await prepare_page(url)
    if not page:
        print("Preparation failed, cannot proceed with scraping.")
        if p:
            await p.stop()
        return

    try:
        await save_html_content(page, "output", timestamp, "listview")
        await save_screenshot(page, "output", timestamp, "listview")
        links = await extract_schedule_links(page, "output", id)
        return links
    finally:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if p:
            await p.stop()


async def loop_schedule_links(prefix="schedule_links", folder="input"):
    # Cek apakah folder ada
    if not os.path.exists(folder):
        raise FileNotFoundError(f"Folder '{folder}' tidak ditemukan")
    
    # Cari file yang dimulai dengan prefix di dalam folder
    files = [f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith('.json')]
    print(f"File ditemukan di {folder}: {files}")  # Debugging
    
    if not files:
        raise FileNotFoundError(f"Tidak ada file yang ditemukan dengan awalan '{prefix}' di folder '{folder}'")
    
    # Ambil file pertama yang cocok
    json_filename = files[0]
    json_path = os.path.join(folder, json_filename)
    
    print(f"Membuka file: {json_path}")
    
    # Baca file JSON
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            urls = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Gagal membaca file JSON: {e}")
    
    # Buat task untuk setiap URL
    tasks = [schedule_links(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results


async def get_schedule_links(urls, ids):
    """
    Menjalankan schedule_links secara sequential (satu per satu) untuk setiap URL.
    
    Args:
        urls: List berisi URL yang akan diproses
        
    Returns:
        List berisi hasil dari setiap URL
    """
    results = []
    
    i = 0
    for url in urls:
        try:
            result = await schedule_links(url, ids[i])
            results.append(result)
            i = i+1
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            results.append(None)  # atau bisa append error message
    
    return results



async def loop_files_schedule(prefix="schedule_links", folder="input"):
    # Cek apakah folder ada
    if not os.path.exists(folder):
        raise FileNotFoundError(f"Folder '{folder}' tidak ditemukan")
    
    # Cari file yang dimulai dengan prefix di dalam folder
    files = [f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith('.json')]
    print(f"File ditemukan di {folder}: {files}")  # Debugging
    
    if not files:
        raise FileNotFoundError(f"Tidak ada file yang ditemukan dengan awalan '{prefix}' di folder '{folder}'")
    
    # Ambil file pertama yang cocok
    json_filename = files[0]
    json_path = os.path.join(folder, json_filename)
    
    print(f"Membuka file: {json_path}")
    
    # Baca file JSON
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            urls = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Gagal membaca file JSON: {e}")
    
    # Buat task untuk setiap URL

    return "dummy"


async def process_schedule_json():
    # Mendapatkan daftar semua file JSON di folder input/schedule
    json_files = glob.glob(os.path.join("input", "schedule", "*.json"))
    
    if not json_files:
        print("Tidak ada file JSON ditemukan di folder input/schedule")
        return
    
    print("\nMemproses file JSON:")
    for json_file in json_files:
        # Mendapatkan nama file dari path
        filename = os.path.basename(json_file)
        print(f"\nMemproses file: {filename}")
        
        # Ekstrak ID dari nama file
        id = extract_number_from_filename(filename)
        
        # Baca isi file JSON
        urls = read_json_list(os.path.join("input", "schedule"), filename)
        
        # Proses setiap URL dalam file JSON
        print("Hasil pemrosesan:")
        for url in urls:
            print(url)
            await match_card_text(url, id)


# Fungsi untuk meminta input dan menyimpan ke variabel global
async def get_match_input():
    global url, id, output, saving

    url = input("Masukkan URL (kosongkan untuk skip): ") or None
    id = input("Masukkan ID (default '130'): ") or "130"
    output = input("Masukkan nama output (default 'output'): ") or "output"

    saving_input = input("Simpan data? (y/n, default 'n'): ").lower()
    saving = saving_input == 'y'

    print(f"url = {url}")
    print(f"id = {id}")
    print(f"output = {output}")
    print(f"saving = {saving}")

    await match_card_text(url, id, output, saving)



async def main():
    if len(sys.argv) < 2:
        print("Gunakan: python gen.py [1|2|3|4|10|11]")
        return

    option = sys.argv[1]

    if option == "1":
        url = "https://bwfworldtour.bwfbadminton.com/tournament/5222/petronas-malaysia-open-2025/results/2025-01-07"
        await match_card_text(url)
    elif option == "2":
        url = "https://bwfworldtour.bwfbadminton.com/tournament/5225/toyota-thailand-open-2025/results/2025-05-14"
        await match_card_text(url)
    elif option == "3":
        url = "https://bwfworldtour.bwfbadminton.com/tournament/5224/perodua-malaysia-masters-2025/results/2025-05-20"
        await schedule_links(url)
    elif option == "3A":
        hasil = await loop_schedule_links(prefix="schedule_links", folder="input")
        # (Opsional) Cetak hasil
        print("\nHasil pemrosesan:")
        for h in hasil:
            print(h)
    elif option == "3B":
        urls = get_string_array_from_json("calendar.json", "Link", "input")
        ids = get_string_array_from_json("calendar.json", "id", "input")
        print("\nHasil pemrosesan:")
        for h in urls:
            print(h)
        await get_schedule_links(urls, ids)

    elif option == "4":
        url = "https://bwfworldtour.bwfbadminton.com/calendar/?cyear=2025&rstate=all"
        await do_extract_calendar(url)

    elif option == "5":
        filename = "schedule_links_01.json"
        id = extract_number_from_filename(filename)
        urls = read_json_list("input", filename)

        print("\nHasil pemrosesan:")
        for h in urls:
            print(h)
            await match_card_text(h, id)

    elif option == "5A":
        filename = "schedule_links_130.json"
        id = extract_number_from_filename(filename)
        urls = read_json_list("input/schedule", filename)

        print("\nHasil pemrosesan:")
        for h in urls:
            print(h)
            await match_card_text(h, id)

    elif option == "6":
        await process_schedule_json()


    elif option == "10":  # SAVE TABLE TOUR KE SUPABASE
        result = await save_tour_to_supabase("output")
        print(f"Supabase insertion result: {result['message']}")
    elif option == "11":  # SAVE TABLE CALENDAR KE SUPABASE
        result = await bwf_calendar_to_supabase("input")
        print(f"Supabase insertion result: {result['message']}")
    elif option == "12":  # SAVE TOUR KE SUPABASE
        result = await bwf_tour_to_supabase("output")
        print(f"Supabase insertion result: {result['message']}")
    elif option == "savetour":  # SAVE TOUR KE SUPABASE
        result = await bwf_tour_to_supabase("output")
        print(f"Supabase insertion result: {result['message']}")
    elif option == "savetourall":  # SAVE TOUR KE SUPABASE
        result = await bwf_tour_to_supabase("output1")
        print(f"Supabase insertion result: {result['message']}")
    elif option == "saveschedule":
        await bwf_schedule_to_supabase()

    elif option == "match":
        await get_match_input()

    elif option == "del":  # SAVE TABLE CALENDAR KE SUPABASE
        delete_files_by_extension("output", ".png")
        delete_files_by_extension("output", ".html")
        delete_files_by_extension("output1", ".png")
        delete_files_by_extension("output1", ".html")
        delete_files_by_extension("output2", ".png")
        delete_files_by_extension("output2", ".html")
    elif option == "101":  # SAVE TABLE CALENDAR KE SUPABASE
        add_id_to_json("input", "calendar.json")

    else:
        print("Opsi tidak valid. Gunakan: 1, 2, atau 3")

if __name__ == "__main__":
    asyncio.run(main())