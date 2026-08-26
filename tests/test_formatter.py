"""
Unit tests for TelegramJobFormatter and batch chunking logic.
"""
import pytest
from src.scraper.base import JobItem
from src.telegram.formatter import TelegramJobFormatter

def test_chunk_jobs_limit_15():
    # Generate 35 sample jobs
    sample_jobs = [
        JobItem(jobname=f"Job {i}", company=f"Company {i}", link=f"https://boss.az/vacancies/{i}")
        for i in range(1, 36)
    ]

    # Chunk with default max 15
    chunks = TelegramJobFormatter.chunk_jobs(sample_jobs, max_per_batch=15)
    
    assert len(chunks) == 3
    assert len(chunks[0]) == 15
    assert len(chunks[1]) == 15
    assert len(chunks[2]) == 5


def test_chunk_jobs_custom_cap():
    sample_jobs = [
        JobItem(jobname=f"Job {i}", company=f"Company {i}", link=f"https://boss.az/vacancies/{i}")
        for i in range(1, 21)
    ]

    chunks = TelegramJobFormatter.chunk_jobs(sample_jobs, max_per_batch=15)
    assert len(chunks) == 2
    assert len(chunks[0]) == 15
    assert len(chunks[1]) == 5


def test_format_batch_message_style():
    batch = [
        JobItem(
            jobname="Senior <C++> Developer",
            company="Global & Local Tech",
            link="https://boss.az/vacancies/cpp"
        ),
        JobItem(
            jobname="Maliyyə Mütəxəssisi",
            company="ABB Bank",
            link="https://jobsearch.az/vacancies/maliyye"
        )
    ]

    msg = TelegramJobFormatter.format_batch_message(batch, batch_index=1, total_batches=1, start_id=1)

    # Check HTML sanitization (< and & escaped)
    assert "&lt;C++&gt;" in msg
    assert "Global &amp; Local Tech" in msg

    # Check style: id, jobname, company, link
    assert "1. Senior &lt;C++&gt; Developer" in msg
    assert "Şirkət:</b> Global &amp; Local Tech" in msg
    assert "https://boss.az/vacancies/cpp" in msg

    assert "2. Maliyyə Mütəxəssisi" in msg
    assert "Şirkət:</b> ABB Bank" in msg


def test_format_all_batches_continuous_ids():
    sample_jobs = [
        JobItem(jobname=f"Developer {i}", company=f"Corp {i}", link=f"https://portal.az/job/{i}")
        for i in range(1, 16)
    ]

    messages = TelegramJobFormatter.format_all_batches(sample_jobs, max_per_batch=10)
    assert len(messages) == 2

    # Batch 1 should have 1. to 10.
    assert "<b>1. Developer 1</b>" in messages[0]
    assert "<b>10. Developer 10</b>" in messages[0]
    assert "(1/2)" in messages[0]

    # Batch 2 should start at 11. and end at 15.
    assert "<b>11. Developer 11</b>" in messages[1]
    assert "<b>15. Developer 15</b>" in messages[1]
    assert "(2/2)" in messages[1]
