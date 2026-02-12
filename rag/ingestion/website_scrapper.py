## This is to scrape official or unofficial websites listed on the Google Maps Website URL
## We use Selenium to simulate browser actions, although it's hard to get information since each website structure is very different.
## Thus, we are to design generic semantic extractor that hopefully will work on many websites.
## Since we definitely won't scrape only the Home page, we are going to implement web crawling to retrieve more information.
## We don't need blog posts, news, careers, legal pages, and some random promotions/ads for our crawler.
## What we do need are "About Us", company story/history, brand philosophy, menu or services description, mission or values, and business positioning.
## We will use: https://github.com/apify/crawlee-python 

from urllib.parse import urlparse, urljoin
from typing import Dict, Set, List
import asyncio
import re

from bs4 import BeautifulSoup
from crawlee.crawlers import HttpCrawler
from crawlee.router import Router

KEYWORDS = ["about", "about-us", "our-story", "story", "company", "mission", "vision", "values", "services", "menu", "team", "philosophy", "brand"]
IGNORED_EXTENSIONS = [".pdf", ".jpg", ".png", ".docx", ".zip"]
ERROR_KEYWORDS = ["page you requested was not found", "404", "not found on this server", "sorry, the page"]

def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "footer", "header", "nav", "aside"]):
        tag.decompose()
    for cookie_stuff in soup.find_all(re.compile(r'cookie|consent|banner', re.I)):
        cookie_stuff.decompose() # Target the cookie banner to ignore the message to accept the cookies
    main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.body
    FORBIDDEN_PHRASES = [
        "use cookies to provide",
        "accept our use of cookies",
        "decline cookies at any time",
        "adjust your settings",
        "function properly",
        "signing in, or filling in forms"
    ]
    text = main_content.get_text(separator="\n")
    lines = []
    for line in text.splitlines():
        clean_line = line.strip()
        # Only keep lines that are long enough and don't contain forbidden phrases; this is to ignore junk messages.
        if len(clean_line) > 50:
            is_cookie_text = any(phrase in clean_line.lower() for phrase in FORBIDDEN_PHRASES)
            if not is_cookie_text:
                lines.append(clean_line)
    return "\n".join(lines)

async def crawl_website(base_url: str, max_pages: int = 10) -> Dict:
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    results = {
        "base_url": base_url,
        "pages_scraped": [],
        "combined_text": ""
    }
    visited_urls: Set[str] = set()
    router = Router()
    @router.default_handler
    async def handle_page(doc):
        response = doc.http_response
        if not response:
            return
        url = doc.request.url
        if url in visited_urls:
            return
        visited_urls.add(url)
        print(f"[INFO] Scraping: {url}")
        body_bytes = await response.read()
        html = body_bytes.decode("utf-8", errors="ignore")
        cleaned = clean_text(html)
        if len(cleaned) < 200:
            return
        lower_cleaned = cleaned.lower()
        if any(err_kw in lower_cleaned for err_kw in ERROR_KEYWORDS):
            # print(f"[INFO] Hit a 404 page: {url}")
            return
        results["pages_scraped"].append(url)
        results["combined_text"] += f"\n\n--- Source: {url} ---\n{cleaned}"
    crawler = HttpCrawler(request_handler=router, max_requests_per_crawl=max_pages)
    candidate_urls: List[str] = [base_url]
    for kw in KEYWORDS:
        candidate_urls.append(urljoin(root, kw))
    candidate_urls = list(set(candidate_urls))
    await crawler.run(candidate_urls)
    return results

def save_results(data: Dict, filename: str) -> None:
    file_path = "rag/data/raw/" + filename
    row = {
        "base_url": data["base_url"],
        "pages_scraped": ", ".join(data["pages_scraped"]),
        "combined_text": data["combined_text"].strip()
    }
    with open(file_path, mode="w", encoding="utf-8") as f:
        f.write(f"BASE_URL: {data['base_url']}\n")
        f.write(f"PAGES_SCRAPED: {', '.join(data['pages_scraped'])}\n")
        f.write("\n" + "="*50 + "\n")
        f.write(data["combined_text"].strip())
        f.write("\n" + "="*50 + "\n")
    print(f"[INFO] Successfully saved context to {file_path}")

# # Test script
# website_url = "https://www.luckincoffee.com.sg/"
# context_data = asyncio.run(crawl_website(website_url, max_pages=5))
# print("Pages scraped:", context_data["pages_scraped"])
# print("Text:", context_data["combined_text"])
# if context_data["pages_scraped"]:
#     save_results(context_data, "luckin_coffee.txt")
