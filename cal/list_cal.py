import asyncio
import os
import json
import random
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup
import re

async def scrape_bwf_tournaments(url, output_dir="output"):
    """Mengikis daftar turnamen dari situs BWF World Tour.
    
    Args:
        url (str): URL halaman kalender turnamen BWF
        output_dir (str): Direktori untuk menyimpan file keluaran
    
    Returns:
        list: Daftar kamus data turnamen, atau None jika pengikisan gagal
    """
    # Konfigurasi
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Buat direktori keluaran
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
            await asyncio.sleep(random.uniform(2, 5))  # Penundaan acak
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(45000)  # Tunggu Cloudflare dan pemuatan lambat
            # Tunggu elemen turnamen
            try:
                await page.wait_for_selector("div.tmt-card-wrapper, div.card.tmt-card.show-add-to-calendar", timeout=30000)
                print("Elemen turnamen terdeteksi.")
            except:
                print("Peringatan: Elemen turnamen tidak ditemukan dalam waktu tunggu.")
                # Coba lagi setelah penundaan tambahan
                await page.wait_for_timeout(10000)
                if not await page.query_selector("div.tmt-card-wrapper, div.card.tmt-card.show-add-to-calendar"):
                    print("Kesalahan: Elemen turnamen masih tidak ditemukan setelah penundaan tambahan.")

            # Tangani persetujuan cookie
            try:
                await page.click('button:has-text("Accept"), [id*="cookie"], [class*="cookie"]', timeout=5000)
                print("Klik tombol persetujuan cookie.")
            except:
                print("Tombol persetujuan cookie tidak ditemukan.")

            # Periksa CAPTCHA
            try:
                captcha = await page.query_selector('[id*="captcha"], [class*="captcha"]')
                if captcha:
                    print("Peringatan: CAPTCHA terdeteksi. Intervensi manual mungkin diperlukan.")
            except:
                pass

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

            # Parsing HTML
            soup = BeautifulSoup(html_content, "html.parser")

            # Periksa blokir Cloudflare
            block_text = soup.find(string=re.compile(r"\bcloudflare\b|\bblocked\b|\bray id\b", re.I))
            if block_text and not soup.select("div.tmt-card-wrapper, div.card.tmt-card.show-add-to-calendar"):
                print(f"Kesalahan: HTML berisi halaman blokir Cloudflare. Teks blokir: {block_text[:100]}...")
                return None
            elif block_text:
                print("Peringatan: Teks Cloudflare terdeteksi, tetapi data turnamen mungkin tersedia. Melanjutkan ekstraksi.")

            # Ekstrak data turnamen
            tournaments = []
            tournament_cards = soup.select("div.tmt-card-wrapper div.card.tmt-card, div.card.tmt-card.show-add-to-calendar")
            for idx, card in enumerate(tournament_cards):
                # Tentukan jenis kartu
                card_type = "tmt-card-wrapper" if card.find_parent("div.tmt-card-wrapper") else "show-add-to-calendar"
                print(f"Memproses kartu ({card_type}) untuk turnamen #{idx + 1}")

                tournament_data = {
                    "index": idx,
                    "name": None,
                    "date": "Tidak Diketahui",
                    "location": None,
                    "category": None,
                    "prize_money": None,
                    "results_url": None,
                    "status": None
                }

                # Ekstrak nama turnamen
                name_elem = card.select_one("span.name.truncate-2-line")
                tournament_data["name"] = name_elem.get_text(strip=True) if name_elem else "Tidak Diketahui"

                # Ekstrak tanggal dari date-post, date-live, atau date-future
                date_classes = ["date-post", "date-live", "date-future"]
                for date_class in date_classes:
                    date_elem = card.select_one(f"div.date.{date_class} span")
                    if date_elem:
                        tournament_data["date"] = date_elem.get_text(strip=True)
                        print(f"Menggunakan tanggal dari {date_class} untuk {tournament_data['name']}: {tournament_data['date']}")
                        break
                if tournament_data["date"] == "Tidak Diketahui":
                    print(f"Peringatan: Tidak ada tanggal ditemukan untuk {tournament_data['name']}.")

                # Ekstrak lokasi
                location_elem = card.select_one("div.country")
                if location_elem:
                    location_text = location_elem.get_text(strip=True)
                    # Hapus nama negara dari lokasi (misalnya, "Taipei, Chinese Taipei" -> "Taipei")
                    location_match = re.match(r"^(.*?),\s*\w+$", location_text)
                    tournament_data["location"] = location_match.group(1) if location_match else location_text

                # Ekstrak kategori
                category_elem = card.select_one("div.label.label-category.truncate-1-line")
                tournament_data["category"] = category_elem.get_text(strip=True) if category_elem else None

                # Ekstrak hadiah (hanya angka)
                prize_elem = card.select_one("div.label.prize-money")
                if prize_elem:
                    prize_text = prize_elem.get_text(strip=True)
                    # Ambil hanya angka dengan menghapus non-digit dan tanda koma
                    prize_numbers = re.sub(r"[^\d]", "", prize_text)
                    tournament_data["prize_money"] = prize_numbers if prize_numbers else None
                    print(f"Hadiah untuk {tournament_data['name']}: {tournament_data['prize_money']}")
                else:
                    print(f"Peringatan: Tidak ada hadiah ditemukan untuk {tournament_data['name']}.")

                # Ekstrak URL hasil
                link_elem = card.find_parent("a")
                if link_elem and "href" in link_elem.attrs and link_elem["href"] and "/results/" in link_elem["href"]:
                    tournament_data["results_url"] = link_elem["href"]
                    print(f"URL hasil untuk {tournament_data['name']}: {tournament_data['results_url']}")
                else:
                    # Coba metode alternatif
                    link_elem_alt = card.select_one("a[href*='/results/']")
                    if link_elem_alt and "href" in link_elem_alt.attrs and link_elem_alt["href"]:
                        tournament_data["results_url"] = link_elem_alt["href"]
                        print(f"URL hasil (alternatif) untuk {tournament_data['name']}: {tournament_data['results_url']}")
                    else:
                        print(f"Peringatan: Tidak ada URL hasil yang valid ditemukan untuk {tournament_data['name']}.")
                        # Simpan HTML kartu untuk debugging
                        card_html = str(card)
                        card_filename = os.path.join(output_dir, f"card_{idx}_{timestamp}.html")
                        with open(card_filename, "w", encoding="utf-8") as f:
                            f.write(card_html)
                        print(f"Menyimpan HTML kartu ke {card_filename} untuk analisis.")

                # Ekstrak status (misalnya, LIVE SCORES)
                status_elem = card.select_one("span.label.label-alert")
                tournament_data["status"] = status_elem.get_text(strip=True) if status_elem else None

                tournaments.append(tournament_data)

            # Keluarkan hasil
            if tournaments:
                print("\nData Turnamen Ditemukan:")
                for tournament in tournaments:
                    print(f"\nTurnamen: {tournament['name']} (Index: {tournament['index']})")
                    print(f"Tanggal: {tournament['date']}")
                    print(f"Lokasi: {tournament['location']}")
                    print(f"Kategori: {tournament['category']}")
                    print(f"Hadiah: {tournament['prize_money']}")
                    print(f"Status: {tournament['status']}")
                    print(f"URL Hasil: {tournament['results_url']}")

                # Simpan ke JSON
                json_filename = os.path.join(output_dir, f"tournament_data_{timestamp}.json")
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(tournaments, f, ensure_ascii=False, indent=2)
                print(f"\nMenyimpan data turnamen ke {json_filename}")
            else:
                print("\nTidak ada data turnamen ditemukan. Periksa HTML dan tangkapan layar yang disimpan untuk perubahan struktur.")

            return tournaments

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