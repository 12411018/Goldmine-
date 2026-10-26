"""Opt-in web research using Tavily's search API."""

from urllib.parse import urlparse

import httpx

from app.core.config import settings

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class ResearchUnavailable(RuntimeError):
    pass


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    if not settings.search_api_key:
        raise ResearchUnavailable("Web research is not configured. Add SEARCH_API_KEY to the backend environment.")

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(18.0, connect=5.0)) as client:
            response = await client.post(
                TAVILY_SEARCH_URL,
                headers={"Authorization": f"Bearer {settings.search_api_key}"},
                json={
                    "query": query[:1000],
                    "topic": "general",
                    "search_depth": "basic",
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            if response.status_code in (401, 403):
                raise ResearchUnavailable("Web research authentication failed. Check SEARCH_API_KEY.")
            if response.status_code == 429:
                raise ResearchUnavailable("The web research provider is rate limiting requests. Try again shortly.")
            response.raise_for_status()
            payload = response.json()
    except ResearchUnavailable:
        raise
    except httpx.TimeoutException as exc:
        raise ResearchUnavailable("The web research provider timed out. Try again shortly.") from exc
    except httpx.HTTPStatusError as exc:
        raise ResearchUnavailable(f"The web research provider returned HTTP {exc.response.status_code}.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise ResearchUnavailable("The web research provider could not be reached.") from exc

    results = []
    for result in payload.get("results", []):
        url = result.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            continue
        title = str(result.get("title") or parsed.hostname)[:300]
        snippet = str(result.get("content") or "")[:5000]
        try:
            score = float(result.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        results.append({
            "title": title,
            "url": url,
            "domain": parsed.hostname[:253],
            "content": snippet,
            "relevance_score": max(0.0, min(1.0, score)),
            "support_type": "neutral",
        })
        if len(results) >= max_results:
            break
    return results
