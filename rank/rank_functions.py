import asyncio
import os
import random
import json
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup
import re

async def initialize_browser():
    """Inisialisasi browser Playwright dengan konteks dan halaman."""
    try:
        p = await async_playwright().start()
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
        
        return p, browser, context, page
    except Exception as e:
        print(f"Gagal menginisialisasi browser: {str(e)}")
        return None, None, None, None

async def navigate_to_page(page, url):
    """Navigasi ke URL dengan penundaan acak."""
    try:
        await asyncio.sleep(random.uniform(2, 5))
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(10000)
        print(f"Berhasil navigasi ke {url}")
        return True
    except Exception as e:
        print(f"Gagal navigasi ke {url}: {str(e)}")
        return False

async def handle_cookie_consent(page):
    """Menangani persetujuan cookie (Cookiebot)."""
    try:
        cookie_button = await page.wait_for_selector(
            '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowallSelection, '
            '#CybotCookiebotDialogBodyButtonAcceptAll, '
            'button:has-text("Allow selection"), '
            'button:has-text("Allow all"), '
            'button:has-text("Accept")',
            timeout=10000
        )
        await cookie_button.click(force=True)
        print("Klik tombol persetujuan cookie.")
        await page.wait_for_timeout(2000)
        return True
    except:
        print("Tombol persetujuan cookie tidak ditemukan.")
        return True

async def check_captcha(page):
    """Memeriksa keberadaan CAPTCHA."""
    try:
        captcha = await page.query_selector('[id*="captcha"], [class*="captcha"]')
        if captcha:
            print("Peringatan: CAPTCHA terdeteksi. Intervensi manual mungkin diperlukan.")
            return True
        return False
    except:
        return False

async def save_ranking_options_to_json(page, output_dir="output"):
    """Mengambil daftar opsi dropdown 'Ranking' dan menyimpannya ke file JSON."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)

    try:
        ranking_selector = 'div.select div.v-select__slot:has(> label:has-text("Ranking"))'
        await page.wait_for_selector(ranking_selector, timeout=15000)
        print("Elemen dropdown berlabel 'Ranking' ditemukan.")
        
        await page.click(ranking_selector, force=True)
        await page.wait_for_timeout(2000)

        options = await page.query_selector_all('div.v-menu__content div[role="listbox"] div.v-list-item__title')
        ranking_options = []
        print("Opsi dropdown 'Ranking' yang tersedia:")
        for opt in options:
            text = await opt.inner_text()
            ranking_options.append(text)
            print(f"- {text}")

        json_path = os.path.join(output_dir, f"ranking_options_{timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(ranking_options, f, indent=2, ensure_ascii=False)
        print(f"Menyimpan opsi dropdown Ranking ke {json_path}")

        return ranking_options
    except Exception as e:
        print(f"Peringatan: Gagal mendapatkan atau menyimpan opsi dropdown Ranking: {str(e)}")
        return []
    
async def get_ranking_options(page):

    try:
        ranking_selector = 'div.select div.v-select__slot:has(> label:has-text("Ranking"))'
        await page.wait_for_selector(ranking_selector, timeout=15000)
        print("Elemen dropdown berlabel 'Ranking' ditemukan.")
        
        await page.click(ranking_selector, force=True)
        await page.wait_for_timeout(2000)

        options = await page.query_selector_all('div.v-menu__content div[role="listbox"] div.v-list-item__title')
        ranking_options = []
        print("Opsi dropdown 'Ranking' yang tersedia:")
        for opt in options:
            text = await opt.inner_text()
            ranking_options.append(text)
            print(f"- {text}")

        return ranking_options
    except Exception as e:
        print(f"Peringatan: Gagal mendapatkan atau menyimpan opsi dropdown Ranking: {str(e)}")
        return []



async def select_ranking_option(page, ranking_option="BWF World Tour Rankings"):
    # """Memilih opsi tertentu dari dropdown 'Ranking'."""
    # if not ranking_options:
    #     print("Tidak ada opsi dropdown 'Ranking' yang tersedia untuk dipilih.")
    #     return False

    try:
        selector = f'div.v-menu__content div[role="listbox"] div.v-list-item__title:text-matches("{ranking_option}", "i")'
        await page.wait_for_selector(selector, timeout=10000)
        await page.click(selector, force=True)
        print(f"Berhasil memilih item dropdown yang memuat '{ranking_option}'.")
        await page.wait_for_timeout(3000)
        return True
    except Exception as e:
        print(f"Gagal memilih item dropdown '{ranking_option}': {str(e)}")
        return False

async def save_week_options_to_json(page, output_dir="output"):
    """Mengambil opsi dropdown 'Week' dan menyaring hanya opsi yang sesuai format Week."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)

    try:
        week_selector = 'div.select div.v-select__slot:has(> label:has-text("Week"))'
        await page.wait_for_selector(week_selector, timeout=15000)
        print("Elemen dropdown berlabel 'Week' ditemukan.")
        
        await page.click(week_selector, force=True)
        await page.wait_for_timeout(2000)

        options = await page.query_selector_all('div.v-menu__content div[role="listbox"] div.v-list-item__title')
        raw_texts = []
        for opt in options:
            text = await opt.inner_text()
            raw_texts.append(text.strip())

        week_pattern = re.compile(r'^Week\s+\d+', re.IGNORECASE)
        week_options = [text for text in raw_texts if week_pattern.match(text)]

        json_path = os.path.join(output_dir, f"week_options_{timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(week_options, f, indent=2, ensure_ascii=False)
        print(f"Menyimpan opsi dropdown Week ke {json_path}")

        return week_options
    except Exception as e:
        print(f"Peringatan: Gagal mendapatkan atau menyimpan opsi dropdown Week: {str(e)}")
        return []

async def select_week_option(page, week_options, target_week="Week 8"):
    """
    Fungsi tandingan untuk memilih opsi tertentu dari dropdown 'Week' menggunakan logika asli.
    
    Args:
        page (Page): Objek halaman Playwright.
        week_options (list): Daftar opsi dropdown Week yang telah diambil.
        target_week (str): Nama opsi minggu yang ingin dipilih (default: 'Week 8').
                         Bisa berupa 'Week X', 'X', atau opsi lengkap seperti 'Week X (YYYY-MM-DD)'.
    
    Returns:
        bool: True jika opsi berhasil dipilih, False jika tidak.
    """
    import re
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("output", exist_ok=True)

    if not week_options:
        print("Tidak ada opsi dropdown 'Week' yang ditemukan.")
        return False

    # Normalisasi target_week
    target_week = target_week.strip()
    if target_week.isdigit():
        target_week = f"Week {target_week}"

    # Cari opsi yang cocok
    selected_option = None
    for option in week_options:
        if target_week == option or target_week in option or re.match(rf"Week\s*{re.escape(target_week.split(' ')[1])}\s*\(\d{{4}}-\d{{2}}-\d{{2}}\)", option, re.IGNORECASE):
            selected_option = option
            break

    # Jika tidak ditemukan, pilih opsi terbaru
    if not selected_option:
        selected_option = week_options[0]  # Opsi pertama adalah yang terbaru
        print(f"Peringatan: Opsi '{target_week}' tidak ditemukan dalam daftar: {week_options}. Memilih opsi terbaru: '{selected_option}'")
    elif selected_option != target_week:
        print(f"Peringatan: Opsi '{target_week}' tidak cocok persis. Menggunakan: '{selected_option}'")

    # Blok 1: Coba pilih opsi langsung
    week_selector = f'div.v-menu__content div[role="listbox"] div.v-list-item__title:text("{selected_option}")'
    try:
        await page.wait_for_selector(week_selector, timeout=20000)
        await page.click(week_selector, force=True)
        print(f"Berhasil memilih item dropdown '{selected_option}' pada percobaan pertama.")
        await page.wait_for_timeout(3000)
        return True
    except Exception as e:
        print(f"Peringatan: Gagal memilih item dropdown '{selected_option}' pada percobaan pertama: {str(e)}")

    # Blok 2: Klik dropdown dan pilih opsi
    try:
        dropdown_selector = 'div.select div.v-select__slot:has(> label:has-text("Week"))'
        await page.wait_for_selector(dropdown_selector, timeout=20000)
        print("Elemen dropdown berlabel 'Week' ditemukan.")

        # Coba klik hingga menu terbuka
        for attempt in range(3):
            await page.click(dropdown_selector, force=True)
            menu_selector = 'div.v-menu__content div[role="listbox"]'
            try:
                await page.wait_for_selector(menu_selector, timeout=5000)
                print("Menu dropdown Week terbuka.")
                break
            except:
                print(f"Percobaan {attempt + 1}: Menu dropdown belum terbuka, mencoba lagi...")
                await page.wait_for_timeout(1000)
        else:
            raise Exception("Gagal membuka menu dropdown setelah 3 percobaan.")

        week_selector = f'div.v-menu__content div[role="listbox"] div.v-list-item__title:text-matches("{re.escape(selected_option)}", "i")'
        await page.wait_for_selector(week_selector, timeout=20000)
        await page.click(week_selector, force=True)
        print(f"Berhasil memilih item dropdown yang memuat '{selected_option}'.")
        await page.wait_for_timeout(3000)
        return True
    except Exception as e:
        print(f"Peringatan: Gagal memilih item dropdown yang memuat '{selected_option}': {str(e)}")
        screenshot_path = os.path.join("output", f"screenshot_week_error_{timestamp}.png")
        await page.screenshot(path=screenshot_path)
        print(f"Menyimpan tangkapan layar ke {screenshot_path}")
        return False


async def select_perpage_option(page, output_dir="output", target_perpage="100"):
    """Memilih opsi tertentu dari dropdown 'Per page'."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)

    try:
        perpage_selector = 'div.select.perpage div.v-select__slot:has(> label:has-text("Per page"))'
        await page.wait_for_selector(perpage_selector, timeout=15000)
        print("Elemen dropdown berlabel 'Per page' ditemukan.")
        icon_selector = 'div.select.perpage i.mdi-menu-down'
        await page.click(icon_selector, force=True)
        await page.wait_for_timeout(5000)
        page_selector = f'div.v-menu__content div[role="listbox"] div.v-list-item__title:text-matches("^{target_perpage}$", "i")'
        await page.wait_for_selector(page_selector, timeout=20000)
        await page.click(page_selector, force=True)
        print(f"Berhasil memilih item dropdown yang memuat '{target_perpage}'.")
        await page.wait_for_timeout(3000)
        return True
    except Exception as e:
        print(f"Peringatan: Gagal memilih item dropdown yang memuat '{target_perpage}': {str(e)}")
        screenshot_path = os.path.join(output_dir, f"screenshot_perpage_error_{timestamp}.png")
        await page.screenshot(path=screenshot_path)
        print(f"Menyimpan tangkapan layar ke {screenshot_path}")
        return False

async def check_page_block(page):
    """Memeriksa apakah halaman diblokir berdasarkan judul."""
    title = await page.title()
    print(f"Judul Halaman: {title}")
    if "blocked" in title.lower() or "cloudflare" in title.lower():
        print("Peringatan: Judul halaman menunjukkan blokir Cloudflare.")
        return True
    return False

async def save_screenshot(page, output_dir, timestamp, suffix=""):
    """Menyimpan tangkapan layar halaman."""
    os.makedirs(output_dir, exist_ok=True)
    screenshot_path = os.path.join(output_dir, f"screenshot{suffix}_{timestamp}.png")
    await page.screenshot(path=screenshot_path)
    print(f"Menyimpan tangkapan layar ke {screenshot_path}")
    return screenshot_path

async def save_html_content(page, output_dir, timestamp, filename_prefix="bwf_tournaments"):
    """Menyimpan konten HTML ke file."""
    os.makedirs(output_dir, exist_ok=True)
    html_content = await page.content()
    html_filename = os.path.join(output_dir, f"{filename_prefix}_{timestamp}.html")
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Menyimpan HTML ke {html_filename}")
    return html_filename

async def check_cloudflare_block(html_content):
    """Memeriksa apakah HTML mengandung indikasi blokir Cloudflare."""
    soup = BeautifulSoup(html_content, "html.parser")
    block_text = soup.find(string=re.compile(r"\bcloudflare\b|\bblocked\b|\bray id\b", re.I))
    if block_text:
        print(f"Kesalahan: HTML berisi halaman blokir Cloudflare. Teks blokir: {block_text[:100]}...")
        return True
    return False

async def rank_to_json(url, output_dir="output"):
    """Mengikis halaman dari situs BWF World Tour untuk menyimpan HTML dan opsi dropdown."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)

    p, browser, context, page = await initialize_browser()
    if not page:
        print("Gagal memulai scraping karena inisialisasi browser gagal.")
        return None

    try:
        if not await navigate_to_page(page, url):
            raise Exception("Navigasi ke halaman gagal.")

        await handle_cookie_consent(page)

        if await check_captcha(page):
            print("Scraping dihentikan karena CAPTCHA terdeteksi.")
            return None

        ranking_options = await save_ranking_options_to_json(page, output_dir=output_dir)

        return ranking_options

    except Exception as e:
        print(f"Terjadi kesalahan: {str(e)}")
        if page:
            await save_html_content(page, output_dir, timestamp, filename_prefix="bwf_tournaments_error")
            await save_screenshot(page, output_dir, timestamp, suffix="_error")
        return None

    finally:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if p:
            await p.stop()


async def scrape_rank(url, ranking_option="BWF World Tour Rankings", output_dir="output"):
    """Mengikis halaman dari situs BWF World Tour untuk menyimpan HTML dan opsi dropdown."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)

    p, browser, context, page = await initialize_browser()
    if not page:
        print("Gagal memulai scraping karena inisialisasi browser gagal.")
        return None

    try:
        if not await navigate_to_page(page, url):
            raise Exception("Navigasi ke halaman gagal.")

        await handle_cookie_consent(page)

        if await check_captcha(page):
            print("Scraping dihentikan karena CAPTCHA terdeteksi.")
            return None

        # ranking_options = await save_ranking_options_to_json(page, output_dir=output_dir)
        # ranking_options = await get_ranking_options(page)

        # if not await select_ranking_option(page, ranking_options, ranking_option):
        #     print("Gagal memilih opsi Ranking, melanjutkan dengan opsi default.")

        if not await select_ranking_option(page,ranking_option):
            print("Gagal memilih opsi Ranking, melanjutkan dengan opsi default.")

        week_options = await save_week_options_to_json(page, output_dir=output_dir)

        return week_options

        await select_week_option(page, week_options, target_week="Week 8")

        await select_perpage_option(page, output_dir=output_dir, target_perpage="100")

        if await check_page_block(page):
            return None

        await save_screenshot(page, output_dir, timestamp)

        html_filename = await save_html_content(page, output_dir, timestamp)

        with open(html_filename, "r", encoding="utf-8") as f:
            html_content = f.read()
        if await check_cloudflare_block(html_content):
            return None

        return None

    except Exception as e:
        print(f"Terjadi kesalahan: {str(e)}")
        if page:
            await save_html_content(page, output_dir, timestamp, filename_prefix="bwf_tournaments_error")
            await save_screenshot(page, output_dir, timestamp, suffix="_error")
        return None

    finally:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if p:
            await p.stop()

