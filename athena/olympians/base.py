"""Shared base classes for all Olympian divisions — single source of truth."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from athena.types import Component, DivisionStatus, Intel


AVAILABLE_MODELS = {
    "opus": "anthropic/claude-opus-4-6",
    "sonnet": "anthropic/claude-sonnet-4-6",
    "qwen-72b": "qwen/qwen3.5-72b",
    "qwen-14b": "qwen/qwen3.5-14b",
    "qwen-7b": "qwen/qwen3.5-7b",
    "qwen-3b": "qwen/qwen3.5-3b",
}


@dataclass
class TitanReport:
    titan_name: str
    status: str
    progress: float
    message: str
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now()


class Titan:
    def __init__(self, name: str, specialty: str, model: str = "qwen-14b"):
        self.name = name
        self.specialty = specialty
        self.model = AVAILABLE_MODELS.get(model, model)
        self.status = "STANDBY"
        self.current_task: Optional[Component] = None
        self.progress: float = 0.0

    def deploy(self, component: Component) -> TitanReport:
        self.status = "ACTIVE"
        self.current_task = component
        self.progress = 0.5
        return TitanReport(
            titan_name=self.name,
            status="DEPLOYED",
            progress=self.progress,
            message=f"{self.name} deployed for {component.name}",
        )

    def get_status(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "specialty": self.specialty,
            "status": self.status,
            "model": self.model,
            "current_task": self.current_task.name if self.current_task else None,
            "progress": self.progress,
        }


class Olympian:
    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain
        self.status = DivisionStatus.STANDBY
        self.current_mission: Optional[Component] = None
        self.titans: List[Titan] = []
        self.intel_stream: List[Intel] = []
        self.missions_completed: int = 0

    def deploy(self, component: Component) -> bool:
        self.status = DivisionStatus.DEPLOYING
        self.current_mission = component
        titan = self._select_titan(component)
        if titan is None:
            self.report_intel(f"No titan available for {component.name}", "WARNING")
            self.status = DivisionStatus.ACTIVE
            return False
        titan.deploy(component)
        component.status = "IN_PROGRESS"
        component.progress = max(component.progress, 0.2)
        self.status = DivisionStatus.ACTIVE
        return True

    def _select_titan(self, component: Component) -> Optional[Titan]:
        if self.titans:
            return self.titans[0]
        return None

    def cease_operations(self) -> None:
        self.status = DivisionStatus.RETURNING
        for titan in self.titans:
            titan.status = "STANDBY"
            titan.current_task = None
        self.current_mission = None

    def report_intel(
        self,
        message: str,
        severity: str = "INFO",
        data: Optional[Dict[str, Any]] = None,
    ) -> Intel:
        report = Intel(
            source=self.name,
            timestamp=datetime.now(),
            message=message,
            severity=severity,
            data=data or {},
        )
        self.intel_stream.append(report)
        return report

    def get_status(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "domain": self.domain,
            "status": self.status.value,
            "current_mission": (
                self.current_mission.name if self.current_mission else None
            ),
            "missions_completed": self.missions_completed,
            "titans_deployed": len([t for t in self.titans if t.status == "ACTIVE"]),
            "titans": [t.get_status() for t in self.titans],
            "intel_count": len(self.intel_stream),
        }

    def get_tactical_report(self) -> Dict[str, object]:
        return {
            "division": self.name,
            "domain": self.domain,
            "status": self.status.value,
            "titan_count": len(self.titans),
            "titan_reports": [t.get_status() for t in self.titans],
            "intel_summary": [
                {"message": i.message, "severity": i.severity}
                for i in self.intel_stream[-10:]
            ],
        }
