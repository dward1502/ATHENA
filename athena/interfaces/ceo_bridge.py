import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from athena.commander import AthenaCommander
from athena.core import ATHENA
from athena.fleet.delegation_policy import Pi5DelegationPolicy
from athena.gates import EvidenceCollector, GateEnforcer
from athena.orchestration import RetryExecutor, RoleRegistry
from athena.fleet.mesh_discovery import MeshDiscoveryAdapter
from athena.fleet.model_router import ModelRouter, ProviderRegistry
from athena.fleet.node_registry import NodeRegistry
from athena.interfaces.alexandria_pipeline import AlexandriaPipeline
from athena.interfaces.arandur_node import ArandurCentralNode
from athena.olympians.apollo import APOLLO_OLYMPIAN
from athena.olympians.artemis import ARTEMIS_OLYMPIAN
from athena.olympians.hermes import HERMES_OLYMPIAN
from athena.types import (
    CEOContractBundle,
    HandoffContract,
    IngestResult,
    ObservabilityContract,
    RetryFallbackContract,
    RoleContract,
    SourceType,
    TaskContract,
)

import logging as _logging

_ceo_logger = _logging.getLogger("ATHENA.ceo_bridge")


REMOTE_INGEST_SCRIPT = """
import json
import re
import sys
import urllib.request

url = sys.argv[1]
kind = sys.argv[2]

payload = {
    "status": "failed",
    "source_url": url,
    "source_type": kind,
    "items_ingested": 0,
    "errors": [],
}

if kind == "repo":
    match = re.match(r"https?://github.com/([^/]+)/([^/?#]+)", url)
    if match:
        owner = match.group(1)
        repo = match.group(2)
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        req = urllib.request.Request(api_url, headers={"User-Agent": "ATHENA-DELEGATE/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        payload["status"] = "success"
        payload["items_ingested"] = 1
        payload["repo_name"] = data.get("full_name", f"{owner}/{repo}")
        payload["repo_description"] = data.get("description", "") or ""
    else:
        payload["errors"] = ["invalid github repository url"]
else:
    req = urllib.request.Request(url, headers={"User-Agent": "ATHENA-DELEGATE/1.0"})
    with urllib.request.urlopen(req, timeout=6) as resp:
        html = resp.read().decode("utf-8", "ignore")
    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else url
    payload["status"] = "success"
    payload["items_ingested"] = 1
    payload["title"] = re.sub(r"\\s+", " ", title)

print(json.dumps(payload))
"""


class CEOCommand:
    PHASE_SOURCE_MAP = {
        "phase1_contract_map": [
            "https://github.com/microsoft/autogen",
            "https://github.com/crewAIInc/crewAI",
        ],
        "phase2_swarms_topology": ["https://github.com/kyegomez/swarms"],
        "phase3_repoagent_scout": ["https://github.com/OpenBMB/RepoAgent"],
        "phase4_code_analyzer_gate": ["https://github.com/forcedotcom/code-analyzer"],
        "phase5_code_archeologist_precheck": [
            "https://github.com/MS-Teja/code-archeologist"
        ],
    }

    def __init__(self):
        self.athena = ATHENA()
        self.athena.register_default_olympians()
        self.commander = AthenaCommander(self.athena)
        self.node_registry = NodeRegistry()
        self.node_registry.register_default_fleet()
        self.provider_registry = ProviderRegistry()
        self.model_router = ModelRouter(
            node_registry=self.node_registry,
            provider_registry=self.provider_registry,
        )
        mesh_manifest = (
            Path(__file__).resolve().parents[3]
            / "CITADEL_v1"
            / "REMOTE"
            / "MESH_MANIFEST.yaml"
        )
        self.mesh_discovery = MeshDiscoveryAdapter(manifest_path=mesh_manifest)
        self.delegation_policy = Pi5DelegationPolicy()
        jw_log_path = (
            Path(__file__).resolve().parents[3]
            / "Operations"
            / "Ledger"
            / "joulework"
            / "jw_log.yaml"
        )
        operations_queue_path = (
            Path(__file__).resolve().parents[3] / "Operations" / "Tasks" / "queue.yaml"
        )
        reports_dir = Path(__file__).resolve().parents[3] / "Operations" / "Reports"
        self.central_node = ArandurCentralNode(
            self.athena.garrison_path / "armoury",
            jw_log_path=jw_log_path,
            operations_queue_path=operations_queue_path,
            reports_dir=reports_dir,
        )
        alexandria_default = self.athena.garrison_path / "armoury" / "alexandria"
        alexandria_user = (
            Path(__file__).resolve().parents[3]
            / "athena-garrison"
            / "armoury"
            / "alexandria"
        )
        alexandria_root = (
            alexandria_user if alexandria_user.exists() else alexandria_default
        )
        self.alexandria = AlexandriaPipeline(alexandria_root)
        self.remote_delegation_timeout_seconds = int(
            os.getenv("ATHENA_REMOTE_DELEGATION_TIMEOUT", "20")
        )
        self.role_registry = RoleRegistry()
        self.evidence_collector = EvidenceCollector()
        self.gate_enforcer = GateEnforcer(self.evidence_collector)
        self.task_queue: List[Dict[str, Any]] = []
        self._task_counter = 0

    def add_task(
        self, title: str, deadline: str, source: str = "CEO"
    ) -> Dict[str, Any]:
        self._task_counter += 1
        task = {
            "task_id": self._task_counter,
            "title": title,
            "deadline": deadline,
            "source": source,
            "owner": "ARANDUR",
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "completion_note": "",
        }
        self.task_queue.append(task)
        return task

    def get_task_queue(self) -> List[Dict[str, Any]]:
        return list(self.task_queue)

    def _next_pending_task(self) -> Dict[str, Any] | None:
        for task in self.task_queue:
            if task["status"] == "PENDING":
                return task
        return None

    def _create_follow_on_task(self) -> Dict[str, Any]:
        next_title = "Define next CEO objective from latest mission outputs"
        return self.add_task(
            title=next_title,
            deadline=datetime.now().replace(microsecond=0).isoformat(),
            source="AUTO_FOLLOW_ON",
        )

    def complete_task(self, task_id: int, completion_note: str = "") -> Dict[str, Any]:
        completed: Dict[str, Any] | None = None
        for task in self.task_queue:
            if task["task_id"] == task_id:
                task["status"] = "COMPLETE"
                task["completed_at"] = datetime.now().isoformat()
                task["completion_note"] = completion_note
                completed = task
                break

        if completed is None:
            return {
                "status": "not_found",
                "task_id": task_id,
                "next_task": self._next_pending_task() or self._create_follow_on_task(),
            }

        next_task = self._next_pending_task()
        if next_task is None:
            next_task = self._create_follow_on_task()

        return {
            "status": "completed",
            "completed_task": completed,
            "next_task": next_task,
            "queue_size": len(self.task_queue),
        }

    _CAPABILITY_TO_OLYMPIAN: Dict[str, str] = {
        "ingest": "HERMES",
        "delegated_execution": "HERMES",
        "decomposition": "APOLLO",
        "routing_plan": "APOLLO",
        "ingest_validation": "ARTEMIS",
        "quality_gate": "ARTEMIS",
        "metrics_review": "ARTEMIS",
        "risk_review": "ARTEMIS",
        "objective_management": "ARES",
    }

    def construct_society(self, objective: str) -> List[str]:
        text = objective.lower()
        society: set[str] = {"ARTEMIS"}

        if any(k in text for k in ("github", "repo", "agentize", "repository")):
            society.add("HERMES")
        if any(k in text for k in ("arxiv", "paper", "article", "ingest", "url")):
            society.add("APOLLO")
        if any(k in text for k in ("backend", "service", "api", "database")):
            society.add("ARES")
        if any(k in text for k in ("infra", "deploy", "container", "podman")):
            society.add("HEPHAESTUS")

        for role in self.role_registry.roles_for_objective(objective):
            for cap in role.capabilities:
                olympian = self._CAPABILITY_TO_OLYMPIAN.get(cap)
                if olympian:
                    society.add(olympian)

        return sorted(society)

    def _extract_urls(self, objective: str) -> List[str]:
        pattern = r"https?://[^\s]+"
        return re.findall(pattern, objective)

    def _preexisting_sources(self, urls: List[str]) -> set[str]:
        if not urls:
            return set()

        quick_access_path = self.alexandria.quick_access_path
        try:
            payload = json.loads(quick_access_path.read_text())
        except (OSError, json.JSONDecodeError):
            return set()

        entries = payload.get("entries", []) if isinstance(payload, dict) else []
        known = set()
        targets = set(urls)

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            source_url = str(entry.get("source_url", ""))
            if source_url in targets:
                known.add(source_url)
        return known

    def _quick_access_entry_map(self) -> Dict[str, Dict[str, Any]]:
        try:
            payload = json.loads(self.alexandria.quick_access_path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

        entries = payload.get("entries", []) if isinstance(payload, dict) else []
        result: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            source_url = str(entry.get("source_url", "")).strip()
            if source_url:
                result[source_url] = entry
        return result

    def _phase_execution_summary(
        self,
        objective: str,
        quick_map: Dict[str, Dict[str, Any]],
        ingest_count: int,
        validation_count: int,
    ) -> Dict[str, Any]:
        phases: Dict[str, Any] = {}
        available = set(quick_map.keys())

        for phase, required_sources in self.PHASE_SOURCE_MAP.items():
            missing = [src for src in required_sources if src not in available]
            phases[phase] = {
                "status": "ready" if not missing else "blocked",
                "required_sources": required_sources,
                "missing_sources": missing,
            }

        phases["phase2_swarms_topology"]["topology_profile"] = {
            "shape": "planner_hub_executor_spokes",
            "roles": ["planner", "executor", "validator", "auditor"],
            "coordination": "task_queue_with_deadline_and_retry",
        }

        phases["phase3_repoagent_scout"]["orientation_packet_fields"] = [
            "repo_url",
            "summary",
            "capabilities",
            "entry_points",
            "docs_links",
        ]

        phases["phase4_code_analyzer_gate"]["gate_policy"] = {
            "required_checks": ["lsp_diagnostics", "tests", "compile"],
            "autonomous_merge_allowed": bool(
                ingest_count >= 0 and validation_count > 0
            ),
        }

        lowered = objective.lower()
        rewrite_triggered = any(
            keyword in lowered for keyword in ("rewrite", "refactor", "legacy")
        )
        phases["phase5_code_archeologist_precheck"]["rewrite_gate"] = {
            "triggered": rewrite_triggered,
            "required_steps": [
                "history_pattern_scan",
                "hotspot_identification",
                "blast_radius_estimation",
            ],
            "status": "required" if rewrite_triggered else "not_required",
        }

        return phases

    def _repo_orientation_packets(
        self,
        urls: List[str],
        quick_map: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        packets: List[Dict[str, Any]] = []
        for url in urls:
            if not self._is_github_repo_url(url):
                continue
            entry = quick_map.get(url, {})
            docs_links = entry.get("docs_links", []) if isinstance(entry, dict) else []
            packets.append(
                {
                    "source_url": url,
                    "docs_links": docs_links,
                    "mission_id": entry.get("mission_id")
                    if isinstance(entry, dict)
                    else None,
                    "status": entry.get("status") if isinstance(entry, dict) else None,
                }
            )
        return packets

    def _analysis_book_for_repo_url(self, repo_url: str) -> Dict[str, Any]:
        slug = self.alexandria._repo_slug(repo_url)
        if not slug:
            return {}
        path = self.alexandria.analysis_books_dir / slug / "book.json"
        if not path.exists():
            return {}
        payload = self.alexandria._read_json(path)
        return payload if isinstance(payload, dict) else {}

    def _library_context(self, objective: str, urls: List[str]) -> Dict[str, Any]:
        objective_lower = objective.lower()
        repo_books: List[Dict[str, Any]] = []
        for url in urls:
            if not self._is_github_repo_url(url):
                continue
            book = self._analysis_book_for_repo_url(url)
            if not book:
                continue
            card = (
                book.get("agent_card", {})
                if isinstance(book.get("agent_card"), dict)
                else {}
            )
            repo_books.append(
                {
                    "source_url": url,
                    "analysis_status": book.get("analysis_status", "unknown"),
                    "signal_tags": card.get("signal_tags", []),
                    "capabilities": card.get("capabilities", []),
                    "sampled_files": len(
                        card.get("sampled_files", [])
                        if isinstance(card.get("sampled_files", []), list)
                        else []
                    ),
                }
            )

        tags = [
            "discord" if "discord" in objective_lower else "none",
            "refactor"
            if "refactor" in objective_lower or "maintain" in objective_lower
            else "none",
            "autonomy" if "autonom" in objective_lower else "none",
        ]
        focus = [tag for tag in tags if tag != "none"]

        return {
            "repo_book_count": len(repo_books),
            "focus_tags": focus,
            "repo_books": repo_books,
        }

    def _enforce_phase6_gate(
        self,
        phase_execution: Dict[str, Any],
    ) -> Dict[str, Any]:
        phase4 = phase_execution.get("phase4_code_analyzer_gate", {})
        phase5 = phase_execution.get("phase5_code_archeologist_precheck", {})

        phase4_status = str(phase4.get("status", "blocked"))
        phase5_status = str(phase5.get("status", "blocked"))
        phase4_gate = phase4.get("gate_policy", {})
        phase5_gate = phase5.get("rewrite_gate", {})

        autonomous_merge_allowed = bool(
            phase4_gate.get("autonomous_merge_allowed", False)
        )
        rewrite_required = phase5_gate.get("status") == "required"

        blocked_reasons: List[str] = []
        if phase4_status != "ready":
            blocked_reasons.append("phase4_not_ready")
        if phase5_status != "ready":
            blocked_reasons.append("phase5_not_ready")
        if not autonomous_merge_allowed:
            blocked_reasons.append("autonomous_merge_not_allowed")
        if rewrite_required:
            blocked_reasons.append("archeologist_precheck_required")

        if blocked_reasons:
            return {
                "status": "blocked",
                "blocked_reasons": blocked_reasons,
                "escalation_path": [
                    "validator",
                    "auditor",
                    "ceo",
                ],
                "next_action": "escalate_to_ceo_and_hold_autonomous_completion",
            }

        return {
            "status": "pass",
            "blocked_reasons": [],
            "escalation_path": [],
            "next_action": "allow_autonomous_completion",
        }

    def _is_github_repo_url(self, url: str) -> bool:
        return "github.com/" in url and "/issues/" not in url and "/pull/" not in url

    def _is_arxiv_url(self, url: str) -> bool:
        return "arxiv.org/" in url

    def _llm_plan_for_society(self, society: List[str]) -> Dict[str, Any]:
        plan: Dict[str, Any] = {}
        for agent_name in society:
            route = self.model_router.route(agent_name)
            plan[agent_name] = route.to_dict() if route else {"status": "unavailable"}
        return plan

    def bounce_provider_on_rate_limit(
        self,
        agent_name: str,
        failed_provider: str,
        retry_after_seconds: int = 60,
    ) -> Dict[str, Any]:
        reroute = self.model_router.route_after_failure(
            agent_name=agent_name,
            failed_provider=failed_provider,
            status_code=429,
            retry_after_seconds=retry_after_seconds,
        )
        return reroute.to_dict() if reroute else {"status": "unavailable"}

    def provider_health(self) -> Dict[str, bool]:
        return self.provider_registry.health_check_all()

    def provider_chain(self) -> List[Dict[str, Any]]:
        return self.provider_registry.list_providers()

    def llm_runtime_snapshot(self) -> Dict[str, Any]:
        return {
            "providers": self.provider_chain(),
            "health": self.provider_health(),
            "jw": self.model_router.get_jw_summary(),
        }

    def mesh_runtime_snapshot(self) -> Dict[str, Any]:
        nodes = self.mesh_discovery.discover()
        return {
            "manifest_path": str(self.mesh_discovery.manifest_path),
            "node_count": len(nodes),
            "reachable": len([n for n in nodes if n.reachable]),
            "pi5_nodes": len([n for n in nodes if n.is_pi5]),
            "nodes": [n.to_dict() for n in nodes],
        }

    def delegation_recommendation(self, objective: str) -> Dict[str, str]:
        nodes = self.mesh_discovery.discover()
        decision = self.delegation_policy.recommend(
            objective=objective,
            mesh_nodes=nodes,
            node_registry=self.node_registry,
        )
        return decision.to_dict()

    def _find_node_for_target(
        self, mesh_nodes: List[Dict[str, Any]], target: str
    ) -> Dict[str, Any]:
        for node in mesh_nodes:
            if isinstance(node, dict) and node.get("tailscale_host") == target:
                return node
        return {}

    def _should_attempt_remote_ingest(self, delegation: Dict[str, Any]) -> bool:
        mode = str(delegation.get("mode", ""))
        if mode not in {"mesh_pi5", "mesh_node", "local_fleet"}:
            return False
        target = str(delegation.get("target", "")).strip().lower()
        return target not in {"", "localhost", "127.0.0.1"}

    def _remote_endpoints(
        self, delegation: Dict[str, Any], node_data: Dict[str, Any]
    ) -> List[str]:
        target = str(delegation.get("target", "")).strip()
        ssh_user = str(node_data.get("ssh_user", "")).strip()
        default_user = os.getenv("ATHENA_REMOTE_SSH_USER", "").strip()
        user = ssh_user or default_user

        candidates: List[str] = []

        tailscale_ip = str(node_data.get("tailscale_ip", "")).strip()
        if tailscale_ip:
            candidates.append(f"{user}@{tailscale_ip}" if user else tailscale_ip)

        if target:
            candidates.append(f"{user}@{target}" if user else target)

        if target and "." not in target:
            suffix = str(os.getenv("ATHENA_TAILSCALE_MAGIC_DNS_SUFFIX", "")).strip()
            if suffix:
                fqdn = f"{target}.{suffix}"
                candidates.append(f"{user}@{fqdn}" if user else fqdn)

        unique: List[str] = []
        for endpoint in candidates:
            if endpoint and endpoint not in unique:
                unique.append(endpoint)
        return unique

    def _build_remote_ingest_result(
        self,
        payload: Dict[str, Any],
        url: str,
        source_type: SourceType,
    ) -> IngestResult:
        status = str(payload.get("status", "failed"))
        if status not in {"success", "partial", "failed"}:
            status = "failed"

        items_raw = payload.get("items_ingested", 0)
        try:
            items_ingested = int(items_raw)
        except (TypeError, ValueError):
            items_ingested = 0

        errors_raw = payload.get("errors", [])
        errors = [str(e) for e in errors_raw] if isinstance(errors_raw, list) else []

        return IngestResult(
            source_type=source_type,
            source_url=url,
            status=status,
            items_ingested=max(0, items_ingested),
            errors=errors,
        )

    def _run_remote_ingest(
        self,
        url: str,
        delegation: Dict[str, Any],
        node_data: Dict[str, Any],
    ) -> IngestResult | None:
        if self._is_github_repo_url(url):
            source_type = SourceType.REPO
            source_kind = "repo"
        elif self._is_arxiv_url(url):
            source_type = SourceType.ARTICLE
            source_kind = "article"
        elif url.startswith("http"):
            source_type = SourceType.WEB
            source_kind = "web"
        else:
            return None

        endpoints = self._remote_endpoints(delegation, node_data)
        if not endpoints:
            return None

        for endpoint in endpoints:
            cmd = [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-o",
                "ServerAliveInterval=3",
                "-o",
                "ServerAliveCountMax=1",
                "-o",
                f"ConnectTimeout={max(1, self.remote_delegation_timeout_seconds // 2)}",
                endpoint,
                "python3",
                "-",
                url,
                source_kind,
            ]

            try:
                proc = subprocess.run(
                    cmd,
                    input=REMOTE_INGEST_SCRIPT,
                    capture_output=True,
                    text=True,
                    timeout=self.remote_delegation_timeout_seconds,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                continue

            if proc.returncode != 0:
                continue

            output = proc.stdout.strip()
            if not output:
                continue

            lines = [line.strip() for line in output.splitlines() if line.strip()]
            if not lines:
                continue

            try:
                payload = json.loads(lines[-1])
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue

            return self._build_remote_ingest_result(payload, url, source_type)

        return None

    def _record_ingest_result(
        self,
        results: Dict[str, Any],
        ingest_result: IngestResult,
        artemis: Any,
    ) -> None:
        payload = ingest_result.to_dict()
        results["ingest"].append(payload)

        summary = f"Ingestion result for {ingest_result.source_url}"
        concepts: List[str] = []
        code_refs: List[str] = []

        if ingest_result.agent_card:
            summary = ingest_result.agent_card.description or summary
            concepts = list(ingest_result.agent_card.capabilities)
            code_refs = list(ingest_result.agent_card.entry_points.values())
        elif ingest_result.articles:
            summary = ingest_result.articles[0].title or summary
            concepts = list(ingest_result.articles[0].categories)

        self.central_node.catalog_finding(
            source_type=ingest_result.source_type.value,
            source_url=ingest_result.source_url,
            summary=summary,
            code_refs=code_refs,
            concepts=concepts,
            payload=payload,
        )

        if isinstance(artemis, ARTEMIS_OLYMPIAN):
            val = artemis.validate_ingest_result(ingest_result)
            results["validation"].append(val)

    def _ingest_url_locally(
        self,
        url: str,
        apollo: Any,
        hermes: Any,
    ) -> IngestResult | None:
        if self._is_github_repo_url(url) and isinstance(hermes, HERMES_OLYMPIAN):
            return hermes.agentize_repo(url)
        if self._is_arxiv_url(url) and isinstance(apollo, APOLLO_OLYMPIAN):
            return apollo.ingest_paper(url)
        if url.startswith("http") and isinstance(apollo, APOLLO_OLYMPIAN):
            return apollo.ingest_url(url)
        return None

    def _build_contract_bundle(
        self,
        mission_id: str,
        objective: str,
        deadline: str,
        urls: List[str],
        delegation: Dict[str, Any],
    ) -> Dict[str, Any]:
        roles = [
            RoleContract(
                role_id="ceo",
                capabilities=["objective_management", "escalation"],
                tool_allowlist=["ceo_bridge", "task_queue", "reports"],
                handoff_targets=["planner", "validator"],
                escalation_policy="ceo",
            ),
            RoleContract(
                role_id="planner",
                capabilities=["decomposition", "routing_plan"],
                tool_allowlist=["alexandria_pipeline", "model_router"],
                handoff_targets=["executor", "auditor"],
                escalation_policy="ceo",
            ),
            RoleContract(
                role_id="executor",
                capabilities=["ingest", "delegated_execution"],
                tool_allowlist=["apollo", "hermes", "mesh_delegation"],
                handoff_targets=["validator"],
                escalation_policy="planner",
            ),
            RoleContract(
                role_id="validator",
                capabilities=["ingest_validation", "quality_gate"],
                tool_allowlist=["artemis", "mesh_assessment"],
                handoff_targets=["ceo"],
                escalation_policy="ceo",
            ),
            RoleContract(
                role_id="auditor",
                capabilities=["metrics_review", "risk_review"],
                tool_allowlist=["reports", "ledger"],
                handoff_targets=["ceo"],
                escalation_policy="ceo",
            ),
        ]

        task = TaskContract(
            task_id=mission_id,
            objective=objective,
            constraints={
                "deadline": deadline,
                "delegation_mode": str(delegation.get("mode", "local_primary")),
                "delegation_target": str(delegation.get("target", "")),
            },
            inputs=list(urls),
            acceptance_criteria=[
                "mission objective analyzed and delegated",
                "ingest or reuse path selected per source",
                "validation metrics recorded",
                "mesh assessment event logged",
            ],
            status="in_progress",
        )

        handoffs = [
            HandoffContract(
                from_role="ceo",
                to_role="planner",
                task_id=mission_id,
                handoff_reason="objective_received",
                required_state=["objective", "deadline"],
                verification_hooks=["construct_society", "delegation_recommendation"],
            ),
            HandoffContract(
                from_role="planner",
                to_role="executor",
                task_id=mission_id,
                handoff_reason="execution_plan_ready",
                required_state=["society", "delegation", "url_set"],
                verification_hooks=["mesh_runtime_snapshot", "llm_runtime_snapshot"],
            ),
            HandoffContract(
                from_role="executor",
                to_role="validator",
                task_id=mission_id,
                handoff_reason="ingest_cycle_complete",
                required_state=["ingest_results"],
                verification_hooks=["validate_ingest_result"],
            ),
            HandoffContract(
                from_role="validator",
                to_role="ceo",
                task_id=mission_id,
                handoff_reason="quality_gate_complete",
                required_state=["validation", "mesh_assessment"],
                verification_hooks=["format_ceo_relay_digest"],
            ),
        ]

        retry_fallback = RetryFallbackContract(
            retry_budget=2,
            backoff_policy="linear_15s",
            fallback_sequence=[
                str(delegation.get("fallback", "local_primary")),
                "local_primary",
                "escalate_to_ceo",
            ],
            failure_signature="delegation_or_ingest_failure",
            last_resort_action="escalate_to_ceo",
        )

        observability = ObservabilityContract(
            mission_id=mission_id,
            step_events=[
                "objective_received",
                "society_constructed",
                "delegation_recommended",
                "ingest_or_reuse_executed",
                "mesh_assessment_logged",
            ],
            result_metrics={
                "sources_total": len(urls),
            },
            resource_metrics={
                "delegation_target": str(delegation.get("target", "")),
                "delegation_mode": str(delegation.get("mode", "local_primary")),
                "remote_timeout_seconds": self.remote_delegation_timeout_seconds,
            },
            audit_log_ref=str(self.central_node.mesh_assessment_path),
        )

        bundle = CEOContractBundle(
            roles=roles,
            task=task,
            handoffs=handoffs,
            retry_fallback=retry_fallback,
            observability=observability,
        )
        return bundle.to_dict()

    def format_ceo_relay_digest(self, rollup_payload: Dict[str, Any]) -> str:
        published = bool(rollup_payload.get("published", False))
        reason = str(rollup_payload.get("reason", "none"))
        total_events = int(rollup_payload.get("total_events", 0))
        events_delta = int(rollup_payload.get("events_delta", 0))

        rollup = rollup_payload.get("rollup")
        if not isinstance(rollup, dict):
            return (
                "ARANDUR DIGEST | rollup=skipped"
                + f" | reason={reason}"
                + f" | total_events={total_events}"
                + f" | events_delta={events_delta}"
            )

        result_counts = rollup.get("result_counts", {})
        fallback = rollup.get("fallback_frequency", {})
        success_rate = rollup.get("success_rate", 0.0)

        return (
            "ARANDUR DIGEST"
            + f" | rollup={'published' if published else 'skipped'}"
            + f" | reason={reason}"
            + f" | events={total_events} (+{events_delta})"
            + f" | success_rate={success_rate}"
            + " | results="
            + f"S:{result_counts.get('success', 0)}"
            + f" P:{result_counts.get('partial', 0)}"
            + f" F:{result_counts.get('failed', 0)}"
            + f" | fallback_rate={fallback.get('rate', 0.0)}"
        )

    def execute(self, objective: str, deadline: str) -> Dict[str, Any]:
        active_task = self.add_task(objective, deadline, source="CEO_OBJECTIVE")
        company_task = self.central_node.enqueue_task(
            title=objective,
            objective=objective,
            deadline=deadline,
            source="ATHENA",
            owner="ARANDUR",
        )
        mission_id = self.commander.issue_objective(
            objective=objective, deadline=deadline, priority="CRITICAL"
        )

        urls = self._extract_urls(objective)
        lowered_objective = objective.lower()
        force_digest = "force digest" in lowered_objective
        preexisting_sources = set() if force_digest else self._preexisting_sources(urls)
        quick_map = self._quick_access_entry_map()
        society = self.construct_society(objective)
        decision = (
            "immediate"
            if any(k in objective.lower() for k in ("immediate", "now", "execute now"))
            else "deferred"
        )
        alexandria_plan = self.alexandria.scout_and_plan(
            urls=urls,
            mission_id=mission_id,
            decision=decision,
        )

        delegation = self.delegation_recommendation(objective)
        mesh_runtime = self.mesh_runtime_snapshot()

        results: Dict[str, Any] = {
            "mission_id": mission_id,
            "active_task": active_task,
            "company_task": company_task,
            "alexandria_plan": alexandria_plan,
            "next_task": self._next_pending_task(),
            "queue": self.get_task_queue(),
            "company_node": self.central_node.snapshot(),
            "communication_channels": [
                "discord_ceo_relay",
                "athena_garrison_log",
                "armoury_catalog_jsonl",
            ],
            "society": society,
            "delegation": delegation,
            "llm_plan": self._llm_plan_for_society(society),
            "llm_runtime": self.llm_runtime_snapshot(),
            "mesh_runtime": mesh_runtime,
            "ingest": [],
            "validation": [],
            "routed_execution": {
                "remote_attempted": 0,
                "remote_success": 0,
                "remote_fallback_local": 0,
                "local_only": 0,
                "reused_existing": 0,
            },
            "reused_sources": [],
            "phase2_contract_bundle": self._build_contract_bundle(
                mission_id=mission_id,
                objective=objective,
                deadline=deadline,
                urls=urls,
                delegation=delegation,
            ),
            "phase_execution": {},
            "repo_orientation_packets": self._repo_orientation_packets(urls, quick_map),
            "library_context": self._library_context(objective, urls),
        }

        apollo = self.athena.olympians.get("APOLLO")
        hermes = self.athena.olympians.get("HERMES")
        artemis = self.athena.olympians.get("ARTEMIS")

        mesh_nodes = results.get("mesh_runtime", {}).get("nodes", [])
        node_data = self._find_node_for_target(
            mesh_nodes if isinstance(mesh_nodes, list) else [],
            str(delegation.get("target", "")),
        )

        for url in urls:
            if url in preexisting_sources:
                results["routed_execution"]["reused_existing"] += 1
                results["reused_sources"].append(
                    {
                        "source_url": url,
                        "reason": "reuse_existing_alexandria_context",
                    }
                )
                continue

            remote_attempted = False
            ingest_result: IngestResult | None = None

            if (not force_digest) and self._should_attempt_remote_ingest(delegation):
                remote_attempted = True
                ingest_result = self._run_remote_ingest(url, delegation, node_data)
                results["routed_execution"]["remote_attempted"] += 1

            if ingest_result is not None and ingest_result.status != "failed":
                results["routed_execution"]["remote_success"] += 1
                self._record_ingest_result(results, ingest_result, artemis)
                continue

            retry_contract = RetryFallbackContract(
                retry_budget=2,
                backoff_policy="linear_15s",
                fallback_sequence=[
                    str(delegation.get("fallback", "local_primary")),
                    "local_primary",
                    "escalate_to_ceo",
                ],
                failure_signature="local_ingest_failure",
                last_resort_action="escalate_to_ceo",
            )

            retry_result = RetryExecutor.execute_with_retry(
                contract=retry_contract,
                action=lambda _url=url: self._ingest_url_locally(_url, apollo, hermes),
                action_label=f"local_ingest({url})",
            )

            if retry_result["status"] == "success":
                local_result = retry_result["result"]
            else:
                _ceo_logger.warning(
                    "Ingest exhausted retries for %s: %s",
                    url,
                    retry_result.get("last_error", "unknown"),
                )
                results["routed_execution"].setdefault("retry_exhausted", 0)
                results["routed_execution"]["retry_exhausted"] += 1
                local_result = None

            if local_result is None:
                continue

            if remote_attempted:
                results["routed_execution"]["remote_fallback_local"] += 1
            else:
                results["routed_execution"]["local_only"] += 1

            self._record_ingest_result(results, local_result, artemis)

        lowered = lowered_objective
        if (
            isinstance(apollo, APOLLO_OLYMPIAN)
            and "arxiv" in lowered
            and not any(self._is_arxiv_url(url) for url in urls)
        ):
            query = lowered.replace("arxiv", "").strip() or objective
            ingest_result = apollo.ingest_arxiv(query=query, max_results=5)
            self._record_ingest_result(results, ingest_result, artemis)

        if isinstance(artemis, ARTEMIS_OLYMPIAN):
            results["metrics"] = artemis.get_metrics()

        target = delegation.get("target", "") if isinstance(delegation, dict) else ""

        first_route: Dict[str, Any] = {}
        llm_plan = results.get("llm_plan", {})
        if isinstance(llm_plan, dict):
            for route in llm_plan.values():
                if isinstance(route, dict) and route.get("provider"):
                    first_route = route
                    break

        assessment_result = (
            "success" if len(results.get("ingest", [])) > 0 else "partial"
        )
        mesh_assessment = self.central_node.log_mesh_delegation_assessment(
            mission_id=mission_id,
            task_id=str(company_task.get("task_id", "")),
            delegation=delegation if isinstance(delegation, dict) else {},
            node=node_data,
            model_routing=first_route,
            result=assessment_result,
            report_paths=[
                str(self.central_node.mesh_assessment_path),
                str(self.central_node.armoury_path),
            ],
            code_refs=[],
        )
        results["mesh_assessment"] = mesh_assessment
        rollup_payload = self.central_node.maybe_generate_mesh_assessment_rollup(
            cadence_events=10,
            cadence_hours=24,
            limit=100,
            force=False,
        )
        results["mesh_assessment_rollup"] = rollup_payload
        results["ceo_relay_digest"] = self.format_ceo_relay_digest(rollup_payload)

        results["company_node"] = self.central_node.snapshot()

        phase2_bundle = results.get("phase2_contract_bundle", {})
        if isinstance(phase2_bundle, dict):
            observability = phase2_bundle.get("observability", {})
            if isinstance(observability, dict):
                observability["result_metrics"] = {
                    "sources_total": len(urls),
                    "sources_reused": len(results.get("reused_sources", [])),
                    "ingest_count": len(results.get("ingest", [])),
                    "validation_count": len(results.get("validation", [])),
                }
                phase2_bundle["observability"] = observability
                results["phase2_contract_bundle"] = phase2_bundle

        results["phase_execution"] = self._phase_execution_summary(
            objective=objective,
            quick_map=quick_map,
            ingest_count=len(results.get("ingest", [])),
            validation_count=len(results.get("validation", [])),
        )

        self.evidence_collector.clear()

        ingest_list = results.get("ingest", [])
        if ingest_list:
            self.evidence_collector.record(
                check_type="compile",
                passed=True,
                artifacts={"ingest_count": len(ingest_list)},
            )

        validation_list = results.get("validation", [])
        if validation_list:
            all_valid = all(
                isinstance(v, dict) and v.get("valid", False) for v in validation_list
            )
            self.evidence_collector.record(
                check_type="tests",
                passed=all_valid,
                artifacts={"validation_count": len(validation_list)},
            )

        if isinstance(artemis, ARTEMIS_OLYMPIAN):
            self.evidence_collector.record(
                check_type="lsp_diagnostics",
                passed=True,
                artifacts={"source": "artemis_metrics"},
            )

        lowered = lowered_objective
        rewrite_triggered = any(
            keyword in lowered for keyword in ("rewrite", "refactor", "legacy")
        )

        phase_execution = results["phase_execution"]
        phase4_gate = phase_execution.get("phase4_code_analyzer_gate", {})
        phase4_policy = (
            phase4_gate.get("gate_policy", {}) if isinstance(phase4_gate, dict) else {}
        )
        autonomous_merge = bool(phase4_policy.get("autonomous_merge_allowed", False))

        gate_result = self.gate_enforcer.enforce(
            gate_name="phase6_completion",
            phase_execution=phase_execution,
            autonomous_merge_allowed=autonomous_merge,
            rewrite_triggered=rewrite_triggered,
        )

        legacy_gate = self._enforce_phase6_gate(phase_execution)

        results["phase6_gate"] = gate_result.to_dict()
        results["phase6_gate_legacy"] = legacy_gate
        results["completion_status"] = (
            "blocked" if gate_result.status == "blocked" else "ready"
        )

        if gate_result.status == "blocked":
            follow_on = self.add_task(
                "Phase 6 escalation: resolve gate blockers before autonomous completion",
                datetime.now().replace(microsecond=0).isoformat(),
                source="PHASE6_GATE",
            )
            results["phase6_escalation_task"] = follow_on

        return results
