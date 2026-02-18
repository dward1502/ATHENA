import json
from pathlib import Path

from athena.interfaces.alexandria_pipeline import AlexandriaPipeline


def test_scout_and_plan_deferred_updates_docs_and_digest_queue(
    monkeypatch, tmp_path: Path
):
    root = tmp_path / "alexandria"
    pipeline = AlexandriaPipeline(root)

    monkeypatch.setattr(
        pipeline,
        "discover_docs_links",
        lambda url: [url + "#readme", url + "/wiki"],
    )

    result = pipeline.scout_and_plan(
        urls=["https://github.com/example/repo"],
        mission_id="ATHENA-TEST-ALX-1",
        decision="deferred",
    )

    assert result["entries"] == 1
    assert result["repos"] == 1
    assert result["queue"]["digest_added"] == 1

    docs = pipeline.documentation_path.read_text()
    assert "### example/repo" in docs
    assert "https://github.com/example/repo#readme" in docs

    quick = pipeline.quick_access_path.read_text()
    assert "ATHENA-TEST-ALX-1" in quick

    digest = pipeline.digest_queue_path.read_text()
    assert '"source_url": "https://github.com/example/repo"' in digest
    assert '"status": "scheduled"' in digest

    analysis_index = pipeline.analysis_index_path.read_text()
    assert '"repo_slug": "example__repo"' in analysis_index
    book_json = (
        root / "analysis" / "books" / "example__repo" / "book.json"
    ).read_text()
    assert '"source_url": "https://github.com/example/repo"' in book_json

    playbook = (root / "reports" / "athena_library_playbook.json").read_text()
    assert '"workstreams"' in playbook


def test_scout_and_plan_immediate_queues_ingest(monkeypatch, tmp_path: Path):
    root = tmp_path / "alexandria"
    pipeline = AlexandriaPipeline(root)

    monkeypatch.setattr(
        pipeline,
        "discover_docs_links",
        lambda url: [url + "#readme"],
    )

    result = pipeline.scout_and_plan(
        urls=["https://github.com/example/repo2"],
        mission_id="ATHENA-TEST-ALX-2",
        decision="immediate",
    )

    assert result["queue"]["ingest_added"] == 1
    ingest = pipeline.ingest_queue_path.read_text()
    assert '"source_url": "https://github.com/example/repo2"' in ingest
    assert '"status": "queued"' in ingest

    book_md = (root / "analysis" / "books" / "example__repo2" / "book.md").read_text()
    assert "# Repo Book: example__repo2" in book_md

    playbook = (root / "reports" / "athena_library_playbook.json").read_text()
    assert '"workstreams"' in playbook


def test_rebuild_repo_books_preserves_deep_analysis_fields(monkeypatch, tmp_path: Path):
    root = tmp_path / "alexandria"
    pipeline = AlexandriaPipeline(root)

    monkeypatch.setattr(
        pipeline,
        "discover_docs_links",
        lambda url: [url + "#readme"],
    )

    pipeline.scout_and_plan(
        urls=["https://github.com/example/repo"],
        mission_id="ATHENA-TEST-ALX-3",
        decision="deferred",
    )

    book_path = root / "analysis" / "books" / "example__repo" / "book.json"
    payload = json.loads(book_path.read_text())
    payload["analysis_status"] = "digested"
    payload["last_digest_mission_id"] = "ATHENA-DIGEST-1"
    payload["agent_card"] = {
        "name": "REPO",
        "sampled_files": ["src/main.ts"],
        "signal_tags": ["openai"],
    }
    book_path.write_text(json.dumps(payload, indent=2) + "\n")

    pipeline.rebuild_repo_books()

    refreshed = json.loads(book_path.read_text())
    assert refreshed["analysis_status"] == "digested"
    assert refreshed["last_digest_mission_id"] == "ATHENA-DIGEST-1"
    assert refreshed["agent_card"]["name"] == "REPO"

    index = json.loads(pipeline.analysis_index_path.read_text())
    row = next(
        item
        for item in index.get("repos", [])
        if item.get("repo_slug") == "example__repo"
    )
    assert row["status"] == "digested"
    assert row["mission_id"] == "ATHENA-DIGEST-1"


def test_rebuild_library_artifacts_writes_playbook(tmp_path: Path):
    root = tmp_path / "alexandria"
    pipeline = AlexandriaPipeline(root)

    pipeline.quick_access_path.write_text(
        json.dumps(
            {
                "version": 1,
                "entries": [
                    {
                        "source_url": "https://github.com/microsoft/autogen",
                        "source_type": "repo",
                        "mission_id": "ATHENA-X",
                        "status": "scouted",
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )

    out = pipeline.rebuild_library_artifacts()
    assert out["playbook"]["workstreams"] >= 1

    payload = json.loads(pipeline.library_playbook_path.read_text())
    names = [w.get("name") for w in payload.get("workstreams", [])]
    assert "W1_orchestration_intelligence" in names
