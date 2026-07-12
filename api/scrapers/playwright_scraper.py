"""
Playwright Scraper — Tier 3 (JavaScript-heavy sites)
For dynamic pages like Udemy, NTS portals, etc.
"""


async def scrape_dynamic_page(url: str) -> dict:
    """Scrape a JavaScript-rendered page using Playwright."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()

            # Block images/fonts to load faster
            await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}",
                             lambda route: route.abort())

            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)

            content = await page.evaluate("""() => {
                const elements = document.querySelectorAll('h1,h2,h3,p,li,a');
                return Array.from(elements).map(el => ({
                    tag: el.tagName,
                    text: el.innerText?.trim(),
                    href: el.href || null
                })).filter(el => el.text && el.text.length > 10);
            }""")

            await browser.close()
            return {"url": url, "content": content[:50]}

    except Exception as e:
        print(f"[Playwright Error] {e}")
        return {"url": url, "content": []}


async def scrape_udemy_courses(query: str) -> list:
    """Scrape Udemy course listings for a given query."""
    url = f"https://www.udemy.com/courses/search/?q={query.replace(' ', '+')}"
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=25000)
            await page.wait_for_timeout(3000)

            courses = await page.evaluate("""() => {
                const cards = document.querySelectorAll('[class*="course-card"]');
                return Array.from(cards).slice(0, 6).map(card => ({
                    title: card.querySelector('h3')?.innerText,
                    instructor: card.querySelector('[class*="instructor"]')?.innerText,
                    rating: card.querySelector('[class*="rating"]')?.innerText,
                    price: card.querySelector('[class*="price"]')?.innerText,
                    url: card.querySelector('a')?.href
                }));
            }""")

            await browser.close()
            return [c for c in courses if c.get("title")]

    except Exception as e:
        print(f"[Udemy Scraper Error] {e}")
        return []
