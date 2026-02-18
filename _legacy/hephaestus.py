#!/usr/bin/env python3

import sys
from pathlib import Path
import os
import subprocess

sys.path.append(str(Path(__file__).parent.parent))

from athena import Olympian, Component, DivisionStatus
from typing import List, Dict, Optional, Sequence, Any
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

    def run_stage(
        self,
        command: Sequence[str],
        workdir: Path,
        timeout_seconds: int = 120,
    ) -> Dict[str, Any]:
        started = datetime.now().isoformat()
        try:
            result = subprocess.run(
                list(command),
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            return {
                "command": " ".join(command),
                "workdir": str(workdir),
                "started_at": started,
                "exit_code": result.returncode,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:],
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "command": " ".join(command),
                "workdir": str(workdir),
                "started_at": started,
                "exit_code": 124,
                "stdout": (exc.stdout or "")[-4000:],
                "stderr": (exc.stderr or "")[-4000:],
                "error": "timeout",
            }


class FORGE_MASTER(Titan):
    def __init__(self):
        super().__init__("FORGE_MASTER", "Build and compile pipelines")


class ANVIL(Titan):
    def __init__(self):
        super().__init__("ANVIL", "Container and image assembly")


class EMBER(Titan):
    def __init__(self):
        super().__init__("EMBER", "Deployment and runtime hardening")


class HEPHAESTUS_OLYMPIAN(Olympian):
    def __init__(self):
        super().__init__(name="HEPHAESTUS", domain="Infrastructure & Forge")
        self.forge_master = FORGE_MASTER()
        self.anvil = ANVIL()
        self.ember = EMBER()
        self.titans: List[Titan] = [self.forge_master, self.anvil, self.ember]
        self.logger = logging.getLogger("HEPHAESTUS")
        self.logger.setLevel(logging.INFO)
        self.forge_operations = 0
        self.numenor_path = Path(
            os.getenv("NUMENOR_PATH", str(Path.home() / "Numenor_prime"))
        ).expanduser()
        self.athena_dir = self.numenor_path / "ATHENA"
        self.pipeline_history: List[Dict[str, Any]] = []

    def deploy(self, component: Component) -> bool:
        self.status = DivisionStatus.DEPLOYING
        self.current_mission = component
        titan = self._select_titan(component)
        if titan is None:
            return False

        titan.deploy(component)
        component.status = "IN_PROGRESS"
        component.progress = max(component.progress, 0.2)
        self.forge_operations += 1

        pipeline_result = self._execute_pipeline(titan=titan, component=component)
        if not pipeline_result["success"]:
            component.status = "FAILED"
            component.progress = max(component.progress, 0.7)
            self.status = DivisionStatus.ACTIVE
            self.report_intel(
                f"{titan.name} pipeline failed for {component.name}",
                "ERROR",
                {
                    "titan": titan.name,
                    "component": component.name,
                    "failed_stage": pipeline_result["failed_stage"],
                },
            )
            return False

        component.status = "COMPLETE"
        component.progress = 1.0
        self.report_intel(
            f"{titan.name} pipeline completed for {component.name}",
            "INFO",
            {
                "titan": titan.name,
                "component": component.name,
                "stages": pipeline_result["stages_run"],
            },
        )
        self.status = DivisionStatus.ACTIVE
        return True

    def _execute_pipeline(self, titan: Titan, component: Component) -> Dict[str, Any]:
        stage_commands = self._build_stage_commands(titan=titan, component=component)
        stages_run = 0

        for idx, command in enumerate(stage_commands, start=1):
            stage_result = titan.run_stage(command=command, workdir=self.athena_dir)
            stages_run += 1
            self.pipeline_history.append(
                {
                    "component": component.name,
                    "titan": titan.name,
                    "stage": idx,
                    **stage_result,
                }
            )
            if stage_result["exit_code"] != 0:
                return {
                    "success": False,
                    "failed_stage": idx,
                    "stages_run": stages_run,
                }

            component.progress = min(
                0.9, component.progress + (0.7 / len(stage_commands))
            )

        return {
            "success": True,
            "failed_stage": None,
            "stages_run": stages_run,
        }

    def _build_stage_commands(
        self,
        titan: Titan,
        component: Component,
    ) -> List[Sequence[str]]:
        component_name = component.name.lower()
        commands: List[Sequence[str]] = [
            ["python", "--version"],
            ["tmux", "-V"],
        ]

        if titan is self.forge_master:
            commands.extend(
                [
                    ["python", "-m", "compileall", "-q", str(self.athena_dir)],
                    [
                        "python",
                        str(self.athena_dir / "athena.py"),
                        "--status",
                        "--no-require-core",
                    ],
                ]
            )
        elif titan is self.anvil:
            commands.extend(
                [
                    ["podman", "--version"],
                    ["podman", "pod", "ps"],
                ]
            )
        else:
            commands.extend(
                [
                    ["opencode", "--version"],
                    ["zeptoclaw", "status"],
                ]
            )

        if any(
            keyword in component_name
            for keyword in ["pipeline", "deploy", "infrastructure"]
        ):
            commands.append(
                ["bash", str(self.athena_dir / "scripts" / "preflight_check.sh")]
            )

        return commands

    def _select_titan(self, component: Component) -> Optional[Titan]:
        name = component.name.lower()
        if any(keyword in name for keyword in ["build", "compile", "artifact"]):
            return self.forge_master
        if any(
            keyword in name for keyword in ["podman", "container", "image", "docker"]
        ):
            return self.anvil
        return self.ember
