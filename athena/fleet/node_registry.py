"""Compute node registry with Ollama health checking."""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib import error as urllib_error, request as urllib_request


logger = logging.getLogger("FLEET.REGISTRY")


@dataclass
class ComputeNode:
    name: str
    host: str
    ollama_port: int = 11434
    gpu: str = "CPU"
    vram_gb: float = 0.0
    models: List[str] = field(default_factory=list)
    current_load: float = 0.0
    reachable: bool = False
    last_health_check: Optional[str] = None

    @property
    def ollama_url(self) -> str:
        return f"http://{self.host}:{self.ollama_port}"

    def check_health(self, timeout: float = 3.0) -> bool:
        url = f"{self.ollama_url}/api/tags"
        req = urllib_request.Request(url, headers={"User-Agent": "ATHENA-FLEET/1.0"})
        try:
            with urllib_request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                live_models = [m.get("name", "") for m in data.get("models", [])]
                if live_models:
                    self.models = live_models
                self.reachable = True
        except (urllib_error.URLError, urllib_error.HTTPError, Exception):
            self.reachable = False

        self.last_health_check = datetime.now().isoformat()
        return self.reachable

    def has_model(self, model_id: str) -> bool:
        short = model_id.split("/")[-1] if "/" in model_id else model_id
        return any(short in m for m in self.models)


class NodeRegistry:
    def __init__(self) -> None:
        self.nodes: Dict[str, ComputeNode] = {}

    def register(self, node: ComputeNode) -> None:
        self.nodes[node.name] = node

    def get(self, name: str) -> Optional[ComputeNode]:
        return self.nodes.get(name)

    def all_nodes(self) -> List[ComputeNode]:
        return list(self.nodes.values())

    def available_nodes(self) -> List[ComputeNode]:
        return [n for n in self.nodes.values() if n.reachable]

    def best_node_for(self, required_vram_gb: float = 0.0) -> Optional[ComputeNode]:
        candidates = [
            n for n in self.available_nodes() if n.vram_gb >= required_vram_gb
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda n: n.current_load)

    def node_with_model(self, model_id: str) -> Optional[ComputeNode]:
        for node in self.available_nodes():
            if node.has_model(model_id):
                return node
        return None

    def health_check_all(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for name, node in self.nodes.items():
            results[name] = node.check_health()
            status = "UP" if results[name] else "DOWN"
            logger.info(f"  {name} ({node.host}): {status}")
        return results

    def register_default_fleet(self) -> None:
        primary_host = os.getenv("ATHENA_PRIMARY_HOST", "localhost")
        beelink_host = os.getenv("ATHENA_BEELINK_HOST", "beelink")

        self.register(
            ComputeNode(
                name="primary",
                host=primary_host,
                ollama_port=11434,
                gpu="RTX 3080",
                vram_gb=10.0,
                models=["qwen3.5:14b-q4", "qwen3.5:7b-fp16"],
            )
        )
        self.register(
            ComputeNode(
                name="scout",
                host=beelink_host,
                ollama_port=11434,
                gpu="Radeon 780M",
                vram_gb=8.0,
                models=["qwen3.5:7b-q4", "qwen3.5:3b-fp16"],
            )
        )
