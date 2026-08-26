# karyerahub - PowerShell Launcher
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🇦🇿 karyerahub (Karyera Hub Telegram Bot)" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

$mode = Read-Host "Choose mode: 
[1] Dry Run (Scrape, AI Parse, Preview - no posting)
[2] Run Once (Scrape, Deduplicate, Post to Telegram)
[3] Daemon (Run continuously with daily schedule)
[4] Test Telegram Bot & Channel
[5] View Database Statistics
[6] Run Test Suite (pytest)
[7] Clear / Reset Database
Enter option (1-7)"

switch ($mode) {
    "1" { python main.py --dry-run }
    "2" { python main.py --run-once }
    "3" { python main.py --daemon }
    "4" { python main.py --test-bot }
    "5" { python main.py --stats }
    "6" { pytest tests/ -v }
    "7" { python main.py --reset-db }
    default { python main.py --dry-run }
}
