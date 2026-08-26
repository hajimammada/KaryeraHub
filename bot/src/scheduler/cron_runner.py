"""
Automated daemon scheduler for daily execution.
"""
import time
import schedule
from typing import Callable
from ..utils.logger import get_logger

logger = get_logger(__name__)

class JobBotScheduler:
    """Manages scheduled daily execution for the job bot."""

    def __init__(self, schedule_time: str, job_task: Callable[[], None]):
        self.schedule_time = schedule_time
        self.job_task = job_task
        self.running = False

    def setup(self, run_immediately: bool = False):
        """Sets up the daily schedule."""
        logger.info(f"⏰ Setting up daily job schedule at {self.schedule_time} (local time)...")
        schedule.every().day.at(self.schedule_time).do(self._run_job_wrapper)
        
        if run_immediately:
            logger.info("Executing immediate initial run before starting daemon loop...")
            self._run_job_wrapper()

    def _run_job_wrapper(self):
        try:
            logger.info("⚡ Triggering scheduled daily job discovery cycle...")
            self.job_task()
        except Exception as e:
            logger.error(f"Error during scheduled execution: {e}", exc_info=True)

    def start(self):
        """Starts the blocking daemon loop."""
        self.running = True
        logger.info(f"🚀 Bot daemon is running. Waiting for next scheduled trigger at {self.schedule_time}...")
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Scheduler stopped by user.")
            self.running = False

    def stop(self):
        self.running = False
