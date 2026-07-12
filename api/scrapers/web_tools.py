"""
Web Search & Scraping Tools — DuckDuckGo Search and BeautifulSoup Clean Scraping
"""

import urllib.parse
import httpx
from bs4 import BeautifulSoup

# Realistic headers mimicking a Windows Chrome browser to avoid bot detection and cloudflare blocks
REAL_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,ur;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1"
}

def search_duckduckgo(query: str, max_results: int = 5) -> list:
    """Perform a web search using DuckDuckGo HTML interface."""
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    try:
        r = httpx.get(url, headers=REAL_BROWSER_HEADERS, timeout=10.0)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for item in soup.find_all("a", class_="result__a"):
            title = item.text.strip()
            href = item.get("href")
            
            # DDG redirects links through /l/?uddg=URL
            if href and "uddg=" in href:
                parsed = urllib.parse.urlparse(href)
                query_params = urllib.parse.parse_qs(parsed.query)
                if "uddg" in query_params:
                    href = query_params["uddg"][0]
            elif href and href.startswith("//"):
                href = "https:" + href
                
            snippet_el = item.find_next(class_="result__snippet")
            snippet = snippet_el.text.strip() if snippet_el else ""
            
            links.append({"title": title, "url": href, "snippet": snippet})
            if len(links) >= max_results:
                break
        return links
    except Exception as e:
        print(f"[DDG Search Tool Error] {e}")
        return []


def web_scrape(url: str) -> str:
    """Fetch and scrape clean text paragraphs from a URL."""
    try:
        # If it's a relative/invalid URL, return error
        if not url.startswith("http"):
            return "Error: Invalid URL. Must start with http:// or https://"
            
        r = httpx.get(url, headers=REAL_BROWSER_HEADERS, timeout=12.0)
        if r.status_code != 200:
            return f"Error: Failed to retrieve page. Status code: {r.status_code}"
            
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "meta", "noscript"]):
            script.decompose()
            
        # Extract headers and paragraphs
        elements = soup.find_all(["h1", "h2", "h3", "p", "li"])
        text_blocks = []
        for el in elements:
            text = el.text.strip()
            if len(text) > 20: # skip very short lines
                text_blocks.append(f"{el.name.upper()}: {text}")
                
        # Limit content to 2500 characters to keep context small
        return "\n".join(text_blocks)[:2500]
    except Exception as e:
        return f"Error scraping URL: {str(e)}"
