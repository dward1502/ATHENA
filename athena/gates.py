"""W3 Quality Gates — evidence-based gate enforcement and phase-6 hardening.

Integrates patterns from Alexandria W3 source (forcedotcom/code-analyzer) into
ATHENA's mission completion path.  Gates are no longer status-flag checks —
they require collected execution evidence before allowing autonomous completion.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ATHENA.gates")


@dataclass
class GateEvidence:
    check_type: str
    passed: bool
    artifacts: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_type": self.check_type,
            "passed": self.passed,
            "artifacts": self.artifacts,
            "error": self.error,
        }


@dataclass
class GateResult:
    status: str  # "pass" | "blocked"
    blocked_reasons: List[str] = field(default_factory=list)
    escalation_path: List[str] = field(default_factory=list)
    next_action: str = ""
    evidence_summary: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "blocked_reasons": self.blocked_reasons,
            "escalation_path": self.escalation_path,
            "next_action": self.next_action,
            "evidence_summary": self.evidence_summary,
        }


GATE_REQUIRED_CHECKS: Dict[str, List[str]] = {
    "phase4_code_analyzer_gate": ["lsp_diagnostics", "tests", "compile"],
    "phase5_code_archeologist_precheck": [
        "history_pattern_scan",
        "hotspot_identification",
        "blast_radius_estimation",
    ],
    "phase6_completion": ["lsp_diagnostics", "tests", "compile"],
}


class EvidenceCollector:
    """Accumulates gate evidence during mission execution."""

    def __init__(self) -> None:
        self._evidence: List[GateEvidence] = []

    def record(
        self,
        check_type: str,
        passed: bool,
        artifacts: Optional[Dict[str, Any]] = None,
        error: str = "",
    ) -> GateEvidence:
        entry = GateEvidence(
            check_type=check_type,
            passed=passed,
            artifacts=artifacts or {},
            error=error,
        )
        self._evidence.append(entry)
        return entry

    def evidence_for(self, check_type: str) -> List[GateEvidence]:
        return [e for e in self._evidence if e.check_type == check_type]

    def has_passing(self, check_type: str) -> bool:
        return any(e.passed for e in self.evidence_for(check_type))

    def all_evidence(self) -> List[GateEvidence]:
        return list(self._evidence)

    def summary(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._evidence]

    def clear(self) -> None:
        self._evidence.clear()


class GateEnforcer:
    """Validates collected evidence against gate policies.

    Phase-6 enforcement blocks autonomous completion when required evidence
    is missing or failing — even if status flags say "ready".
    """

    def __init__(self, collector: EvidenceCollector) -> None:
        self._collector = collector

    def enforce(
        self,
        gate_name: str,
        phase_execution: Optional[Dict[str, Any]] = None,
        autonomous_merge_allowed: bool = False,
        rewrite_triggered: bool = False,
    ) -> GateResult:
        required_checks = GATE_REQUIRED_CHECKS.get(gate_name, [])
        blocked_reasons: List[str] = []

        for check in required_checks:
            evidence = self._collector.evidence_for(check)
            if not evidence:
                blocked_reasons.append(f"missing_evidence:{check}")
            elif not any(e.passed for e in evidence):
                blocked_reasons.append(f"failed_evidence:{check}")

        if not autonomous_merge_allowed:
            blocked_reasons.append("autonomous_merge_not_allowed")

        if rewrite_triggered:
            precheck_checks = GATE_REQUIRED_CHECKS.get(
                "phase5_code_archeologist_precheck", []
            )
            for check in precheck_checks:
                if not self._collector.has_passing(check):
                    blocked_reasons.append(f"archeologist_precheck_missing:{check}")

        if phase_execution and isinstance(phase_execution, dict):
            for phase_key in (
                "phase4_code_analyzer_gate",
                "phase5_code_archeologist_precheck",
            ):
                phase_data = phase_execution.get(phase_key, {})
                if isinstance(phase_data, dict) and phase_data.get("status") != "ready":
                    reason = f"{phase_key}_not_ready"
                    if reason not in blocked_reasons:
                        blocked_reasons.append(reason)

        if blocked_reasons:
            return GateResult(
                status="blocked",
                blocked_reasons=blocked_reasons,
                escalation_path=["validator", "auditor", "ceo"],
                next_action="escalate_to_ceo_and_hold_autonomous_completion",
                evidence_summary=self._collector.summary(),
            )

        return GateResult(
            status="pass",
            blocked_reasons=[],
            escalation_path=[],
            next_action="allow_autonomous_completion",
            evidence_summary=self._collector.summary(),
        )

    def enforce_mission_completion(
        self,
        incomplete_components: int,
        force: bool = False,
    ) -> GateResult:
        """Gate check for ATHENA.complete_mission() — consults evidence."""
        blocked_reasons: List[str] = []

        if incomplete_components > 0 and not force:
            blocked_reasons.append(f"incomplete_components:{incomplete_components}")

        for check in GATE_REQUIRED_CHECKS.get("phase6_completion", []):
            evidence = self._collector.evidence_for(check)
            if not evidence:
                blocked_reasons.append(f"no_completion_evidence:{check}")
            elif not any(e.passed for e in evidence):
                blocked_reasons.append(f"completion_evidence_failed:{check}")

        if blocked_reasons and not force:
            logger.warning("Mission completion blocked by gate: %s", blocked_reasons)
            return GateResult(
                status="blocked",
                blocked_reasons=blocked_reasons,
                escalation_path=["validator", "ceo"],
                next_action="resolve_gate_blockers_before_completion",
                evidence_summary=self._collector.summary(),
            )

        return GateResult(
            status="pass",
            blocked_reasons=[],
            escalation_path=[],
            next_action="allow_completion",
            evidence_summary=self._collector.summary(),
        )
