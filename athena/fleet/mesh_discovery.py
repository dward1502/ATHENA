import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class MeshNode:
    name: str
    tailscale_host: str
    tailscale_ip: str
    role: str
    status: str
    identity_file: str = ""
    soul_file: str = ""
    ssh_user: str = ""
    reachable: bool = False

    @property
    def is_pi5(self) -> bool:
        host = self.tailscale_host.lower()
        return host.startswith("raspberrypi") or "pi5" in host

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "tailscale_host": self.tailscale_host,
            "tailscale_ip": self.tailscale_ip,
            "role": self.role,
            "status": self.status,
            "identity_file": self.identity_file,
            "soul_file": self.soul_file,
            "ssh_user": self.ssh_user,
            "reachable": self.reachable,
            "is_pi5": self.is_pi5,
        }


class MeshDiscoveryAdapter:
    def __init__(self, manifest_path: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[3]
        self.manifest_path = manifest_path or (
            root / "CITADEL_v1" / "REMOTE" / "MESH_MANIFEST.yaml"
        )

    def discover(self) -> List[MeshNode]:
        nodes = self._discover_from_manifest()
        online = self._tailscale_online_map()
        for node in nodes:
            if node.tailscale_host in online:
                node.reachable = online[node.tailscale_host]
            else:
                node.reachable = node.status.lower() == "active"
        return nodes

    def _discover_from_manifest(self) -> List[MeshNode]:
        if not self.manifest_path.exists():
            return []

        with open(self.manifest_path) as f:
            lines = f.readlines()

        nodes_raw: Dict[str, Dict[str, str]] = {}
        in_nodes = False
        current = ""

        for raw in lines:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped:
                continue

            if stripped == "nodes:":
                in_nodes = True
                continue

            if in_nodes and stripped == "policy:":
                break

            if not in_nodes:
                continue

            node_match = re.match(r"^\s{2}([a-zA-Z0-9_-]+):\s*$", line)
            if node_match:
                name = node_match.group(1)
                if not name:
                    continue
                current = name
                nodes_raw[current] = {}
                continue

            value_match = re.match(r"^\s{4}([a-zA-Z0-9_]+):\s*(.*)$", line)
            if current and value_match:
                key = value_match.group(1)
                if not key:
                    continue
                value = value_match.group(2).strip().strip('"').strip("'")
                nodes_raw[current][key] = value

        nodes: List[MeshNode] = []
        for name, data in nodes_raw.items():
            nodes.append(
                MeshNode(
                    name=name,
                    tailscale_host=data.get("tailscale_host", ""),
                    tailscale_ip=data.get("tailscale_ip", ""),
                    role=data.get("role", ""),
                    status=data.get("status", "unknown"),
                    identity_file=data.get("identity_file", ""),
                    soul_file=data.get("soul_file", ""),
                    ssh_user=data.get("ssh_user", ""),
                )
            )
        return nodes

    def _tailscale_online_map(self) -> Dict[str, bool]:
        try:
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return {}
            payload = json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return {}

        online: Dict[str, bool] = {}
        peer_map = payload.get("Peer", {}) if isinstance(payload, dict) else {}
        if isinstance(peer_map, dict):
            for peer in peer_map.values():
                if not isinstance(peer, dict):
                    continue
                host = str(peer.get("HostName", "")).strip()
                if host:
                    online[host] = bool(peer.get("Online", False))
        return online
