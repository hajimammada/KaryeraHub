"""
Telegram message formatting and batch chunking.
Ensures maximum 10 jobs per message block and formats in the requested style:
'id, jobname, company, link to job'
"""
import html
from datetime import datetime
from typing import List, Dict, Any, Union
from ..scraper.base import JobItem
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TelegramJobFormatter:
    """Formats job vacancies into Telegram-friendly HTML message batches."""

    @staticmethod
    def chunk_jobs(
        jobs: List[Union[JobItem, Dict[str, Any]]],
        max_per_batch: int = 15
    ) -> List[List[Union[JobItem, Dict[str, Any]]]]:
        """
        Splits a list of jobs into chunks of at most `max_per_batch` (default 15).
        """
        if max_per_batch < 1:
            max_per_batch = 1

        chunks = []
        for i in range(0, len(jobs), max_per_batch):
            chunks.append(jobs[i:i + max_per_batch])
        return chunks

    @classmethod
    def format_batch_message(
        cls,
        batch_jobs: List[Union[JobItem, Dict[str, Any]]],
        batch_index: int = 1,
        total_batches: int = 1,
        start_id: int = 1
    ) -> str:
        """
        Formats a single batch of up to 10 jobs into an attractive, clean Telegram message.
        Format style: id, jobname, company, link to job
        """
        now_str = datetime.now().strftime("%d.%m.%Y")
        
        # Header
        if total_batches > 1:
            header = f"🇦🇿 <b>Karyera Hub | Günün Yeni Vakansiyaları ({batch_index}/{total_batches})</b>\n📅 <i>{now_str}</i>\n"
        else:
            header = f"🇦🇿 <b>Karyera Hub | Günün Yeni Vakansiyaları</b>\n📅 <i>{now_str}</i>\n"

        lines = [header]

        for i, item in enumerate(batch_jobs):
            current_id = start_id + i
            if isinstance(item, JobItem):
                jobname = item.jobname
                company = item.company
                link = item.link
            else:
                jobname = item.get("jobname", "")
                company = item.get("company", "Qeyd edilməyib")
                link = item.get("link", "")

            # Sanitize HTML
            safe_jobname = html.escape(jobname)
            safe_company = html.escape(company)
            safe_link = html.escape(link)

            # Style: id, jobname, company, link
            job_block = (
                f"\n<b>{current_id}. {safe_jobname}</b>\n"
                f"🏢 <b>Şirkət:</b> {safe_company}\n"
                f"🔗 <b>Keçid:</b> <a href=\"{safe_link}\">{safe_link}</a>"
            )
            lines.append(job_block)

        lines.append("\n━━━━━━━━━━━━━━━━━━━━")
        lines.append("🔔 <i>Gündəlik ən son elanlar üçün kanala abunə olun:</i> @karyerahub")

        return "\n".join(lines)

    @classmethod
    def format_all_batches(
        cls,
        jobs: List[Union[JobItem, Dict[str, Any]]],
        max_per_batch: int = 10
    ) -> List[str]:
        """
        Chunks and formats all jobs into a list of ready-to-send Telegram message strings.
        """
        if not jobs:
            return []

        chunks = cls.chunk_jobs(jobs, max_per_batch=max_per_batch)
        messages = []
        current_id = 1

        for idx, chunk in enumerate(chunks, 1):
            msg = cls.format_batch_message(
                batch_jobs=chunk,
                batch_index=idx,
                total_batches=len(chunks),
                start_id=current_id
            )
            messages.append(msg)
            current_id += len(chunk)

        return messages
