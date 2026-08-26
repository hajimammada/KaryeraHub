"""
Telegram Dispatcher.
Coordinates batch formatting, channel delivery, and database updates.
"""
import time
from typing import List, Dict, Any, Optional
from ..scraper.base import JobItem
from ..database.repository import JobRepository
from .client import TelegramClient
from .formatter import TelegramJobFormatter
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TelegramDispatcher:
    """Orchestrates job batching, posting to Telegram channel, and registering posted status in DB."""

    def __init__(
        self,
        telegram_client: TelegramClient,
        repository: JobRepository,
        channel_id: str,
        max_jobs_per_message: int = 15
    ):
        self.client = telegram_client
        self.repository = repository
        self.channel_id = channel_id
        self.max_jobs_per_message = max(1, min(max_jobs_per_message, 25))

    def dispatch_jobs(
        self,
        jobs: List[JobItem],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Dispatches newly found jobs to the Telegram channel in chunks of <= 10.
        If dry_run is True, simulates the process and logs message previews without sending.
        """
        if not jobs:
            logger.info("No jobs to dispatch.")
            return {"status": "empty", "posted_count": 0, "batches": 0}

        chunks = TelegramJobFormatter.chunk_jobs(jobs, max_per_batch=self.max_jobs_per_message)
        total_batches = len(chunks)
        logger.info(f"Preparing to dispatch {len(jobs)} jobs across {total_batches} batch(es) (Max {self.max_jobs_per_message} per message)...")

        posted_count = 0
        current_id = 1

        for idx, chunk in enumerate(chunks, 1):
            msg_text = TelegramJobFormatter.format_batch_message(
                batch_jobs=chunk,
                batch_index=idx,
                total_batches=total_batches,
                start_id=current_id
            )

            if dry_run:
                logger.info(f"--- [DRY RUN PREVIEW: BATCH {idx}/{total_batches}] ---")
                print("\n" + "="*50)
                print(msg_text)
                print("="*50 + "\n")
                posted_count += len(chunk)
                current_id += len(chunk)
                continue

            try:
                logger.info(f"Sending batch {idx}/{total_batches} ({len(chunk)} jobs) to {self.channel_id}...")
                resp = self.client.send_message(
                    chat_id=self.channel_id,
                    text=msg_text,
                    parse_mode="HTML"
                )
                msg_id = resp.get("message_id")

                # Record each job as posted in database
                for job in chunk:
                    self.repository.save_job(
                        jobname=job.jobname,
                        company=job.company,
                        link=job.link,
                        source=job.source,
                        telegram_message_id=msg_id
                    )
                
                posted_count += len(chunk)
                current_id += len(chunk)

                # Delay between batches to respect Telegram broadcast rate limits
                if idx < total_batches:
                    time.sleep(2)

            except Exception as e:
                logger.error(f"Failed to post batch {idx}/{total_batches} to Telegram: {e}")
                break

        logger.info(f"Dispatch complete: {posted_count}/{len(jobs)} jobs handled.")
        return {
            "status": "success" if not dry_run else "dry_run_success",
            "posted_count": posted_count,
            "batches": total_batches
        }
