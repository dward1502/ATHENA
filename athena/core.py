"""ATHENA — Supreme Commander of all agent operations."""

import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from athena.memory.core_client import CoreMemoryClient
from athena.memory.local_client import LocalCoreMemoryClient
from athena.olympians.base import Olympian
from athena.gates import EvidenceCollector, GateEnforcer
from athena.orchestration import ContractDecomposer, HandoffEnforcer, RoleRegistry
from athena.types import (
    BattlePlan,
    Component,
    Intel,
    MissionReport,
    MissionStatus,
    Objective,
    Priority,
)


class ATHENA:
    """Supreme Commander of all agent operations.

    "I am ATHENA. Goddess of wisdom and strategic warfare.
     I do not lose battles. I adapt, learn, and conquer."
    """

    def __init__(
        self,
        garrison_path: str = str(Path.home() / "Eregion" / "athena-garrison"),
        core_base_url: Optional[str] = None,
        core_api_key: Optional[str] = None,
        core_mode: str = "local",
        require_core: bool = False,
        core_score_threshold: float = 0.35,
        core_template_score_threshold: float = 0.5,
        core_refresh_before_plan: bool = True,
        core_refresh_timeout_seconds: int = 8,
    ):
        self.garrison_path = Path(garrison_path)
        self.garrison_path.mkdir(exist_ok=True)

        self.logger = self._setup_logging()

        self.current_objective: Optional[Objective] = None
        self.current_plan: Optional[BattlePlan] = None
        self.mission_status: MissionStatus = MissionStatus.RECEIVED

        self.olympians: Dict[str, Olympian] = {}
        self.knowledge_base = self._load_knowledge_base()
        self.mission_history: List[MissionReport] = []
        self.intel_stream: List[Intel] = []

        self.role_registry = RoleRegistry()
        self.contract_decomposer = ContractDecomposer(self.role_registry)
        self.handoff_enforcer = HandoffEnforcer()
        self.evidence_collector = EvidenceCollector()
        self.gate_enforcer = GateEnforcer(self.evidence_collector)

        self.require_core = require_core
        self.core_score_threshold = max(0.0, min(float(core_score_threshold), 1.0))
        self.core_template_score_threshold = max(
            0.0, min(float(core_template_score_threshold), 1.0)
        )
        self.core_refresh_before_plan = core_refresh_before_plan
        self.core_refresh_timeout_seconds = max(0, int(core_refresh_timeout_seconds))
        self.core_client: Optional[Any] = None
        self._initialize_core(
            core_base_url=core_base_url, core_api_key=core_api_key, core_mode=core_mode
        )

        self.logger.info("ATHENA ONLINE - Strategic command initialized")
        self.logger.info(f"Garrison established at {self.garrison_path}")

    # ── Core memory initialization ────────────────────────────────

    def _initialize_core(
        self,
        core_base_url: Optional[str],
        core_api_key: Optional[str],
        core_mode: Optional[str],
    ):
        mode = (core_mode or os.getenv("CORE_MODE", "local")).strip().lower()

        if mode == "local":
            client = LocalCoreMemoryClient(self.garrison_path / "core_memory.db")
            try:
                client.health_check()
            except Exception as exc:
                if self.require_core:
                    raise RuntimeError(
                        f"Local Core required but unavailable: {exc}"
                    ) from exc
                self.logger.warning(
                    f"Local Core unavailable, continuing without Core persistence: {exc}"
                )
                return
            self.core_client = client
            self.logger.info(f"Core memory connected: local sqlite ({client.db_path})")
            return

        if mode != "cloud":
            if self.require_core:
                raise RuntimeError(f"Unsupported CORE_MODE: {mode}")
            self.logger.warning(
                f"Unsupported CORE_MODE '{mode}'; Core persistence disabled"
            )
            return

        base_url = core_base_url or os.getenv(
            "CORE_API_BASE_URL", "https://core.heysol.ai"
        )
        api_key = core_api_key or os.getenv("CORE_API_KEY")

        if not api_key:
            if self.require_core:
                raise RuntimeError("CORE_API_KEY is required but not set")
            self.logger.warning("CORE_API_KEY not set; Core persistence disabled")
            return

        client = CoreMemoryClient(base_url=base_url, api_key=api_key)
        try:
            client.health_check()
        except RuntimeError as exc:
            if self.require_core:
                raise RuntimeError(f"Core required but unavailable: {exc}") from exc
            self.logger.warning(
                f"Core unavailable, continuing without Core persistence: {exc}"
            )
            return

        self.core_client = client
        self.logger.info(f"Core memory connected: {base_url}")

    def _persist_core_event(self, event_type: str, payload: Dict[str, Any]):
        if not self.core_client:
            if self.require_core:
                raise RuntimeError(
                    "Core persistence required but core client not initialized"
                )
            return

        episode = json.dumps(
            {
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "payload": payload,
            },
            ensure_ascii=True,
        )
        try:
            self.core_client.add_episode(
                episode_body=episode,
                reference_time=datetime.now().isoformat(),
                source="athena",
                metadata={"system": "ATHENA", "event_type": event_type},
            )
        except RuntimeError as exc:
            if self.require_core:
                self.mission_status = MissionStatus.FAILED
                raise RuntimeError(f"Core persistence failed: {exc}") from exc
            self.logger.warning(f"Core persistence failed (non-fatal): {exc}")

    def _retrieve_core_context(self, query: str) -> List[Dict[str, Any]]:
        if not self.core_client:
            if self.require_core:
                raise RuntimeError(
                    "Core retrieval required but core client not initialized"
                )
            return []

        try:
            response = self.core_client.search_knowledge_graph(
                query=query,
                limit=10,
                score_threshold=self.core_score_threshold,
                min_results=1,
            )
        except RuntimeError as exc:
            if self.require_core:
                self.mission_status = MissionStatus.FAILED
                raise RuntimeError(f"Core retrieval failed: {exc}") from exc
            self.logger.warning(f"Core retrieval failed (non-fatal): {exc}")
            return []

        results = response.get("results", []) if isinstance(response, dict) else []
        self.logger.info(f"Core retrieval results: {len(results)}")
        if results:
            self._persist_core_event(
                "core_context_retrieved",
                {
                    "query": query,
                    "result_count": len(results),
                    "top_result_ids": [r.get("id") for r in results[:3]],
                },
            )
        return results

    def refresh_core_ingestion(
        self, timeout_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Poll Core ingestion logs so recent queued events become searchable.

        Safe to call even if Core is unavailable.
        """
        if not self.core_client:
            return {"enabled": False, "pending": 0, "completed": 0, "failed": 0}

        timeout = (
            self.core_refresh_timeout_seconds
            if timeout_seconds is None
            else max(0, int(timeout_seconds))
        )
        deadline = datetime.now().timestamp() + timeout
        last_summary: Dict[str, Any] = {
            "enabled": True,
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
        }

        while True:
            try:
                payload = self.core_client.get_ingestion_logs()
                logs = payload.get("logs", []) if isinstance(payload, dict) else []
                athena_logs = [
                    entry
                    for entry in logs
                    if isinstance(entry, dict)
                    and entry.get("source") in {"athena", "ATHENA"}
                ]
                status_counts: Dict[str, int] = {
                    "pending": 0,
                    "processing": 0,
                    "completed": 0,
                    "failed": 0,
                }
                for log in athena_logs:
                    status = str(log.get("status", "")).lower()
                    if status in status_counts:
                        status_counts[status] += 1
                last_summary = {"enabled": True, **status_counts}
            except RuntimeError as exc:
                if self.require_core:
                    raise RuntimeError(f"Core ingestion refresh failed: {exc}") from exc
                self.logger.warning(f"Core ingestion refresh failed (non-fatal): {exc}")
                return {
                    "enabled": True,
                    "pending": 0,
                    "completed": 0,
                    "failed": 0,
                    "error": str(exc),
                }

            if (last_summary["pending"] + last_summary["processing"]) == 0:
                break
            if datetime.now().timestamp() >= deadline:
                break
            time.sleep(1.0)

        self._persist_core_event("core_ingestion_refreshed", last_summary)
        return last_summary

    # ── Core text extraction and priority weighting ───────────────

    def _extract_core_text(self, item: Dict[str, Any]) -> str:
        if not isinstance(item, dict):
            return ""

        parts = []
        for key in ("content", "episodeBody", "title", "summary", "text"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value)

        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            for value in metadata.values():
                if isinstance(value, str) and value.strip():
                    parts.append(value)

        return " ".join(parts).strip()

    def _apply_core_priority_weighting(
        self,
        components: List[Component],
        core_context: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Component]:
        if not components or not core_context:
            return sorted(components, key=lambda c: (c.priority, c.name))

        type_keywords = {
            "audio": ["audio", "voice", "stt", "tts", "wake word"],
            "frontend": ["ui", "frontend", "dashboard", "react", "design"],
            "backend": ["backend", "service", "fastapi", "flask", "worker"],
            "api": ["api", "integration", "webhook", "discord", "oauth", "grpc"],
            "database": ["database", "sql", "orm", "redis", "schema", "migration"],
            "infrastructure": [
                "podman",
                "deploy",
                "infrastructure",
                "container",
                "systemd",
            ],
            "testing": ["test", "qa", "validation", "coverage", "security"],
        }

        scores: Dict[int, float] = {idx: 0.0 for idx, _ in enumerate(components)}
        for item in core_context:
            text = self._extract_core_text(item).lower()
            if not text:
                continue

            result_score = item.get("score")
            try:
                result_weight = float(result_score) if result_score is not None else 1.0
            except (TypeError, ValueError):
                result_weight = 1.0

            for idx, comp in enumerate(components):
                keywords = type_keywords.get(comp.type, [])
                match_count = sum(
                    1 for term in keywords if re.search(rf"\b{re.escape(term)}\b", text)
                )
                if match_count:
                    scores[idx] += match_count * max(result_weight, 0.25)

        for idx, comp in enumerate(components):
            boost = min(int(scores[idx]), 2)
            comp.priority = max(1, comp.priority - boost)

        weighted = sorted(components, key=lambda c: (c.priority, c.name))
        self._persist_core_event(
            "planning_priority_weighted",
            {
                "components": [
                    {"name": c.name, "type": c.type, "priority": c.priority}
                    for c in weighted
                ]
            },
        )
        return weighted

    def _component_from_dict(self, data: Dict[str, Any]) -> Optional[Component]:
        if not isinstance(data, dict):
            return None
        name = data.get("name")
        comp_type = data.get("type")
        priority = data.get("priority", 2)
        if not isinstance(name, str) or not isinstance(comp_type, str):
            return None
        try:
            prio = int(priority)
        except (TypeError, ValueError):
            prio = 2
        return Component(name=name, type=comp_type, priority=max(1, min(prio, 5)))

    def _extract_component_templates(
        self, core_context: Optional[List[Dict[str, Any]]]
    ) -> List[Component]:
        if not core_context:
            return []

        templates: List[Component] = []
        seen: set[tuple[str, str]] = set()

        def add_component(comp: Optional[Component]):
            if not comp:
                return
            key = (comp.name.lower(), comp.type.lower())
            if key in seen:
                return
            seen.add(key)
            templates.append(comp)

        for item in core_context:
            if not isinstance(item, dict):
                continue
            try:
                item_score = float(item.get("score", 1.0))
            except (TypeError, ValueError):
                item_score = 1.0
            if item_score < self.core_template_score_threshold:
                continue

            if isinstance(item.get("components"), list):
                for entry in item["components"]:
                    add_component(self._component_from_dict(entry))

            metadata = item.get("metadata")
            if isinstance(metadata, dict):
                meta_component = self._component_from_dict(metadata)
                add_component(meta_component)

            # Parse JSON payload blobs (persisted episodes are JSON strings)
            for field_name in ("episodeBody", "content", "text", "summary"):
                blob = item.get(field_name)
                if not isinstance(blob, str) or not blob.strip():
                    continue
                try:
                    parsed_payload = json.loads(blob)
                except (json.JSONDecodeError, TypeError):
                    continue

                if isinstance(parsed_payload, dict):
                    if isinstance(parsed_payload.get("components"), list):
                        for entry in parsed_payload["components"]:
                            add_component(self._component_from_dict(entry))
                    inner_payload = parsed_payload.get("payload")
                    if isinstance(inner_payload, dict):
                        if isinstance(inner_payload.get("components"), list):
                            for entry in inner_payload["components"]:
                                add_component(self._component_from_dict(entry))
                elif isinstance(parsed_payload, list):
                    for entry in parsed_payload:
                        add_component(self._component_from_dict(entry))

        return templates

    def _component_relevant_to_text(
        self, component: Component, combined_text: str
    ) -> bool:
        type_keywords = {
            "audio": ["audio", "voice", "wake", "stt", "tts"],
            "frontend": ["ui", "frontend", "dashboard"],
            "backend": ["backend", "service", "worker"],
            "api": ["api", "integration", "discord", "webhook", "oauth"],
            "database": ["database", "sql", "schema", "storage", "redis"],
            "infrastructure": [
                "deploy",
                "podman",
                "infrastructure",
                "container",
                "systemd",
            ],
            "testing": ["test", "validate", "quality", "coverage", "security"],
        }
        for keyword in component.name.lower().replace("_", " ").split():
            if re.search(rf"\b{re.escape(keyword)}\b", combined_text):
                return True

        for term in type_keywords.get(component.type, []):
            if re.search(rf"\b{re.escape(term)}\b", combined_text):
                return True
        return False

    def _merge_component_templates(
        self,
        base_components: List[Component],
        template_components: List[Component],
        combined_text: str,
    ) -> List[Component]:
        if not template_components:
            return base_components

        merged = list(base_components)
        existing_keys = {(c.name.lower(), c.type.lower()) for c in merged}
        applied = []

        for template in template_components:
            if not self._component_relevant_to_text(template, combined_text):
                continue
            key = (template.name.lower(), template.type.lower())
            if key in existing_keys:
                continue
            merged.append(
                Component(
                    name=template.name,
                    type=template.type,
                    priority=max(1, min(template.priority + 1, 5)),
                )
            )
            existing_keys.add(key)
            applied.append({"name": template.name, "type": template.type})

        if applied:
            self._persist_core_event(
                "planning_templates_applied", {"templates": applied}
            )
        return merged

    # ── Logging and knowledge base ────────────────────────────────

    def _setup_logging(self) -> logging.Logger:
        log_path = self.garrison_path / "athena.log"

        logger = logging.getLogger("ATHENA")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        if logger.handlers:
            logger.handlers.clear()

        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def _load_knowledge_base(self) -> Dict[str, Any]:
        kb_path = self.garrison_path / "knowledge_base.json"
        if kb_path.exists():
            try:
                with open(kb_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                self.logger.warning(
                    f"Knowledge base load failed, reinitializing: {exc}"
                )
        return {"repositories": {}, "patterns": {}, "integrations": {}, "missions": []}

    def _save_knowledge_base(self):
        kb_path = self.garrison_path / "knowledge_base.json"
        with open(kb_path, "w") as f:
            json.dump(self.knowledge_base, f, indent=2)

    # ── Command interface ─────────────────────────────────────────

    def receive_objective(
        self,
        description: str,
        deadline: datetime,
        priority: Priority = Priority.NORMAL,
        constraints: Optional[Dict[str, Any]] = None,
        success_criteria: Optional[List[str]] = None,
    ) -> str:
        self.logger.info("=" * 70)
        self.logger.info("NEW OBJECTIVE RECEIVED FROM COMMANDER")
        self.logger.info("=" * 70)

        objective = Objective(
            description=description,
            deadline=deadline,
            priority=priority,
            constraints=constraints or {},
            success_criteria=success_criteria or [],
        )

        self.current_objective = objective
        self.mission_status = MissionStatus.RECEIVED
        self._persist_core_event("objective_received", objective.to_dict())

        self.logger.info(f"Description: {description}")
        self.logger.info(f"Deadline: {deadline}")
        self.logger.info(f"Priority: {priority.name}")
        self.logger.info("=" * 70)

        self._analyze_objective()

        return f"ATHENA-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    def _analyze_objective(self):
        self.logger.info("ANALYZING OBJECTIVE...")
        self.mission_status = MissionStatus.ANALYZING

        if self.core_refresh_before_plan:
            self.refresh_core_ingestion()
        objective = self.current_objective
        if objective is None:
            self.mission_status = MissionStatus.FAILED
            self.logger.error("Objective missing during analysis")
            return

        core_context = self._retrieve_core_context(objective.description)
        components = self._decompose_objective(objective, core_context=core_context)

        self.logger.info(f"Identified {len(components)} components")
        for comp in components:
            self.logger.info(f"  - {comp.name} ({comp.type})")

        self._create_battle_plan(components)

    def _decompose_objective(
        self,
        objective: Objective,
        core_context: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Component]:
        components = self.contract_decomposer.decompose(
            objective, core_context=core_context
        )

        context_text = " ".join(
            [
                self._extract_core_text(item)
                for item in (core_context or [])
                if isinstance(item, dict)
            ]
        ).lower()
        combined_text = f"{objective.description.lower()} {context_text}".strip()

        templates = self._extract_component_templates(core_context)
        components = self._merge_component_templates(
            components, templates, combined_text
        )

        if not components and templates:
            components = templates[:6]

        return self._apply_core_priority_weighting(
            components, core_context=core_context
        )

    def _create_battle_plan(self, components: List[Component]):
        self.logger.info("CREATING BATTLE PLAN...")
        self.mission_status = MissionStatus.PLANNING

        olympians_needed = self._determine_olympians(components)
        estimated_hours = len(components) * 2.0

        risk = self._assess_risks(components)

        objective = self.current_objective
        if objective is None:
            self.mission_status = MissionStatus.FAILED
            self.logger.error("Cannot create battle plan without objective")
            return

        plan = BattlePlan(
            objective=objective,
            components=components,
            olympians_required=olympians_needed,
            estimated_duration=estimated_hours,
            risk_assessment=risk,
        )

        self.current_plan = plan
        self._persist_core_event("battle_plan_created", plan.to_dict())

        self.logger.info("Battle plan created")
        self.logger.info(f"  Olympians required: {', '.join(olympians_needed)}")
        self.logger.info(f"  Estimated duration: {estimated_hours:.1f} hours")
        self.logger.info(f"  Risk assessment: {risk}")

        self._deploy_olympians()

    def _determine_olympians(self, components: List[Component]) -> List[str]:
        olympians: set[str] = set()

        type_mapping = {
            "audio": "APOLLO",
            "frontend": "APOLLO",
            "backend": "ARES",
            "api": "HERMES",
            "database": "ARES",
            "infrastructure": "HEPHAESTUS",
            "testing": "ARTEMIS",
        }

        for comp in components:
            if comp.type in type_mapping:
                olympians.add(type_mapping[comp.type])

        olympians.add("ARTEMIS")

        return sorted(list(olympians))

    def _assess_risks(self, components: List[Component]) -> str:
        num_components = len(components)

        if num_components > 10:
            return "HIGH - Complex integration required"
        elif num_components > 5:
            return "MODERATE - Multiple components to coordinate"
        else:
            return "LOW - Straightforward implementation"

    def _deploy_olympians(self):
        self.logger.info("DEPLOYING OLYMPIAN DIVISIONS...")
        self.mission_status = MissionStatus.DEPLOYING

        if not self.current_plan or not self.current_plan.components:
            self.mission_status = MissionStatus.FAILED
            self.logger.error("No components available for deployment")
            return

        successful_deployments = 0
        for olympian_name in self.current_plan.olympians_required:
            effective_name = olympian_name
            if olympian_name not in self.olympians:
                fallback = self._resolve_olympian_fallback(olympian_name)
                if fallback:
                    effective_name = fallback
                    self.logger.warning(
                        f"  {olympian_name} unavailable, using fallback {fallback}"
                    )

            if effective_name in self.olympians:
                olympian = self.olympians[effective_name]
                relevant_components = [
                    c
                    for c in self.current_plan.components
                    if c.assigned_to is None
                    and (
                        self._component_matches_domain(c, olympian.domain)
                        or self._component_matches_olympian_name(c, olympian_name)
                    )
                ]

                if relevant_components:
                    self.logger.info(
                        f"  Deploying {effective_name} for {len(relevant_components)} components"
                    )
                    for comp in relevant_components:
                        deployed = olympian.deploy(comp)
                        if deployed:
                            comp.assigned_to = effective_name
                            comp.status = "IN_PROGRESS"
                            comp.progress = max(comp.progress, 0.1)
                            successful_deployments += 1
            else:
                self.logger.warning(
                    f"  {olympian_name} not available - needs to be registered"
                )

        if successful_deployments == 0:
            self.mission_status = MissionStatus.FAILED
            self.logger.error("No successful component deployments")
            return

        self.mission_status = MissionStatus.IN_PROGRESS
        self._persist_core_event(
            "deployment_started",
            {
                "successful_deployments": successful_deployments,
                "required_olympians": self.current_plan.olympians_required
                if self.current_plan
                else [],
                "components": [
                    c.to_dict()
                    for c in (self.current_plan.components if self.current_plan else [])
                ],
            },
        )
        self.logger.info(
            f"Olympians deployed ({successful_deployments} components assigned)"
        )

    def _resolve_olympian_fallback(self, olympian_name: str) -> Optional[str]:
        fallback_order = {
            "HERMES": ["ARES", "APOLLO"],
            "HEPHAESTUS": ["ARES", "APOLLO"],
        }
        for candidate in fallback_order.get(olympian_name, []):
            if candidate in self.olympians:
                return candidate
        return None

    def _component_matches_domain(self, component: Component, domain: str) -> bool:
        domain_mappings = {
            "Backend Warfare": ["backend", "api", "database"],
            "Frontend & Creative": ["frontend", "ui", "audio"],
            "Infrastructure & Forge": ["infrastructure", "devops", "deployment"],
            "Communications & Integration": ["api", "integration"],
            "Testing & Quality": ["testing", "validation"],
        }

        return component.type in domain_mappings.get(domain, [])

    def _component_matches_olympian_name(
        self, component: Component, olympian_name: str
    ) -> bool:
        type_mapping = {
            "audio": "APOLLO",
            "frontend": "APOLLO",
            "backend": "ARES",
            "api": "HERMES",
            "database": "ARES",
            "infrastructure": "HEPHAESTUS",
            "testing": "ARTEMIS",
        }
        return type_mapping.get(component.type) == olympian_name

    # ── Olympian management ───────────────────────────────────────

    def register_olympian(self, olympian: Olympian):
        self.olympians[olympian.name] = olympian
        self.logger.info(f"Registered {olympian.name} - {olympian.domain}")

    def register_default_olympians(self):
        loaded = []
        for module_name, class_name in [
            ("athena.olympians.apollo", "APOLLO_OLYMPIAN"),
            ("athena.olympians.ares", "ARES_OLYMPIAN"),
            ("athena.olympians.artemis", "ARTEMIS_OLYMPIAN"),
            ("athena.olympians.hermes", "HERMES_OLYMPIAN"),
            ("athena.olympians.hephaestus", "HEPHAESTUS_OLYMPIAN"),
        ]:
            try:
                module = __import__(module_name, fromlist=[class_name])
                olympian_cls = getattr(module, class_name)
                olympian = olympian_cls()
                self.register_olympian(olympian)
                loaded.append(olympian.name)
            except Exception as exc:
                self.logger.warning(f"Could not auto-register {class_name}: {exc}")
        if loaded:
            self.logger.info(f"Auto-registered Olympians: {', '.join(sorted(loaded))}")

    def deploy_olympian(self, name: str, component: Component) -> bool:
        if name not in self.olympians:
            self.logger.error(f"{name} not found in Olympian roster")
            return False

        olympian = self.olympians[name]
        return olympian.deploy(component)

    def recall_olympian(self, name: str):
        if name in self.olympians:
            self.olympians[name].cease_operations()
            self.logger.info(f"{name} recalled")

    # ── Intel and monitoring ──────────────────────────────────────

    def receive_intel(self, intel: Intel):
        self.intel_stream.append(intel)

        severity_emoji = {
            "INFO": "i",
            "WARNING": "!",
            "ERROR": "X",
            "CRITICAL": "!!",
        }

        emoji = severity_emoji.get(intel.severity, "?")
        self.logger.info(f"[{emoji}] INTEL from {intel.source}: {intel.message}")

        if intel.severity == "CRITICAL":
            self._handle_critical_intel(intel)

    def _handle_critical_intel(self, intel: Intel):
        self.logger.warning("CRITICAL SITUATION - Evaluating response...")

    def generate_sitrep(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("ATHENA SITUATION REPORT")
        lines.append("=" * 70)

        if self.current_objective:
            lines.append(f"Mission: {self.current_objective.description}")
            lines.append(f"Status: {self.mission_status.name}")
            lines.append(f"Deadline: {self.current_objective.deadline}")
            lines.append(f"Priority: {self.current_objective.priority.name}")
        else:
            lines.append("Status: STANDBY - No active mission")

        lines.append("=" * 70)
        lines.append("OLYMPIAN DIVISIONS:")

        for name, olympian in self.olympians.items():
            status = olympian.get_status()
            lines.append(f"\n{name}: {status['status']}")
            if status["current_mission"]:
                lines.append(f"  Mission: {status['current_mission']}")
            lines.append(f"  Titans deployed: {status['titans_deployed']}")

        if self.current_plan:
            lines.append("\n" + "=" * 70)
            lines.append("COMPONENTS:")
            for comp in self.current_plan.components:
                status_icon = "+" if comp.status == "COMPLETE" else "~"
                lines.append(
                    f"{status_icon} {comp.name} ({comp.status}) - {comp.progress:.0%}"
                )

        lines.append("=" * 70)

        return "\n".join(lines)

    # ── Mission completion ────────────────────────────────────────

    def complete_mission(
        self, lessons_learned: Optional[List[str]] = None, force: bool = False
    ):
        if not self.current_objective:
            self.logger.warning("No active mission to complete")
            return None

        incomplete_count = 0
        if self.current_plan:
            incomplete = [
                c for c in self.current_plan.components if c.status != "COMPLETE"
            ]
            incomplete_count = len(incomplete)

        gate_result = self.gate_enforcer.enforce_mission_completion(
            incomplete_components=incomplete_count,
            force=force,
        )

        if gate_result.status == "blocked":
            self.mission_status = MissionStatus.VALIDATING
            self.logger.warning(
                "Mission completion blocked by gate: %s",
                gate_result.blocked_reasons,
            )
            self._persist_core_event(
                "mission_completion_blocked",
                gate_result.to_dict(),
            )
            return None

        self.logger.info("=" * 70)
        self.logger.info("MISSION COMPLETE")
        self.logger.info("=" * 70)

        duration = (
            datetime.now() - self.current_objective.received_at
        ).total_seconds() / 3600

        report = MissionReport(
            objective=self.current_objective,
            status=MissionStatus.COMPLETE,
            components_completed=self.current_plan.components
            if self.current_plan
            else [],
            duration=duration,
            resources_used={"olympians": len(self.olympians)},
            lessons_learned=lessons_learned or [],
        )

        self.mission_history.append(report)
        self.mission_status = MissionStatus.COMPLETE
        self._persist_core_event("mission_completed", report.to_dict())

        self._update_knowledge_base(report)

        self.logger.info(f"Duration: {duration:.2f} hours")
        self.logger.info(f"Components completed: {len(report.components_completed)}")
        self.logger.info("=" * 70)

        return report

    def _update_knowledge_base(self, report: MissionReport):
        self.knowledge_base["missions"].append(report.to_dict())
        self._save_knowledge_base()
        self.logger.info("Knowledge base updated")
