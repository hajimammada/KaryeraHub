"""
Azerbaijan Job Telegram Bot - Unified CLI Entrypoint.
Orchestrates AI job extraction, 7-day deduplication, and chunked Telegram channel posting.
"""
import sys
import argparse
from pathlib import Path
from config.settings import settings
from src.utils.logger import setup_logger
from src.database.repository import JobRepository
from src.scraper.gemini_extractor import GeminiExtractor
from src.scraper.web_collector import WebCollector
from src.scraper.pipeline import JobDiscoveryPipeline
from src.scraper.balancer import SourceDiversityBalancer
from src.telegram.client import TelegramClient
from src.telegram.dispatcher import TelegramDispatcher
from src.scheduler.cron_runner import JobBotScheduler

# Initialize logger
logger = setup_logger(
    name="az_job_bot",
    log_dir=settings.logs_dir,
    level=settings.log_level
)


class AzerbaijanJobBotApp:
    """Core application controller."""

    def __init__(self):
        self.repository = JobRepository(settings.db_full_path)
        self.extractor = GeminiExtractor(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model
        )
        self.collector = WebCollector()
        self.pipeline = JobDiscoveryPipeline(
            gemini_extractor=self.extractor,
            web_collector=self.collector
        )
        self.telegram_client = TelegramClient(
            bot_token=settings.telegram_bot_token
        )
        self.dispatcher = TelegramDispatcher(
            telegram_client=self.telegram_client,
            repository=self.repository,
            channel_id=settings.telegram_channel_id,
            max_jobs_per_message=settings.max_jobs_per_message
        )

    def run_cycle(self, dry_run: bool = False):
        """Executes a single job discovery, deduplication, and dispatch cycle."""
        logger.info("=" * 60)
        logger.info(f"🔄 Starting execution cycle (Dry Run: {dry_run})")
        logger.info("=" * 60)

        # 1. Discover all jobs from enabled portals via Gemini AI
        discovered_jobs = self.pipeline.discover_latest_jobs()
        if not discovered_jobs:
            logger.info("No job vacancies were found in this cycle.")
            return

        logger.info(f"Scraped & extracted {len(discovered_jobs)} raw vacancies from web.")

        # 2. Apply 7-day deduplication filter
        new_jobs = []
        for job in discovered_jobs:
            if not self.repository.is_job_posted_recently(
                link=job.link,
                jobname=job.jobname,
                company=job.company,
                days=settings.deduplication_days
            ):
                new_jobs.append(job)

        filtered_count = len(discovered_jobs) - len(new_jobs)
        logger.info(
            f"🔍 Deduplication Check: {len(new_jobs)} NEW vacancies found "
            f"({filtered_count} duplicates skipped from the last {settings.deduplication_days} days)."
        )

        # 3. Apply Multi-Source Proportional Diversity & Daily Cap (Max 15 jobs)
        final_jobs = SourceDiversityBalancer.balance_and_cap(
            jobs=new_jobs,
            max_total=settings.daily_max_jobs
        )

        logger.info(
            f"🎯 Multi-Source Selection: Selected {len(final_jobs)} jobs (Daily Cap: {settings.daily_max_jobs}) "
            f"balanced proportionally across sources."
        )

        # 4. Dispatch selected jobs (chunked into messages <= 10 jobs)
        result = self.dispatcher.dispatch_jobs(final_jobs, dry_run=dry_run)
        logger.info(f"✅ Execution cycle completed successfully: {result}")

    def test_telegram_bot(self):
        """Tests Telegram connection, Bot identity, and optionally sends a verification message."""
        logger.info("Testing Telegram Bot connection...")
        try:
            bot_info = self.telegram_client.get_me()
            logger.info(f"✅ Bot connected successfully!")
            logger.info(f"   - Bot ID: {bot_info.get('id')}")
            logger.info(f"   - Bot Name: {bot_info.get('first_name')}")
            logger.info(f"   - Username: @{bot_info.get('username')}")
            logger.info(f"   - Configured Channel: {settings.telegram_channel_id}")
            
            if settings.telegram_channel_id and settings.telegram_channel_id != "@your_channel_username":
                logger.info(f"Sending test ping message to {settings.telegram_channel_id}...")
                test_msg = "🤖 <b>Azerbaijan Job Bot - Test Message</b>\n\nBot is active and ready to publish daily job listings!"
                self.telegram_client.send_message(settings.telegram_channel_id, test_msg)
                logger.info(f"✅ Test message posted to channel successfully!")
            else:
                logger.info("ℹ️ To test posting to your channel, update TELEGRAM_CHANNEL_ID in your .env file.")
        except Exception as e:
            logger.error(f"❌ Telegram test failed: {e}")

    def print_stats(self):
        """Displays database metrics and posting history."""
        stats = self.repository.get_stats()
        print("\n" + "=" * 50)
        print("📊 AZERBAIJAN JOB BOT - DATABASE STATISTICS")
        print("=" * 50)
        print(f"📁 Database Location: {settings.db_full_path}")
        print(f"📦 Total Vacancies Tracked: {stats['total_jobs_tracked']}")
        print(f"📅 Posted in Last 7 Days:   {stats['jobs_posted_last_7_days']}")
        print(f"🕒 Posted in Last 24 Hours: {stats['jobs_posted_last_24_hours']}")
        print("\n🌐 Vacancies by Source Portal:")
        for src, count in stats.get("sources_breakdown", {}).items():
            print(f"   - {src:<15}: {count} jobs")
        print("=" * 50 + "\n")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Azerbaijan Job Telegram Bot - AI Powered Vacancy Aggregator"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run discovery and deduplication pipeline, printing formatted Telegram messages to terminal without sending or saving."
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Execute 1 discovery and posting cycle immediately and exit."
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in continuous background mode with daily scheduler."
    )
    parser.add_argument(
        "--test-bot",
        action="store_true",
        help="Verify Telegram bot token and channel connectivity."
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Display database deduplication statistics."
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Clear all stored job history from the SQLite database."
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    app = AzerbaijanJobBotApp()

    if args.reset_db:
        app.repository.clear_all_records()
        print("✅ Database cleared successfully! You can now start posting from the beginning.")
    elif args.stats:
        app.print_stats()
    elif args.test_bot:
        app.test_telegram_bot()
    elif args.dry_run:
        app.run_cycle(dry_run=True)
    elif args.daemon:
        scheduler = JobBotScheduler(
            schedule_time=settings.daily_schedule_time,
            job_task=lambda: app.run_cycle(dry_run=False)
        )
        scheduler.setup(run_immediately=True)
        scheduler.start()
    else:
        # Default to run-once if no flags specified or --run-once provided
        app.run_cycle(dry_run=False)


if __name__ == "__main__":
    main()
