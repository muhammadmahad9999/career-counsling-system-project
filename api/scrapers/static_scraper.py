"""
Static HTML Scraper — Tier 2 (BeautifulSoup + httpx)
For pages that don't need JavaScript to render content.
"""

import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}


async def scrape_static_page(url: str) -> dict:
    """Scrape a static HTML page and return clean text content."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Remove junk tags
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()

            return {
                "title": soup.title.string if soup.title else "",
                "text": soup.get_text(separator=" ", strip=True)[:3000],
                "links": [a["href"] for a in soup.find_all("a", href=True)][:20]
            }
    except Exception as e:
        print(f"[Static Scraper Error] {e}")
        return {"title": "", "text": "", "links": []}


async def scrape_peef_scholarships() -> list:
    """Scrape PEEF scholarship listings."""
    url = "https://www.peef.org.pk/scholarships"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, "lxml")

            scholarships = []
            for item in soup.select(".scholarship-item, .program-card, article"):
                title = item.find(["h2", "h3", "h4"])
                description = item.find("p")
                link = item.find("a", href=True)

                if title:
                    scholarships.append({
                        "title": title.get_text(strip=True),
                        "description": description.get_text(strip=True) if description else "",
                        "url": link["href"] if link else url,
                        "source": "PEEF"
                    })
            return scholarships
    except Exception as e:
        print(f"[PEEF Scraper Error] {e}")
        return []
