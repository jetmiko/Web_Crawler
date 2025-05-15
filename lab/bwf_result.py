import asyncio
import os
import json
import base64
from pathlib import Path
from typing import List
from crawl4ai import ProxyConfig
from datetime import datetime

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, CrawlResult
from crawl4ai import RoundRobinProxyStrategy
from crawl4ai import JsonCssExtractionStrategy, LLMExtractionStrategy
from crawl4ai import LLMConfig
from crawl4ai import PruningContentFilter, BM25ContentFilter
from crawl4ai import DefaultMarkdownGenerator
from crawl4ai import BFSDeepCrawlStrategy, DomainFilter, FilterChain
from crawl4ai import BrowserConfig

__cur_dir__ = Path(__file__).parent

async def demo_basic_crawl():
    """Basic web crawling with markdown generation and file output"""
    print("\n=== 1. Basic Web Crawling ===")
    async with AsyncWebCrawler(config=BrowserConfig(
        viewport_height=800,
        viewport_width=1200,
        headless=True,
        verbose=True,
    )) as crawler:
        results: List[CrawlResult] = await crawler.arun(
            url="https://bwfworldtour.bwfbadminton.com/tournament/5225/toyota-thailand-open-2025/results/",
        )

        # Create output directory if it doesn't exist
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Open a file to write results in the output subfolder
        with open(os.path.join(output_dir, "crawl_results.txt"), "w", encoding="utf-8") as f:
            for i, result in enumerate(results):
                print(f"Result {i + 1}:")
                print(f"Success: {result.success}")
                f.write(f"Result {i + 1}:\n")
                f.write(f"Success: {result.success}\n")
                
                if result.success:
                    print(f"Markdown length: {len(result.markdown.raw_markdown)} chars")
                    print(f"Content:\n{result.markdown.raw_markdown}")
                    f.write(f"Markdown length: {len(result.markdown.raw_markdown)} chars\n")
                    f.write(f"Content:\n{result.markdown.raw_markdown}\n")
                    f.write("-" * 50 + "\n")
                else:
                    print("Failed to crawl the URL")
                    f.write("Failed to crawl the URL\n")
                    f.write("-" * 50 + "\n")



async def demo_parallel_crawl():
    """Crawl multiple URLs in parallel"""
    print("\n=== 2. Parallel Crawling ===")

    urls = [
        "https://news.ycombinator.com/",
        "https://example.com/",
        "https://httpbin.org/html",
    ]

    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun_many(
            urls=urls,
        )

        print(f"Crawled {len(results)} URLs in parallel:")
        for i, result in enumerate(results):
            print(
                f"  {i + 1}. {result.url} - {'Success' if result.success else 'Failed'}"
            )

async def demo_fit_markdown():
    """Generate focused markdown with LLM content filter"""
    print("\n=== 3. Fit Markdown with LLM Content Filter ===")

    async with AsyncWebCrawler() as crawler:
        result: CrawlResult = await crawler.arun(
            url = "https://en.wikipedia.org/wiki/Python_(programming_language)",
            config=CrawlerRunConfig(
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter()
                )
            ),
        )

        # Print stats and save the fit markdown
        print(f"Raw: {len(result.markdown.raw_markdown)} chars")
        print(f"Fit: {len(result.markdown.fit_markdown)} chars")

async def demo_llm_structured_extraction_no_schema():
    # Create a simple LLM extraction strategy (no schema required)
    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="groq/meta-llama/llama-4-scout-17b-16e-instruct",
            api_token="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",
        ),
        instruction="This is news.ycombinator.com, extract all news, and for each, I want title, source url, number of comments.",
        extract_type="schema",
        schema="{title: string, url: string, comments: int}",
        extra_args={
            "temperature": 0.0,
            "max_tokens": 4096,
        },
        verbose=True,
    )

    config = CrawlerRunConfig(extraction_strategy=extraction_strategy)

    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(
            "https://news.ycombinator.com/", config=config
        )

        for result in results:
            print(f"URL: {result.url}")
            print(f"Success: {result.success}")
            if result.success:
                data = json.loads(result.extracted_content)
                print(json.dumps(data, indent=2))
            else:
                print("Failed to extract structured data")

async def llm_bwf():
    # Create a simple LLM extraction strategy (no schema required)
    url = "https://bwfworldtour.bwfbadminton.com/tournament/5225/toyota-thailand-open-2025/results/"
    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="groq/meta-llama/llama-4-scout-17b-16e-instruct",
            api_token="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",
        ),
        instruction=f"This is {url}, extract all  match results, court, player name, scores.",
        extract_type="schema",
        schema="{court: string, playername: string, scores: string}",
        extra_args={
            "temperature": 0.0,
            "max_tokens": 4096,
        },
        verbose=True,
    )

    config = CrawlerRunConfig(extraction_strategy=extraction_strategy)

    # Create output folder if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Initialize list to store all extracted data
    all_extracted_data = []

    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(
            url, config=config
        )

        for result in results:
            print(f"URL: {result.url}")
            print(f"Success: {result.success}")
            if result.success:
                data = json.loads(result.extracted_content)
                print(json.dumps(data, indent=2))
                all_extracted_data.extend(data)  # Add extracted data to the list
            else:
                print("Failed to extract structured data")

    # Save results to a JSON file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"hackernews_extract_{timestamp}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_extracted_data, f, indent=2, ensure_ascii=False)
    print(f"Results saved to {output_file}")



async def demo_css_structured_extraction_no_schema():
    """Extract structured data using CSS selectors"""
    print("\n=== 5. CSS-Based Structured Extraction ===")
    # Sample HTML for schema generation (one-time cost)
    url0 = "https://bwfworldtour.bwfbadminton.com/tournament/5225/toyota-thailand-open-2025/results/"
    sample_html = f"""
<div class="body-post clear">
    <a class="story-link" href="{url0}">
        <div class="clear home-post-box cf">
            <div class="home-img clear">
                <div class="img-ratio">
                    <img alt="..." src="...">
                </div>
            </div>
            <div class="clear home-right">
                <h2 class="home-title">Malicious Python Packages on PyPI Downloaded 39,000+ Times, Steal Sensitive Data</h2>
                <div class="item-label">
                    <span class="h-datetime"><i class="icon-font icon-calendar"></i>Apr 05, 2025</span>
                    <span class="h-tags">Malware / Supply Chain Attack</span>
                </div>
                <div class="home-desc"> Cybersecurity researchers have...</div>
            </div>
        </div>
    </a>
</div>
    """

    # Ensure the tmp directory exists
    tmp_dir = __cur_dir__ / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    # Check if schema file exists
    schema_file_path = tmp_dir / "schema.json"
    if schema_file_path.exists():
        with open(schema_file_path, "r") as f:
            schema = json.load(f)
    else:
        # Generate schema using LLM (one-time setup)
        schema = JsonCssExtractionStrategy.generate_schema(
            html=sample_html,
            llm_config=LLMConfig(
                provider="groq/meta-llama/llama-4-scout-17b-16e-instruct",
                api_token="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",
            ),
            query=f"From {url0}, I have shared a sample of one news div with a title, date, and description. Please generate a schema for this news div.",
        )

    print(f"Generated schema: {json.dumps(schema, indent=2)}")
    # Save the schema to a file, and use it for future extractions
    with open(schema_file_path, "w") as f:
        json.dump(schema, f, indent=2)

    # Create no-LLM extraction strategy with the generated schema
    extraction_strategy = JsonCssExtractionStrategy(schema)
    config = CrawlerRunConfig(extraction_strategy=extraction_strategy)

    # Use the fast CSS extraction (no LLM calls during extraction)
    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(
            url0, config=config
        )

        for result in results:
            print(f"URL: {result.url}")
            print(f"Success: {result.success}")
            if result.success:
                data = json.loads(result.extracted_content)
                print(json.dumps(data, indent=2))
            else:
                print("Failed to extract structured data")

async def demo_deep_crawl():
    """Deep crawling with BFS strategy"""
    print("\n=== 6. Deep Crawling ===")

    filter_chain = FilterChain([DomainFilter(allowed_domains=["crawl4ai.com"])])

    deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=1, max_pages=5, filter_chain=filter_chain
    )

    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(
            url="https://docs.crawl4ai.com",
            config=CrawlerRunConfig(deep_crawl_strategy=deep_crawl_strategy),
        )

        print(f"Deep crawl returned {len(results)} pages:")
        for i, result in enumerate(results):
            depth = result.metadata.get("depth", "unknown")
            print(f"  {i + 1}. {result.url} (Depth: {depth})")

async def demo_js_interaction():
    """Execute JavaScript to load more content"""
    print("\n=== 7. JavaScript Interaction ===")
    url0 = "https://bwfworldtour.bwfbadminton.com/tournament/5225/toyota-thailand-open-2025/results/"

    async with AsyncWebCrawler(config=BrowserConfig(headless=False)) as crawler:
        # Initial load
        news_schema = {
            "name": "match_results",
            "baseSelector": "div.tournament-results__match",  # Selector utama untuk setiap pertandingan
            "fields": [
                {
                    "name": "event",
                    "selector": "div.tournament-results__event-title",
                    "type": "text",
                },
                {
                    "name": "players",
                    "selector": "div.tournament-results__players",
                    "type": "text",
                },
                {
                    "name": "score",
                    "selector": "div.tournament-results__score",
                    "type": "text",
                },
                {
                    "name": "round",
                    "selector": "div.tournament-results__round",
                    "type": "text",
                },
            ],
        }
        results: List[CrawlResult] = await crawler.arun(
            url = url0,
            config=CrawlerRunConfig(
                session_id="hn_session",  # Keep session
                extraction_strategy=JsonCssExtractionStrategy(schema=news_schema),
            ),
        )

        news = []
        for result in results:
            if result.success:
                data = json.loads(result.extracted_content)
                news.extend(data)
                print(json.dumps(data, indent=2))
            else:
                print("Failed to extract structured data")

        print(f"Initial items: {len(news)}")

        # Click "More" link and wait for navigation
        more_config = CrawlerRunConfig(
            js_code="""
                (function() {
                    const moreLink = document.querySelector('a.morelink');
                    if (moreLink) {
                        moreLink.click();
                        return true;
                    }
                    return false;
                })();
            """,
            js_only=False,  # Allow navigation
            session_id="hn_session",  # Keep session
            extraction_strategy=JsonCssExtractionStrategy(schema=news_schema),
            wait_for="() => document.querySelectorAll('tr.athing').length > 0",  # Wait for new content
        )

        try:
            more_results: List[CrawlResult] = await crawler.arun(
                url=url0, config=more_config
            )

            # Extract new items
            for result in more_results:
                if result.success:
                    data = json.loads(result.extracted_content)
                    news.extend(data)
                    print(json.dumps(data, indent=2))
                else:
                    print("Failed to extract structured data from 'More' page")
        except Exception as e:
            print(f"Error processing 'More' link: {e}")
            print("Skipping additional items due to JavaScript execution error")

        print(f"Total items: {len(news)}")

async def demo_media_and_links():
    """Extract media and links from a page"""
    print("\n=== 8. Media and Links Extraction ===")

    async with AsyncWebCrawler() as crawler:
        result: List[CrawlResult] = await crawler.arun("https://en.wikipedia.org/wiki/Main_Page")

        for i, result in enumerate(result):
            # Extract and save all images
            images = result.media.get("images", [])
            print(f"Found {len(images)} images")

            # Extract and save all links (internal and external)
            internal_links = result.links.get("internal", [])
            external_links = result.links.get("external", [])
            print(f"Found {len(internal_links)} internal links")
            print(f"Found {len(external_links)} external links")

            # Print some of the images and links
            for image in images[:3]:
                print(f"Image: {image['src']}")
            for link in internal_links[:3]:
                print(f"Internal link: {link['href']}")
            for link in external_links[:3]:
                print(f"External link: {link['href']}")

            # # Save everything to files
            with open(f"{__cur_dir__}/tmp/images.json", "w") as f:
                json.dump(images, f, indent=2)

            with open(f"{__cur_dir__}/tmp/links.json", "w") as f:
                json.dump(
                    {"internal": internal_links, "external": external_links},
                    f,
                    indent=2,
                )



async def demo_proxy_rotation():
    """Proxy rotation for multiple requests"""
    print("\n=== 10. Proxy Rotation ===")

    # Example proxies (replace with real ones)
    proxies = [
        ProxyConfig(server="http://proxy1.example.com:8080"),
        ProxyConfig(server="http://proxy2.example.com:8080"),
    ]

    proxy_strategy = RoundRobinProxyStrategy(proxies)

    print(f"Using {len(proxies)} proxies in rotation")
    print(
        "Note: This example uses placeholder proxies - replace with real ones to test"
    )

    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            proxy_rotation_strategy=proxy_strategy
        )

        # In a real scenario, these would be run and the proxies would rotate
        print("In a real scenario, requests would rotate through the available proxies")



async def main():
    """Run all demo functions sequentially"""
    print("=== Comprehensive Crawl4AI Demo ===")
    print("Note: Some examples require API keys or other configurations")

    # Run all demos
    # await demo_basic_crawl()
    # await demo_parallel_crawl()
    # await demo_fit_markdown()
    # await demo_llm_structured_extraction_no_schema()
    # await llm_bwf()
    await demo_css_structured_extraction_no_schema()
    # await demo_deep_crawl()
    # await demo_js_interaction()
    # await demo_media_and_links()
    # await demo_screenshot_and_pdf()
    # # # await demo_proxy_rotation()
    # await demo_raw_html_and_file()

    # Clean up any temp files that may have been created
    # print("\n=== Demo Complete ===")
    # print("Check for any generated files (screenshots, PDFs) in the current directory")

if __name__ == "__main__":
    asyncio.run(main())