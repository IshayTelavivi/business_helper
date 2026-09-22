import os
import json
import logging
from database import (
    get_client, get_all_clients, create_client, update_client,
    get_search_settings, update_search_settings, seed_from_profile
)

logger = logging.getLogger(__name__)

_config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
CUSTOM_PROFILE_PATH = os.path.join(_config_dir, "nurit_profile.json")
DEFAULT_PROFILE_PATH = os.path.join(_config_dir, "default_profile.json")


def _find_profile_path() -> str | None:
    for path in [CUSTOM_PROFILE_PATH, DEFAULT_PROFILE_PATH]:
        if os.path.exists(path):
            return path
    # Also check for any custom *_profile.json
    if os.path.isdir(_config_dir):
        for f in os.listdir(_config_dir):
            if f.endswith("_profile.json") and f != "default_profile.json":
                return os.path.join(_config_dir, f)
    return None


def load_or_create_default_profile() -> int:
    clients = get_all_clients()
    if clients:
        return clients[0]["id"]

    profile_path = _find_profile_path()
    if profile_path:
        client_id = seed_from_profile(profile_path)
        if client_id:
            logger.info("Seeded profile from %s: client_id=%d", os.path.basename(profile_path), client_id)
            return client_id

    return create_client({"name": "Default Client"})


def get_client_profile(client_id: int) -> dict:
    client = get_client(client_id) or {}
    settings = get_search_settings(client_id)
    return {**client, **settings}


def save_client_profile(client_id: int, profile_data: dict) -> None:
    client_fields = {
        "name": profile_data.get("name", ""),
        "website": profile_data.get("website", ""),
        "linkedin": profile_data.get("linkedin", ""),
        "email": profile_data.get("email", ""),
        "professional_summary": profile_data.get("professional_summary", ""),
        "preferred_language": profile_data.get("preferred_language", "he"),
    }
    update_client(client_id, client_fields)

    settings_fields = {
        "services": profile_data.get("services", []),
        "sectors": profile_data.get("sectors", []),
        "signals": profile_data.get("signals", []),
        "keywords_he": profile_data.get("keywords_he", []),
        "keywords_en": profile_data.get("keywords_en", []),
        "exclusions": profile_data.get("exclusions", []),
        "past_clients": profile_data.get("past_clients", []),
        "target_roles": profile_data.get("target_roles", []),
        "min_company_size": profile_data.get("min_company_size", 50),
        "max_company_size": profile_data.get("max_company_size", 5000),
        "max_results": profile_data.get("max_results", 5),
        "cooldown_days": profile_data.get("cooldown_days", 90),
        "date_range_days": profile_data.get("date_range_days", 30),
    }
    update_search_settings(client_id, settings_fields)


def create_new_client(name: str) -> int:
    return create_client({"name": name})


def get_client_display_list() -> list[tuple[int, str]]:
    clients = get_all_clients()
    return [(c["id"], c["name"]) for c in clients]
