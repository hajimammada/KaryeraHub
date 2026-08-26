# 🇦🇿 İş Radarı Bot (isradaribot)

[![Telegram Channel](https://img.shields.io/badge/Telegram-@isradari-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://isradari.t.me)
[![Live Channel](https://img.shields.io/badge/Channel_Link-isradari.t.me-blue?style=for-the-badge)](https://isradari.t.me)

> 📢 **Official Telegram Channel**: [https://isradari.t.me](https://isradari.t.me) (`@isradari`)

An intelligent, automated Telegram bot application for **[@isradari](https://isradari.t.me)** that monitors top Azerbaijani job portals (`linkedin`, `jobsearch.az`, `hellojob.az`, `ishelanlari.az`, `banker.az`, `boss.az`), uses **Google Gemini AI** for structured vacancy extraction, filters out duplicates using a **7-day historical lookback** SQLite database, and publishes a balanced, date-ordered daily batch of **15 fresh vacancies** in **1 single clean message**.

---

## 🌟 Key Features

- 🧠 **AI-Assisted Parsing**: No brittle custom regex or fragile CSS scrapers. Fresh page content is passed to Google Gemini (`gemini-3.1-flash-lite`), returning structured JSON data.
- 💼 **LinkedIn Azerbaijan Jobs**: Scrapes genuine LinkedIn postings in Azerbaijan and cleans tracking parameters.
- 🛡️ **Spam Recruiter Filter**: Automatically drops spam mass-recruiters (Agoda, Turing, BairesDev, etc.).
- 📅 **Date Ordering (Latest First)**: Sorts vacancies so the freshest opportunities appear at the top.
- ⚖️ **Proportional Multi-Source Diversity**: Balances daily vacancies across all active job portals.
- 🛡️ **7-Day Deduplication**: Built-in SQLite database prevents duplicate posts across a 7-day rolling window.
- 📬 **Single Message Delivery**: Consolidates 15 jobs into 1 clean Telegram post.
- ☁️ **100% Cloud Automation**: Includes GitHub Actions workflow to run daily for free without keeping your PC on.
- 🧪 **Full Test Suite**: 20 passing unit and integration tests with `pytest`.

---

## 🏗️ Project Architecture

```
isradaribot/
├── config/
│   ├── __init__.py
│   └── settings.py            # Pydantic environment configuration
├── src/
│   ├── database/
│   │   ├── models.py          # SQLite schema & URL normalization/hashing
│   │   └── repository.py      # 7-day deduplication repository
│   ├── scraper/
│   │   ├── base.py            # Base dataclasses & Collector interface
│   │   ├── balancer.py        # Proportional multi-source balancer & date sorter
│   │   ├── gemini_extractor.py# Gemini API client with spam filter & HTML cleaner
│   │   ├── web_collector.py   # Multi-source fetcher (LinkedIn, JobSearch, HelloJob, etc.)
│   │   └── pipeline.py        # Complete discovery orchestrator
│   ├── telegram/
│   │   ├── client.py          # Telegram Bot API wrapper
│   │   ├── formatter.py       # 'id, jobname, company, link' formatting
│   │   └── dispatcher.py      # Channel batch publisher
│   ├── scheduler/
│   │   └── cron_runner.py     # Daemon scheduler
│   └── utils/
│       └── logger.py          # Colorized console & rotating file logger
├── .github/workflows/         # Daily GitHub Actions cloud scheduler
├── tests/                     # 20 pytest unit and integration tests
├── data/                      # SQLite database storage (jobs.db)
├── logs/                      # Rotating log files (bot.log)
├── main.py                    # Unified CLI entrypoint
├── requirements.txt           # Dependencies
└── .env                       # Pre-configured credentials
```

---

## 🚀 Quick Start Guide

### 1. Installation

Ensure Python 3.10+ is installed:
```powershell
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

Edit `.env` to configure your tokens:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHANNEL_ID=@isradari
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
DAILY_MAX_JOBS=15
MAX_JOBS_PER_MESSAGE=15
DEDUPLICATION_DAYS=7
DAILY_SCHEDULE_TIME=09:00
```

> [!IMPORTANT]
> Make sure you add your bot (`@hajimammmadabot`) as an **Administrator** in your Telegram channel with **Post Messages** permission.

---

## 🛠️ CLI Usage

### 1. Dry Run (Test AI Extraction & Formatting without posting)
```powershell
python main.py --dry-run
```

### 2. Test Bot & Channel Connection
```powershell
python main.py --test-bot
```

### 3. Run Single Cycle (Post today's new vacancies)
```powershell
python main.py --run-once
```

### 4. Run Continuous Daemon
```powershell
python main.py --daemon
```

### 5. Check Database & Deduplication Statistics
```powershell
python main.py --stats
```

---

## 🧪 Running Automated Tests

Run the test suite to verify deduplication, batch formatting, and AI response handlers:
```powershell
pytest tests/ -v
```

---

## 🔄 Application Lifecycle Stages

1. **Development & Local Verification**:
   - Run unit tests with `pytest`.
   - Run `python main.py --dry-run` to inspect live data from job portals.
2. **Channel Integration**:
   - Create your Telegram channel, add `@hajimammmadabot` as Administrator.
   - Run `python main.py --test-bot` to verify posting permissions.
3. **Production Deployment**:
   - **Option A (Daemon)**: Run `python main.py --daemon` as a background process or systemd service.
   - **Option B (Cron / Windows Task Scheduler)**: Schedule `python main.py --run-once` daily at 09:00 AM.
