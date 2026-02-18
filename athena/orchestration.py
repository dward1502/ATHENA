"""W1 Orchestration Intelligence — contract-driven decomposition, handoff enforcement, retry execution.

Integrates patterns from Alexandria W1 sources (AutoGen, crewAI, Swarms) into
ATHENA's mission planning and execution flow.  Contracts are defined in
athena.types; this module makes them *govern* execution rather than just
describe it.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

from athena.types import (
    Component,
    HandoffContract,
    Objective,
    RetryFallbackContract,
    RoleContract,
)

logger = logging.getLogger("ATHENA.orchestration")

# ═══════════════════════════════════════════════════════════════════════
# ROLE REGISTRY
# ═══════════════════════════════════════════════════════════════════════


class RoleRegistry:
    """Canonical role definitions from the Phase 1 contract map.

    Provides lookup by role_id, capability matching against objective text,
    and handoff-target resolution.
    """

    # Default roles derived from Phase 1 AutoGen + crewAI contract mapping.
    _DEFAULT_ROLES: List[Dict[str, Any]] = [
        {
            "role_id": "ceo",
            "capabilities": ["objective_management", "escalation"],
            "tool_allowlist": ["ceo_bridge", "task_queue", "reports"],
            "handoff_targets": ["planner", "validator"],
            "escalation_policy": "ceo",
        },
        {
            "role_id": "planner",
            "capabilities": ["decomposition", "routing_plan"],
            "tool_allowlist": ["alexandria_pipeline", "model_router"],
            "handoff_targets": ["executor", "auditor"],
            "escalation_policy": "ceo",
        },
        {
            "role_id": "executor",
            "capabilities": ["ingest", "delegated_execution"],
            "tool_allowlist": ["apollo", "hermes", "mesh_delegation"],
            "handoff_targets": ["validator"],
            "escalation_policy": "planner",
        },
        {
            "role_id": "validator",
            "capabilities": ["ingest_validation", "quality_gate"],
            "tool_allowlist": ["artemis", "mesh_assessment"],
            "handoff_targets": ["ceo"],
            "escalation_policy": "ceo",
        },
        {
            "role_id": "auditor",
            "capabilities": ["metrics_review", "risk_review"],
            "tool_allowlist": ["reports", "ledger"],
            "handoff_targets": ["ceo"],
            "escalation_policy": "ceo",
        },
    ]

    # Keywords that activate each role when found in objective text.
    _ROLE_ACTIVATION_KEYWORDS: Dict[str, List[str]] = {
        "ceo": ["objective", "escalat", "manage", "oversee", "govern"],
        "planner": [
            "plan",
            "decompos",
            "orchestrat",
            "route",
            "strateg",
            "breakdown",
        ],
        "executor": [
            "ingest",
            "repo",
            "scout",
            "deploy",
            "infra",
            "build",
            "execute",
            "implement",
            "container",
            "podman",
        ],
        "validator": [
            "validat",
            "test",
            "quality",
            "gate",
            "check",
            "verify",
            "lint",
            "diagnos",
        ],
        "auditor": [
            "audit",
            "metric",
            "report",
            "ledger",
            "cost",
            "joule",
            "review",
        ],
    }

    def __init__(self) -> None:
        self._roles: Dict[str, RoleContract] = {}
        for role_def in self._DEFAULT_ROLES:
            contract = RoleContract(
                role_id=role_def["role_id"],
                capabilities=list(role_def["capabilities"]),
                tool_allowlist=list(role_def["tool_allowlist"]),
                handoff_targets=list(role_def["handoff_targets"]),
                escalation_policy=role_def["escalation_policy"],
            )
            self._roles[contract.role_id] = contract

    def get_role(self, role_id: str) -> Optional[RoleContract]:
        """Return the contract for *role_id*, or ``None``."""
        return self._roles.get(role_id)

    def all_roles(self) -> List[RoleContract]:
        """Return every registered role."""
        return list(self._roles.values())

    def handoff_targets(self, from_role: str) -> List[str]:
        """Return allowed handoff targets for *from_role*."""
        role = self._roles.get(from_role)
        return list(role.handoff_targets) if role else []

    def roles_for_objective(self, objective_text: str) -> List[RoleContract]:
        """Return roles whose activation keywords match *objective_text*.

        The *validator* role is always included (mirrors ARTEMIS-always logic).
        """
        lowered = objective_text.lower()
        activated: Dict[str, RoleContract] = {}

        for role_id, keywords in self._ROLE_ACTIVATION_KEYWORDS.items():
            for kw in keywords:
                if kw in lowered:
                    role = self._roles.get(role_id)
                    if role:
                        activated[role_id] = role
                    break

        # Validator is always active (same as ARTEMIS-always in core).
        validator = self._roles.get("validator")
        if validator:
            activated.setdefault("validator", validator)

        return list(activated.values())


# ═══════════════════════════════════════════════════════════════════════
# CONTRACT-DRIVEN DECOMPOSER
# ═══════════════════════════════════════════════════════════════════════

# Maps (role_id, keyword_fragment) → (component_name, component_type, priority).
_ROLE_COMPONENT_MAP: List[Dict[str, Any]] = [
    {
        "role_id": "planner",
        "keywords": ["orchestrat", "decompos", "plan", "strateg", "route"],
        "component": ("mission_decomposition", "backend", 1),
    },
    {
        "role_id": "executor",
        "keywords": ["ingest", "repo", "scout", "github", "arxiv", "url"],
        "component": ("source_ingestion", "api", 1),
    },
    {
        "role_id": "executor",
        "keywords": ["deploy", "infra", "container", "podman", "systemd"],
        "component": ("deployment_pipeline", "infrastructure", 2),
    },
    {
        "role_id": "executor",
        "keywords": ["backend", "service", "api", "worker"],
        "component": ("service_layer", "backend", 1),
    },
    {
        "role_id": "executor",
        "keywords": ["discord", "webhook", "integration"],
        "component": ("integration_bridge", "api", 2),
    },
    {
        "role_id": "validator",
        "keywords": [],  # Always active — no keyword needed.
        "component": ("validation_suite", "testing", 2),
    },
    {
        "role_id": "auditor",
        "keywords": ["audit", "metric", "report", "ledger", "cost"],
        "component": ("audit_reporting", "backend", 3),
    },
]

# Heuristic keyword groups preserved from the original _decompose_objective.
_HEURISTIC_GROUPS: List[Dict[str, Any]] = [
    {
        "keywords": ["voice", "audio", "wake word"],
        "components": [
            ("wake_word_detection", "audio", 1),
            ("speech_to_text", "audio", 1),
            ("text_to_speech", "audio", 1),
            ("intent_recognition", "frontend", 2),
        ],
    },
    {
        "keywords": ["api", "backend", "service"],
        "components": [
            ("api_gateway", "api", 1),
            ("service_layer", "backend", 1),
        ],
    },
    {
        "keywords": ["database", "data", "storage"],
        "components": [("data_modeling", "database", 2)],
    },
    {
        "keywords": ["ui", "frontend", "dashboard"],
        "components": [("ui_shell", "frontend", 2)],
    },
    {
        "keywords": ["deploy", "podman", "infrastructure"],
        "components": [("deployment_pipeline", "infrastructure", 2)],
    },
    {
        "keywords": ["discord", "webhook", "integration"],
        "components": [("integration_bridge", "api", 2)],
    },
    {
        "keywords": ["test", "validate", "quality"],
        "components": [("validation_suite", "testing", 2)],
    },
]


class ContractDecomposer:
    """Decomposes an Objective into Components using role-contract analysis.

    Uses the RoleRegistry to determine which roles are activated for a given
    objective, then maps activated roles to concrete Components.  Falls back
    to heuristic keyword matching (the original logic) when contract-based
    decomposition yields nothing.
    """

    def __init__(self, registry: RoleRegistry) -> None:
        self._registry = registry

    # ── public API ────────────────────────────────────────────────

    def decompose(
        self,
        objective: Objective,
        core_context: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Component]:
        """Return a deduplicated, priority-sorted list of Components."""
        desc = objective.description.lower()
        context_text = self._flatten_core_context(core_context)
        combined = f"{desc} {context_text}".strip()

        # Phase A — contract-driven decomposition.
        contract_components = self._contract_pass(combined)

        # Phase B — heuristic keyword supplement.
        heuristic_components = self._heuristic_pass(combined)

        # Merge: contract results first, heuristic fills gaps.
        merged = self._merge(contract_components, heuristic_components)

        # Fallback if both passes are empty.
        if not merged:
            merged = [
                Component("core_implementation", "backend", 1),
                Component("integration_bridge", "api", 2),
                Component("validation_suite", "testing", 2),
            ]

        return sorted(merged, key=lambda c: (c.priority, c.name))

    # ── internal ──────────────────────────────────────────────────

    @staticmethod
    def _flatten_core_context(
        core_context: Optional[List[Dict[str, Any]]],
    ) -> str:
        if not core_context:
            return ""
        parts: List[str] = []
        for item in core_context:
            if not isinstance(item, dict):
                continue
            for key in ("content", "episodeBody", "title", "summary", "text"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    parts.append(value)
        return " ".join(parts).lower()

    def _contract_pass(self, combined_text: str) -> List[Component]:
        """Use role activation + role-component map to produce Components."""
        activated_roles = self._registry.roles_for_objective(combined_text)
        activated_ids = {r.role_id for r in activated_roles}

        components: List[Component] = []
        seen: set[tuple[str, str]] = set()

        for entry in _ROLE_COMPONENT_MAP:
            role_id: str = entry["role_id"]
            if role_id not in activated_ids:
                continue
            keywords: List[str] = entry["keywords"]
            name, comp_type, priority = entry["component"]

            # If entry has no keywords it fires unconditionally (e.g. validator).
            if keywords and not any(kw in combined_text for kw in keywords):
                continue

            key = (name, comp_type)
            if key not in seen:
                seen.add(key)
                components.append(Component(name, comp_type, priority))

        return components

    @staticmethod
    def _heuristic_pass(combined_text: str) -> List[Component]:
        """Original keyword-group heuristic from core.py."""
        components: List[Component] = []

        def has_any(terms: List[str]) -> bool:
            return any(
                re.search(rf"\b{re.escape(term)}\b", combined_text) for term in terms
            )

        for group in _HEURISTIC_GROUPS:
            if has_any(group["keywords"]):
                for name, comp_type, priority in group["components"]:
                    components.append(Component(name, comp_type, priority))

        return components

    @staticmethod
    def _merge(
        primary: List[Component],
        secondary: List[Component],
    ) -> List[Component]:
        """Merge two component lists, deduplicating by (name, type)."""
        merged: List[Component] = []
        seen: set[tuple[str, str]] = set()
        for comp in primary + secondary:
            key = (comp.name.lower(), comp.type.lower())
            if key not in seen:
                seen.add(key)
                merged.append(comp)
        return merged


# ═══════════════════════════════════════════════════════════════════════
# HANDOFF ENFORCER
# ═══════════════════════════════════════════════════════════════════════


class HandoffEnforcer:
    """Validates handoff preconditions before allowing role transitions.

    Inspired by crewAI/AutoGen handoff patterns: every role boundary must
    have its required_state artifacts present and verification_hooks named.
    """

    @staticmethod
    def validate_handoff(
        handoff: HandoffContract,
        available_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check that *handoff.required_state* keys exist in *available_state*.

        Returns a validation dict with ``valid``, ``missing_state``, and
        ``missing_hooks`` fields.
        """
        missing_state = [
            key for key in handoff.required_state if key not in available_state
        ]
        missing_hooks = [
            hook for hook in handoff.verification_hooks if not hook or not hook.strip()
        ]
        return {
            "valid": len(missing_state) == 0 and len(missing_hooks) == 0,
            "from_role": handoff.from_role,
            "to_role": handoff.to_role,
            "task_id": handoff.task_id,
            "missing_state": missing_state,
            "missing_hooks": missing_hooks,
        }

    @staticmethod
    def enforce_or_escalate(
        handoff: HandoffContract,
        available_state: Dict[str, Any],
        registry: RoleRegistry,
    ) -> Dict[str, Any]:
        """Validate a handoff; escalate when preconditions are unmet.

        Returns either ``{"status": "proceed", ...}`` or
        ``{"status": "escalate", ...}`` with escalation target derived
        from the *from_role*'s escalation_policy.
        """
        result = HandoffEnforcer.validate_handoff(handoff, available_state)

        if result["valid"]:
            return {
                "status": "proceed",
                "from_role": handoff.from_role,
                "to_role": handoff.to_role,
                "task_id": handoff.task_id,
            }

        from_role = registry.get_role(handoff.from_role)
        escalation_target = from_role.escalation_policy if from_role else "ceo"

        logger.warning(
            "Handoff %s -> %s blocked: missing_state=%s, missing_hooks=%s. "
            "Escalating to %s.",
            handoff.from_role,
            handoff.to_role,
            result["missing_state"],
            result["missing_hooks"],
            escalation_target,
        )

        return {
            "status": "escalate",
            "from_role": handoff.from_role,
            "to_role": handoff.to_role,
            "task_id": handoff.task_id,
            "escalation_target": escalation_target,
            "missing_state": result["missing_state"],
            "missing_hooks": result["missing_hooks"],
        }


# ═══════════════════════════════════════════════════════════════════════
# RETRY EXECUTOR
# ═══════════════════════════════════════════════════════════════════════

# Backoff strategies: name → (base_seconds, multiplier).
_BACKOFF_STRATEGIES: Dict[str, tuple[float, float]] = {
    "linear_15s": (15.0, 1.0),
    "linear_30s": (30.0, 1.0),
    "exponential_5s": (5.0, 2.0),
    "none": (0.0, 1.0),
}


class RetryExecutor:
    """Execute a callable with retry/fallback governed by RetryFallbackContract.

    Implements retry budgets, configurable backoff, and ordered fallback
    sequences derived from the Swarms/AutoGen retry patterns.
    """

    @staticmethod
    def execute_with_retry(
        contract: RetryFallbackContract,
        action: Any,  # Callable[[], Any]
        action_label: str = "action",
    ) -> Dict[str, Any]:
        """Run *action* up to ``contract.retry_budget + 1`` times.

        Parameters
        ----------
        contract:
            Retry policy governing budget, backoff, and fallback.
        action:
            A zero-argument callable.  Should return a result dict on success
            or raise an exception on failure.
        action_label:
            Human-readable label for logging.

        Returns
        -------
        dict with ``status`` (``"success"`` | ``"exhausted"``),
        ``attempts``, ``last_error``, and ``result`` (on success).
        """
        budget = max(0, contract.retry_budget)
        base_delay, multiplier = _BACKOFF_STRATEGIES.get(
            contract.backoff_policy, (15.0, 1.0)
        )

        last_error = ""
        for attempt in range(budget + 1):
            try:
                result = action()
                return {
                    "status": "success",
                    "attempts": attempt + 1,
                    "result": result,
                    "last_error": "",
                }
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Retry %d/%d for %s failed: %s",
                    attempt + 1,
                    budget + 1,
                    action_label,
                    last_error,
                )
                if attempt < budget:
                    delay = base_delay * (multiplier**attempt)
                    if delay > 0:
                        time.sleep(delay)

        return {
            "status": "exhausted",
            "attempts": budget + 1,
            "result": None,
            "last_error": last_error,
            "fallback_sequence": list(contract.fallback_sequence),
            "last_resort_action": contract.last_resort_action,
            "failure_signature": contract.failure_signature,
        }

    @staticmethod
    def select_fallback(
        contract: RetryFallbackContract,
        failed_targets: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Return the next fallback target not in *failed_targets*."""
        excluded = set(failed_targets or [])
        for candidate in contract.fallback_sequence:
            if candidate not in excluded:
                return candidate
        return None
