import os
import logging
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

_app_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_app_dir, ".env"), override=True)

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from database import init_db, get_search_results, get_search_runs, search_history, create_search_run, update_search_run, save_search_results, update_result_contacts, get_recent_org_names
from profile_manager import load_or_create_default_profile, get_client_profile, save_client_profile, create_new_client, get_client_display_list
from search_engine import generate_queries, execute_search
from analyzer import score_and_filter, generate_outreach
from enricher import enrich_contacts
from email_sender import send_results_email

init_db()

# --- Bilingual Text System ---
TEXTS = {
    "he": {
        "app_title": "מנוע לידים",
        "search": "חיפוש",
        "history": "היסטוריה",
        "search_settings": "הגדרות חיפוש",
        "client_profile": "פרופיל לקוח",
        "run_search": "הפעל חיפוש",
        "searching": "מחפש...",
        "generating_queries": "מכין שאילתות חיפוש...",
        "executing_searches": "מחפש שינויים ארגוניים...",
        "analyzing_results": "מנתח תוצאות...",
        "finding_contacts": "מחפש אנשי קשר...",
        "generating_outreach": "מכין המלצות פנייה...",
        "search_complete": "החיפוש הושלם!",
        "signal": "סיגנל",
        "sector": "מגזר",
        "opportunity": "הזדמנות",
        "contacts": "אנשי קשר",
        "outreach_draft": "טיוטת פנייה",
        "outreach_recommendation": "המלצת פנייה",
        "copy": "העתק",
        "source": "מקור",
        "send_email": "שלח תוצאות במייל",
        "email_sent": "המייל נשלח בהצלחה!",
        "email_not_configured": "נא להגדיר כתובת מייל בפרופיל הלקוח",
        "no_results": "לא נמצאו תוצאות רלוונטיות",
        "few_results": "נמצאו מעט תוצאות. ניתן להרחיב את טווח התאריכים או להוסיף מילות חיפוש.",
        "results_found": "נמצאו {count} תוצאות",
        "search_by_name": "חיפוש לפי שם חברה או איש קשר",
        "filter_by_date": "סינון לפי תאריך",
        "run_date": "תאריך הרצה",
        "results_count": "תוצאות",
        "companies": "חברות",
        "save": "שמור",
        "saved": "נשמר בהצלחה!",
        "services": "שירותים",
        "sectors": "מגזרים",
        "signals": "סיגנלים לזיהוי",
        "keywords_he": "מילות חיפוש בעברית",
        "keywords_en": "מילות חיפוש באנגלית",
        "exclusions": "קטגוריות לא רלוונטיות",
        "past_clients": "לקוחות עבר (להחרגה)",
        "target_roles": "תפקידי יעד",
        "min_company_size": "גודל חברה מינימלי (עובדים)",
        "max_company_size": "גודל חברה מקסימלי (עובדים)",
        "max_results": "מספר תוצאות מרבי",
        "date_range": "טווח תאריכים (ימים)",
        "name": "שם",
        "website": "אתר",
        "linkedin": "לינקדאין",
        "email": "אימייל",
        "professional_summary": "תיאור מקצועי",
        "language": "שפה",
        "new_client": "לקוח חדש",
        "new_client_name": "שם הלקוח החדש",
        "create": "צור",
        "select_client": "בחר לקוח",
        "missing_keys": "מפתחות API חסרים: {keys}",
        "setup_instructions": "יש ליצור קובץ .env עם המפתחות הנדרשים. ראה .env.example.",
        "welcome_title": "ברוכים הבאים!",
        "welcome_msg": "לחצו על 'הפעל חיפוש' כדי למצוא ארגונים שעוברים שינויים ועשויים להזדקק לשירותיכם.",
        "errors_occurred": "חלק מהשאילתות נכשלו ({count}), אך החיפוש המשיך.",
        "query_progress": "שאילתה {current}/{total}",
        "contact_progress": "מחפש איש קשר {current}/{total}",
        "include_contacts": "חפש גם אנשי קשר",
        "find_contacts_for": "חפש אנשי קשר",
        "find_all_contacts": "חפש אנשי קשר לכל התוצאות",
        "contacts_found": "אנשי קשר נמצאו!",
        "no_contacts_yet": "לא חיפשנו אנשי קשר — לחצו על הכפתור למטה",
        "cooldown_days": "תקופת צינון (ימים)",
        "include_previous": "כלול ארגונים שכבר נמצאו בעבר",
        "filtered_cooldown": "סוננו {count} ארגונים שנמצאו ב-{days} הימים האחרונים",
    },
    "en": {
        "app_title": "Lead Engine",
        "search": "Search",
        "history": "History",
        "search_settings": "Search Settings",
        "client_profile": "Client Profile",
        "run_search": "Run Search",
        "searching": "Searching...",
        "generating_queries": "Generating search queries...",
        "executing_searches": "Searching for organizational changes...",
        "analyzing_results": "Analyzing results...",
        "finding_contacts": "Finding contact information...",
        "generating_outreach": "Generating outreach recommendations...",
        "search_complete": "Search complete!",
        "signal": "Signal",
        "sector": "Sector",
        "opportunity": "Opportunity",
        "contacts": "Contacts",
        "outreach_draft": "Outreach Draft",
        "outreach_recommendation": "Outreach Recommendation",
        "copy": "Copy",
        "source": "Source",
        "send_email": "Send results by email",
        "email_sent": "Email sent successfully!",
        "email_not_configured": "Please configure email in Client Profile settings",
        "no_results": "No relevant results found",
        "few_results": "Few results found. Try expanding the date range or adding search keywords.",
        "results_found": "{count} results found",
        "search_by_name": "Search by company or contact name",
        "filter_by_date": "Filter by date",
        "run_date": "Run Date",
        "results_count": "Results",
        "companies": "Companies",
        "save": "Save",
        "saved": "Saved successfully!",
        "services": "Services",
        "sectors": "Sectors",
        "signals": "Change Signals",
        "keywords_he": "Hebrew Search Keywords",
        "keywords_en": "English Search Keywords",
        "exclusions": "Excluded Categories",
        "past_clients": "Past Clients (excluded from results)",
        "target_roles": "Target Roles",
        "min_company_size": "Minimum Company Size (employees)",
        "max_company_size": "Maximum Company Size (employees)",
        "max_results": "Maximum Results",
        "date_range": "Date Range (days)",
        "name": "Name",
        "website": "Website",
        "linkedin": "LinkedIn",
        "email": "Email",
        "professional_summary": "Professional Summary",
        "language": "Language",
        "new_client": "New Client",
        "new_client_name": "New client name",
        "create": "Create",
        "select_client": "Select Client",
        "missing_keys": "Missing API keys: {keys}",
        "setup_instructions": "Create a .env file with the required keys. See .env.example.",
        "welcome_title": "Welcome!",
        "welcome_msg": "Click 'Run Search' to find organizations undergoing changes that may need your services.",
        "errors_occurred": "Some queries failed ({count}), but the search continued.",
        "query_progress": "Query {current}/{total}",
        "contact_progress": "Finding contact {current}/{total}",
        "include_contacts": "Also find contacts",
        "find_contacts_for": "Find contacts",
        "find_all_contacts": "Find contacts for all results",
        "contacts_found": "Contacts found!",
        "no_contacts_yet": "Contacts not searched yet — click the button below",
        "cooldown_days": "Cooldown Period (days)",
        "include_previous": "Include previously found organizations",
        "filtered_cooldown": "Filtered out {count} organizations found in the last {days} days",
    },
}


def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("language", "he")
    text = TEXTS.get(lang, TEXTS["en"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


# --- Session State Init ---
if "language" not in st.session_state:
    st.session_state.language = "he"
if "client_id" not in st.session_state:
    st.session_state.client_id = load_or_create_default_profile()
if "current_results" not in st.session_state:
    st.session_state.current_results = None
if "current_run_id" not in st.session_state:
    st.session_state.current_run_id = None

# --- Page Config ---
st.set_page_config(
    page_title="Business Helper",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- RTL Support ---
if st.session_state.language == "he":
    st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .stTextInput > div > div > input { direction: rtl; }
    .stTextArea > div > div > textarea { direction: rtl; }
    .stSelectbox > div > div { direction: rtl; }
    .stMultiSelect > div > div { direction: rtl; }
    [data-testid="stSidebar"] { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# --- API Key Check ---
required_keys = ["TAVILY_API_KEY", "ANTHROPIC_API_KEY"]
missing = [k for k in required_keys if not os.getenv(k)]
if missing:
    st.error(t("missing_keys", keys=", ".join(missing)))
    st.info(t("setup_instructions"))
    st.stop()

# --- Sidebar ---
with st.sidebar:
    col1, col2 = st.columns([3, 1])
    with col2:
        lang_options = {"he": "עב", "en": "EN"}
        current_lang = st.session_state.language
        other_lang = "en" if current_lang == "he" else "he"
        if st.button(lang_options[other_lang], key="lang_toggle"):
            st.session_state.language = other_lang
            st.rerun()

    st.divider()

    # Client selector
    clients = get_client_display_list()
    if clients:
        client_names = [c[1] for c in clients]
        client_ids = [c[0] for c in clients]
        current_idx = 0
        if st.session_state.client_id in client_ids:
            current_idx = client_ids.index(st.session_state.client_id)

        selected_name = st.selectbox(
            t("select_client"),
            client_names,
            index=current_idx,
            key="client_selector",
        )
        selected_idx = client_names.index(selected_name)
        if client_ids[selected_idx] != st.session_state.client_id:
            st.session_state.client_id = client_ids[selected_idx]
            st.session_state.current_results = None
            st.rerun()

    # New client
    with st.expander(t("new_client")):
        new_name = st.text_input(t("new_client_name"), key="new_client_input")
        if st.button(t("create"), key="create_client_btn") and new_name:
            new_id = create_new_client(new_name)
            st.session_state.client_id = new_id
            st.rerun()

    st.divider()

    # Navigation
    pages = {
        f"🔍 {t('search')}": "search",
        f"📋 {t('history')}": "history",
        f"⚙️ {t('search_settings')}": "settings",
        f"👤 {t('client_profile')}": "profile",
    }
    selected_page = st.radio(
        "Navigation",
        list(pages.keys()),
        label_visibility="collapsed",
        key="nav",
    )
    page = pages[selected_page]


# --- Result Card Component ---
def render_result_card(result: dict, idx: int):
    score = result.get("score", 0)
    stars = "⭐" * min(int(score), 5)
    org_name = result.get("org_name", "Unknown")

    with st.expander(f"{stars} {org_name} ({score}/5)", expanded=(idx == 0)):
        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown(f"**{t('signal')}:** {result.get('signal', 'N/A')}")
            st.markdown(f"**{t('sector')}:** {result.get('sector', 'N/A')}")
            if result.get("description"):
                st.caption(result["description"])

        with col2:
            if result.get("source_url"):
                st.markdown(f"[{t('source')}]({result['source_url']})")

        st.divider()

        if result.get("opportunity"):
            st.markdown(f"**{t('opportunity')}:**")
            st.markdown(result["opportunity"])

        # Contacts
        contacts = result.get("contacts", [])
        if contacts:
            st.markdown(f"**{t('contacts')}:**")
            for c in contacts:
                name = c.get("name", "")
                role = c.get("role", "")
                linkedin = c.get("linkedin_url", "")
                if name:
                    if linkedin:
                        st.markdown(f"- **{name}** — {role} | [LinkedIn]({linkedin})")
                    else:
                        st.markdown(f"- **{name}** — {role}")
        else:
            st.caption(t("no_contacts_yet"))
            result_id = result.get("id")
            if result_id and st.button(
                f"🔍 {t('find_contacts_for')}",
                key=f"enrich_{idx}_{result_id}",
            ):
                org_name = result.get("org_name", "")
                with st.spinner(t("finding_contacts")):
                    enriched = enrich_contacts(
                        [{"org_name": org_name, "contacts": []}],
                        progress_callback=None,
                    )
                    new_contacts = enriched[0].get("contacts", []) if enriched else []
                    update_result_contacts(result_id, new_contacts)
                    result["contacts"] = new_contacts
                    st.success(t("contacts_found"))
                    st.rerun()

        st.divider()

        # Outreach
        if result.get("outreach_recommendation"):
            st.markdown(f"**{t('outreach_recommendation')}:**")
            st.markdown(result["outreach_recommendation"])

        if result.get("outreach_draft"):
            st.markdown(f"**{t('outreach_draft')}:**")
            st.text_area(
                "",
                value=result["outreach_draft"],
                height=150,
                key=f"draft_{idx}_{result.get('id', idx)}",
                label_visibility="collapsed",
            )


# === PAGE: SEARCH ===
def page_search():
    st.title(t("app_title"))

    profile = get_client_profile(st.session_state.client_id)

    # Show existing results
    if st.session_state.current_results:
        results = st.session_state.current_results
        st.success(t("results_found", count=len(results)))

        # "Find all contacts" button if any results lack contacts
        has_missing_contacts = any(not r.get("contacts") for r in results)
        if has_missing_contacts:
            if st.button(f"🔍 {t('find_all_contacts')}", type="primary", key="enrich_all_btn"):
                with st.status(t("finding_contacts"), expanded=True) as enrich_status:
                    progress_bar = st.progress(0)
                    to_enrich = [r for r in results if not r.get("contacts")]
                    total = len(to_enrich)
                    for j, r in enumerate(to_enrich):
                        enriched = enrich_contacts(
                            [{"org_name": r.get("org_name", ""), "contacts": []}],
                            progress_callback=None,
                        )
                        new_contacts = enriched[0].get("contacts", []) if enriched else []
                        result_id = r.get("id")
                        if result_id:
                            update_result_contacts(result_id, new_contacts)
                        r["contacts"] = new_contacts
                        progress_bar.progress(int((j + 1) / total * 100))
                    enrich_status.update(label=t("contacts_found"), state="complete")
                st.rerun()

        for i, r in enumerate(results):
            render_result_card(r, i)

        # Email button
        st.divider()
        email = profile.get("email", "")
        if email:
            if st.button(t("send_email"), key="send_email_btn"):
                try:
                    send_results_email(
                        email,
                        profile.get("name", ""),
                        results,
                        datetime.now().strftime("%Y-%m-%d %H:%M"),
                        rtl=(st.session_state.language == "he"),
                    )
                    st.success(t("email_sent"))
                except Exception as e:
                    st.error(str(e))
        else:
            st.info(t("email_not_configured"))
        return

    # Welcome / run search
    if not st.session_state.current_results:
        st.markdown(f"### {t('welcome_title')}")
        st.markdown(t("welcome_msg"))

    include_contacts = st.checkbox(t("include_contacts"), value=False, key="include_contacts_cb")
    include_previous = st.checkbox(t("include_previous"), value=False, key="include_previous_cb")

    if st.button(t("run_search"), type="primary", key="run_search_btn"):
        settings = profile
        run_id = create_search_run(st.session_state.client_id)

        with st.status(t("searching"), expanded=True) as status:
            # Step 1: Generate queries
            st.write(t("generating_queries"))
            queries = generate_queries(settings)
            update_search_run(run_id, query_count=len(queries))

            # Step 2: Execute searches
            st.write(t("executing_searches"))
            progress_bar = st.progress(0)
            query_status = st.empty()

            def search_progress(current, total):
                progress_bar.progress(int(current / total * 30))
                query_status.text(t("query_progress", current=current, total=total))

            raw_results, errors = execute_search(
                queries, settings.get("date_range_days", 30), progress_callback=search_progress
            )
            update_search_run(run_id, raw_result_count=len(raw_results))

            if errors:
                st.warning(t("errors_occurred", count=len(errors)))

            if not raw_results:
                update_search_run(run_id, status="completed", filtered_result_count=0)
                status.update(label=t("no_results"), state="error")
                st.warning(t("no_results"))
                return

            # Step 3: Score and filter
            st.write(t("analyzing_results"))
            progress_bar.progress(35)
            scored = score_and_filter(
                raw_results, settings, settings.get("past_clients", [])
            )
            progress_bar.progress(55)

            # Step 3b: Cooldown filter
            if not include_previous:
                cooldown_days = settings.get("cooldown_days", 90)
                recent_orgs = get_recent_org_names(st.session_state.client_id, cooldown_days)
                before_count = len(scored)
                scored = [r for r in scored if r.get("org_name", "") not in recent_orgs]
                filtered_count = before_count - len(scored)
                if filtered_count > 0:
                    st.info(t("filtered_cooldown", count=filtered_count, days=cooldown_days))

            if not scored:
                update_search_run(run_id, status="completed", filtered_result_count=0)
                status.update(label=t("no_results"), state="error")
                st.warning(t("no_results"))
                return

            if include_contacts:
                # Step 4: Enrich contacts
                st.write(t("finding_contacts"))
                contact_status = st.empty()

                def contact_progress(current, total):
                    progress_bar.progress(55 + int(current / total * 25))
                    contact_status.text(t("contact_progress", current=current, total=total))

                enriched = enrich_contacts(scored, settings.get("target_roles", []), progress_callback=contact_progress)
                progress_bar.progress(80)
            else:
                enriched = scored
                for r in enriched:
                    r.setdefault("contacts", [])
                progress_bar.progress(80)

            # Step 5: Generate outreach
            st.write(t("generating_outreach"))
            final = generate_outreach(enriched, profile)
            progress_bar.progress(100)

            # Save to database
            result_ids = save_search_results(run_id, final)
            for i, rid in enumerate(result_ids):
                final[i]["id"] = rid

            update_search_run(
                run_id,
                status="completed",
                filtered_result_count=len(final),
                error_log="\n".join(errors) if errors else None,
            )

            status.update(label=t("search_complete"), state="complete")

        st.session_state.current_results = final
        st.session_state.current_run_id = run_id

        if len(final) < 5:
            st.info(t("few_results"))

        st.rerun()


# === PAGE: HISTORY ===
def page_history():
    st.title(t("history"))

    search_query = st.text_input(t("search_by_name"), key="history_search")

    if search_query:
        results = search_history(st.session_state.client_id, search_query)
        if results:
            st.success(t("results_found", count=len(results)))
            for i, r in enumerate(results):
                render_result_card(r, i)
        else:
            st.info(t("no_results"))
        return

    runs = get_search_runs(st.session_state.client_id)
    if not runs:
        st.info(t("welcome_msg"))
        return

    for run in runs:
        run_date = run.get("run_date", "")
        count = run.get("filtered_result_count", 0)
        org_names = run.get("org_names", "") or ""
        status_icon = "✅" if run.get("status") == "completed" else "🔄"

        header = f"{status_icon} {run_date} — {count} {t('results_count')}"
        if org_names:
            header += f" | {org_names}"

        with st.expander(header):
            results = get_search_results(run["id"])
            if results:
                for i, r in enumerate(results):
                    render_result_card(r, i + run["id"] * 100)

                # Email button for historical results
                profile = get_client_profile(st.session_state.client_id)
                email = profile.get("email", "")
                if email:
                    if st.button(t("send_email"), key=f"email_run_{run['id']}"):
                        try:
                            send_results_email(
                                email,
                                profile.get("name", ""),
                                results,
                                run_date,
                                rtl=(st.session_state.language == "he"),
                            )
                            st.success(t("email_sent"))
                        except Exception as e:
                            st.error(str(e))
            else:
                st.info(t("no_results"))


# === PAGE: SEARCH SETTINGS ===
def page_settings():
    st.title(t("search_settings"))

    profile = get_client_profile(st.session_state.client_id)

    with st.form("settings_form"):
        sectors = st.text_area(
            t("sectors"),
            value="\n".join(profile.get("sectors", [])),
            height=200,
            key="settings_sectors",
        )
        signals = st.text_area(
            t("signals"),
            value="\n".join(profile.get("signals", [])),
            height=250,
            key="settings_signals",
        )
        exclusions = st.text_area(
            t("exclusions"),
            value="\n".join(profile.get("exclusions", [])),
            height=150,
            key="settings_exclusions",
        )

        col1, col2 = st.columns(2)
        with col1:
            keywords_he = st.text_area(
                t("keywords_he"),
                value="\n".join(profile.get("keywords_he", [])),
                height=250,
                key="settings_kw_he",
            )
        with col2:
            keywords_en = st.text_area(
                t("keywords_en"),
                value="\n".join(profile.get("keywords_en", [])),
                height=250,
                key="settings_kw_en",
            )

        past_clients = st.text_area(
            t("past_clients"),
            value="\n".join(profile.get("past_clients", [])),
            height=200,
            key="settings_past",
        )
        target_roles = st.text_area(
            t("target_roles"),
            value="\n".join(profile.get("target_roles", [])),
            height=150,
            key="settings_roles",
        )

        col1, col2 = st.columns(2)
        with col1:
            min_size = st.number_input(
                t("min_company_size"),
                value=profile.get("min_company_size", 50),
                min_value=1,
                key="settings_min_size",
            )
        with col2:
            max_size = st.number_input(
                t("max_company_size"),
                value=profile.get("max_company_size", 5000),
                min_value=1,
                key="settings_max_size",
            )

        col1, col2, col3 = st.columns(3)
        with col1:
            max_results = st.number_input(
                t("max_results"),
                min_value=1,
                max_value=10,
                value=profile.get("max_results", 5),
                key="settings_max_results",
            )
        with col2:
            date_range = st.number_input(
                t("date_range"),
                min_value=7,
                max_value=90,
                value=profile.get("date_range_days", 30),
                key="settings_date_range",
            )
        with col3:
            cooldown = st.number_input(
                t("cooldown_days"),
                min_value=7,
                max_value=365,
                value=profile.get("cooldown_days", 90),
                key="settings_cooldown",
            )

        if st.form_submit_button(t("save"), type="primary"):
            def split_lines(text):
                return [line.strip() for line in text.strip().split("\n") if line.strip()]

            save_client_profile(st.session_state.client_id, {
                **profile,
                "sectors": split_lines(sectors),
                "signals": split_lines(signals),
                "exclusions": split_lines(exclusions),
                "keywords_he": split_lines(keywords_he),
                "keywords_en": split_lines(keywords_en),
                "past_clients": split_lines(past_clients),
                "target_roles": split_lines(target_roles),
                "min_company_size": min_size,
                "max_company_size": max_size,
                "max_results": max_results,
                "date_range_days": date_range,
                "cooldown_days": cooldown,
            })
            st.success(t("saved"))


# === PAGE: CLIENT PROFILE ===
def page_profile():
    st.title(t("client_profile"))

    profile = get_client_profile(st.session_state.client_id)

    with st.form("profile_form"):
        name = st.text_input(t("name"), value=profile.get("name", ""), key="profile_name")
        website = st.text_input(t("website"), value=profile.get("website", ""), key="profile_website")
        linkedin = st.text_input(t("linkedin"), value=profile.get("linkedin", ""), key="profile_linkedin")
        email = st.text_input(t("email"), value=profile.get("email", ""), key="profile_email")

        summary = st.text_area(
            t("professional_summary"),
            value=profile.get("professional_summary", ""),
            height=200,
            key="profile_summary",
        )

        services = st.text_area(
            t("services"),
            value="\n".join(profile.get("services", [])),
            height=200,
            help="One service per line" if st.session_state.language == "en" else "שירות אחד בכל שורה",
            key="profile_services",
        )

        target_roles = st.text_area(
            t("target_roles"),
            value="\n".join(profile.get("target_roles", [])),
            height=100,
            key="profile_roles",
        )

        if st.form_submit_button(t("save"), type="primary"):
            def split_lines(text):
                return [line.strip() for line in text.strip().split("\n") if line.strip()]

            save_client_profile(st.session_state.client_id, {
                **profile,
                "name": name,
                "website": website,
                "linkedin": linkedin,
                "email": email,
                "professional_summary": summary,
                "services": split_lines(services),
                "target_roles": split_lines(target_roles),
            })
            st.success(t("saved"))


# --- Page Router ---
if page == "search":
    page_search()
elif page == "history":
    page_history()
elif page == "settings":
    page_settings()
elif page == "profile":
    page_profile()
