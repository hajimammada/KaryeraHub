@echo off
title isradaribot - Is Radari Telegram Bot
echo ==========================================
echo  isradaribot - Is Radari Telegram Bot
echo ==========================================
echo.
echo Choose execution mode:
echo [1] Dry Run (Scrape, AI Parse, Preview - no posting)
echo [2] Run Once (Scrape, Deduplicate, Post to Telegram)
echo [3] Daemon (Run continuously with daily schedule)
echo [4] Test Telegram Bot and Channel Connection
echo [5] View Database Statistics
echo [6] Run Unit Test Suite (pytest)
echo [7] Clear / Reset Database
echo.
set /p opt="Enter choice (1-7): "

if "%opt%"=="1" python main.py --dry-run
if "%opt%"=="2" python main.py --run-once
if "%opt%"=="3" python main.py --daemon
if "%opt%"=="4" python main.py --test-bot
if "%opt%"=="5" python main.py --stats
if "%opt%"=="6" pytest tests/ -v
if "%opt%"=="7" python main.py --reset-db

pause
