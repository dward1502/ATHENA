from athena.interfaces.ceo_bridge import CEOCommand
from athena.types import IngestResult, SourceType


def test_construct_society_for_ingest_objective():
    cmd = CEOCommand()
    society = cmd.construct_society(
        "Ingest arxiv papers and agentize github repositories"
    )
    assert "APOLLO" in society
    assert "HERMES" in society
    assert "ARTEMIS" in society


def test_llm_runtime_snapshot_shape():
    cmd = CEOCommand()
    snap = cmd.llm_runtime_snapshot()
    assert "providers" in snap
    assert "health" in snap
    assert "jw" in snap


def test_mesh_runtime_snapshot_shape():
    cmd = CEOCommand()
    snap = cmd.mesh_runtime_snapshot()
    assert "manifest_path" in snap
    assert "node_count" in snap
    assert "nodes" in snap


def test_delegation_recommendation_for_scout_objective():
    cmd = CEOCommand()
    decision = cmd.delegation_recommendation("Scout github repositories for ingestion")
    assert "mode" in decision
    assert "target" in decision


def test_bounce_provider_on_rate_limit(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("XAI_API_KEY", "test-xai")

    cmd = CEOCommand()
    first = cmd.model_router.route("APOLLO")
    if first is None:
        return

    bounced = cmd.bounce_provider_on_rate_limit(
        agent_name="APOLLO",
        failed_provider=first.provider_name,
        retry_after_seconds=60,
    )
    assert "status" in bounced or "provider" in bounced
    if "provider" in bounced:
        assert bounced["provider"] != first.provider_name


def test_complete_task_returns_next_from_queue():
    cmd = CEOCommand()
    t1 = cmd.add_task("Task One", "2026-02-20T10:00:00")
    t2 = cmd.add_task("Task Two", "2026-02-20T11:00:00")

    result = cmd.complete_task(t1["task_id"], completion_note="done")
    assert result["status"] == "completed"
    assert result["completed_task"]["task_id"] == t1["task_id"]
    assert result["next_task"]["task_id"] == t2["task_id"]


def test_complete_task_creates_follow_on_when_queue_empty():
    cmd = CEOCommand()
    t1 = cmd.add_task("Only Task", "2026-02-20T10:00:00")

    result = cmd.complete_task(t1["task_id"], completion_note="done")
    assert result["status"] == "completed"
    assert result["next_task"]["status"] == "PENDING"
    assert result["next_task"]["source"] == "AUTO_FOLLOW_ON"


def test_ceo_relay_digest_format_skipped_rollup():
    cmd = CEOCommand()
    digest = cmd.format_ceo_relay_digest(
        {
            "published": False,
            "reason": "none",
            "total_events": 2,
            "events_delta": 0,
            "rollup": None,
        }
    )
    assert "ARANDUR DIGEST" in digest
    assert "rollup=skipped" in digest


def test_ceo_relay_digest_format_published_rollup():
    cmd = CEOCommand()
    digest = cmd.format_ceo_relay_digest(
        {
            "published": True,
            "reason": "event_threshold",
            "total_events": 15,
            "events_delta": 10,
            "rollup": {
                "success_rate": 0.8,
                "result_counts": {"success": 8, "partial": 1, "failed": 1},
                "fallback_frequency": {"rate": 0.2},
            },
        }
    )
    assert "rollup=published" in digest
    assert "success_rate=0.8" in digest


def test_execute_routes_ingest_to_remote_when_mesh_target(monkeypatch):
    cmd = CEOCommand()

    monkeypatch.setattr(cmd.commander, "issue_objective", lambda **_: "M-1")
    monkeypatch.setattr(
        cmd.alexandria,
        "scout_and_plan",
        lambda **_: {"ingest_count": 0, "digest_count": 0},
    )
    monkeypatch.setattr(
        cmd,
        "delegation_recommendation",
        lambda _objective: {
            "mode": "mesh_node",
            "target": "beelink",
            "reason": "mesh available",
            "fallback": "local_fleet_scout",
        },
    )
    monkeypatch.setattr(
        cmd,
        "mesh_runtime_snapshot",
        lambda: {
            "manifest_path": "x",
            "node_count": 1,
            "reachable": 1,
            "pi5_nodes": 0,
            "nodes": [
                {
                    "name": "forge",
                    "tailscale_host": "beelink",
                    "ssh_user": "numenor",
                    "reachable": True,
                    "role": "research_assistant",
                }
            ],
        },
    )
    monkeypatch.setattr(cmd, "_llm_plan_for_society", lambda _society: {})
    monkeypatch.setattr(
        cmd,
        "llm_runtime_snapshot",
        lambda: {"providers": [], "health": {}, "jw": {}},
    )
    monkeypatch.setattr(
        cmd,
        "_run_remote_ingest",
        lambda *_args: IngestResult(
            source_type=SourceType.WEB,
            source_url="https://example.com/brief",
            status="success",
            items_ingested=1,
        ),
    )

    result = cmd.execute(
        objective="Scout this source https://example.com/brief",
        deadline="2026-02-20T10:00:00",
    )

    routed = result["routed_execution"]
    assert routed["remote_attempted"] == 1
    assert routed["remote_success"] == 1
    assert routed["remote_fallback_local"] == 0
    assert len(result["ingest"]) == 1


def test_execute_falls_back_local_when_remote_ingest_fails(monkeypatch):
    cmd = CEOCommand()

    monkeypatch.setattr(cmd.commander, "issue_objective", lambda **_: "M-2")
    monkeypatch.setattr(
        cmd.alexandria,
        "scout_and_plan",
        lambda **_: {"ingest_count": 0, "digest_count": 0},
    )
    monkeypatch.setattr(
        cmd,
        "delegation_recommendation",
        lambda _objective: {
            "mode": "mesh_node",
            "target": "beelink",
            "reason": "mesh available",
            "fallback": "local_fleet_scout",
        },
    )
    monkeypatch.setattr(
        cmd,
        "mesh_runtime_snapshot",
        lambda: {
            "manifest_path": "x",
            "node_count": 1,
            "reachable": 1,
            "pi5_nodes": 0,
            "nodes": [
                {
                    "name": "forge",
                    "tailscale_host": "beelink",
                    "ssh_user": "numenor",
                    "reachable": True,
                    "role": "research_assistant",
                }
            ],
        },
    )
    monkeypatch.setattr(cmd, "_llm_plan_for_society", lambda _society: {})
    monkeypatch.setattr(
        cmd,
        "llm_runtime_snapshot",
        lambda: {"providers": [], "health": {}, "jw": {}},
    )
    monkeypatch.setattr(cmd, "_run_remote_ingest", lambda *_args: None)

    apollo = cmd.athena.olympians.get("APOLLO")
    assert apollo is not None
    artemis = cmd.athena.olympians.get("ARTEMIS")
    assert artemis is not None
    monkeypatch.setattr(
        apollo,
        "ingest_url",
        lambda url: IngestResult(
            source_type=SourceType.WEB,
            source_url=url,
            status="success",
            items_ingested=1,
        ),
    )
    monkeypatch.setattr(
        artemis,
        "validate_ingest_result",
        lambda _result: {"valid": True},
    )

    result = cmd.execute(
        objective="Audit this source https://example.com/post",
        deadline="2026-02-20T10:00:00",
    )

    routed = result["routed_execution"]
    assert routed["remote_attempted"] == 1
    assert routed["remote_success"] == 0
    assert routed["remote_fallback_local"] == 1
    assert len(result["ingest"]) == 1


def test_execute_reuses_existing_alexandria_context(monkeypatch):
    cmd = CEOCommand()
    url = "https://github.com/microsoft/autogen"

    monkeypatch.setattr(cmd.commander, "issue_objective", lambda **_: "M-3")
    monkeypatch.setattr(
        cmd.alexandria,
        "scout_and_plan",
        lambda **_: {"ingest_count": 0, "digest_count": 0},
    )
    monkeypatch.setattr(
        cmd,
        "delegation_recommendation",
        lambda _objective: {
            "mode": "mesh_node",
            "target": "beelink",
            "reason": "mesh available",
            "fallback": "local_fleet_scout",
        },
    )
    monkeypatch.setattr(
        cmd,
        "mesh_runtime_snapshot",
        lambda: {
            "manifest_path": "x",
            "node_count": 1,
            "reachable": 1,
            "pi5_nodes": 0,
            "nodes": [
                {
                    "name": "forge",
                    "tailscale_host": "beelink",
                    "ssh_user": "numenor",
                    "reachable": True,
                    "role": "research_assistant",
                }
            ],
        },
    )
    monkeypatch.setattr(cmd, "_extract_urls", lambda _objective: [url])
    monkeypatch.setattr(cmd, "_preexisting_sources", lambda _urls: {url})
    monkeypatch.setattr(cmd, "_llm_plan_for_society", lambda _society: {})
    monkeypatch.setattr(
        cmd,
        "llm_runtime_snapshot",
        lambda: {"providers": [], "health": {}, "jw": {}},
    )

    def _fail_remote(*_args):
        raise AssertionError("remote ingest should be skipped for reused sources")

    monkeypatch.setattr(cmd, "_run_remote_ingest", _fail_remote)

    result = cmd.execute(
        objective="Revisit existing source for planning",
        deadline="2026-02-20T10:00:00",
    )

    routed = result["routed_execution"]
    assert routed["reused_existing"] == 1
    assert routed["remote_attempted"] == 0
    assert len(result["ingest"]) == 0
    assert len(result["reused_sources"]) == 1


def test_remote_endpoints_prioritize_tailscale_ip(monkeypatch):
    cmd = CEOCommand()
    monkeypatch.setenv("ATHENA_TAILSCALE_MAGIC_DNS_SUFFIX", "tail91c3c1.ts.net")

    endpoints = cmd._remote_endpoints(
        delegation={"target": "raspberrypi"},
        node_data={"ssh_user": "numenor_scout", "tailscale_ip": "100.115.186.127"},
    )

    assert endpoints[0] == "numenor_scout@100.115.186.127"
    assert "numenor_scout@raspberrypi" in endpoints
    assert "numenor_scout@raspberrypi.tail91c3c1.ts.net" in endpoints


def test_execute_includes_phase2_contract_bundle(monkeypatch):
    cmd = CEOCommand()

    monkeypatch.setattr(cmd.commander, "issue_objective", lambda **_: "M-4")
    monkeypatch.setattr(
        cmd.alexandria,
        "scout_and_plan",
        lambda **_: {"ingest_count": 0, "digest_count": 0},
    )
    monkeypatch.setattr(
        cmd,
        "delegation_recommendation",
        lambda _objective: {
            "mode": "mesh_node",
            "target": "beelink",
            "reason": "mesh available",
            "fallback": "local_fleet_scout",
        },
    )
    monkeypatch.setattr(
        cmd,
        "mesh_runtime_snapshot",
        lambda: {
            "manifest_path": "x",
            "node_count": 1,
            "reachable": 1,
            "pi5_nodes": 0,
            "nodes": [
                {
                    "name": "forge",
                    "tailscale_host": "beelink",
                    "tailscale_ip": "100.94.135.106",
                    "ssh_user": "citadel",
                    "reachable": True,
                    "role": "research_assistant",
                }
            ],
        },
    )
    monkeypatch.setattr(cmd, "_llm_plan_for_society", lambda _society: {})
    monkeypatch.setattr(
        cmd,
        "llm_runtime_snapshot",
        lambda: {"providers": [], "health": {}, "jw": {}},
    )
    monkeypatch.setattr(cmd, "_run_remote_ingest", lambda *_args: None)
    monkeypatch.setattr(
        cmd,
        "_quick_access_entry_map",
        lambda: {
            "https://github.com/microsoft/autogen": {},
            "https://github.com/crewAIInc/crewAI": {},
            "https://github.com/kyegomez/swarms": {},
            "https://github.com/OpenBMB/RepoAgent": {},
            "https://github.com/forcedotcom/code-analyzer": {},
            "https://github.com/MS-Teja/code-archeologist": {},
        },
    )

    apollo = cmd.athena.olympians.get("APOLLO")
    assert apollo is not None
    artemis = cmd.athena.olympians.get("ARTEMIS")
    assert artemis is not None
    monkeypatch.setattr(
        apollo,
        "ingest_url",
        lambda url: IngestResult(
            source_type=SourceType.WEB,
            source_url=url,
            status="success",
            items_ingested=1,
        ),
    )
    monkeypatch.setattr(
        artemis,
        "validate_ingest_result",
        lambda _result: {"valid": True},
    )

    result = cmd.execute(
        objective="Build contract baseline https://example.com/contract",
        deadline="2026-02-20T10:00:00",
    )

    bundle = result["phase2_contract_bundle"]
    assert len(bundle["roles"]) == 5
    assert bundle["task"]["task_id"] == "M-4"
    assert bundle["retry_fallback"]["fallback_sequence"][0] == "local_fleet_scout"
    assert bundle["observability"]["result_metrics"]["sources_total"] == 1
    assert bundle["observability"]["result_metrics"]["ingest_count"] == 1

    phases = result["phase_execution"]
    assert phases["phase1_contract_map"]["status"] == "ready"
    assert phases["phase4_code_analyzer_gate"]["gate_policy"]["required_checks"] == [
        "lsp_diagnostics",
        "tests",
        "compile",
    ]
    assert result["phase6_gate"]["status"] == "pass"
    assert result["completion_status"] == "ready"


def test_phase6_gate_blocks_when_merge_not_allowed():
    cmd = CEOCommand()
    gate = cmd._enforce_phase6_gate(
        {
            "phase4_code_analyzer_gate": {
                "status": "ready",
                "gate_policy": {
                    "required_checks": ["lsp_diagnostics", "tests", "compile"],
                    "autonomous_merge_allowed": False,
                },
            },
            "phase5_code_archeologist_precheck": {
                "status": "ready",
                "rewrite_gate": {
                    "triggered": False,
                    "required_steps": [],
                    "status": "not_required",
                },
            },
        }
    )

    assert gate["status"] == "blocked"
    assert "autonomous_merge_not_allowed" in gate["blocked_reasons"]


def test_phase6_gate_passes_when_all_clear():
    cmd = CEOCommand()
    gate = cmd._enforce_phase6_gate(
        {
            "phase4_code_analyzer_gate": {
                "status": "ready",
                "gate_policy": {
                    "required_checks": ["lsp_diagnostics", "tests", "compile"],
                    "autonomous_merge_allowed": True,
                },
            },
            "phase5_code_archeologist_precheck": {
                "status": "ready",
                "rewrite_gate": {
                    "triggered": False,
                    "required_steps": [],
                    "status": "not_required",
                },
            },
        }
    )

    assert gate["status"] == "pass"
    assert gate["blocked_reasons"] == []


def test_force_digest_bypasses_reuse_and_remote(monkeypatch):
    cmd = CEOCommand()

    monkeypatch.setattr(cmd.commander, "issue_objective", lambda **_: "M-5")
    monkeypatch.setattr(
        cmd.alexandria,
        "scout_and_plan",
        lambda **_: {"ingest_count": 0, "digest_count": 0},
    )
    monkeypatch.setattr(
        cmd,
        "delegation_recommendation",
        lambda _objective: {
            "mode": "mesh_pi5",
            "target": "raspberrypi",
            "reason": "mesh available",
            "fallback": "local_fleet_scout",
        },
    )
    monkeypatch.setattr(
        cmd,
        "mesh_runtime_snapshot",
        lambda: {"nodes": []},
    )
    monkeypatch.setattr(cmd, "_llm_plan_for_society", lambda _society: {})
    monkeypatch.setattr(
        cmd,
        "llm_runtime_snapshot",
        lambda: {"providers": [], "health": {}, "jw": {}},
    )
    monkeypatch.setattr(
        cmd,
        "_preexisting_sources",
        lambda _urls: {"https://github.com/example/repo"},
    )

    def _fail_remote(*_args):
        raise AssertionError("remote ingest should be skipped in force digest")

    monkeypatch.setattr(cmd, "_run_remote_ingest", _fail_remote)

    hermes = cmd.athena.olympians.get("HERMES")
    assert hermes is not None
    monkeypatch.setattr(
        hermes,
        "agentize_repo",
        lambda url: IngestResult(
            source_type=SourceType.REPO,
            source_url=url,
            status="success",
            items_ingested=1,
        ),
    )

    result = cmd.execute(
        objective="Digest queued Alexandria repository (force digest): https://github.com/example/repo",
        deadline="2026-02-20T10:00:00",
    )

    routed = result["routed_execution"]
    assert routed["reused_existing"] == 0
    assert routed["remote_attempted"] == 0
    assert routed["local_only"] == 1


def test_library_context_includes_repo_book_signals(monkeypatch):
    cmd = CEOCommand()
    url = "https://github.com/example/repo"

    monkeypatch.setattr(
        cmd,
        "_analysis_book_for_repo_url",
        lambda _url: {
            "analysis_status": "digested",
            "agent_card": {
                "signal_tags": ["discord", "openai"],
                "capabilities": ["multi_agent"],
                "sampled_files": ["src/main.ts", "README.md"],
            },
        },
    )

    context = cmd._library_context(
        objective="Improve discord orchestration for autonomous runtime",
        urls=[url],
    )

    assert context["repo_book_count"] == 1
    assert "discord" in context["focus_tags"]
    assert context["repo_books"][0]["sampled_files"] == 2
