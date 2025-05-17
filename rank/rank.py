import asyncio
import os
import random
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup
import re

async def scrape_rank(url, ranking_option="BWF World Tour Rankings", output_dir="output"):
    """Mengikis halaman dari situs BWF World Tour untuk menyimpan HTML.
    
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

            # Pilih item dropdown berlabel "Ranking" yang memuat ranking_option
            try:
                ranking_selector = 'div.select div.v-select__slot:has(> label:has-text("Ranking"))'
                await page.wait_for_selector(ranking_selector, timeout=15000)
                print("Elemen dropdown berlabel 'Ranking' ditemukan.")
                await page.click(ranking_selector, force=True)
                await page.wait_for_timeout(2000)  # Tunggu opsi muncul
                bwf_ranking_selector = f'div.v-menu__content div[role="listbox"] div.v-list-item__title:text-matches("{ranking_option}", "i")'
                await page.wait_for_selector(bwf_ranking_selector, timeout=10000)
                await page.click(bwf_ranking_selector, force=True)
                print(f"Berhasil memilih item dropdown yang memuat '{ranking_option}'.")
                await page.wait_for_timeout(3000)  # Tunggu pembaruan halaman
            except Exception as e:
                print(f"Peringatan: Gagal memilih item dropdown yang memuat '{ranking_option}': {str(e)}")
                try:
                    options = await page.query_selector_all('div.v-menu__content div[role="listbox"] div.v-list-item__title')
                    print("Opsi dropdown 'Ranking' yang tersedia:")
                    for opt in options:
                        text = await opt.inner_text()
                        print(f"- {text}")
                except:
                    print("Gagal mengambil opsi dropdown 'Ranking' untuk debugging.")

            # Pilih item dropdown berlabel "Week" yang memuat "Week 10"
            try:
                dropdown_selector = 'div.select div.v-select__slot:has(> label:has-text("Week"))'
                await page.wait_for_selector(dropdown_selector, timeout=15000)
                print("Elemen dropdown berlabel 'Week' ditemukan.")
                await page.click(dropdown_selector, force=True)
                await page.wait_for_timeout(2000)  # Tunggu opsi muncul
                week_10_selector = 'div.v-menu__content div[role="listbox"] div.v-list-item__title:text-matches("Week 10", "i")'
                await page.wait_for_selector(week_10_selector, timeout=10000)
                await page.click(week_10_selector, force=True)
                print("Berhasil memilih item dropdown yang memuat 'Week 10'.")
                await page.wait_for_timeout(3000)  # Tunggu pembaruan halaman
            except Exception as e:
                print(f"Peringatan: Gagal memilih item dropdown yang memuat 'Week 10': {str(e)}")
                try:
                    options = await page.query_selector_all('div.v-menu__content div[role="listbox"] div.v-list-item__title')
                    print("Opsi dropdown 'Week' yang tersedia:")
                    for opt in options:
                        text = await opt.inner_text()
                        print(f"- {text}")
                except:
                    print("Gagal mengambil opsi dropdown 'Week' untuk debugging.")

            # Pilih item dropdown berlabel "Per page" yang memuat "25"
            try:
                perpage_selector = 'div.select.perpage div.v-select__slot:has(> label:has-text("Per page"))'
                await page.wait_for_selector(perpage_selector, timeout=15000)
                print("Elemen dropdown berlabel 'Per page' ditemukan.")
                icon_selector = 'div.select.perpage i.mdi-menu-down'
                await page.click(icon_selector, force=True)
                await page.wait_for_timeout(5000)  # Tunggu menu opsi muncul
                page_25_selector = 'div.v-menu__content div[role="listbox"] div.v-list-item__title:text-matches("^25$", "i")'
                await page.wait_for_selector(page_25_selector, timeout=20000)
                await page.click(page_25_selector, force=True)
                print("Berhasil memilih item dropdown yang memuat '25'.")
                await page.wait_for_timeout(3000)  # Tunggu pembaruan halaman
            except Exception as e:
                print(f"Peringatan: Gagal memilih item dropdown yang memuat '25': {str(e)}")
                await page.screenshot(path=os.path.join(output_dir, f"screenshot_perpage_error_{timestamp}.png"))
                print(f"Menyimpan tangkapan layar dropdown error ke screenshot_perpage_error_{timestamp}.png")
                try:
                    options = await page.query_selector_all('div.v-menu__content div[role="listbox"] div.v-list-item__title')
                    print("Opsi dropdown yang tersedia di menu aktif:")
                    for opt in options:
                        text = await opt.inner_text()
                        print(f"- {text}")
                except:
                    print("Gagal mengambil opsi dropdown untuk debugging.")

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