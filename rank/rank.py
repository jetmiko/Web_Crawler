import asyncio
import os
import random
import json
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup
import re


async def save_ranking_options_to_json(page, output_dir="output"):
    """Fungsi untuk mengambil daftar opsi dropdown 'Ranking' dan menyimpannya ke file JSON."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Tunggu elemen dropdown Ranking dengan label "Ranking"
        ranking_selector = 'div.select div.v-select__slot:has(> label:has-text("Ranking"))'
        await page.wait_for_selector(ranking_selector, timeout=15000)
        print("Elemen dropdown berlabel 'Ranking' ditemukan.")
        
        # Klik dropdown untuk membuka opsi
        await page.click(ranking_selector, force=True)
        await page.wait_for_timeout(2000)  # Tunggu menu muncul

        # Ambil semua opsi dari dropdown
        options = await page.query_selector_all('div.v-menu__content div[role="listbox"] div.v-list-item__title')
        ranking_options = []
        print("Opsi dropdown 'Ranking' yang tersedia:")
        for opt in options:
            text = await opt.inner_text()
            ranking_options.append(text)
            print(f"- {text}")

        # Simpan ke file JSON
        json_path = os.path.join(output_dir, f"ranking_options_{timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(ranking_options, f, indent=2, ensure_ascii=False)
        print(f"Menyimpan opsi dropdown Ranking ke {json_path}")

        return ranking_options

    except Exception as e:
        print(f"Peringatan: Gagal mendapatkan atau menyimpan opsi dropdown Ranking: {str(e)}")
        return []
    

async def save_week_options_to_json(page, output_dir="output"):
    """Fungsi untuk mengambil opsi dropdown 'Week' dan menyaring hanya opsi yang sesuai format Week."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Tunggu_elemen_dropdown_Week_dengan_label_"Week"
        week_selector = 'div.select div.v-select__slot:has(> label:has-text("Week"))'
        await page.wait_for_selector(week_selector, timeout=15000)
        print("Elemen dropdown berlabel 'Week' ditemukan.")
        
        # Klik dropdown untuk membuka opsi
        await page.click(week_selector, force=True)
        await page.wait_for_timeout(2000)

        # Ambil semua opsi dari dropdown
        options = await page.query_selector_all('div.v-menu__content div[role="listbox"] div.v-list-item__title')
        raw_texts = []
        for opt in options:
            text = await opt.inner_text()
            raw_texts.append(text.strip())

        # Filter hanya opsi yang cocok dengan pola "Week [angka]"
        week_pattern = re.compile(r'^Week\s+\d+', re.IGNORECASE)
        week_options = [text for text in raw_texts if week_pattern.match(text)]

        # Simpan hasil yang sudah difilter
        json_path = os.path.join(output_dir, f"week_options_{timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(week_options, f, indent=2, ensure_ascii=False)
        print(f"Menyimpan opsi dropdown Week (hanya opsi minggu) ke {json_path}")

        return week_options

    except Exception as e:
        print(f"Peringatan: Gagal mendapatkan atau menyimpan opsi dropdown Week: {str(e)}")
        return []

async def select_ranking_option(page, ranking_options, ranking_option="BWF World Tour Rankings"):
    """
    Fungsi untuk memilih opsi tertentu dari dropdown 'Ranking'.
    
    Args:
        page (Page): Objek halaman Playwright.
        ranking_options (list): Daftar opsi dropdown Ranking yang telah diambil.
        ranking_option (str): Nama opsi yang ingin dipilih.
    
    Returns:
        bool: True jika opsi berhasil dipilih, False jika tidak.
    """
    if not ranking_options:
        print("Tidak ada opsi dropdown 'Ranking' yang tersedia untuk dipilih.")
        return False

    try:
        # Buat selector dinamis berdasarkan teks opsi
        selector = f'div.v-menu__content div[role="listbox"] div.v-list-item__title:text-matches("{ranking_option}", "i")'
        
        # Tunggu hingga opsi dapat ditemukan
        await page.wait_for_selector(selector, timeout=10000)
        
        # Klik opsi dropdown
        await page.click(selector, force=True)
        print(f"Berhasil memilih item dropdown yang memuat '{ranking_option}'.")
        
        # Tunggu halaman memperbarui konten
        await page.wait_for_timeout(3000)
        return True
    
    except Exception as e:
        print(f"Gagal memilih item dropdown '{ranking_option}': {str(e)}")
        return False



async def select_week_option(page, week_options, target_week="Week 10"):
    """
    Fungsi tandingan untuk memilih opsi tertentu dari dropdown 'Week' menggunakan logika asli.
    
    Args:
        page (Page): Objek halaman Playwright.
        week_options (list): Daftar opsi dropdown Week yang telah diambil.
        target_week (str): Nama opsi minggu yang ingin dipilih (default: 'Week 10').
    
    Returns:
        bool: True jika opsi berhasil dipilih, False jika tidak.
    """
    if week_options:
        # Pilih salah satu opsi
        week_selector = f'div.v-menu__content div[role="listbox"] div.v-list-item__title:text("{target_week}")'
        try:
            await page.wait_for_selector(week_selector, timeout=10000)
            await page.click(week_selector, force=True)
            print(f"Berhasil memilih item dropdown '{target_week}'.")
            await page.wait_for_timeout(3000)
            return True
        except Exception as e:
            print(f"Peringatan: Gagal memilih item dropdown '{target_week}' pada percobaan pertama: {str(e)}")
    else:
        print("Tidak ada opsi dropdown 'Week' yang ditemukan.")
        return False

    # Pilih item dropdown berlabel "Week" yang memuat target_week
    try:
        dropdown_selector = 'div.select div.v-select__slot:has(> label:has-text("Week"))'
        await page.wait_for_selector(dropdown_selector, timeout=15000)
        print("Elemen dropdown berlabel 'Week' ditemukan.")
        await page.click(dropdown_selector, force=True)
        await page.wait_for_timeout(2000)  # Tunggu opsi muncul
        week_selector = f'div.v-menu__content div[role="listbox"] div.v-list-item__title:text-matches("{target_week}", "i")'
        await page.wait_for_selector(week_selector, timeout=10000)
        await page.click(week_selector, force=True)
        print(f"Berhasil memilih item dropdown yang memuat '{target_week}'.")
        await page.wait_for_timeout(3000)  # Tunggu pembaruan halaman
        return True
    except Exception as e:
        print(f"Peringatan: Gagal memilih item dropdown yang memuat '{target_week}': {str(e)}")
        return False    
    

async def select_perpage_option(page, output_dir="output", target_perpage="25"):
    """
    Fungsi untuk memilih opsi tertentu dari dropdown 'Per page'.
    
    Args:
        page (Page): Objek halaman Playwright.
        output_dir (str): Direktori untuk menyimpan tangkapan layar jika terjadi error.
        target_perpage (str): Nilai opsi yang ingin dipilih (default: '25').
    
    Returns:
        bool: True jika opsi berhasil dipilih, False jika tidak.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)

    try:
        perpage_selector = 'div.select.perpage div.v-select__slot:has(> label:has-text("Per page"))'
        await page.wait_for_selector(perpage_selector, timeout=15000)
        print("Elemen dropdown berlabel 'Per page' ditemukan.")
        icon_selector = 'div.select.perpage i.mdi-menu-down'
        await page.click(icon_selector, force=True)
        await page.wait_for_timeout(5000)  # Tunggu menu opsi muncul
        page_selector = f'div.v-menu__content div[role="listbox"] div.v-list-item__title:text-matches("^{target_perpage}$", "i")'
        await page.wait_for_selector(page_selector, timeout=20000)
        await page.click(page_selector, force=True)
        print(f"Berhasil memilih item dropdown yang memuat '{target_perpage}'.")
        await page.wait_for_timeout(3000)  # Tunggu pembaruan halaman
        return True
    except Exception as e:
        print(f"Peringatan: Gagal memilih item dropdown yang memuat '{target_perpage}': {str(e)}")
        screenshot_path = os.path.join(output_dir, f"screenshot_perpage_error_{timestamp}.png")
        await page.screenshot(path=screenshot_path)
        print(f"Menyimpan tangkapan layar dropdown error ke {screenshot_path}")
        return False
    
async def scrape_rank(url, ranking_option="BWF World Tour Rankings", output_dir="output"):
    """Mengikis halaman dari situs BWF World Tour untuk menyimpan HTML dan opsi dropdown Ranking.
    Args:
        url (str): URL halaman kalender turnamen BWF
        ranking_option (str): Opsi untuk dropdown Ranking (default: 'BWF World Tour Rankings')
        output_dir (str): Direktori untuk menyimpan file keluaran
    Returns:
        None: Mengembalikan None setelah menyimpan HTML atau jika gagal
    """
    # Konfigurasi timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(output_dir, exist_ok=True)

    async with async_playwright() as p:
        # Inisialisasi browser dengan user-agent acak
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

        # Atur header HTTP
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
            # Navigasi ke halaman
            await asyncio.sleep(random.uniform(2, 5))
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(10000)  # Tunggu pemuatan awal

            # Tangani persetujuan cookie (Cookiebot)
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
                await page.wait_for_timeout(2000)  # Tunggu dialog cookie tertutup
            except:
                print("Tombol persetujuan cookie tidak ditemukan.")

            # Periksa CAPTCHA
            try:
                captcha = await page.query_selector('[id*="captcha"], [class*="captcha"]')
                if captcha:
                    print("Peringatan: CAPTCHA terdeteksi. Intervensi manual mungkin diperlukan.")
            except:
                pass

            # Panggil fungsi baru untuk menyimpan opsi dropdown Ranking
            ranking_options = await save_ranking_options_to_json(page, output_dir=output_dir)

            # Pilih opsi tertentu menggunakan fungsi baru
            await select_ranking_option(page, ranking_options, ranking_option)
            # Sisa logika scraping lainnya...
            # Setelah bagian ranking selesai...

            # Panggil fungsi baru untuk menyimpan opsi dropdown Week
            week_options = await save_week_options_to_json(page, output_dir=output_dir)

            # Pilih opsi Week menggunakan fungsi baru
            # await select_week_option(page, week_options, target_week="Week 11 (2025-03-11)")
            # await select_week_option(page, week_options, target_week="Week 11 (2025-03-11)")
            await select_week_option(page, week_options, target_week="Week 8")

            # # Pilih item dropdown berlabel "Per page" yang memuat "25"
            await select_perpage_option(page, output_dir=output_dir, target_perpage="100")
 

            # Periksa halaman blokir
            title = await page.title()
            print(f"Judul Halaman: {title}")
            if "blocked" in title.lower() or "cloudflare" in title.lower():
                print("Peringatan: Judul halaman menunjukkan blokir Cloudflare.")

            # Simpan tangkapan layar
            screenshot_path = os.path.join(output_dir, f"screenshot_{timestamp}.png")
            await page.screenshot(path=screenshot_path)
            print(f"Menyimpan tangkapan layar ke {screenshot_path}")

            # Ambil dan simpan HTML
            html_content = await page.content()
            html_filename = os.path.join(output_dir, f"bwf_tournaments_{timestamp}.html")
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Menyimpan HTML ke {html_filename}")

            # Parsing HTML dan periksa blokir Cloudflare
            soup = BeautifulSoup(html_content, "html.parser")
            block_text = soup.find(string=re.compile(r"\bcloudflare\b|\bblocked\b|\bray id\b", re.I))
            if block_text:
                print(f"Kesalahan: HTML berisi halaman blokir Cloudflare. Teks blokir: {block_text[:100]}...")
                return None

            return None

        except Exception as e:
            print(f"Terjadi kesalahan: {str(e)}")
            html_content = await page.content()
            html_filename = os.path.join(output_dir, f"bwf_tournaments_error_{timestamp}.html")
            with open(html_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Menyimpan HTML kesalahan ke {html_filename}")
            await page.screenshot(path=os.path.join(output_dir, f"screenshot_error_{timestamp}.png"))
            return None

        finally:
            await context.close()
            await browser.close()


