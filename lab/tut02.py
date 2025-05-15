import asyncio
import json
import os
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

async def main():
    schema = {
        "name": "Match Card",
        "baseSelector": ".match-card",
        "fields": [
            {"name": "participant_names", "selector": ".participant-name", "type": "text"},
            {"name": "scores", "selector": ".score", "type": "text"},
            {"name": "round", "selector": ".tournament-phase-title", "type": "text"}
        ]
    }

    extraction_strategy = JsonCssExtractionStrategy(schema)

    js_click_label = """
    (() => {
        const label = document.querySelector('label[for="switchListView"]');
        if (label) {
            label.click();
            return true;
        }
        return false;
    })();
    """

    run_config = CrawlerRunConfig(
        extraction_strategy=extraction_strategy,
        wait_for="css:.participant-name",
        page_timeout=20000,
        delay_before_return_html=5.0,  # beri waktu render ulang setelah klik label
        js_code=[js_click_label]
    )

    url = "https://bwfworldtour.bwfbadminton.com/tournament/5225/toyota-thailand-open-2025/results/2025-05-15"

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
            config=run_config
        )

    if result.success:
        data = json.loads(result.extracted_content)

        os.makedirs("output", exist_ok=True)
        json_path = os.path.join("output", "results_2025-05-15_list_view.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Hasil JSON disimpan di {json_path}")

        html_path = os.path.join("output", "rendered_page_list_view_2025-05-15.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(result.html)
        print(f"File HTML render disimpan di {html_path}")

    else:
        print("Gagal crawling:", result.error_message)

if __name__ == "__main__":
    asyncio.run(main())
