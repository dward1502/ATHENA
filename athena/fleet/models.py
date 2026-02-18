"""Model assignment registry — provider-agnostic model routing.

Sovereignty-first: local Ollama is always the preferred tier.
Cloud providers are pluggable fallbacks — no vendor lock-in.
Any provider implementing the ProviderConfig interface can be slotted in.

Routing priority: LOCAL → CLOUD_TIER_1 → CLOUD_TIER_2 → ... → CLOUD_TIER_N
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════
# PROVIDER ABSTRACTION
# ═══════════════════════════════════════════════════════════════════════


class ProviderType(Enum):
    """Where the model runs."""

    LOCAL = "local"  # Ollama, llama.cpp, vLLM on-prem
    CLOUD = "cloud"  # Any remote API


@dataclass
class ProviderConfig:
    """A pluggable LLM provider — local or cloud."""

    name: str  # e.g. "ollama", "openai", "xai", "anthropic"
    provider_type: ProviderType
    base_url: str  # e.g. "http://localhost:11434"
    api_key_env: Optional[str] = None  # env var name for API key
    priority: int = 0  # lower = preferred. 0 = local
    models: List[str] = field(default_factory=list)
    enabled: bool = True
    cost_per_1k_input: float = 0.0  # $ per 1k input tokens
    cost_per_1k_output: float = 0.0  # $ per 1k output tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "provider_type": self.provider_type.value,
            "base_url": self.base_url,
            "priority": self.priority,
            "models": self.models,
            "enabled": self.enabled,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
        }


# ═══════════════════════════════════════════════════════════════════════
# MODEL CAPABILITY TIERS
# ═══════════════════════════════════════════════════════════════════════


class ModelTier(Enum):
    """Capability tier — what the agent NEEDS, not which model it IS."""

    FLAGSHIP = "flagship"  # Complex reasoning, planning, architecture
    STANDARD = "standard"  # General purpose: code gen, analysis
    LIGHTWEIGHT = "lightweight"  # Fast + cheap: routing, classification
    SCOUT = "scout"  # Minimal: health checks, formatting


# Maps each tier to model IDs per provider. Order within list = preference.
TIER_MODEL_MAP: Dict[str, Dict[str, List[str]]] = {
    "ollama": {
        ModelTier.FLAGSHIP.value: ["qwen3.5:72b", "qwen3.5:32b", "llama3.3:70b"],
        ModelTier.STANDARD.value: ["qwen3.5:14b", "qwen3.5:8b", "llama3.3:8b"],
        ModelTier.LIGHTWEIGHT.value: ["qwen3.5:7b", "qwen3.5:3b", "phi4:14b"],
        ModelTier.SCOUT.value: ["qwen3.5:3b", "qwen3.5:1.5b", "phi4-mini:3.8b"],
    },
    "anthropic": {
        ModelTier.FLAGSHIP.value: [
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
        ],
        ModelTier.STANDARD.value: [
            "claude-sonnet-4-20250514",
            "claude-haiku-3-20250307",
        ],
        ModelTier.LIGHTWEIGHT.value: ["claude-haiku-3-20250307"],
        ModelTier.SCOUT.value: ["claude-haiku-3-20250307"],
    },
    "openai": {
        ModelTier.FLAGSHIP.value: ["gpt-4.1", "o4-mini", "gpt-4.1-mini"],
        ModelTier.STANDARD.value: ["gpt-4.1-mini", "gpt-4.1-nano"],
        ModelTier.LIGHTWEIGHT.value: ["gpt-4.1-nano"],
        ModelTier.SCOUT.value: ["gpt-4.1-nano"],
    },
    "xai": {
        ModelTier.FLAGSHIP.value: ["grok-3", "grok-3-mini"],
        ModelTier.STANDARD.value: ["grok-3-mini", "grok-3-fast"],
        ModelTier.LIGHTWEIGHT.value: ["grok-3-fast"],
        ModelTier.SCOUT.value: ["grok-3-fast"],
    },
    "google": {
        ModelTier.FLAGSHIP.value: ["gemini-2.5-pro", "gemini-2.5-flash"],
        ModelTier.STANDARD.value: ["gemini-2.5-flash"],
        ModelTier.LIGHTWEIGHT.value: ["gemini-2.0-flash-lite"],
        ModelTier.SCOUT.value: ["gemini-2.0-flash-lite"],
    },
    "mistral": {
        ModelTier.FLAGSHIP.value: ["mistral-large-latest"],
        ModelTier.STANDARD.value: [
            "mistral-medium-latest",
            "mistral-small-latest",
        ],
        ModelTier.LIGHTWEIGHT.value: ["mistral-small-latest"],
        ModelTier.SCOUT.value: ["mistral-small-latest"],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# AGENT → TIER MAPPING
# ═══════════════════════════════════════════════════════════════════════

AGENT_TIER_ASSIGNMENTS: Dict[str, str] = {
    # Supreme command
    "ATHENA": ModelTier.FLAGSHIP.value,
    # Olympians
    "APOLLO": ModelTier.STANDARD.value,
    "ARES": ModelTier.STANDARD.value,
    "ARTEMIS": ModelTier.STANDARD.value,
    "HERMES": ModelTier.STANDARD.value,
    "HEPHAESTUS": ModelTier.STANDARD.value,
    # Heavyweight titans
    "PROMETHEUS": ModelTier.FLAGSHIP.value,
    "ATLAS": ModelTier.FLAGSHIP.value,
    "HYPERION": ModelTier.FLAGSHIP.value,
    "HADES": ModelTier.FLAGSHIP.value,
    "CALLISTO": ModelTier.FLAGSHIP.value,
    # Standard titans
    "OCEANUS": ModelTier.STANDARD.value,
    "CRONOS": ModelTier.STANDARD.value,
    "HELIOS": ModelTier.STANDARD.value,
    "SELENE": ModelTier.STANDARD.value,
    "MNEMOSYNE": ModelTier.STANDARD.value,
    "CALLIOPE": ModelTier.STANDARD.value,
    "ORPHEUS": ModelTier.STANDARD.value,
    "ORION": ModelTier.STANDARD.value,
    "ACTAEON": ModelTier.STANDARD.value,
    "ATALANTA": ModelTier.STANDARD.value,
    "MELEAGER": ModelTier.STANDARD.value,
    # New titans — HERMES refactor
    "IRIS": ModelTier.STANDARD.value,
    "HERMES_BUS": ModelTier.STANDARD.value,
    "COURIER": ModelTier.LIGHTWEIGHT.value,
    # New titans — APOLLO refactor
    "SCHOLAR": ModelTier.STANDARD.value,
    "NAVIGATOR": ModelTier.LIGHTWEIGHT.value,
    "SCRIBE": ModelTier.STANDARD.value,
    # Lightweight / scouts
    "TERPSICHORE": ModelTier.LIGHTWEIGHT.value,
    "ACHILLES": ModelTier.SCOUT.value,
    "ODYSSEUS": ModelTier.SCOUT.value,
    "PERSEUS": ModelTier.SCOUT.value,
}


# ═══════════════════════════════════════════════════════════════════════
# DEFAULT PROVIDER REGISTRY
# ═══════════════════════════════════════════════════════════════════════


def build_default_providers() -> List[ProviderConfig]:
    """Build the default provider chain. Priority 0 = local (always first)."""
    return [
        ProviderConfig(
            name="ollama",
            provider_type=ProviderType.LOCAL,
            base_url="http://localhost:11434",
            api_key_env=None,
            priority=0,
            models=["qwen3.5:72b", "qwen3.5:14b", "qwen3.5:7b", "qwen3.5:3b"],
            enabled=True,
        ),
        ProviderConfig(
            name="openai",
            provider_type=ProviderType.CLOUD,
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            priority=10,
            models=["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "o4-mini"],
            enabled=True,
            cost_per_1k_input=0.002,
            cost_per_1k_output=0.008,
        ),
        ProviderConfig(
            name="xai",
            provider_type=ProviderType.CLOUD,
            base_url="https://api.x.ai/v1",
            api_key_env="XAI_API_KEY",
            priority=15,
            models=["grok-3", "grok-3-mini", "grok-3-fast"],
            enabled=True,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
        ),
        ProviderConfig(
            name="anthropic",
            provider_type=ProviderType.CLOUD,
            base_url="https://api.anthropic.com/v1",
            api_key_env="ANTHROPIC_API_KEY",
            priority=20,
            models=[
                "claude-opus-4-20250514",
                "claude-sonnet-4-20250514",
                "claude-haiku-3-20250307",
            ],
            enabled=True,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
        ),
        ProviderConfig(
            name="google",
            provider_type=ProviderType.CLOUD,
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key_env="GOOGLE_API_KEY",
            priority=25,
            models=["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash-lite"],
            enabled=True,
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.004,
        ),
        ProviderConfig(
            name="mistral",
            provider_type=ProviderType.CLOUD,
            base_url="https://api.mistral.ai/v1",
            api_key_env="MISTRAL_API_KEY",
            priority=30,
            models=[
                "mistral-large-latest",
                "mistral-medium-latest",
                "mistral-small-latest",
            ],
            enabled=True,
            cost_per_1k_input=0.002,
            cost_per_1k_output=0.006,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════
# BACKWARD-COMPAT SHIM (existing code in base.py / old tests)
# ═══════════════════════════════════════════════════════════════════════

AGENT_MODEL_ASSIGNMENTS: Dict[str, str] = {
    agent: f"tier/{tier}" for agent, tier in AGENT_TIER_ASSIGNMENTS.items()
}


def get_model_for_agent(agent_name: str) -> str:
    """Return the tier identifier for an agent (backward compat)."""
    tier = AGENT_TIER_ASSIGNMENTS.get(agent_name, ModelTier.STANDARD.value)
    return f"tier/{tier}"


def get_tier_for_agent(agent_name: str) -> str:
    """Return the raw tier string for an agent."""
    return AGENT_TIER_ASSIGNMENTS.get(agent_name, ModelTier.STANDARD.value)
