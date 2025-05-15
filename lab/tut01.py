
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    # Membuat instance AsyncWebCrawler
    async with AsyncWebCrawler() as crawler:
        # Jalankan crawling pada URL target
        result = await crawler.arun(url="https://bwfworldtour.bwfbadminton.com/tournament/5225/toyota-thailand-open-2025/results/2025-05-15")
        # Cetak hasil ekstraksi dalam format Markdown
        print(result.markdown)

# Jalankan fungsi utama secara asinkron
asyncio.run(main())
