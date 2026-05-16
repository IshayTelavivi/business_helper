# Business Helper — Lead Generation for Organizational Consultants

A web-based tool that helps organizational consultants and coaches find organizations currently undergoing change processes and likely to need their services.

## What It Does

1. **Searches** Israeli news and business sites for organizations experiencing changes (new CEO appointments, mergers, restructuring, etc.)
2. **Analyzes** each organization for relevance using AI (Claude)
3. **Finds contacts** — CEO and VP HR names with LinkedIn profile links
4. **Generates** personalized outreach drafts in Hebrew
5. **Sends** formatted results by email

## Prerequisites

- Python 3.9 or higher
- Three API keys (see below)

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd business_helper
```

### 2. Create a `.env` file

Copy the example file and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
RESEND_API_KEY=re_...
```

**Where to get the keys:**
- **Anthropic API Key**: Sign up at [console.anthropic.com](https://console.anthropic.com/)
- **Tavily API Key**: Sign up at [tavily.com](https://tavily.com/) (free tier available)
- **Resend API Key**: Sign up at [resend.com](https://resend.com/) (optional — only needed for email)

### 3. Customize your profile

Edit `config/default_profile.json` before the first run. This file seeds your consultant profile:

- **name**: Your full name
- **website**: Your website URL
- **linkedin**: Your LinkedIn profile URL
- **professional_summary**: A paragraph describing your consulting practice
- **services**: List of services you offer (used for matching and outreach)
- **target_sectors**: Industries you serve (used for scoring relevance)
- **change_signals**: Types of organizational changes that indicate a need for your services
- **exclusions**: Categories to skip (e.g., too-small companies, irrelevant industries)
- **past_clients**: Organizations to exclude from results (your existing clients)
- **search_keywords_he**: Hebrew search terms for finding relevant news
- **search_keywords_en**: English search terms
- **preferred_language**: `"he"` for Hebrew (RTL) or `"en"` for English

All of these can also be edited later in the app via Search Settings and Client Profile pages.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## First Run

On the first run, the app will:
- Create a local database (`business_helper.db`)
- Load your profile from `config/default_profile.json`
- Show the main search page

To run your first search:
1. Click **"Run Search"** (or "הפעל חיפוש" in Hebrew)
2. Wait 30-90 seconds while the system searches, analyzes, and enriches results
3. Review the results cards with organization details, contacts, and outreach drafts

## Features

- **Bilingual UI**: Toggle between Hebrew (RTL) and English
- **Multi-client**: Add multiple consultant profiles, each with their own settings and history
- **Two-phase search**: Find organizations first, then optionally enrich with contacts
- **Cooldown filter**: Avoids showing the same organization repeatedly (configurable period)
- **Search history**: All past searches are saved and searchable
- **Email delivery**: Send formatted results to any email address
- **Configurable**: Customize sectors, signals, keywords, and filters per client

## Project Structure

```
├── app.py              # Streamlit web interface
├── search_engine.py    # Tavily search queries
├── analyzer.py         # Claude AI analysis and scoring
├── enricher.py         # Contact finding and LinkedIn search
├── email_sender.py     # Email delivery via Resend
├── database.py         # SQLite data layer
├── profile_manager.py  # Client profile management
├── config/
│   └── default_profile.json  # Profile template (customize before first run)
├── .env.example        # API key template
└── requirements.txt    # Python dependencies
```
