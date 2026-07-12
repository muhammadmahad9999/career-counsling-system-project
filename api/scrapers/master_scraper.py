"""
Master Scraper — combines all scraping tiers into one async call.
Runs YouTube API, BeautifulSoup, and Playwright scrapers in parallel.
"""

import asyncio
from scrapers.youtube_api import search_youtube_videos
from scrapers.static_scraper import scrape_peef_scholarships
from scrapers.playwright_scraper import scrape_udemy_courses


async def get_resources_for_query(query: str, resource_type: str = "all") -> dict:
    """
    Fetch resources from multiple sources in parallel.
    resource_type: 'videos' | 'scholarships' | 'courses' | 'all'
    """
    results = {
        "youtube_videos": [],
        "courses": [],
        "scholarships": [],
    }

    tasks = []
    task_labels = []

    # YouTube API (sync, wrapped in executor)
    if resource_type in ["videos", "all"]:
        loop = asyncio.get_event_loop()
        tasks.append(loop.run_in_executor(None, search_youtube_videos, query))
        task_labels.append("youtube_videos")

    # Scholarships (async)
    if resource_type in ["scholarships", "all"]:
        tasks.append(scrape_peef_scholarships())
        task_labels.append("scholarships")

    # Udemy courses (async)
    if resource_type in ["courses", "all"]:
        tasks.append(scrape_udemy_courses(query))
        task_labels.append("courses")

    # Run all scrapers in parallel — failures are isolated
    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    for label, result in zip(task_labels, all_results):
        if isinstance(result, Exception):
            print(f"[Master Scraper] {label} failed: {result}")
            continue
        if isinstance(result, list):
            results[label] = result

    return results
