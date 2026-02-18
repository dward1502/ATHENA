from athena.fleet.model_router import ModelRouter, ProviderRegistry
from athena.fleet.models import ProviderConfig, ProviderType


def test_router_bounces_on_rate_limit(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("XAI_API_KEY", "test-xai")

    providers = [
        ProviderConfig(
            name="openai",
            provider_type=ProviderType.CLOUD,
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            priority=10,
            models=["gpt-4.1-mini"],
        ),
        ProviderConfig(
            name="xai",
            provider_type=ProviderType.CLOUD,
            base_url="https://api.x.ai/v1",
            api_key_env="XAI_API_KEY",
            priority=20,
            models=["grok-3-mini"],
        ),
    ]
    router = ModelRouter(provider_registry=ProviderRegistry(providers=providers))

    first = router.route("APOLLO")
    assert first is not None
    assert first.provider_name == "openai"

    bounced = router.route_after_failure(
        agent_name="APOLLO",
        failed_provider="openai",
        status_code=429,
        retry_after_seconds=60,
    )
    assert bounced is not None
    assert bounced.provider_name == "xai"
