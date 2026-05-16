import os
import time
import logging
import re
from urllib.parse import urlparse
from tavily import TavilyClient

logger = logging.getLogger(__name__)


def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning("Retry %d/%d after %.1fs: %s", attempt + 1, max_retries, delay, e)
            time.sleep(delay)


def generate_queries(settings: dict) -> list[str]:
    queries = []
    keywords_he = settings.get("keywords_he", [])
    keywords_en = settings.get("keywords_en", [])
    sectors = settings.get("sectors", [])
    signals = settings.get("signals", [])

    # Hebrew keyword queries (pick up to 8)
    for kw in keywords_he[:8]:
        queries.append(kw)

    # English keyword queries (pick up to 4)
    for kw in keywords_en[:4]:
        queries.append(kw)

    # Sector-specific Hebrew queries
    sector_short = {
        "Finance": "פיננסים",
        "Healthcare": "בריאות",
        "High-Tech": "הייטק",
        "Government": "ממשלתי",
        "Municipal": "רשויות מקומיות",
    }
    for sector in sectors[:5]:
        sector_key = sector.split(":")[0].strip() if ":" in sector else sector.split()[0]
        he_sector = sector_short.get(sector_key, "")
        if he_sector:
            queries.append(f"{he_sector} מינוי חדש")

    # Ensure 12-15 queries total
    if len(queries) > 15:
        queries = queries[:15]

    return queries


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def _org_name_similarity(a: str, b: str) -> float:
    a_lower = a.lower().strip()
    b_lower = b.lower().strip()
    if not a_lower or not b_lower:
        return 0.0
    shorter = min(len(a_lower), len(b_lower))
    longer = max(len(a_lower), len(b_lower))
    common = sum(1 for c in a_lower if c in b_lower)
    return common / longer if longer > 0 else 0.0


def _deduplicate(results: list[dict]) -> list[dict]:
    seen_urls = set()
    unique = []
    for r in results:
        norm = _normalize_url(r.get("url", ""))
        if norm in seen_urls:
            continue
        seen_urls.add(norm)

        is_duplicate = False
        for existing in unique:
            domain_match = urlparse(r.get("url", "")).netloc == urlparse(existing.get("url", "")).netloc
            name_sim = _org_name_similarity(
                r.get("org_name", r.get("title", "")),
                existing.get("org_name", existing.get("title", ""))
            )
            if domain_match and name_sim > 0.7:
                if len(r.get("content", "")) > len(existing.get("content", "")):
                    unique.remove(existing)
                    unique.append(r)
                is_duplicate = True
                break
        if not is_duplicate:
            unique.append(r)
    return unique


def execute_search(queries: list[str], date_range_days: int = 30, progress_callback=None) -> tuple[list[dict], list[str]]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not set")

    client = TavilyClient(api_key=api_key)
    all_results = []
    errors = []

    for i, query in enumerate(queries):
        try:
            def do_search(q=query):
                return client.search(
                    query=q,
                    search_depth="advanced",
                    max_results=10,
                    include_raw_content=False,
                    days=date_range_days,
                )

            response = retry_with_backoff(do_search)
            results = response.get("results", [])
            for r in results:
                all_results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0),
                    "query": query,
                })
            logger.info("Query '%s': %d results", query[:50], len(results))
        except Exception as e:
            logger.error("Query '%s' failed: %s", query[:50], e)
            errors.append(f"Query '{query[:50]}': {str(e)}")

        if progress_callback:
            progress_callback(i + 1, len(queries))

        if i < len(queries) - 1:
            time.sleep(0.5)

    unique = _deduplicate(all_results)
    logger.info("Total results: %d raw, %d after dedup", len(all_results), len(unique))
    return unique, errors
