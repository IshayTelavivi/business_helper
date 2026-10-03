import os
import json
import re
import logging
import time
import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-5-5"

BATCH_SIZE = 20


def _get_client():
    return anthropic.Anthropic()


def _parse_json_response(text: str) -> list | dict:
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def _call_claude(prompt: str, max_tokens: int = 16000) -> str:
    client = _get_client()
    for attempt in range(3):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            if message.stop_reason == "refusal":
                category = getattr(message.stop_details, "category", None)
                raise RuntimeError(f"Claude declined the request (category: {category})")
            # Thinking is on by default, so the text block is not always first.
            text = next((b.text for b in message.content if b.type == "text"), None)
            if message.stop_reason == "max_tokens":
                logger.warning("Response hit max_tokens (%d); output may be truncated", max_tokens)
            if text is None:
                raise RuntimeError(f"No text block in response (stop_reason: {message.stop_reason})")
            return text
        except RuntimeError:
            raise
        except anthropic.RateLimitError:
            if attempt == 2:
                raise
            delay = 30 * (attempt + 1)
            logger.warning("Rate limited, waiting %ds before retry %d/3", delay, attempt + 1)
            time.sleep(delay)
        except Exception as e:
            if attempt == 2:
                raise
            delay = 5 * (2 ** attempt)
            logger.warning("Claude API retry %d/3 after %ds: %s", attempt + 1, delay, e)
            time.sleep(delay)


# === PROMPT: SCORE AND FILTER ===
SCORING_PROMPT = """You are an expert at identifying business opportunities for organizational consultants and coaches in Israel.

Given the consultant's profile:
- Services offered: {services}
- Target sectors: {sectors}
- Change signals of interest: {signals}
- Past clients (EXCLUDE these — score 0): {past_clients}
- Excluded categories (score 0): {exclusions}
- Minimum company size: {min_company_size} employees
- Geography: Israel only

Analyze each search result and score 1-5 for relevance as a potential client:

5 = Perfect match — clear change signal + target sector + right size + Israel
4 = Strong match — most criteria met, good opportunity
3 = Moderate — some criteria met, possible opportunity
2 = Weak — tangential relevance, unclear fit
1 = Minimal — barely relevant but still an Israeli organization

Score 0 ONLY for: past clients, excluded categories, not in Israel, or clearly irrelevant (e.g. sports, entertainment).

IMPORTANT: Be generous with scoring. If an organization is Israeli and has ANY change signal, score at least 3. Most Israeli organizations undergoing change should score 3-5.

{results_text}

Return a JSON array. Each object must have:
- org_name: the organization name (extract from the article, NOT the article title)
- score: integer 0-5
- signal: which change signal was detected (be specific)
- sector: which sector
- description: one sentence about what the organization does
- reasoning: brief explanation of the score
- source_url: the URL from the search result
- source_title: the title from the search result
- raw_snippet: key excerpt from the content (2-3 sentences max)

Combine duplicates (same org from different results) into one entry with the best data.

Return ONLY a valid JSON array. No other text."""


def _score_batch(batch: list[dict], settings: dict, past_clients: list[str]) -> list[dict]:
    results_text = ""
    for i, r in enumerate(batch, 1):
        content = r.get("content", "N/A")
        if len(content) > 500:
            content = content[:500] + "..."
        results_text += f"\n--- Result {i} ---\n"
        results_text += f"Title: {r.get('title', 'N/A')}\n"
        results_text += f"URL: {r.get('url', 'N/A')}\n"
        results_text += f"Content: {content}\n"

    prompt = SCORING_PROMPT.format(
        services=json.dumps(settings.get("services", []), ensure_ascii=False),
        sectors=json.dumps(settings.get("sectors", []), ensure_ascii=False),
        signals=json.dumps(settings.get("signals", []), ensure_ascii=False),
        past_clients=json.dumps(past_clients, ensure_ascii=False),
        exclusions=json.dumps(settings.get("exclusions", []), ensure_ascii=False),
        min_company_size=settings.get("min_company_size", 50),
        results_text=results_text,
    )

    response_text = _call_claude(prompt, max_tokens=16000)
    return _parse_json_response(response_text)


def score_and_filter(raw_results: list[dict], settings: dict, past_clients: list[str]) -> list[dict]:
    if not raw_results:
        return []

    # Process in batches to avoid rate limits
    all_scored = []
    for i in range(0, len(raw_results), BATCH_SIZE):
        batch = raw_results[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(raw_results) + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info("Scoring batch %d/%d (%d results)", batch_num, total_batches, len(batch))

        try:
            scored = _score_batch(batch, settings, past_clients)
            all_scored.extend(scored)
        except Exception as e:
            logger.error("Scoring batch %d failed: %s", batch_num, e)

        # Wait between batches to avoid rate limits
        if i + BATCH_SIZE < len(raw_results):
            time.sleep(5)

    if not all_scored:
        logger.warning("All scoring batches failed, returning raw results as fallback")
        fallback = []
        for r in raw_results[:settings.get("max_results", 5)]:
            fallback.append({
                "org_name": r.get("title", "Unknown"),
                "score": 1,
                "signal": "Unknown — scoring failed",
                "sector": "Unknown",
                "description": "",
                "reasoning": "Automatic fallback — AI scoring was unavailable",
                "source_url": r.get("url", ""),
                "source_title": r.get("title", ""),
                "raw_snippet": r.get("content", "")[:300],
            })
        return fallback

    # Deduplicate by org name (keep highest score)
    seen = {}
    for r in all_scored:
        name = r.get("org_name", "").strip()
        if not name:
            continue
        existing = seen.get(name)
        if not existing or r.get("score", 0) > existing.get("score", 0):
            seen[name] = r
    all_scored = list(seen.values())

    # Filter out score 0, sort by score descending
    all_scored = [r for r in all_scored if r.get("score", 0) > 0]
    all_scored.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Always return results — prefer high scores but never return empty
    max_results = settings.get("max_results", 5)
    return all_scored[:max_results]


# === PROMPT: GENERATE OUTREACH ===
OUTREACH_PROMPT = """You are an expert business development consultant helping an organizational consultant craft personalized outreach.

Consultant profile:
- Name: {consultant_name}
- Services: {services}
- Professional summary: {summary}
- Website: {website}
- LinkedIn: {linkedin}

For each of the following organizations, generate personalized outreach content:

{orgs_text}

For each organization, return a JSON array of objects with:
- org_name: the organization name
- opportunity: 2-3 sentences explaining the specific opportunity (what change was detected, why it creates a need for the consultant's services, which specific services are most relevant)
- outreach_draft: a personalized outreach message in Hebrew (3-4 sentences). The message should:
  * Reference the specific change/event detected
  * Connect it to a specific service the consultant offers
  * Be professional but warm in tone
  * Include a soft call to action (suggest a brief meeting or call)
  * NOT be overly salesy
- outreach_recommendation: which channel to use (email/LinkedIn/phone) and why, plus suggested tone
- lead_service: which specific service to lead with for this organization

Return ONLY a valid JSON array. No other text."""


def generate_outreach(scored_results: list[dict], client_profile: dict) -> list[dict]:
    if not scored_results:
        return []

    orgs_text = ""
    for i, r in enumerate(scored_results, 1):
        orgs_text += f"\n--- Organization {i} ---\n"
        orgs_text += f"Name: {r.get('org_name', 'N/A')}\n"
        orgs_text += f"Signal detected: {r.get('signal', 'N/A')}\n"
        orgs_text += f"Sector: {r.get('sector', 'N/A')}\n"
        orgs_text += f"Description: {r.get('description', 'N/A')}\n"
        orgs_text += f"Context: {r.get('raw_snippet', r.get('reasoning', 'N/A'))}\n"

    prompt = OUTREACH_PROMPT.format(
        consultant_name=client_profile.get("name", ""),
        services=json.dumps(client_profile.get("services", []), ensure_ascii=False),
        summary=client_profile.get("professional_summary", ""),
        website=client_profile.get("website", ""),
        linkedin=client_profile.get("linkedin", ""),
        orgs_text=orgs_text,
    )

    try:
        response_text = _call_claude(prompt, max_tokens=16000)
        outreach_data = _parse_json_response(response_text)
    except Exception as e:
        logger.error("Outreach generation failed: %s", e)
        return scored_results

    outreach_map = {item["org_name"]: item for item in outreach_data if "org_name" in item}

    for result in scored_results:
        org_name = result.get("org_name", "")
        outreach = outreach_map.get(org_name, {})
        result["opportunity"] = outreach.get("opportunity", result.get("reasoning", ""))
        result["outreach_draft"] = outreach.get("outreach_draft", "")
        result["outreach_recommendation"] = outreach.get("outreach_recommendation", "")

    return scored_results
