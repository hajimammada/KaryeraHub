"""
Unit tests for JobRepository and 7-day deduplication logic.
"""
import sqlite3
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.database.models import JobRecord
from src.database.repository import JobRepository

@pytest.fixture
def temp_repo(tmp_path: Path):
    db_file = tmp_path / "test_jobs.db"
    repo = JobRepository(db_file)
    return repo


def test_save_and_retrieve_job(temp_repo: JobRepository):
    job = temp_repo.save_job(
        jobname="Python Backend Developer",
        company="PASHA Bank",
        link="https://boss.az/vacancies/123-python",
        source="boss.az"
    )
    assert job.id is not None
    assert job.jobname == "Python Backend Developer"
    assert job.company == "PASHA Bank"

    stats = temp_repo.get_stats()
    assert stats["total_jobs_tracked"] == 1
    assert stats["jobs_posted_last_7_days"] == 1
    assert stats["sources_breakdown"].get("boss.az") == 1


def test_deduplication_within_7_days(temp_repo: JobRepository):
    # Save a job today
    temp_repo.save_job(
        jobname="Senior Data Engineer",
        company="SOCAR",
        link="https://jobsearch.az/vacancies/456",
        source="jobsearch.az"
    )

    # Check immediate duplicate detection
    is_dupe = temp_repo.is_job_posted_recently(
        link="https://jobsearch.az/vacancies/456",
        jobname="Senior Data Engineer",
        company="SOCAR",
        days=7
    )
    assert is_dupe is True

    # Check with slightly different URL query parameters (e.g. tracking tokens)
    is_dupe_with_utm = temp_repo.is_job_posted_recently(
        link="https://jobsearch.az/vacancies/456?utm_source=telegram",
        jobname="Senior Data Engineer",
        company="SOCAR",
        days=7
    )
    assert is_dupe_with_utm is True


def test_deduplication_older_than_7_days(temp_repo: JobRepository):
    # Save a job with posted_at 8 days ago
    old_date = (datetime.now(timezone.utc) - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
    
    with temp_repo._get_connection() as conn:
        cursor = conn.cursor()
        job_hash = JobRecord.generate_hash(
            "https://boss.az/vacancies/old-job",
            "Junior Analyst",
            "Azercell"
        )
        cursor.execute("""
            INSERT INTO posted_jobs (job_hash, jobname, company, link, source, first_seen_at, posted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (job_hash, "Junior Analyst", "Azercell", "https://boss.az/vacancies/old-job", "boss.az", old_date, old_date))
        conn.commit()

    # Now check if it's considered recently posted (7 days window)
    is_dupe = temp_repo.is_job_posted_recently(
        link="https://boss.az/vacancies/old-job",
        jobname="Junior Analyst",
        company="Azercell",
        days=7
    )
    # Should be False because 8 days > 7 days window
    assert is_dupe is False


def test_filter_new_jobs(temp_repo: JobRepository):
    # Save 1 existing job
    temp_repo.save_job(
        jobname="DevOps Engineer",
        company="Kapital Bank",
        link="https://hellojob.az/vakansiyalar/devops",
        source="hellojob.az"
    )

    incoming_batch = [
        {"jobname": "DevOps Engineer", "company": "Kapital Bank", "link": "https://hellojob.az/vakansiyalar/devops"}, # dupe
        {"jobname": "Flutter Developer", "company": "Tech Group", "link": "https://boss.az/vacancies/flutter"},       # new
        {"jobname": "Product Manager", "company": "Bakcell", "link": "https://jobsearch.az/vacancies/pm"},            # new
        {"jobname": "Flutter Developer", "company": "Tech Group", "link": "https://boss.az/vacancies/flutter"},       # batch dupe
    ]

    filtered = temp_repo.filter_new_jobs(incoming_batch, days=7)
    assert len(filtered) == 2
    assert filtered[0]["jobname"] == "Flutter Developer"
    assert filtered[1]["jobname"] == "Product Manager"
