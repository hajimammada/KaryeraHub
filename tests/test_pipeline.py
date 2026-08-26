"""
Integration test for the full discovery and dispatch pipeline.
"""
from unittest.mock import MagicMock
from pathlib import Path
from src.database.repository import JobRepository
from src.scraper.base import JobItem
from src.scraper.pipeline import JobDiscoveryPipeline
from src.telegram.dispatcher import TelegramDispatcher

def test_full_pipeline_flow(tmp_path: Path):
    # 1. Setup mock repo in tmp directory
    db_file = tmp_path / "integration_test.db"
    repo = JobRepository(db_file)

    # 2. Setup mock pipeline returning 12 discovered jobs
    mock_extractor = MagicMock()
    mock_collector = MagicMock()
    
    mock_collector.fetch_all_sources.return_value = [
        {"portal": MagicMock(name="boss.az", base_url="https://boss.az"), "content": "<html>mock</html>"}
    ]
    
    mock_extractor.extract_jobs_from_content.return_value = [
        JobItem(jobname=f"Job {i}", company=f"Company {i}", link=f"https://boss.az/vacancies/{i}", source="boss.az")
        for i in range(1, 13)
    ]

    pipeline = JobDiscoveryPipeline(gemini_extractor=mock_extractor, web_collector=mock_collector)
    jobs = pipeline.discover_latest_jobs()
    assert len(jobs) == 12

    # 3. Setup mock Telegram client
    mock_telegram_client = MagicMock()
    mock_telegram_client.send_message.return_value = {"message_id": 999}

    dispatcher = TelegramDispatcher(
        telegram_client=mock_telegram_client,
        repository=repo,
        channel_id="@test_channel",
        max_jobs_per_message=10
    )

    # 4. Dispatch (should create 2 batches: 10 + 2)
    result = dispatcher.dispatch_jobs(jobs, dry_run=False)
    assert result["status"] == "success"
    assert result["posted_count"] == 12
    assert result["batches"] == 2
    assert mock_telegram_client.send_message.call_count == 2

    # 5. Check database state
    stats = repo.get_stats()
    assert stats["total_jobs_tracked"] == 12
    assert stats["jobs_posted_last_7_days"] == 12

    # 6. Re-running with same jobs should be detected as duplicates
    new_jobs = []
    for j in jobs:
        if not repo.is_job_posted_recently(j.link, j.jobname, j.company, days=7):
            new_jobs.append(j)
    
    assert len(new_jobs) == 0, "All 12 jobs should now be marked as duplicate within 7 days!"
