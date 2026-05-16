import sqlite3
import json
import os
import logging
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "business_helper.db")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate_db(conn):
    cursor = conn.execute("PRAGMA table_info(search_settings)")
    columns = {row[1] for row in cursor.fetchall()}
    if "max_company_size" not in columns:
        conn.execute("ALTER TABLE search_settings ADD COLUMN max_company_size INTEGER DEFAULT 5000")
        logger.info("Migration: added max_company_size column")
    if "cooldown_days" not in columns:
        conn.execute("ALTER TABLE search_settings ADD COLUMN cooldown_days INTEGER DEFAULT 90")
        logger.info("Migration: added cooldown_days column")


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                website TEXT,
                linkedin TEXT,
                email TEXT,
                professional_summary TEXT,
                logo_path TEXT,
                preferred_language TEXT DEFAULT 'he',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS search_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL UNIQUE REFERENCES clients(id) ON DELETE CASCADE,
                services TEXT DEFAULT '[]',
                sectors TEXT DEFAULT '[]',
                signals TEXT DEFAULT '[]',
                keywords_he TEXT DEFAULT '[]',
                keywords_en TEXT DEFAULT '[]',
                exclusions TEXT DEFAULT '[]',
                past_clients TEXT DEFAULT '[]',
                target_roles TEXT DEFAULT '[]',
                min_company_size INTEGER DEFAULT 50,
                max_company_size INTEGER DEFAULT 5000,
                max_results INTEGER DEFAULT 5,
                date_range_days INTEGER DEFAULT 30,
                cooldown_days INTEGER DEFAULT 90
            );

            CREATE TABLE IF NOT EXISTS search_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                query_count INTEGER DEFAULT 0,
                raw_result_count INTEGER DEFAULT 0,
                filtered_result_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                error_log TEXT
            );

            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES search_runs(id) ON DELETE CASCADE,
                org_name TEXT NOT NULL,
                score REAL,
                signal TEXT,
                sector TEXT,
                description TEXT,
                opportunity TEXT,
                outreach_draft TEXT,
                outreach_recommendation TEXT,
                source_url TEXT,
                source_title TEXT,
                raw_snippet TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id INTEGER NOT NULL REFERENCES search_results(id) ON DELETE CASCADE,
                name TEXT,
                role TEXT,
                linkedin_url TEXT,
                email TEXT,
                source TEXT
            );
        """)
        _migrate_db(conn)


def seed_from_profile(json_path: str) -> int | None:
    with open(json_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM clients WHERE name = ?", (profile["name"],)
        ).fetchone()
        if existing:
            return existing["id"]

        cursor = conn.execute(
            """INSERT INTO clients (name, website, linkedin, email, professional_summary, preferred_language)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                profile["name"],
                profile.get("website", ""),
                profile.get("linkedin", ""),
                profile.get("email", ""),
                profile.get("professional_summary", ""),
                profile.get("preferred_language", "he"),
            ),
        )
        client_id = cursor.lastrowid

        conn.execute(
            """INSERT INTO search_settings
               (client_id, services, sectors, signals, keywords_he, keywords_en,
                exclusions, past_clients, target_roles, min_company_size, max_results, date_range_days)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                client_id,
                json.dumps(profile.get("services", []), ensure_ascii=False),
                json.dumps(profile.get("target_sectors", []), ensure_ascii=False),
                json.dumps(profile.get("change_signals", []), ensure_ascii=False),
                json.dumps(profile.get("search_keywords_he", []), ensure_ascii=False),
                json.dumps(profile.get("search_keywords_en", []), ensure_ascii=False),
                json.dumps(profile.get("exclusions", []), ensure_ascii=False),
                json.dumps(profile.get("past_clients", []), ensure_ascii=False),
                json.dumps(profile.get("target_roles", []), ensure_ascii=False),
                profile.get("ideal_org_size", {}).get("minimum", 50),
                5,
                30,
            ),
        )
        return client_id


# --- Client CRUD ---

def get_all_clients() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def get_client(client_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        return dict(row) if row else None


def create_client(data: dict) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO clients (name, website, linkedin, email, professional_summary, preferred_language)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data.get("name", ""),
                data.get("website", ""),
                data.get("linkedin", ""),
                data.get("email", ""),
                data.get("professional_summary", ""),
                data.get("preferred_language", "he"),
            ),
        )
        client_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO search_settings (client_id) VALUES (?)", (client_id,)
        )
        return client_id


def update_client(client_id: int, data: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE clients SET name=?, website=?, linkedin=?, email=?,
               professional_summary=?, preferred_language=?, updated_at=?
               WHERE id=?""",
            (
                data.get("name", ""),
                data.get("website", ""),
                data.get("linkedin", ""),
                data.get("email", ""),
                data.get("professional_summary", ""),
                data.get("preferred_language", "he"),
                datetime.now().isoformat(),
                client_id,
            ),
        )


def delete_client(client_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))


# --- Search Settings ---

def get_search_settings(client_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM search_settings WHERE client_id = ?", (client_id,)
        ).fetchone()
        if not row:
            return {}
        d = dict(row)
        for key in ["services", "sectors", "signals", "keywords_he", "keywords_en",
                     "exclusions", "past_clients", "target_roles"]:
            d[key] = json.loads(d[key]) if d[key] else []
        d.setdefault("max_company_size", 5000)
        d.setdefault("cooldown_days", 90)
        return d


def update_search_settings(client_id: int, settings: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE search_settings SET
               services=?, sectors=?, signals=?, keywords_he=?, keywords_en=?,
               exclusions=?, past_clients=?, target_roles=?,
               min_company_size=?, max_company_size=?, max_results=?, date_range_days=?,
               cooldown_days=?
               WHERE client_id=?""",
            (
                json.dumps(settings.get("services", []), ensure_ascii=False),
                json.dumps(settings.get("sectors", []), ensure_ascii=False),
                json.dumps(settings.get("signals", []), ensure_ascii=False),
                json.dumps(settings.get("keywords_he", []), ensure_ascii=False),
                json.dumps(settings.get("keywords_en", []), ensure_ascii=False),
                json.dumps(settings.get("exclusions", []), ensure_ascii=False),
                json.dumps(settings.get("past_clients", []), ensure_ascii=False),
                json.dumps(settings.get("target_roles", []), ensure_ascii=False),
                settings.get("min_company_size", 50),
                settings.get("max_company_size", 5000),
                settings.get("max_results", 5),
                settings.get("date_range_days", 30),
                settings.get("cooldown_days", 90),
                client_id,
            ),
        )


# --- Search Runs ---

def create_search_run(client_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO search_runs (client_id) VALUES (?)", (client_id,)
        )
        return cursor.lastrowid


def update_search_run(run_id: int, **kwargs) -> None:
    if not kwargs:
        return
    valid_fields = {"query_count", "raw_result_count", "filtered_result_count", "status", "error_log"}
    fields = {k: v for k, v in kwargs.items() if k in valid_fields}
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [run_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE search_runs SET {set_clause} WHERE id=?", values)


def get_search_runs(client_id: int, limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT sr.*, GROUP_CONCAT(DISTINCT sres.org_name) as org_names
               FROM search_runs sr
               LEFT JOIN search_results sres ON sres.run_id = sr.id
               WHERE sr.client_id = ?
               GROUP BY sr.id
               ORDER BY sr.run_date DESC
               LIMIT ?""",
            (client_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_search_run(run_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM search_runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None


# --- Search Results ---

def save_search_results(run_id: int, results: list[dict]) -> list[int]:
    result_ids = []
    with get_connection() as conn:
        for r in results:
            cursor = conn.execute(
                """INSERT INTO search_results
                   (run_id, org_name, score, signal, sector, description,
                    opportunity, outreach_draft, outreach_recommendation, source_url, source_title, raw_snippet)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    r.get("org_name", ""),
                    r.get("score", 0),
                    r.get("signal", ""),
                    r.get("sector", ""),
                    r.get("description", ""),
                    r.get("opportunity", ""),
                    r.get("outreach_draft", ""),
                    r.get("outreach_recommendation", ""),
                    r.get("source_url", ""),
                    r.get("source_title", ""),
                    r.get("raw_snippet", ""),
                ),
            )
            result_id = cursor.lastrowid
            result_ids.append(result_id)

            for contact in r.get("contacts", []):
                conn.execute(
                    """INSERT INTO contacts (result_id, name, role, linkedin_url, email, source)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        result_id,
                        contact.get("name", ""),
                        contact.get("role", ""),
                        contact.get("linkedin_url", ""),
                        contact.get("email", ""),
                        contact.get("source", ""),
                    ),
                )
    return result_ids


def get_search_results(run_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM search_results WHERE run_id = ? ORDER BY score DESC",
            (run_id,),
        ).fetchall()
        results = []
        for row in rows:
            r = dict(row)
            contacts = conn.execute(
                "SELECT * FROM contacts WHERE result_id = ?", (r["id"],)
            ).fetchall()
            r["contacts"] = [dict(c) for c in contacts]
            results.append(r)
        return results


def get_recent_org_names(client_id: int, cooldown_days: int = 90) -> set[str]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT DISTINCT sres.org_name
               FROM search_results sres
               JOIN search_runs srun ON srun.id = sres.run_id
               WHERE srun.client_id = ?
                 AND srun.run_date >= datetime('now', ?)""",
            (client_id, f"-{cooldown_days} days"),
        ).fetchall()
        return {row["org_name"] for row in rows}


def update_result_contacts(result_id: int, contacts: list[dict]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM contacts WHERE result_id = ?", (result_id,))
        for contact in contacts:
            conn.execute(
                """INSERT INTO contacts (result_id, name, role, linkedin_url, email, source)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    result_id,
                    contact.get("name", ""),
                    contact.get("role", ""),
                    contact.get("linkedin_url", ""),
                    contact.get("email", ""),
                    contact.get("source", ""),
                ),
            )


def search_history(client_id: int, query: str) -> list[dict]:
    with get_connection() as conn:
        pattern = f"%{query}%"
        rows = conn.execute(
            """SELECT sr.*, sres.org_name, sres.signal, sres.score, sres.id as result_id,
                      srun.run_date
               FROM search_results sres
               JOIN search_runs srun ON srun.id = sres.run_id
               LEFT JOIN search_results sr ON sr.id = sres.id
               WHERE srun.client_id = ?
                 AND (sres.org_name LIKE ? OR EXISTS (
                     SELECT 1 FROM contacts c WHERE c.result_id = sres.id AND c.name LIKE ?
                 ))
               ORDER BY srun.run_date DESC""",
            (client_id, pattern, pattern),
        ).fetchall()
        results = []
        for row in rows:
            r = dict(row)
            contacts = conn.execute(
                "SELECT * FROM contacts WHERE result_id = ?", (r["result_id"],)
            ).fetchall()
            r["contacts"] = [dict(c) for c in contacts]
            results.append(r)
        return results
