"""
YouTube Data API v3 — Tier 1 Scraper (Official API)
FREE: 10,000 units/day
"""

import os

def search_youtube_videos(query: str, max_results=5) -> list:
    """Search YouTube for career-related videos for Pakistani students."""
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        return []

    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", developerKey=api_key)

        request = youtube.search().list(
            part="snippet",
            q=f"{query} Pakistan FSc students",
            type="video",
            maxResults=max_results,
            relevanceLanguage="ur",
            order="relevance"
        )
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            videos.append({
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
                "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                "description": item["snippet"]["description"][:100]
            })
        return videos

    except Exception as e:
        print(f"[YouTube API Error] {e}")
        return []
