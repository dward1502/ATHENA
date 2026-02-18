"""Model router — provider-agnostic routing with local-first fallback.

Routes agent requests through a priority-ordered provider chain:
  LOCAL (Ollama) → CLOUD providers (sorted by priority)

Tracks $JW$ (JouleWork) cost per request for SOUL.md compliance.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from urllib import error as urllib_error, request as urllib_request

from athena.fleet.models import (
    ProviderConfig,
    ProviderType,
    TIER_MODEL_MAP,
    build_default_providers,
    get_tier_for_agent,
)
from athena.fleet.node_registry import NodeRegistry


logger = logging.getLogger("FLEET.ROUTER")


@dataclass
class RouteResult:
    provider_name: str
    provider_type: str
    base_url: str
    model_id: str
    tier: str
    estimated_cost_input: float = 0.0
    estimated_cost_output: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "type": self.provider_type,
            "base_url": self.base_url,
            "model_id": self.model_id,
            "tier": self.tier,
            "cost_input_1k": self.estimated_cost_input,
            "cost_output_1k": self.estimated_cost_output,
        }


@dataclass
class JouleWorkEntry:
    agent_name: str
    provider: str
    model_id: str
    tier: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "provider": self.provider,
            "model": self.model_id,
            "tier": self.tier,
            "tokens_in": self.input_tokens,
            "tokens_out": self.output_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "ts": self.timestamp,
        }


class ProviderRegistry:
    """Manages the ordered list of LLM providers with health checking."""

    def __init__(self, providers: Optional[List[ProviderConfig]] = None) -> None:
        self.providers: List[ProviderConfig] = providers or build_default_providers()
        self._health_cache: Dict[str, bool] = {}

    def add_provider(self, config: ProviderConfig) -> None:
        self.providers.append(config)
        self.providers.sort(key=lambda p: p.priority)

    def remove_provider(self, name: str) -> None:
        self.providers = [p for p in self.providers if p.name != name]

    def get_provider(self, name: str) -> Optional[ProviderConfig]:
        for p in self.providers:
            if p.name == name:
                return p
        return None

    def enabled_providers(self) -> List[ProviderConfig]:
        return sorted(
            [p for p in self.providers if p.enabled],
            key=lambda p: p.priority,
        )

    def check_provider_health(self, config: ProviderConfig) -> bool:
        if config.provider_type == ProviderType.LOCAL:
            return self._check_ollama(config.base_url)
        return self._check_cloud_api_key(config)

    def _check_ollama(self, base_url: str) -> bool:
        url = f"{base_url}/api/tags"
        req = urllib_request.Request(url, headers={"User-Agent": "ATHENA-FLEET/1.0"})
        try:
            with urllib_request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                return len(models) > 0
        except (urllib_error.URLError, urllib_error.HTTPError, Exception):
            return False

    def _check_cloud_api_key(self, config: ProviderConfig) -> bool:
        if not config.api_key_env:
            return False
        key = os.getenv(config.api_key_env, "")
        return len(key) > 0

    def health_check_all(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for provider in self.providers:
            healthy = self.check_provider_health(provider)
            results[provider.name] = healthy
            self._health_cache[provider.name] = healthy
            status = "UP" if healthy else "DOWN"
            logger.info(f"  {provider.name} ({provider.provider_type.value}): {status}")
        return results

    def list_providers(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.providers]


class ModelRouter:
    """Routes agent requests to the best available provider + model.

    Sovereignty-first: always tries local Ollama before any cloud provider.
    Provider-agnostic: any cloud API can be slotted in via ProviderConfig.
    """

    def __init__(
        self,
        node_registry: Optional[NodeRegistry] = None,
        provider_registry: Optional[ProviderRegistry] = None,
    ) -> None:
        self.node_registry = node_registry
        self.provider_registry = provider_registry or ProviderRegistry()
        self.jw_ledger: List[JouleWorkEntry] = []
        self.provider_backoff_until: Dict[str, datetime] = {}

    @property
    def registry(self) -> Optional[NodeRegistry]:
        return self.node_registry

    def route(
        self,
        agent_name: str,
        excluded_providers: Optional[Set[str]] = None,
    ) -> Optional[RouteResult]:
        tier = get_tier_for_agent(agent_name)
        excluded = excluded_providers or set()

        for provider in self.provider_registry.enabled_providers():
            if provider.name in excluded:
                continue
            if self._is_provider_throttled(provider.name):
                logger.debug(f"Skipping {provider.name}: rate-limited")
                continue

            tier_models = TIER_MODEL_MAP.get(provider.name, {})
            candidates = tier_models.get(tier, [])

            if not candidates:
                continue

            if not self.provider_registry.check_provider_health(provider):
                logger.debug(f"Skipping {provider.name}: unhealthy")
                continue

            if provider.provider_type == ProviderType.LOCAL:
                model_id = self._resolve_local_model(provider, candidates)
            else:
                model_id = candidates[0]

            if model_id:
                return RouteResult(
                    provider_name=provider.name,
                    provider_type=provider.provider_type.value,
                    base_url=provider.base_url,
                    model_id=model_id,
                    tier=tier,
                    estimated_cost_input=provider.cost_per_1k_input,
                    estimated_cost_output=provider.cost_per_1k_output,
                )

        logger.warning(f"No provider available for {agent_name} (tier={tier})")
        return None

    def route_after_failure(
        self,
        agent_name: str,
        failed_provider: str,
        status_code: Optional[int] = None,
        retry_after_seconds: Optional[int] = None,
    ) -> Optional[RouteResult]:
        self.report_provider_failure(
            provider_name=failed_provider,
            status_code=status_code,
            retry_after_seconds=retry_after_seconds,
        )
        return self.route(agent_name, excluded_providers={failed_provider})

    def route_simple(self, agent_name: str) -> Optional[str]:
        result = self.route(agent_name)
        if result is None:
            return None
        if result.provider_type == "local":
            return f"{result.base_url}/api/generate"
        return f"{result.provider_name}/{result.model_id}"

    def _resolve_local_model(
        self, provider: ProviderConfig, candidates: List[str]
    ) -> Optional[str]:
        if self.node_registry:
            for model_id in candidates:
                node = self.node_registry.node_with_model(model_id)
                if node:
                    return model_id

        for model_id in candidates:
            if model_id in provider.models:
                return model_id

        return candidates[0] if candidates else None

    def _is_provider_throttled(self, provider_name: str) -> bool:
        until = self.provider_backoff_until.get(provider_name)
        if until is None:
            return False
        if datetime.now() >= until:
            self.provider_backoff_until.pop(provider_name, None)
            return False
        return True

    def report_provider_failure(
        self,
        provider_name: str,
        status_code: Optional[int] = None,
        retry_after_seconds: Optional[int] = None,
    ) -> None:
        if status_code != 429:
            return
        cooldown = int(retry_after_seconds or 60)
        backoff_until = datetime.now() + timedelta(seconds=max(1, cooldown))
        self.provider_backoff_until[provider_name] = backoff_until
        logger.warning(
            f"Provider {provider_name} rate-limited (429). "
            + f"Cooling down for {cooldown}s until {backoff_until.isoformat()}"
        )

    def log_jw(
        self,
        agent_name: str,
        route: RouteResult,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
    ) -> JouleWorkEntry:
        cost = route.estimated_cost_input * (
            input_tokens / 1000.0
        ) + route.estimated_cost_output * (output_tokens / 1000.0)
        entry = JouleWorkEntry(
            agent_name=agent_name,
            provider=route.provider_name,
            model_id=route.model_id,
            tier=route.tier,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost, 6),
            latency_ms=latency_ms,
        )
        self.jw_ledger.append(entry)
        msg = (
            f"$JW$ {agent_name} via {route.provider_name}/{route.model_id}: "
            + f"${cost:.6f} ({input_tokens}+{output_tokens} tokens, {latency_ms:.0f}ms)"
        )
        logger.info(msg)
        return entry

    def get_jw_summary(self) -> Dict[str, Any]:
        total_cost = sum(e.cost_usd for e in self.jw_ledger)
        by_provider: Dict[str, float] = {}
        for entry in self.jw_ledger:
            by_provider[entry.provider] = (
                by_provider.get(entry.provider, 0.0) + entry.cost_usd
            )
        return {
            "total_cost_usd": round(total_cost, 6),
            "total_requests": len(self.jw_ledger),
            "by_provider": by_provider,
            "entries": [e.to_dict() for e in self.jw_ledger[-50:]],
        }
