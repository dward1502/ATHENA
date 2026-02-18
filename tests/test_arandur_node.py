from pathlib import Path

from athena.interfaces.arandur_node import ArandurCentralNode


def test_enqueue_and_complete_task(tmp_path: Path):
    node = ArandurCentralNode(tmp_path / "armoury")

    t1 = node.enqueue_task(
        title="Build A",
        objective="Build A",
        deadline="2026-02-20T10:00:00",
    )
    t2 = node.enqueue_task(
        title="Build B",
        objective="Build B",
        deadline="2026-02-20T11:00:00",
    )

    result = node.complete_task(t1["task_id"], completion_note="done")
    assert result["status"] == "completed"
    assert result["completed_task"]["task_id"] == t1["task_id"]
    assert result["next_task"]["task_id"] == t2["task_id"]


def test_auto_follow_on_task_when_empty(tmp_path: Path):
    node = ArandurCentralNode(tmp_path / "armoury")

    t1 = node.enqueue_task(
        title="Only Task",
        objective="Only Task",
        deadline="2026-02-20T10:00:00",
    )
    result = node.complete_task(t1["task_id"], completion_note="done")

    assert result["status"] == "completed"
    assert result["next_task"]["source"] == "AUTO_FOLLOW_ON"
    assert result["next_task"]["status"] == "queued"


def test_catalog_updates_armoury_index(tmp_path: Path):
    node = ArandurCentralNode(tmp_path / "armoury")
    node.catalog_finding(
        source_type="repo",
        source_url="https://github.com/example/repo",
        summary="Agentized repository",
        code_refs=["src/main.py"],
        concepts=["multi_agent"],
    )
    snap = node.snapshot()
    assert snap["armoury_entries"] == 1


def test_log_mesh_delegation_writes_assessment_and_jw(tmp_path: Path):
    jw_log = tmp_path / "jw_log.yaml"
    ops_queue = tmp_path / "queue.yaml"
    reports_dir = tmp_path / "reports"
    node = ArandurCentralNode(
        tmp_path / "armoury",
        jw_log_path=jw_log,
        operations_queue_path=ops_queue,
        reports_dir=reports_dir,
    )

    assessment = node.log_mesh_delegation_assessment(
        mission_id="ATHENA-TEST-1",
        task_id="NP-TEST-1",
        delegation={"mode": "mesh_pi5", "target": "raspberrypi"},
        node={
            "name": "warden",
            "role": "vision_intel",
            "tailscale_host": "raspberrypi",
            "tailscale_ip": "100.1.1.1",
            "reachable": True,
            "soul_file": "CITADEL_v1/REMOTE/WARDEN_SOUL.md",
            "capabilities_file": "ATHENA/athena/fleet/node_profiles/warden.capabilities.yaml",
        },
        model_routing={"provider": "ollama", "model_id": "qwen3.5:7b"},
        result="success",
        report_paths=["Operations/Reports/mesh_test.md"],
        code_refs=["athena/fleet/mesh_discovery.py"],
    )

    assert assessment["delegation_mode"] == "mesh_pi5"
    assert assessment["node"]["tailscale_host"] == "raspberrypi"
    assert assessment["jw_entry_id"] != ""
    assert assessment["operations_queue_task_id"].startswith("NP-ACT-MESH-")

    mesh_text = node.mesh_assessment_path.read_text()
    assert "ATHENA-TEST-1" in mesh_text

    jw_text = jw_log.read_text()
    assert "jw_entries_append_mesh_runtime" in jw_text
    assert "NP-TEST-1" in jw_text

    queue_text = ops_queue.read_text()
    assert "mesh_assessment_entries" in queue_text
    assert "source_task=NP-TEST-1" in queue_text

    report_files = list(reports_dir.glob("mesh_assessment_*.md"))
    assert len(report_files) == 1
    report_text = report_files[0].read_text()
    assert "Mesh Assessment" in report_text
    assert "ATHENA-TEST-1" in report_text


def test_mesh_rollup_summary_metrics(tmp_path: Path):
    node = ArandurCentralNode(
        tmp_path / "armoury",
        reports_dir=(tmp_path / "reports"),
    )

    node.log_mesh_delegation_assessment(
        mission_id="ATHENA-R1",
        task_id="NP-R1",
        delegation={"mode": "mesh_pi5", "target": "raspberrypi"},
        node={"name": "warden", "tailscale_host": "raspberrypi", "reachable": True},
        model_routing={"provider": "ollama", "model_id": "qwen3.5:7b"},
        result="success",
        error="",
    )
    node.log_mesh_delegation_assessment(
        mission_id="ATHENA-R2",
        task_id="NP-R2",
        delegation={"mode": "mesh_pi5", "target": "raspberrypi-1"},
        node={"name": "avatar", "tailscale_host": "raspberrypi-1", "reachable": True},
        model_routing={
            "provider": "openai",
            "model_id": "gpt-4.1-mini",
            "fallback_used": True,
        },
        result="failed",
        error="timeout",
    )

    rollup = node.generate_mesh_assessment_rollup(limit=10)
    assert rollup["window_events"] == 2
    assert rollup["result_counts"]["success"] == 1
    assert rollup["result_counts"]["failed"] == 1
    assert rollup["fallback_frequency"]["count"] == 1
    assert rollup["node_utilization"]["warden"] == 1
    assert rollup["node_utilization"]["avatar"] == 1
    assert rollup["report_path"].endswith(".md")


def test_mesh_rollup_cadence_threshold(tmp_path: Path):
    node = ArandurCentralNode(
        tmp_path / "armoury",
        reports_dir=(tmp_path / "reports"),
    )

    node.log_mesh_delegation_assessment(
        mission_id="ATHENA-C1",
        task_id="NP-C1",
        delegation={"mode": "mesh_pi5", "target": "raspberrypi"},
        node={"name": "warden", "tailscale_host": "raspberrypi", "reachable": True},
        model_routing={"provider": "ollama", "model_id": "qwen3.5:7b"},
        result="success",
    )

    first = node.maybe_generate_mesh_assessment_rollup(
        cadence_events=10,
        cadence_hours=24,
        limit=100,
        force=False,
    )
    assert first["published"] is True
    assert first["reason"] == "first_rollup"

    second = node.maybe_generate_mesh_assessment_rollup(
        cadence_events=10,
        cadence_hours=24,
        limit=100,
        force=False,
    )
    assert second["published"] is False


def test_rollup_cadence_status_fields(tmp_path: Path):
    node = ArandurCentralNode(tmp_path / "armoury", reports_dir=(tmp_path / "reports"))
    status = node.rollup_cadence_status()
    assert "last_generated_at" in status
    assert "last_event_count" in status
    assert "total_events" in status
    assert "pending_delta" in status
