import json
import os
import time
from pathlib import Path

from athena.interfaces.alexandria_auto_runner import AlexandriaAutoRunner


def test_process_queue_marks_task_completed_and_writes_run_file(tmp_path: Path):
    root = tmp_path / "alexandria"
    runner = AlexandriaAutoRunner(root)

    queue_path = runner.pipeline.ingest_queue_path
    queue = {
        "version": 1,
        "tasks": [
            {
                "task_id": "ALX-TEST-1",
                "source_url": "https://github.com/example/repo",
                "source_type": "repo",
                "decision": "immediate",
                "phase": "digest",
                "status": "queued",
                "scheduled_for": "2026-01-01T00:00:00",
                "created_at": "2026-01-01T00:00:00",
                "plan": {},
            }
        ],
    }
    queue_path.write_text(json.dumps(queue, indent=2) + "\n")

    def _fake_execute(_objective: str, _deadline: str):
        return {
            "mission_id": "ATHENA-TEST-1",
            "routed_execution": {"remote_success": 0},
            "ingest": [],
            "validation": [],
            "phase6_gate": {"status": "pass"},
            "completion_status": "ready",
        }

    summary = runner._process_queue(queue_path, "ingest", 1, _fake_execute)
    assert summary["processed"] == 1

    updated = json.loads(queue_path.read_text())
    task = updated["tasks"][0]
    assert task["status"] == "completed"
    assert task["mission_id"] == "ATHENA-TEST-1"

    run_file = root / "runs" / "run_ALX-TEST-1.json"
    assert run_file.exists()

    book_json = root / "analysis" / "books" / "example__repo" / "book.json"
    assert book_json.exists()
    payload = json.loads(book_json.read_text())
    assert payload["analysis_status"] == "reused_context"


def test_apply_retention_moves_old_run_artifacts(tmp_path: Path):
    root = tmp_path / "alexandria"
    runner = AlexandriaAutoRunner(root)

    old_file = runner.pipeline.runs_dir / "old_run.json"
    old_file.write_text("{}\n")

    old_time = time.time() - (20 * 24 * 60 * 60)
    os.utime(old_file, (old_time, old_time))

    result = runner.apply_retention(days=14)
    assert result["moved_to_archive"] == 1
    assert not old_file.exists()
    assert (runner.archive_dir / "old_run.json").exists()


def test_pipeline_status_report_contains_backlog_counts(tmp_path: Path):
    root = tmp_path / "alexandria"
    runner = AlexandriaAutoRunner(root)

    runner.pipeline.quick_access_path.write_text(
        json.dumps(
            {
                "version": 1,
                "entries": [
                    {
                        "source_url": "https://github.com/example/repo",
                        "source_type": "repo",
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )
    runner.pipeline.ingest_queue_path.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": [
                    {
                        "task_id": "ALX-TEST-INGEST",
                        "source_url": "https://github.com/example/repo",
                        "status": "queued",
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )
    runner.pipeline.digest_queue_path.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": [
                    {
                        "task_id": "ALX-TEST-DIGEST",
                        "source_url": "https://github.com/example/repo",
                        "status": "scheduled",
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )

    status = runner.pipeline_status()
    assert status["ingest"]["backlog"] == 1
    assert status["digest"]["backlog"] == 1
    assert status["scout"]["repo_entries"] == 1

    runner._write_pipeline_status_report(status)
    assert (runner.pipeline.reports_dir / "pipeline_status.json").exists()
    md = (runner.pipeline.reports_dir / "pipeline_status.md").read_text()
    assert "ingest_backlog: 1" in md


def test_run_pods_processes_multiple_batches(tmp_path: Path):
    root = tmp_path / "alexandria"
    runner = AlexandriaAutoRunner(root)

    queue = {
        "version": 1,
        "tasks": [
            {
                "task_id": "ALX-POD-1",
                "source_url": "https://github.com/example/repo1",
                "source_type": "repo",
                "decision": "deferred",
                "phase": "digest",
                "status": "queued",
                "scheduled_for": "2026-01-01T00:00:00",
                "created_at": "2026-01-01T00:00:00",
                "plan": {},
            },
            {
                "task_id": "ALX-POD-2",
                "source_url": "https://github.com/example/repo2",
                "source_type": "repo",
                "decision": "deferred",
                "phase": "digest",
                "status": "queued",
                "scheduled_for": "2026-01-01T00:00:00",
                "created_at": "2026-01-01T00:00:00",
                "plan": {},
            },
            {
                "task_id": "ALX-POD-3",
                "source_url": "https://github.com/example/repo3",
                "source_type": "repo",
                "decision": "deferred",
                "phase": "digest",
                "status": "queued",
                "scheduled_for": "2026-01-01T00:00:00",
                "created_at": "2026-01-01T00:00:00",
                "plan": {},
            },
        ],
    }
    runner.pipeline.digest_queue_path.write_text(json.dumps(queue, indent=2) + "\n")

    class _FakeCEO:
        def execute(self, _objective: str, _deadline: str):
            return {
                "mission_id": "ATHENA-POD",
                "routed_execution": {},
                "ingest": [],
                "validation": [],
                "phase6_gate": {"status": "pass"},
                "completion_status": "ready",
            }

    from athena.interfaces import alexandria_auto_runner as runner_mod

    original = runner_mod.CEOCommand
    runner_mod.CEOCommand = _FakeCEO  # type: ignore[assignment]
    try:
        result = runner.run_pods(
            queue_mode="digest", pod_size=2, max_pods=2, pause_seconds=0
        )
    finally:
        runner_mod.CEOCommand = original  # type: ignore[assignment]

    assert result["pods_run"] == 2
    assert result["total_processed"] == 3


def test_repo_book_updates_with_agent_card_from_digest_result(tmp_path: Path):
    root = tmp_path / "alexandria"
    runner = AlexandriaAutoRunner(root)

    task = {
        "task_id": "ALX-TEST-2",
        "source_url": "https://github.com/example/repo",
        "status": "completed",
        "mission_id": "ATHENA-TEST-2",
        "completion_status": "ready",
        "processed_at": "2026-02-17T22:20:00",
    }
    result = {
        "mission_id": "ATHENA-TEST-2",
        "routed_execution": {"remote_success": 1},
        "phase6_gate": {"status": "pass"},
        "ingest": [
            {
                "agent_card": {
                    "name": "REPO",
                    "capabilities": ["multi_agent"],
                    "dependencies": ["package.json"],
                    "sampled_files": ["src/main.ts"],
                    "signal_tags": ["react"],
                    "language": "TypeScript",
                }
            }
        ],
        "validation": [],
        "completion_status": "ready",
    }

    runner._write_run_artifact(task, result)

    book_path = root / "analysis" / "books" / "example__repo" / "book.json"
    payload = json.loads(book_path.read_text())
    assert payload["analysis_status"] == "digested"
    assert payload["agent_card"]["name"] == "REPO"
