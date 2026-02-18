#!/usr/bin/env python3
"""
ATHENA - Autonomous Tactical Harvesting & Execution Network Architecture
Supreme Commander - Orchestrates all agent divisions

"Wisdom through warfare. Victory through code."
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
import argparse
import json
import logging
import os
import re
import sqlite3
import uuid
from pathlib import Path
from urllib import error, request
from urllib.parse import urlencode


# ═══════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════


class Priority(Enum):
    """Mission priority levels"""

    ROUTINE = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class MissionStatus(Enum):
    """Current state of mission"""

    RECEIVED = "RECEIVED"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    DEPLOYING = "DEPLOYING"
    IN_PROGRESS = "IN_PROGRESS"
    VALIDATING = "VALIDATING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class DivisionStatus(Enum):
    """Status of Olympian divisions"""

    STANDBY = "STANDBY"
    DEPLOYING = "DEPLOYING"
    ACTIVE = "ACTIVE"
    RETURNING = "RETURNING"
    OFFLINE = "OFFLINE"


# ═══════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Objective:
    """Mission objective from human commander"""

    description: str
    deadline: datetime
    priority: Priority
    constraints: Dict[str, Any] = field(default_factory=dict)
    success_criteria: List[str] = field(default_factory=list)
    received_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "deadline": self.deadline.isoformat(),
            "priority": self.priority.name,
            "constraints": self.constraints,
            "success_criteria": self.success_criteria,
            "received_at": self.received_at.isoformat(),
        }


@dataclass
class Component:
    """Individual component to be built/harvested"""

    name: str
    type: str
    priority: int
    dependencies: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    status: str = "PENDING"
    progress: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "assigned_to": self.assigned_to,
            "status": self.status,
            "progress": self.progress,
        }


@dataclass
class BattlePlan:
    """Strategic plan for achieving objective"""

    objective: Objective
    components: List[Component]
    olympians_required: List[str]
    estimated_duration: float  # hours
    risk_assessment: str
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective.to_dict(),
            "components": [c.to_dict() for c in self.components],
            "olympians_required": self.olympians_required,
            "estimated_duration": self.estimated_duration,
            "risk_assessment": self.risk_assessment,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Intel:
    """Intelligence report from field operations"""

    source: str  # Which division/agent
    timestamp: datetime
    message: str
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "severity": self.severity,
            "data": self.data,
        }


@dataclass
class MissionReport:
    """Final report on mission outcome"""

    objective: Objective
    status: MissionStatus
    components_completed: List[Component]
    duration: float  # hours
    resources_used: Dict[str, Any]
    lessons_learned: List[str]
    completed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective.to_dict(),
            "status": self.status.name,
            "components_completed": [c.to_dict() for c in self.components_completed],
            "duration": self.duration,
            "resources_used": self.resources_used,
            "lessons_learned": self.lessons_learned,
            "completed_at": self.completed_at.isoformat(),
        }


class CoreMemoryClient:
    """Minimal RedPlanet Core API client."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(
        self, method: str, path: str, payload: Optional[Dict[str, Any]] = None
    ):
        url = f"{self.base_url}{path}"
        data = None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = request.Request(
            url=url, data=data, method=method.upper(), headers=headers
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Core API HTTP {exc.code} at {path}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(
                f"Core API network error at {path}: {exc.reason}"
            ) from exc

    def health_check(self):
        return self._request("GET", "/api/profile")

    def get_ingestion_logs(self, params: Optional[Dict[str, Any]] = None):
        path = "/api/v1/logs"
        if params:
            query = urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                path = f"{path}?{query}"
        return self._request("GET", path)

    def get_specific_log(self, log_id: str):
        return self._request("GET", f"/api/v1/logs/{log_id}")

    def add_episode(
        self,
        episode_body: str,
        reference_time: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        label_ids: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ):
        payload: Dict[str, Any] = {
            "episodeBody": episode_body,
            "referenceTime": reference_time,
            "source": source,
            "metadata": metadata or {},
        }
        if label_ids is not None:
            payload["labelIds"] = label_ids
        if session_id:
            payload["sessionId"] = session_id
        return self._request("POST", "/api/v1/add", payload)

    def search_knowledge_graph(
        self,
        query: str,
        limit: int = 20,
        score_threshold: float = 0.4,
        min_results: int = 1,
    ):
        payload = {
            "query": query,
            "limit": limit,
            "scoreThreshold": score_threshold,
            "minResults": min_results,
        }
        return self._request("POST", "/api/v1/search", payload)


class LocalCoreMemoryClient:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _initialize_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    episode_body TEXT NOT NULL,
                    reference_time TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    label_ids TEXT NOT NULL,
                    session_id TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'completed'
                )
                """
            )

    def health_check(self):
        return {
            "status": "ok",
            "mode": "local",
            "db_path": str(self.db_path),
        }

    def get_ingestion_logs(self, params: Optional[Dict[str, Any]] = None):
        limit = 100
        if params and params.get("limit") is not None:
            try:
                limit = max(1, int(params["limit"]))
            except (TypeError, ValueError):
                limit = 100

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, source, status, reference_time, created_at, session_id
                FROM episodes
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        logs = [
            {
                "id": row["id"],
                "source": row["source"],
                "status": row["status"],
                "reference_time": row["reference_time"],
                "created_at": row["created_at"],
                "session_id": row["session_id"],
            }
            for row in rows
        ]
        return {"logs": logs}

    def get_specific_log(self, log_id: str):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source, status, reference_time, created_at, session_id
                FROM episodes
                WHERE id = ?
                """,
                (log_id,),
            ).fetchone()

        if row is None:
            raise RuntimeError(f"Log not found: {log_id}")

        return {
            "id": row["id"],
            "source": row["source"],
            "status": row["status"],
            "reference_time": row["reference_time"],
            "created_at": row["created_at"],
            "session_id": row["session_id"],
        }

    def add_episode(
        self,
        episode_body: str,
        reference_time: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        label_ids: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ):
        episode_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO episodes (
                    id, episode_body, reference_time, source,
                    metadata, label_ids, session_id, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed')
                """,
                (
                    episode_id,
                    episode_body,
                    reference_time,
                    source,
                    json.dumps(metadata or {}, ensure_ascii=True),
                    json.dumps(label_ids or [], ensure_ascii=True),
                    session_id,
                    now,
                ),
            )

        return {"success": True, "id": episode_id}

    def search_knowledge_graph(
        self,
        query: str,
        limit: int = 20,
        score_threshold: float = 0.4,
        min_results: int = 1,
    ):
        terms = [term.lower() for term in re.findall(r"[a-zA-Z0-9_]+", query)]
        if not terms:
            return {"results": []}

        like_pattern = "%" + "%".join(terms[:3]) + "%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, episode_body, reference_time, source, metadata, label_ids, session_id, created_at
                FROM episodes
                WHERE lower(episode_body) LIKE ?
                ORDER BY created_at DESC
                LIMIT 500
                """,
                (like_pattern.lower(),),
            ).fetchall()

        scored = []
        total_terms = len(terms)
        for row in rows:
            body = (row["episode_body"] or "").lower()
            matches = sum(1 for term in terms if term in body)
            if matches == 0:
                continue
            score = matches / total_terms
            if score < score_threshold:
                continue

            metadata = {}
            if row["metadata"]:
                try:
                    metadata = json.loads(row["metadata"])
                except json.JSONDecodeError:
                    metadata = {}

            scored.append(
                {
                    "id": row["id"],
                    "score": score,
                    "episodeBody": row["episode_body"],
                    "referenceTime": row["reference_time"],
                    "source": row["source"],
                    "metadata": metadata,
                    "sessionId": row["session_id"],
                    "createdAt": row["created_at"],
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        results = scored[: max(1, limit)]
        if len(results) < min_results:
            return {"results": []}
        return {"results": results}


# ═══════════════════════════════════════════════════════════════════════
# OLYMPIAN BASE CLASS
# ═══════════════════════════════════════════════════════════════════════


class Olympian:
    """Base class for domain commanders"""

    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain
        self.status = DivisionStatus.STANDBY
        self.titans: List[Any] = []
        self.current_mission: Optional[Component] = None
        self.intel_log: List[Intel] = []

    def deploy(self, component: Component) -> bool:
        """Deploy this division for a specific component"""
        self.status = DivisionStatus.DEPLOYING
        self.current_mission = component
        self.report_intel(f"Deploying for {component.name}", "INFO")
        # Override in subclasses
        return True

    def report_intel(
        self,
        message: str,
        severity: str = "INFO",
        data: Optional[Dict[str, Any]] = None,
    ):
        """Send intelligence report to ATHENA"""
        intel = Intel(
            source=f"OLYMPIAN:{self.name}",
            timestamp=datetime.now(),
            message=message,
            severity=severity,
            data=data or {},
        )
        self.intel_log.append(intel)
        return intel

    def get_status(self) -> Dict[str, Any]:
        """Return current status"""
        return {
            "name": self.name,
            "domain": self.domain,
            "status": self.status.name,
            "current_mission": self.current_mission.name
            if self.current_mission
            else None,
            "titans_deployed": len(self.titans),
            "recent_intel": [i.to_dict() for i in self.intel_log[-5:]],
        }

    def cease_operations(self):
        """Recall this division"""
        self.status = DivisionStatus.RETURNING
        self.report_intel("Ceasing operations, returning to base", "INFO")


# ═══════════════════════════════════════════════════════════════════════
# ATHENA SUPREME COMMANDER
# ═══════════════════════════════════════════════════════════════════════


class ATHENA:
    """
    Supreme Commander of all agent operations

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

        # Initialize logging
        self.logger = self._setup_logging()

        # Command state
        self.current_objective: Optional[Objective] = None
        self.current_plan: Optional[BattlePlan] = None
        self.mission_status: MissionStatus = MissionStatus.RECEIVED

        # Olympian Council (domain commanders)
        self.olympians: Dict[str, Olympian] = {}

        # Knowledge base
        self.knowledge_base = self._load_knowledge_base()

        # Mission history
        self.mission_history: List[MissionReport] = []

        # Intel stream
        self.intel_stream: List[Intel] = []

        # Core memory integration
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

        self.logger.info("⚔️  ATHENA ONLINE - Strategic command initialized")
        self.logger.info(f"📍 Garrison established at {self.garrison_path}")

    def _initialize_core(
        self,
        core_base_url: Optional[str],
        core_api_key: Optional[str],
        core_mode: Optional[str],
    ):
        """Initialize RedPlanet Core memory client."""
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
            self.logger.info(
                f"🧠 Core memory connected: local sqlite ({client.db_path})"
            )
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
        self.logger.info(f"🧠 Core memory connected: {base_url}")

    def _persist_core_event(self, event_type: str, payload: Dict[str, Any]):
        """Persist mission event to RedPlanet Core."""
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
        """Retrieve relevant memories from Core to guide planning."""
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
        self.logger.info(f"🧠 Core retrieval results: {len(results)}")
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
        """
        Poll Core ingestion logs briefly so recent queued events become searchable.
        Returns summary stats and is safe to call even if Core is unavailable.
        """
        if not self.core_client:
            return {"enabled": False, "pending": 0, "completed": 0, "failed": 0}

        timeout = (
            self.core_refresh_timeout_seconds
            if timeout_seconds is None
            else max(0, int(timeout_seconds))
        )
        deadline = datetime.now().timestamp() + timeout
        last_summary = {
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
                    l
                    for l in logs
                    if isinstance(l, dict) and l.get("source") in {"athena", "ATHENA"}
                ]
                status_counts = {
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
            # Small polling delay; keep standard library only.
            import time  # local import to keep module surface minimal

            time.sleep(1.0)

        self._persist_core_event("core_ingestion_refreshed", last_summary)
        return last_summary

    def _extract_core_text(self, item: Dict[str, Any]) -> str:
        """Extract textual payload from a Core search result item."""
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
        """Adjust component priority based on retrieved Core context."""
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

        scores = {idx: 0.0 for idx, _ in enumerate(components)}
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
            boost = min(int(scores[idx]), 2)  # cap so priority stays predictable
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
        """Build a Component from dict-like data if possible."""
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
        """Extract reusable component templates from Core search results."""
        if not core_context:
            return []

        templates: List[Component] = []
        seen = set()

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

            # Direct structure in search result
            if isinstance(item.get("components"), list):
                for entry in item["components"]:
                    add_component(self._component_from_dict(entry))

            # Component hints in metadata
            metadata = item.get("metadata")
            if isinstance(metadata, dict):
                meta_component = self._component_from_dict(metadata)
                add_component(meta_component)

            # Parse JSON payload blobs (our persisted episodes are JSON strings)
            for field_name in ("episodeBody", "content", "text", "summary"):
                blob = item.get(field_name)
                if not isinstance(blob, str) or not blob.strip():
                    continue
                try:
                    payload = json.loads(blob)
                except (json.JSONDecodeError, TypeError):
                    continue

                if isinstance(payload, dict):
                    if isinstance(payload.get("components"), list):
                        for entry in payload["components"]:
                            add_component(self._component_from_dict(entry))
                    inner_payload = payload.get("payload")
                    if isinstance(inner_payload, dict):
                        if isinstance(inner_payload.get("components"), list):
                            for entry in inner_payload["components"]:
                                add_component(self._component_from_dict(entry))
                elif isinstance(payload, list):
                    for entry in payload:
                        add_component(self._component_from_dict(entry))

        return templates

    def _component_relevant_to_text(
        self, component: Component, combined_text: str
    ) -> bool:
        """Determine whether a template component is relevant to objective/context text."""
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
        """Merge Core templates into planning components based on relevance."""
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

    def _setup_logging(self) -> logging.Logger:
        """Configure logging system"""
        log_path = self.garrison_path / "athena.log"

        logger = logging.getLogger("ATHENA")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        if logger.handlers:
            logger.handlers.clear()

        # File handler
        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.DEBUG)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
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
        """Load tactical knowledge base"""
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
        """Persist knowledge base"""
        kb_path = self.garrison_path / "knowledge_base.json"
        with open(kb_path, "w") as f:
            json.dump(self.knowledge_base, f, indent=2)

    # ═══════════════════════════════════════════════════════════════
    # COMMAND INTERFACE
    # ═══════════════════════════════════════════════════════════════

    def receive_objective(
        self,
        description: str,
        deadline: datetime,
        priority: Priority = Priority.NORMAL,
        constraints: Optional[Dict[str, Any]] = None,
        success_criteria: Optional[List[str]] = None,
    ) -> str:
        """
        Receive mission objective from human commander

        Args:
            description: What needs to be accomplished
            deadline: When it must be complete
            priority: Mission priority level
            constraints: Any limitations or requirements
            success_criteria: How to measure success

        Returns:
            Mission ID
        """
        self.logger.info("=" * 70)
        self.logger.info("🎯 NEW OBJECTIVE RECEIVED FROM COMMANDER")
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

        # Immediately begin analysis
        self._analyze_objective()

        return f"ATHENA-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    def _analyze_objective(self):
        """Analyze objective and break down into components"""
        self.logger.info("🔍 ANALYZING OBJECTIVE...")
        self.mission_status = MissionStatus.ANALYZING

        # This is where we'd use LLM to break down the objective
        # For now, demonstration logic

        if self.core_refresh_before_plan:
            self.refresh_core_ingestion()
        objective = self.current_objective
        if objective is None:
            self.mission_status = MissionStatus.FAILED
            self.logger.error("Objective missing during analysis")
            return

        core_context = self._retrieve_core_context(objective.description)
        components = self._decompose_objective(objective, core_context=core_context)

        self.logger.info(f"✓ Identified {len(components)} components")
        for comp in components:
            self.logger.info(f"  - {comp.name} ({comp.type})")

        # Create battle plan
        self._create_battle_plan(components)

    def _decompose_objective(
        self,
        objective: Objective,
        core_context: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Component]:
        """
        Break objective into tactical components

        TODO: Use LLM to intelligently decompose based on objective description
        """
        # Heuristic decomposition fallback until model-driven planner is wired in.
        components = []
        desc = objective.description.lower()
        context_text = " ".join(
            [
                self._extract_core_text(item)
                for item in (core_context or [])
                if isinstance(item, dict)
            ]
        ).lower()
        combined_text = f"{desc} {context_text}".strip()

        def has_any(terms: List[str]) -> bool:
            return any(
                re.search(rf"\b{re.escape(term)}\b", combined_text) for term in terms
            )

        if has_any(["voice", "audio", "wake word"]):
            components.extend(
                [
                    Component("wake_word_detection", "audio", 1),
                    Component("speech_to_text", "audio", 1),
                    Component("text_to_speech", "audio", 1),
                    Component("intent_recognition", "frontend", 2),
                ]
            )

        if has_any(["api", "backend", "service"]):
            components.extend(
                [
                    Component("api_gateway", "api", 1),
                    Component("service_layer", "backend", 1),
                ]
            )

        if has_any(["database", "data", "storage"]):
            components.append(Component("data_modeling", "database", 2))

        if has_any(["ui", "frontend", "dashboard"]):
            components.append(Component("ui_shell", "frontend", 2))

        if has_any(["deploy", "podman", "infrastructure"]):
            components.append(Component("deployment_pipeline", "infrastructure", 2))

        if has_any(["discord", "webhook", "integration"]):
            components.append(Component("integration_bridge", "api", 2))

        if has_any(["test", "validate", "quality"]):
            components.append(Component("validation_suite", "testing", 2))

        if not components:
            components = [
                Component("core_implementation", "backend", 1),
                Component("integration_bridge", "api", 2),
                Component("validation_suite", "testing", 2),
            ]

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
        """Develop strategic battle plan"""
        self.logger.info("📋 CREATING BATTLE PLAN...")
        self.mission_status = MissionStatus.PLANNING

        # Determine which Olympians are needed
        olympians_needed = self._determine_olympians(components)

        # Estimate duration
        estimated_hours = len(components) * 2.0  # Placeholder

        # Assess risks
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

        self.logger.info(f"✓ Battle plan created")
        self.logger.info(f"  Olympians required: {', '.join(olympians_needed)}")
        self.logger.info(f"  Estimated duration: {estimated_hours:.1f} hours")
        self.logger.info(f"  Risk assessment: {risk}")

        # Automatically deploy
        self._deploy_olympians()

    def _determine_olympians(self, components: List[Component]) -> List[str]:
        """Determine which Olympian divisions are needed"""
        olympians = set()

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

        # Always include ARTEMIS for validation
        olympians.add("ARTEMIS")

        return sorted(list(olympians))

    def _assess_risks(self, components: List[Component]) -> str:
        """Assess mission risks"""
        num_components = len(components)

        if num_components > 10:
            return "HIGH - Complex integration required"
        elif num_components > 5:
            return "MODERATE - Multiple components to coordinate"
        else:
            return "LOW - Straightforward implementation"

    def _deploy_olympians(self):
        """Deploy Olympian divisions"""
        self.logger.info("🚀 DEPLOYING OLYMPIAN DIVISIONS...")
        self.mission_status = MissionStatus.DEPLOYING

        if not self.current_plan or not self.current_plan.components:
            self.mission_status = MissionStatus.FAILED
            self.logger.error("❌ No components available for deployment")
            return

        successful_deployments = 0
        for olympian_name in self.current_plan.olympians_required:
            effective_name = olympian_name
            if olympian_name not in self.olympians:
                fallback = self._resolve_olympian_fallback(olympian_name)
                if fallback:
                    effective_name = fallback
                    self.logger.warning(
                        f"  ⚠️  {olympian_name} unavailable, using fallback {fallback}"
                    )

            if effective_name in self.olympians:
                olympian = self.olympians[effective_name]
                # Assign components to this olympian
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
                    f"  ⚠️  {olympian_name} not available - needs to be registered"
                )

        if successful_deployments == 0:
            self.mission_status = MissionStatus.FAILED
            self.logger.error("❌ No successful component deployments")
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
            f"✓ Olympians deployed ({successful_deployments} components assigned)"
        )

    def _resolve_olympian_fallback(self, olympian_name: str) -> Optional[str]:
        """Fallback routing for divisions not yet implemented in this repo."""
        fallback_order = {
            "HERMES": ["ARES", "APOLLO"],
            "HEPHAESTUS": ["ARES", "APOLLO"],
        }
        for candidate in fallback_order.get(olympian_name, []):
            if candidate in self.olympians:
                return candidate
        return None

    def _component_matches_domain(self, component: Component, domain: str) -> bool:
        """Check if component belongs to domain"""
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
        """Check component type against expected olympian role mapping."""
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

    # ═══════════════════════════════════════════════════════════════
    # OLYMPIAN MANAGEMENT
    # ═══════════════════════════════════════════════════════════════

    def register_olympian(self, olympian: Olympian):
        """Register an Olympian division"""
        self.olympians[olympian.name] = olympian
        self.logger.info(f"✓ Registered {olympian.name} - {olympian.domain}")

    def register_default_olympians(self):
        """Register built-in Olympians available in this repository."""
        loaded = []
        for module_name, class_name in [
            ("apollo", "APOLLO_OLYMPIAN"),
            ("ares", "ARES_OLYMPIAN"),
            ("artemis", "ARTEMIS_OLYMPIAN"),
            ("hermes", "HERMES_OLYMPIAN"),
            ("hephaestus", "HEPHAESTUS_OLYMPIAN"),
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
        """Deploy specific Olympian for component"""
        if name not in self.olympians:
            self.logger.error(f"❌ {name} not found in Olympian roster")
            return False

        olympian = self.olympians[name]
        return olympian.deploy(component)

    def recall_olympian(self, name: str):
        """Recall Olympian division"""
        if name in self.olympians:
            self.olympians[name].cease_operations()
            self.logger.info(f"↩️  {name} recalled")

    # ═══════════════════════════════════════════════════════════════
    # INTEL & MONITORING
    # ═══════════════════════════════════════════════════════════════

    def receive_intel(self, intel: Intel):
        """Receive intelligence report from field"""
        self.intel_stream.append(intel)

        severity_emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🔥"}

        emoji = severity_emoji.get(intel.severity, "📡")
        self.logger.info(f"{emoji} INTEL from {intel.source}: {intel.message}")

        # React to critical intel
        if intel.severity == "CRITICAL":
            self._handle_critical_intel(intel)

    def _handle_critical_intel(self, intel: Intel):
        """Handle critical intelligence"""
        self.logger.warning("🔥 CRITICAL SITUATION - Evaluating response...")
        # Placeholder for crisis response logic

    def generate_sitrep(self) -> str:
        """Generate situation report"""
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
                lines.append(f"  └─ Mission: {status['current_mission']}")
            lines.append(f"  └─ Titans deployed: {status['titans_deployed']}")

        if self.current_plan:
            lines.append("\n" + "=" * 70)
            lines.append("COMPONENTS:")
            for comp in self.current_plan.components:
                status_icon = "✓" if comp.status == "COMPLETE" else "⋯"
                lines.append(
                    f"{status_icon} {comp.name} ({comp.status}) - {comp.progress:.0%}"
                )

        lines.append("=" * 70)

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════
    # MISSION COMPLETION
    # ═══════════════════════════════════════════════════════════════

    def complete_mission(
        self, lessons_learned: Optional[List[str]] = None, force: bool = False
    ):
        """Mark mission as complete and generate report"""
        if not self.current_objective:
            self.logger.warning("No active mission to complete")
            return

        if self.current_plan and not force:
            incomplete = [
                c for c in self.current_plan.components if c.status != "COMPLETE"
            ]
            if incomplete:
                self.mission_status = MissionStatus.VALIDATING
                self.logger.warning(
                    f"Mission completion blocked: {len(incomplete)} components not COMPLETE"
                )
                return None

        self.logger.info("=" * 70)
        self.logger.info("🎖️  MISSION COMPLETE")
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

        # Update knowledge base
        self._update_knowledge_base(report)

        self.logger.info(f"Duration: {duration:.2f} hours")
        self.logger.info(f"Components completed: {len(report.components_completed)}")
        self.logger.info("=" * 70)

        return report

    def _update_knowledge_base(self, report: MissionReport):
        """Update knowledge base with mission learnings"""
        self.knowledge_base["missions"].append(report.to_dict())
        self._save_knowledge_base()
        self.logger.info("📚 Knowledge base updated")


# ═══════════════════════════════════════════════════════════════════════
# COMMAND LINE INTERFACE
# ═══════════════════════════════════════════════════════════════════════


class AthenaCommander:
    """Human interface to ATHENA"""

    def __init__(self, athena: ATHENA):
        self.athena = athena

    def issue_objective(self, objective: str, deadline: str, priority: str = "NORMAL"):
        """Issue mission to ATHENA"""
        try:
            deadline_dt = datetime.fromisoformat(deadline)
        except ValueError as exc:
            raise ValueError(f"Invalid deadline format: {deadline}") from exc

        try:
            priority_enum = Priority[priority.upper()]
        except KeyError as exc:
            allowed = ", ".join([p.name for p in Priority])
            raise ValueError(
                f"Invalid priority '{priority}'. Allowed: {allowed}"
            ) from exc

        mission_id = self.athena.receive_objective(
            description=objective, deadline=deadline_dt, priority=priority_enum
        )

        return mission_id

    def status_report(self) -> str:
        """Get current battle status"""
        return self.athena.generate_sitrep()

    def recall_division(self, olympian: str):
        """Recall specific division"""
        self.athena.recall_olympian(olympian)


# ═══════════════════════════════════════════════════════════════════════
# DEMO / TEST
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ATHENA command interface")
    parser.add_argument("--objective", help="Mission objective to execute")
    parser.add_argument(
        "--deadline", help="Deadline in ISO format, e.g. 2026-02-19T23:59:59"
    )
    parser.add_argument(
        "--priority", default="NORMAL", help="ROUTINE|NORMAL|HIGH|CRITICAL|EMERGENCY"
    )
    parser.add_argument(
        "--garrison-path",
        default=os.getenv(
            "ATHENA_GARRISON_PATH", str(Path.home() / "Eregion" / "athena-garrison")
        ),
        help="ATHENA garrison path",
    )
    parser.add_argument(
        "--core-mode",
        default=os.getenv("CORE_MODE", "local"),
        choices=["local", "cloud"],
        help="Core persistence mode: local sqlite or cloud API",
    )
    parser.add_argument(
        "--core-base-url", default=None, help="RedPlanet Core API base URL"
    )
    parser.add_argument(
        "--core-api-key",
        default=None,
        help="RedPlanet Core API key (or CORE_API_KEY env)",
    )
    parser.add_argument(
        "--core-score-threshold",
        type=float,
        default=float(os.getenv("ATHENA_CORE_SCORE_THRESHOLD", "0.35")),
        help="Minimum Core search score for retrieval candidates (0.0-1.0)",
    )
    parser.add_argument(
        "--core-template-score-threshold",
        type=float,
        default=float(os.getenv("ATHENA_CORE_TEMPLATE_SCORE_THRESHOLD", "0.50")),
        help="Minimum Core result score to apply template components (0.0-1.0)",
    )
    parser.add_argument(
        "--core-refresh-timeout",
        type=int,
        default=int(os.getenv("ATHENA_CORE_REFRESH_TIMEOUT", "8")),
        help="Seconds to poll Core ingestion logs before planning",
    )
    parser.add_argument(
        "--core-refresh-before-plan",
        action="store_true",
        default=os.getenv("ATHENA_CORE_REFRESH_BEFORE_PLAN", "1").strip()
        not in {"0", "false", "False"},
        help="Refresh Core ingestion logs before planning",
    )
    parser.add_argument(
        "--no-core-refresh-before-plan",
        action="store_false",
        dest="core_refresh_before_plan",
        help="Disable Core ingestion refresh before planning",
    )
    parser.add_argument(
        "--require-core",
        action="store_true",
        default=os.getenv("ATHENA_REQUIRE_CORE", "1").strip()
        not in {"0", "false", "False"},
        help="Fail fast if RedPlanet Core is unavailable",
    )
    parser.add_argument(
        "--no-require-core",
        action="store_false",
        dest="require_core",
        help="Allow operation without Core (for local testing only)",
    )
    parser.add_argument(
        "--status", action="store_true", help="Print current SITREP and exit"
    )
    parser.add_argument(
        "--no-auto-register",
        action="store_true",
        help="Disable automatic registration of APOLLO/ARES/ARTEMIS if available",
    )
    args = parser.parse_args()

    try:
        athena = ATHENA(
            garrison_path=args.garrison_path,
            core_base_url=args.core_base_url,
            core_api_key=args.core_api_key,
            core_mode=args.core_mode,
            require_core=args.require_core,
            core_score_threshold=args.core_score_threshold,
            core_template_score_threshold=args.core_template_score_threshold,
            core_refresh_before_plan=args.core_refresh_before_plan,
            core_refresh_timeout_seconds=args.core_refresh_timeout,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(3) from exc
    if not args.no_auto_register:
        athena.register_default_olympians()
    commander = AthenaCommander(athena)

    if args.status:
        print(commander.status_report())
        raise SystemExit(0)

    if not args.objective:
        parser.error("--objective is required unless --status is used")

    deadline = args.deadline or datetime.now().replace(microsecond=0).isoformat()

    try:
        mission_id = commander.issue_objective(
            objective=args.objective,
            deadline=deadline,
            priority=args.priority,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2) from exc

    print(mission_id)
    print(commander.status_report())
