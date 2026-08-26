"""
Database package for job history tracking and deduplication.
"""
from .models import JobRecord
from .repository import JobRepository

__all__ = ["JobRecord", "JobRepository"]
