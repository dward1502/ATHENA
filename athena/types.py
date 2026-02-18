"""Shared types for the ATHENA package — enums and dataclasses extracted from athena.py."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(Enum):
    REPO = "repo"
    ARTICLE = "article"
    DOCUMENT = "document"
    WEB = "web"


class AgentStatus(Enum):
    DISCOVERED = "DISCOVERED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    ERROR = "ERROR"


class Priority(Enum):
    ROUTINE = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class MissionStatus(Enum):
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
    STANDBY = "STANDBY"
    DEPLOYING = "DEPLOYING"
    ACTIVE = "ACTIVE"
    RETURNING = "RETURNING"
    OFFLINE = "OFFLINE"


@dataclass
class Objective:
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
    objective: Objective
    components: List[Component]
    olympians_required: List[str]
    estimated_duration: float
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
    source: str
    timestamp: datetime
    message: str
    severity: str = "INFO"
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
    objective: Objective
    status: MissionStatus
    components_completed: List[Component]
    duration: float
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


# ═══════════════════════════════════════════════════════════════════════
# AGENTIZATION & INGESTION TYPES (EnvX / OWL patterns)
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class AgentCard:
    """A2A-compatible card describing a repo-agent's capabilities."""

    name: str
    repo_url: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    entry_points: Dict[str, str] = field(default_factory=dict)
    sampled_files: List[str] = field(default_factory=list)
    signal_tags: List[str] = field(default_factory=list)
    analysis_notes: List[str] = field(default_factory=list)
    language: str = "Unknown"
    license: Optional[str] = None
    status: AgentStatus = AgentStatus.DISCOVERED
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "repo_url": self.repo_url,
            "description": self.description,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "entry_points": self.entry_points,
            "sampled_files": self.sampled_files,
            "signal_tags": self.signal_tags,
            "analysis_notes": self.analysis_notes,
            "language": self.language,
            "license": self.license,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ResearchArticle:
    """A research article ingested from ArXiv or other sources."""

    title: str
    authors: List[str]
    abstract: str
    source_url: str
    source: str  # "arxiv", "web", "pdf"
    published_date: Optional[str] = None
    arxiv_id: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    key_findings: List[str] = field(default_factory=list)
    ingested_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "source_url": self.source_url,
            "source": self.source,
            "published_date": self.published_date,
            "arxiv_id": self.arxiv_id,
            "categories": self.categories,
            "key_findings": self.key_findings,
            "ingested_at": self.ingested_at.isoformat(),
        }


@dataclass
class IngestResult:
    """Result of an ingestion operation (repo agentization or article ingestion)."""

    source_type: SourceType
    source_url: str
    status: str  # "success", "partial", "failed"
    items_ingested: int
    agent_card: Optional[AgentCard] = None
    articles: List[ResearchArticle] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type.value,
            "source_url": self.source_url,
            "status": self.status,
            "items_ingested": self.items_ingested,
            "agent_card": self.agent_card.to_dict() if self.agent_card else None,
            "articles": [a.to_dict() for a in self.articles],
            "errors": self.errors,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RoleContract:
    role_id: str
    capabilities: List[str] = field(default_factory=list)
    tool_allowlist: List[str] = field(default_factory=list)
    handoff_targets: List[str] = field(default_factory=list)
    escalation_policy: str = "ceo"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_id": self.role_id,
            "capabilities": self.capabilities,
            "tool_allowlist": self.tool_allowlist,
            "handoff_targets": self.handoff_targets,
            "escalation_policy": self.escalation_policy,
        }


@dataclass
class TaskContract:
    task_id: str
    objective: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "constraints": self.constraints,
            "inputs": self.inputs,
            "acceptance_criteria": self.acceptance_criteria,
            "status": self.status,
        }


@dataclass
class HandoffContract:
    from_role: str
    to_role: str
    task_id: str
    handoff_reason: str
    required_state: List[str] = field(default_factory=list)
    verification_hooks: List[str] = field(default_factory=list)
    timeout_seconds: int = 1200

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_role": self.from_role,
            "to_role": self.to_role,
            "task_id": self.task_id,
            "handoff_reason": self.handoff_reason,
            "required_state": self.required_state,
            "verification_hooks": self.verification_hooks,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class RetryFallbackContract:
    retry_budget: int = 2
    backoff_policy: str = "linear_15s"
    fallback_sequence: List[str] = field(default_factory=list)
    failure_signature: str = "unclassified"
    last_resort_action: str = "escalate_to_ceo"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retry_budget": self.retry_budget,
            "backoff_policy": self.backoff_policy,
            "fallback_sequence": self.fallback_sequence,
            "failure_signature": self.failure_signature,
            "last_resort_action": self.last_resort_action,
        }


@dataclass
class ObservabilityContract:
    mission_id: str
    step_events: List[str] = field(default_factory=list)
    result_metrics: Dict[str, Any] = field(default_factory=dict)
    resource_metrics: Dict[str, Any] = field(default_factory=dict)
    audit_log_ref: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "step_events": self.step_events,
            "result_metrics": self.result_metrics,
            "resource_metrics": self.resource_metrics,
            "audit_log_ref": self.audit_log_ref,
        }


@dataclass
class CEOContractBundle:
    roles: List[RoleContract] = field(default_factory=list)
    task: Optional[TaskContract] = None
    handoffs: List[HandoffContract] = field(default_factory=list)
    retry_fallback: Optional[RetryFallbackContract] = None
    observability: Optional[ObservabilityContract] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roles": [role.to_dict() for role in self.roles],
            "task": self.task.to_dict() if self.task else None,
            "handoffs": [handoff.to_dict() for handoff in self.handoffs],
            "retry_fallback": (
                self.retry_fallback.to_dict() if self.retry_fallback else None
            ),
            "observability": (
                self.observability.to_dict() if self.observability else None
            ),
        }
