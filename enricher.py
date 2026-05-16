import os
import time
import logging
import re
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


def _extract_linkedin_url(results: list[dict]) -> str:
    for r in results:
        url = r.get("url", "")
        if "linkedin.com/in/" in url:
            return url
    return ""


def _extract_person_name(results: list[dict], role_hint: str) -> str:
    for r in results:
        title = r.get("title", "")
        # LinkedIn titles: "FirstName LastName - Title - Company | LinkedIn"
        if "linkedin.com" in r.get("url", "") and " - " in title:
            name_part = title.split(" - ")[0].strip()
            name_part = name_part.replace(" | LinkedIn", "").strip()
            if name_part and len(name_part) > 2:
                return name_part

        # Try extracting from content
        content = r.get("content", "")
        if content and role_hint:
            # Look for name patterns near role mentions
            for pattern in [
                rf"(\S+ \S+)\s*[,\-–]\s*{re.escape(role_hint)}",
                rf"{re.escape(role_hint)}\s*[,\-–:]\s*(\S+ \S+)",
            ]:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
    return ""


def _search_contact(client: TavilyClient, org_name: str, role_he: str, role_en: str) -> dict:
    contact = {"name": "", "role": role_en, "linkedin_url": "", "source": "tavily"}

    # Try LinkedIn-targeted search first
    try:
        query = f'"{org_name}" {role_he} OR {role_en} site:linkedin.com'

        def do_search():
            return client.search(query=query, search_depth="basic", max_results=5)

        response = retry_with_backoff(do_search)
        results = response.get("results", [])

        contact["linkedin_url"] = _extract_linkedin_url(results)
        contact["name"] = _extract_person_name(results, role_en)
    except Exception as e:
        logger.warning("LinkedIn search for %s %s failed: %s", org_name, role_en, e)

    # Fallback to general search if no name found
    if not contact["name"]:
        try:
            query = f'"{org_name}" {role_he} OR "{role_en}"'

            def do_fallback():
                return client.search(query=query, search_depth="basic", max_results=5)

            response = retry_with_backoff(do_fallback)
            results = response.get("results", [])
            contact["name"] = _extract_person_name(results, role_en)
            if not contact["linkedin_url"]:
                contact["linkedin_url"] = _extract_linkedin_url(results)
        except Exception as e:
            logger.warning("Fallback search for %s %s failed: %s", org_name, role_en, e)

    return contact


def enrich_contacts(results: list[dict], target_roles: list[str] = None, progress_callback=None) -> list[dict]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.error("TAVILY_API_KEY not set, skipping enrichment")
        for r in results:
            r.setdefault("contacts", [])
        return results

    client = TavilyClient(api_key=api_key)

    role_pairs = [
        ("מנכ\"ל", "CEO"),
        ("סמנכ\"ל משאבי אנוש", "VP HR"),
    ]

    total_searches = len(results) * len(role_pairs)
    completed = 0

    for r in results:
        org_name = r.get("org_name", "")
        contacts = []

        for role_he, role_en in role_pairs:
            contact = _search_contact(client, org_name, role_he, role_en)
            if contact["name"] or contact["linkedin_url"]:
                contacts.append(contact)

            completed += 1
            if progress_callback:
                progress_callback(completed, total_searches)

            time.sleep(0.5)

        r["contacts"] = contacts

    return results
