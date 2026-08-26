# 🇦🇿 Karyera Hub (karyerahub)

Azərbaycanın ən son vakansiyaları, karyera imkanları və avtomatlaşdırılmış iş axtarış platforması.

[![Telegram Channel](https://img.shields.io/badge/Telegram-@karyerahub-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/karyerahub)

> 📢 **Rəsmi Telegram Kanalı**: [https://t.me/karyerahub](https://t.me/karyerahub) (`@karyerahub`)

---

## 🏗️ Repository Architecture & Components

```
karyerahub/
├── bot/                       # 🤖 Automated Telegram Job Aggregator Bot
│   ├── config/                # Environment & operational settings
│   ├── data/                  # SQLite 7-day deduplication storage (jobs.db)
│   ├── logs/                  # Application logs
│   ├── src/                   # Core bot engine (scrapers, AI extractor, telegram)
│   ├── tests/                 # 20 pytest unit & integration tests
│   ├── main.py                # Unified CLI entrypoint
│   ├── requirements.txt       # Bot dependencies
│   ├── run.bat                # Windows 1-click launcher
│   └── run.ps1                # PowerShell launcher
├── .github/workflows/         # ☁️ Twice-daily GitHub Actions cloud automation
├── .gitignore
└── README.md
```

---

## 🤖 `bot/` Component Overview

The **`bot/`** component is an intelligent job discovery engine that monitors top Azerbaijani portals (`linkedin`, `jobsearch.az`, `hellojob.az`, `ishelanlari.az`, `banker.az`, `boss.az`), uses **Google Gemini AI** for structured vacancy extraction, filters duplicates using a **7-day historical lookback** SQLite database, and publishes a balanced, date-ordered daily batch of **15 fresh vacancies** in **1 single clean message**.

### 🌟 Key Features:
- 🧠 **AI Extraction**: Uses `gemini-3.1-flash-lite` for high-speed vacancy parsing.
- 💼 **LinkedIn Azerbaijan Jobs**: Scrapes genuine local postings and cleans tracking parameters.
- 🛡️ **Spam Recruiter Filter**: Automatically drops spam mass-recruiters (Agoda, Turing, BairesDev, etc.).
- 📅 **Date Ordering**: Places the newest opportunities at the top.
- ⚖️ **Source Balancing**: Proportional multi-source allocation across all portals.
- ⏰ **Twice-Daily Schedule**: Runs at **10:00 AM & 19:00 PM Baku Time** in GitHub Actions.

### 🚀 Running the Bot Locally:
```powershell
cd bot
pip install -r requirements.txt

# Post single cycle
python main.py --run-once

# Or use 1-click launcher
.\run.ps1
```
