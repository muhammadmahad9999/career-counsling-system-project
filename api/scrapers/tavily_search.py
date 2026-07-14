"""
Tavily Search Agent — FuturePath
Replaces DuckDuckGo with Tavily AI Search for higher quality, structured results.
Tavily API Key env var: TAVILYA_API_KEY (as set in .env)
Free tier: 1,000 searches/month
"""

import os
import httpx

TAVILY_API_URL = "https://api.tavily.com/search"


def search_tavily(query: str, max_results: int = 5, search_depth: str = "basic") -> list:
    """
    Search the web using Tavily AI Search API.
    Returns a list of {title, url, snippet, score} dicts.
    Falls back to empty list on any failure so callers handle gracefully.
    
    search_depth: "basic" (fast, free quota) or "advanced" (deeper, costs more units)
    """
    # Note: env key has a typo "TAVILYA" — reading both for safety
    api_key = (
        os.environ.get("TAVILYA_API_KEY") or
        os.environ.get("TAVILY_API_KEY") or
        ""
    )
    if not api_key:
        print("[Tavily] API key not found in environment (TAVILYA_API_KEY / TAVILY_API_KEY)")
        return []

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "include_answer": False,       # We want raw results, LLM will synthesize
        "include_raw_content": False,  # Keep payload small
        "include_images": False,
    }

    try:
        resp = httpx.post(TAVILY_API_URL, json=payload, timeout=12.0)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("results", []):
            results.append({
                "title":   item.get("title", ""),
                "url":     item.get("url", ""),
                "snippet": item.get("content", "")[:300],   # truncate for LLM context
                "score":   round(item.get("score", 0.0), 3),
            })
        return results

    except httpx.HTTPStatusError as e:
        print(f"[Tavily] HTTP error {e.response.status_code}: {e.response.text[:200]}")
        return []
    except Exception as e:
        print(f"[Tavily] Search failed: {e}")
        return []


def format_tavily_results_for_llm(results: list, query: str = "") -> str:
    """Format Tavily results into a compact string the LLM can use as context."""
    if not results:
        return f"No web results found for: {query}"
    
    lines = [f"Web search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   URL: {r['url']}")
        lines.append(f"   {r['snippet']}")
        lines.append("")
    return "\n".join(lines)
