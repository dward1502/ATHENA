#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from athena import Olympian, Component, DivisionStatus
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class TitanReport:
    titan_name: str
    status: str
    progress: float
    message: str
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class Titan:
    def __init__(self, name: str, specialty: str):
        self.name = name
        self.specialty = specialty
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
            "current_task": self.current_task.name if self.current_task else None,
            "progress": self.progress,
        }


class IRIS(Titan):
    def __init__(self):
        super().__init__("IRIS", "Webhook & event relays")


class HERMES_BUS(Titan):
    def __init__(self):
        super().__init__("HERMES_BUS", "API integration routing")


class COURIER(Titan):
    def __init__(self):
        super().__init__("COURIER", "Session and message transport")


class HERMES_OLYMPIAN(Olympian):
    def __init__(self):
        super().__init__(name="HERMES", domain="Communications & Integration")
        self.iris = IRIS()
        self.hermes_bus = HERMES_BUS()
        self.courier = COURIER()
        self.titans: List[Titan] = [self.iris, self.hermes_bus, self.courier]
        self.logger = logging.getLogger("HERMES")
        self.logger.setLevel(logging.INFO)
        self.relay_operations = 0

    def deploy(self, component: Component) -> bool:
        self.status = DivisionStatus.DEPLOYING
        self.current_mission = component
        titan = self._select_titan(component)
        if titan is None:
            return False

        titan.deploy(component)
        component.status = "IN_PROGRESS"
        component.progress = max(component.progress, 0.4)
        self.relay_operations += 1
        self.report_intel(
            f"{titan.name} deployed for {component.name}",
            "INFO",
            {"titan": titan.name, "component": component.name},
        )
        self.status = DivisionStatus.ACTIVE
        return True

    def _select_titan(self, component: Component) -> Optional[Titan]:
        name = component.name.lower()
        if any(keyword in name for keyword in ["webhook", "event", "trigger"]):
            return self.iris
        if any(
            keyword in name
            for keyword in ["session", "message", "channel", "transport"]
        ):
            return self.courier
        return self.hermes_bus
