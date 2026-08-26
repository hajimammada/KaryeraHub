"""
Data models for database records and job representations.
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import hashlib
import re

@dataclass
class JobRecord:
    jobname: str
    company: str
    link: str
    source: str = "web"
    id: Optional[int] = None
    job_hash: Optional[str] = None
    first_seen_at: Optional[str] = None
    posted_at: Optional[str] = None
    telegram_message_id: Optional[int] = None

    def __post_init__(self):
        if not self.job_hash:
            self.job_hash = self.generate_hash(self.link, self.jobname, self.company)

    @staticmethod
    def normalize_str(s: str) -> str:
        if not s:
            return ""
        # Remove extra whitespace and lowercase
        return " ".join(s.lower().strip().split())

    @staticmethod
    def normalize_url(url: str) -> str:
        if not url:
            return ""
        # Remove trailing slash and tracking query params (utm_*, ref, etc.)
        url = url.strip()
        url = re.sub(r'(\?|&)(utm_[^&]+|ref=[^&]+|source=[^&]+)', '', url)
        url = url.rstrip('?')
        return url.rstrip('/')

    @classmethod
    def generate_hash(cls, link: str, jobname: str, company: str) -> str:
        """
        Generates a robust SHA256 hash using normalized URL, job title, and company.
        """
        norm_url = cls.normalize_url(link)
        norm_title = cls.normalize_str(jobname)
        norm_company = cls.normalize_str(company)
        
        # Primary identity is the clean URL; if URL is generic, combined with title + company
        raw_key = f"{norm_url}|{norm_title}|{norm_company}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)
