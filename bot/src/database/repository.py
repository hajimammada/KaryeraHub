"""
SQLite repository for job persistence and 7-day deduplication.
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any
from .models import JobRecord
from ..utils.logger import get_logger

logger = get_logger(__name__)

class JobRepository:
    """Manages SQLite storage, querying, and 7-day deduplication logic."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes database tables and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posted_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_hash TEXT UNIQUE NOT NULL,
                    jobname TEXT NOT NULL,
                    company TEXT NOT NULL,
                    link TEXT NOT NULL,
                    source TEXT DEFAULT 'web',
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    telegram_message_id INTEGER
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_hash ON posted_jobs(job_hash);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posted_at ON posted_jobs(posted_at);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_title_company ON posted_jobs(jobname, company);
            """)
            conn.commit()

    def is_job_posted_recently(
        self,
        link: str,
        jobname: str,
        company: str,
        days: int = 7
    ) -> bool:
        """
        Checks if a job was already posted in the last N days (7 days by default).
        Checks both URL hash and normalized (jobname, company) pair.
        """
        job_hash = JobRecord.generate_hash(link, jobname, company)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Exact hash check within cutoff window
            cursor.execute("""
                SELECT id FROM posted_jobs
                WHERE job_hash = ? AND posted_at >= ?
                LIMIT 1
            """, (job_hash, cutoff_date))
            if cursor.fetchone() is not None:
                return True

            # 2. Normalized title + company similarity check within cutoff window
            norm_title = JobRecord.normalize_str(jobname)
            norm_company = JobRecord.normalize_str(company)
            
            cursor.execute("""
                SELECT jobname, company FROM posted_jobs
                WHERE posted_at >= ?
            """, (cutoff_date,))
            
            for row in cursor.fetchall():
                if (JobRecord.normalize_str(row["jobname"]) == norm_title and 
                    JobRecord.normalize_str(row["company"]) == norm_company):
                    return True

        return False

    def save_job(
        self,
        jobname: str,
        company: str,
        link: str,
        source: str = "web",
        telegram_message_id: Optional[int] = None
    ) -> JobRecord:
        """Saves or updates a posted job."""
        record = JobRecord(
            jobname=jobname,
            company=company,
            link=link,
            source=source,
            telegram_message_id=telegram_message_id
        )
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        record.posted_at = now_str
        record.first_seen_at = now_str

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posted_jobs (job_hash, jobname, company, link, source, first_seen_at, posted_at, telegram_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_hash) DO UPDATE SET
                    posted_at = excluded.posted_at,
                    telegram_message_id = COALESCE(excluded.telegram_message_id, posted_jobs.telegram_message_id)
            """, (
                record.job_hash,
                record.jobname,
                record.company,
                record.link,
                record.source,
                record.first_seen_at,
                record.posted_at,
                record.telegram_message_id
            ))
            record.id = cursor.lastrowid
            conn.commit()

        return record

    def filter_new_jobs(self, jobs: List[Dict[str, Any]], days: int = 7) -> List[Dict[str, Any]]:
        """
        Takes a list of raw job dicts and filters out any job seen in the last N days.
        Returns only genuinely new jobs.
        """
        new_jobs = []
        seen_in_batch = set()

        for j in jobs:
            link = j.get("link", "")
            jobname = j.get("jobname", "")
            company = j.get("company", "")

            if not link or not jobname:
                continue

            # Batch deduplication key
            batch_key = JobRecord.generate_hash(link, jobname, company)
            if batch_key in seen_in_batch:
                continue

            if not self.is_job_posted_recently(link, jobname, company, days=days):
                new_jobs.append(j)
                seen_in_batch.add(batch_key)
            else:
                logger.debug(f"Filtered out duplicate job within {days} days: {jobname} at {company}")

        return new_jobs

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics on stored jobs and recent postings."""
        cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as cnt FROM posted_jobs")
            total = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM posted_jobs WHERE posted_at >= ?", (cutoff_7d,))
            last_7d = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM posted_jobs WHERE posted_at >= ?", (cutoff_24h,))
            last_24h = cursor.fetchone()["cnt"]

            cursor.execute("""
                SELECT source, COUNT(*) as cnt
                FROM posted_jobs
                GROUP BY source
            """)
            sources = {row["source"]: row["cnt"] for row in cursor.fetchall()}

        return {
            "total_jobs_tracked": total,
            "jobs_posted_last_7_days": last_7d,
            "jobs_posted_last_24_hours": last_24h,
            "sources_breakdown": sources
        }

    def clear_all_records(self):
        """Clears all stored records from the database table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM posted_jobs")
            conn.commit()
        logger.info("🗑️ Cleared all job records from SQLite database.")
