from pathlib import Path

from athena.fleet.delegation_policy import Pi5DelegationPolicy
from athena.fleet.mesh_discovery import MeshDiscoveryAdapter
from athena.fleet.node_registry import NodeRegistry


def _write_manifest(path: Path) -> None:
    path.write_text(
        """version: 1
manifest_id: test
nodes:
  warden:
    tailscale_host: raspberrypi
    tailscale_ip: 100.1.1.1
    ssh_user: numenor
    role: vision_intel
    status: active
    identity_file: CITADEL_v1/REMOTE/WARDEN_IDENTITY.md
    soul_file: CITADEL_v1/REMOTE/WARDEN_SOUL.md
  forge:
    tailscale_host: beelink
    tailscale_ip: 100.1.1.2
    ssh_user: root
    role: development_sandbox
    status: active
    identity_file: CITADEL_v1/REMOTE/FORGE_IDENTITY.md
    soul_file: CITADEL_v1/REMOTE/FORGE_SOUL.md
policy:
  default_mode: think
"""
    )


def _write_manifest_without_reachable_pi(path: Path) -> None:
    path.write_text(
        """version: 1
manifest_id: test-no-pi
nodes:
  warden:
    tailscale_host: raspberrypi
    tailscale_ip: 100.1.1.1
    ssh_user: numenor
    role: vision_intel
    status: offline
    identity_file: CITADEL_v1/REMOTE/WARDEN_IDENTITY.md
    soul_file: CITADEL_v1/REMOTE/WARDEN_SOUL.md
  forge:
    tailscale_host: beelink
    tailscale_ip: 100.1.1.2
    ssh_user: root
    role: research_assistant
    status: active
    identity_file: CITADEL_v1/REMOTE/FORGE_IDENTITY.md
    soul_file: CITADEL_v1/REMOTE/FORGE_SOUL.md
policy:
  default_mode: think
"""
    )


def _write_manifest_no_reachable_mesh(path: Path) -> None:
    path.write_text(
        """version: 1
manifest_id: test-no-mesh
nodes:
  warden:
    tailscale_host: raspberrypi
    tailscale_ip: 100.1.1.1
    ssh_user: numenor
    role: vision_intel
    status: offline
    identity_file: CITADEL_v1/REMOTE/WARDEN_IDENTITY.md
    soul_file: CITADEL_v1/REMOTE/WARDEN_SOUL.md
  forge:
    tailscale_host: beelink
    tailscale_ip: 100.1.1.2
    ssh_user: root
    role: research_assistant
    status: offline
    identity_file: CITADEL_v1/REMOTE/FORGE_IDENTITY.md
    soul_file: CITADEL_v1/REMOTE/FORGE_SOUL.md
policy:
  default_mode: think
"""
    )


def test_mesh_discovery_from_manifest(tmp_path: Path):
    manifest = tmp_path / "MESH_MANIFEST.yaml"
    _write_manifest(manifest)

    adapter = MeshDiscoveryAdapter(manifest_path=manifest)
    nodes = adapter.discover()

    assert len(nodes) == 2
    assert any(n.tailscale_host == "raspberrypi" for n in nodes)
    assert any(n.is_pi5 for n in nodes)


def test_pi5_delegation_policy_prefers_mesh_pi5(tmp_path: Path):
    manifest = tmp_path / "MESH_MANIFEST.yaml"
    _write_manifest(manifest)

    adapter = MeshDiscoveryAdapter(manifest_path=manifest)
    nodes = adapter.discover()

    policy = Pi5DelegationPolicy()
    decision = policy.recommend(
        objective="Scout github repositories for auth patterns",
        mesh_nodes=nodes,
        node_registry=NodeRegistry(),
    )

    assert decision.mode == "mesh_pi5"
    assert decision.target == "raspberrypi"


def test_pi5_delegation_policy_prefers_mesh_pi5_for_audit(tmp_path: Path):
    manifest = tmp_path / "MESH_MANIFEST.yaml"
    _write_manifest(manifest)

    adapter = MeshDiscoveryAdapter(manifest_path=manifest)
    nodes = adapter.discover()

    policy = Pi5DelegationPolicy()
    decision = policy.recommend(
        objective="Run ATHENA code audit for memory pressure hotspots",
        mesh_nodes=nodes,
        node_registry=NodeRegistry(),
    )

    assert decision.mode == "mesh_pi5"
    assert decision.target == "raspberrypi"


def test_delegation_policy_uses_reachable_non_pi_mesh_node_when_pi_unavailable(
    tmp_path: Path,
    monkeypatch,
):
    manifest = tmp_path / "MESH_MANIFEST.yaml"
    _write_manifest_without_reachable_pi(manifest)

    adapter = MeshDiscoveryAdapter(manifest_path=manifest)
    monkeypatch.setattr(
        adapter,
        "_tailscale_online_map",
        lambda: {"raspberrypi": False, "beelink": True},
    )
    nodes = adapter.discover()

    policy = Pi5DelegationPolicy()
    decision = policy.recommend(
        objective="Scout code patterns for ingestion",
        mesh_nodes=nodes,
        node_registry=NodeRegistry(),
    )

    assert decision.mode == "mesh_node"
    assert decision.target == "beelink"


def test_delegation_policy_falls_back_to_local_scout_when_mesh_unreachable(
    tmp_path: Path,
    monkeypatch,
):
    manifest = tmp_path / "MESH_MANIFEST.yaml"
    _write_manifest_no_reachable_mesh(manifest)

    adapter = MeshDiscoveryAdapter(manifest_path=manifest)
    monkeypatch.setattr(
        adapter,
        "_tailscale_online_map",
        lambda: {"raspberrypi": False, "beelink": False},
    )
    nodes = adapter.discover()

    registry = NodeRegistry()
    registry.register_default_fleet()
    policy = Pi5DelegationPolicy()
    decision = policy.recommend(
        objective="Run ATHENA code audit for memory pressure hotspots",
        mesh_nodes=nodes,
        node_registry=registry,
    )

    assert decision.mode == "local_fleet"
    assert decision.target == "beelink"


def test_pi5_delegation_policy_uses_local_primary_for_non_scout(tmp_path: Path):
    manifest = tmp_path / "MESH_MANIFEST.yaml"
    _write_manifest(manifest)

    adapter = MeshDiscoveryAdapter(manifest_path=manifest)
    nodes = adapter.discover()

    registry = NodeRegistry()
    registry.register_default_fleet()

    policy = Pi5DelegationPolicy()
    decision = policy.recommend(
        objective="Deploy backend API and run migrations",
        mesh_nodes=nodes,
        node_registry=registry,
    )

    assert decision.mode == "local_primary"
