import base64

import athena.olympians.hermes as hermes_mod
from athena.olympians.hermes import HERMES_OLYMPIAN


def test_agentize_repo_collects_sampled_files_and_signals(monkeypatch):
    def _fake_github_get(path: str):
        if path == "/repos/example/repo":
            return {
                "description": "Autonomous orchestration runtime",
                "language": "TypeScript",
                "license": {"spdx_id": "MIT"},
                "stargazers_count": 42,
                "default_branch": "main",
                "topics": ["agentic", "orchestration"],
                "has_wiki": False,
            }
        if path == "/repos/example/repo/readme":
            content = base64.b64encode(b"# Repo\nMulti-agent orchestrator").decode()
            return {"encoding": "base64", "content": content}
        if path == "/repos/example/repo/git/trees/main?recursive=1":
            return {
                "tree": [
                    {"path": "package.json", "type": "blob"},
                    {"path": "src/main.ts", "type": "blob"},
                    {"path": "src/agent/router.ts", "type": "blob"},
                    {"path": "README.md", "type": "blob"},
                ]
            }
        if path.startswith("/repos/example/repo/contents/package.json"):
            body = b'{"dependencies":{"discord.js":"^14.0.0","langchain":"0.2.0"}}'
            return {"encoding": "base64", "content": base64.b64encode(body).decode()}
        if path.startswith("/repos/example/repo/contents/src/main.ts"):
            body = b"import OpenAI from 'openai';\nconst app = 'agent';"
            return {"encoding": "base64", "content": base64.b64encode(body).decode()}
        if path.startswith("/repos/example/repo/contents/src/agent/router.ts"):
            body = b"import { StateGraph } from 'langgraph';"
            return {"encoding": "base64", "content": base64.b64encode(body).decode()}
        if path.startswith("/repos/example/repo/contents/README.md"):
            body = b"Agentic runtime with Discord support"
            return {"encoding": "base64", "content": base64.b64encode(body).decode()}
        return None

    monkeypatch.setattr(hermes_mod, "_github_get", _fake_github_get)

    hermes = HERMES_OLYMPIAN()
    result = hermes.agentize_repo("https://github.com/example/repo")

    assert result.status == "success"
    assert result.agent_card is not None
    card = result.agent_card
    assert "multi_agent" in card.capabilities
    assert "package.json" in card.dependencies
    assert "src/main.ts" in card.sampled_files
    assert "openai" in card.signal_tags
