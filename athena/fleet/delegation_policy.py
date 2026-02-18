from dataclasses import dataclass
from typing import Dict, List, Optional

from athena.fleet.mesh_discovery import MeshNode
from athena.fleet.node_registry import NodeRegistry


SCOUT_KEYWORDS = (
    "scout",
    "search",
    "research",
    "github",
    "repo",
    "article",
    "paper",
    "arxiv",
    "crawl",
)

AUDIT_KEYWORDS = (
    "audit",
    "code audit",
    "security audit",
    "repo audit",
    "codebase audit",
)


@dataclass
class DelegationDecision:
    mode: str
    target: str
    reason: str
    fallback: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "mode": self.mode,
            "target": self.target,
            "reason": self.reason,
            "fallback": self.fallback,
        }


class Pi5DelegationPolicy:
    ROLE_HINTS = (
        "scout",
        "intel",
        "research",
        "crawler",
        "watch",
        "analysis",
    )

    def recommend(
        self,
        objective: str,
        mesh_nodes: List[MeshNode],
        node_registry: Optional[NodeRegistry] = None,
    ) -> DelegationDecision:
        lower = objective.lower()
        is_scout_work = any(keyword in lower for keyword in SCOUT_KEYWORDS)
        is_audit_work = any(keyword in lower for keyword in AUDIT_KEYWORDS)

        if is_scout_work or is_audit_work:
            pi5_nodes = [n for n in mesh_nodes if n.is_pi5 and n.reachable]
            if pi5_nodes:
                chosen = pi5_nodes[0]
                return DelegationDecision(
                    mode="mesh_pi5",
                    target=chosen.tailscale_host,
                    reason="Scout/audit objective matched reachable Pi5 node",
                    fallback="local_fleet_scout",
                )

            role_matched_mesh_nodes = [
                n
                for n in mesh_nodes
                if n.reachable
                and not n.is_pi5
                and any(hint in n.role.lower() for hint in self.ROLE_HINTS)
            ]
            if role_matched_mesh_nodes:
                chosen = role_matched_mesh_nodes[0]
                return DelegationDecision(
                    mode="mesh_node",
                    target=chosen.tailscale_host,
                    reason=(
                        "No reachable Pi5 available; using reachable mesh node "
                        "with scout/intel-aligned role"
                    ),
                    fallback="local_fleet_scout",
                )

            reachable_mesh_nodes = [
                n for n in mesh_nodes if n.reachable and n.tailscale_host
            ]
            if reachable_mesh_nodes:
                chosen = reachable_mesh_nodes[0]
                return DelegationDecision(
                    mode="mesh_node",
                    target=chosen.tailscale_host,
                    reason=(
                        "No reachable Pi5 available; using first reachable mesh node"
                    ),
                    fallback="local_fleet_scout",
                )

            if node_registry is not None:
                scout = node_registry.get("scout")
                if scout is not None:
                    return DelegationDecision(
                        mode="local_fleet",
                        target=scout.host,
                        reason="No reachable Pi5 in mesh, using local scout node",
                        fallback="local_primary",
                    )

        primary_target = "localhost"
        if node_registry is not None:
            primary = node_registry.get("primary")
            if primary is not None:
                primary_target = primary.host

        return DelegationDecision(
            mode="local_primary",
            target=primary_target,
            reason="Objective does not require external scout delegation",
            fallback="cloud_router",
        )
