"""HERMES — Communications & Repo Agentization Division."""

import base64
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib import error as urllib_error, request as urllib_request

from athena.olympians.base import Olympian, Titan
from athena.types import (
    AgentCard,
    AgentStatus,
    Component,
    DivisionStatus,
    IngestResult,
    SourceType,
)


CAPABILITY_SIGNALS: Dict[str, List[str]] = {
    "image_processing": ["image", "vision", "cv", "ocr", "detection"],
    "speech_recognition": ["speech", "asr", "stt", "whisper", "transcription"],
    "text_to_speech": ["tts", "text-to-speech", "speech synthesis"],
    "nlp": ["nlp", "text analysis", "sentiment", "tokeniz"],
    "search": ["search", "retrieval", "rag", "embedding"],
    "code_generation": ["code generation", "codegen", "copilot"],
    "document_processing": ["document", "pdf", "parsing", "extraction"],
    "web_scraping": ["scraping", "crawl", "spider", "playwright"],
    "ml_training": ["training", "fine-tune", "finetuning", "dataset"],
    "multi_agent": ["multi-agent", "agent", "autonomous", "agentic"],
    "video_processing": ["video", "ffmpeg", "streaming"],
    "data_analysis": ["data analysis", "pandas", "visualization", "plotting"],
}

FRAMEWORK_SIGNALS: Dict[str, List[str]] = {
    "react": ["react", "nextjs", "next.js"],
    "express": ["express", "fastify", "koa"],
    "discord": ["discord.py", "discord.js", "discord"],
    "langchain": ["langchain", "langgraph"],
    "openai": ["openai", "gpt-", "chat.completions"],
    "anthropic": ["anthropic", "claude"],
    "ollama": ["ollama"],
    "docker": ["docker", "dockerfile", "compose"],
}

ANALYSIS_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".md",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
}

ENTRY_PATTERNS: Dict[str, List[str]] = {
    "main": ["main.py", "app.py", "run.py", "cli.py", "__main__.py"],
    "api": ["api.py", "server.py"],
    "setup": ["setup.py", "pyproject.toml", "Makefile"],
    "docs": ["README.md", "docs/index.md"],
}


def _github_get(path: str) -> Optional[Dict[str, Any]]:
    url = f"https://api.github.com{path}"
    headers: Dict[str, str] = {
        "User-Agent": "ATHENA-HERMES/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib_request.Request(url, headers=headers)
    try:
        with urllib_request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib_error.HTTPError, urllib_error.URLError, Exception):
        return None


def _parse_repo_url(url: str) -> Optional[str]:
    match = re.search(r"github\.com[/:]([^/]+)/([^/\s?.#]+)", url)
    if match:
        repo = match.group(2).removesuffix(".git")
        return f"{match.group(1)}/{repo}"
    return None


# ═══════════════════════════════════════════════════════════════════════
# TITANS
# ═══════════════════════════════════════════════════════════════════════


class IRIS(Titan):
    def __init__(self) -> None:
        super().__init__("IRIS", "Repo discovery & analysis")
        self.logger = logging.getLogger("HERMES.IRIS")

    def discover_repo(self, repo_url: str) -> Dict[str, Any]:
        full_name = _parse_repo_url(repo_url)
        if not full_name:
            return {"error": f"Could not parse repo URL: {repo_url}"}

        repo_data = _github_get(f"/repos/{full_name}")
        if not repo_data:
            return {"error": f"Could not fetch repo: {full_name}"}

        branch = repo_data.get("default_branch", "main")
        readme = self._fetch_readme(full_name)
        tree = self._fetch_file_tree(full_name, branch)
        entry_points = self._detect_entry_points(tree)
        dependency_files = self._detect_dep_files(tree)
        sampled = self._collect_file_samples(
            full_name=full_name,
            branch=branch,
            tree=tree,
            entry_points=entry_points,
            dependency_files=dependency_files,
            readme=readme,
        )
        signal_tags = self._infer_framework_signals(repo_data, sampled)
        analysis_notes = self._build_analysis_notes(tree, sampled, signal_tags)

        return {
            "full_name": full_name,
            "url": repo_url,
            "description": repo_data.get("description", ""),
            "language": repo_data.get("language", "Unknown"),
            "license": (repo_data.get("license") or {}).get("spdx_id"),
            "stars": repo_data.get("stargazers_count", 0),
            "default_branch": branch,
            "topics": repo_data.get("topics", []),
            "readme_excerpt": (readme or "")[:2000],
            "capabilities": self._infer_capabilities(repo_data, readme, tree, sampled),
            "dependencies": dependency_files,
            "file_count": len(tree),
            "entry_points": entry_points,
            "sampled_files": [sample["path"] for sample in sampled],
            "signal_tags": signal_tags,
            "analysis_notes": analysis_notes,
        }

    def _fetch_readme(self, full_name: str) -> Optional[str]:
        data = _github_get(f"/repos/{full_name}/readme")
        if data and data.get("encoding") == "base64":
            try:
                return base64.b64decode(data["content"]).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                pass
        return None

    def _fetch_file_tree(self, full_name: str, branch: str) -> List[Dict[str, str]]:
        data = _github_get(f"/repos/{full_name}/git/trees/{branch}?recursive=1")
        if data and "tree" in data:
            return [{"path": e["path"], "type": e["type"]} for e in data["tree"]]
        return []

    def _fetch_file_content(
        self, full_name: str, path: str, branch: str
    ) -> Optional[str]:
        safe_path = "/".join(segment for segment in path.split("/") if segment)
        if not safe_path:
            return None
        data = _github_get(f"/repos/{full_name}/contents/{safe_path}?ref={branch}")
        if not data:
            return None
        if data.get("encoding") != "base64":
            return None
        raw = data.get("content", "")
        if not isinstance(raw, str) or not raw:
            return None
        try:
            decoded = base64.b64decode(raw).decode("utf-8", errors="replace")
        except Exception:
            return None
        if len(decoded) > 12000:
            return decoded[:12000]
        return decoded

    def _collect_file_samples(
        self,
        full_name: str,
        branch: str,
        tree: List[Dict[str, str]],
        entry_points: Dict[str, str],
        dependency_files: List[str],
        readme: Optional[str],
    ) -> List[Dict[str, str]]:
        candidates: List[str] = []
        if readme:
            candidates.append("README.md")

        for path in entry_points.values():
            if path:
                candidates.append(path)

        for path in dependency_files:
            candidates.append(path)

        for entry in tree:
            if entry.get("type") != "blob":
                continue
            path = str(entry.get("path", ""))
            lowered = path.lower()
            if not path:
                continue
            if any(
                marker in lowered
                for marker in (
                    "node_modules/",
                    "/dist/",
                    "/build/",
                    "/vendor/",
                    "/.git/",
                )
            ):
                continue
            if not any(lowered.endswith(ext) for ext in ANALYSIS_EXTENSIONS):
                continue
            if any(
                key in lowered
                for key in (
                    "main",
                    "app",
                    "server",
                    "cli",
                    "agent",
                    "workflow",
                    "router",
                    "orchestr",
                    "discord",
                    "README",
                    "docs/",
                )
            ):
                candidates.append(path)

        unique: List[str] = []
        for path in candidates:
            if path and path not in unique:
                unique.append(path)

        sampled: List[Dict[str, str]] = []
        for path in unique[:10]:
            content = self._fetch_file_content(full_name, path, branch)
            if not content:
                continue
            sampled.append({"path": path, "content": content})

        if not sampled:
            fallback_candidates: List[str] = []
            for entry in tree:
                if entry.get("type") != "blob":
                    continue
                path = str(entry.get("path", ""))
                lowered = path.lower()
                if not path:
                    continue
                if any(lowered.endswith(ext) for ext in ANALYSIS_EXTENSIONS):
                    fallback_candidates.append(path)

            seen_fallback: List[str] = []
            for path in fallback_candidates:
                if path not in seen_fallback:
                    seen_fallback.append(path)
            for path in seen_fallback[:5]:
                content = self._fetch_file_content(full_name, path, branch)
                if not content:
                    continue
                sampled.append({"path": path, "content": content})

        return sampled

    def _detect_dep_files(self, tree: List[Dict[str, str]]) -> List[str]:
        known = {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "setup.py",
        }
        return [
            e["path"]
            for e in tree
            if e.get("type") == "blob" and e.get("path") in known
        ]

    def _detect_entry_points(self, tree: List[Dict[str, str]]) -> Dict[str, str]:
        file_lookup: Dict[str, str] = {}
        for entry in tree:
            if entry.get("type") == "blob":
                file_lookup[entry["path"].split("/")[-1].lower()] = entry["path"]

        entry_points: Dict[str, str] = {}
        for category, patterns in ENTRY_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in file_lookup:
                    entry_points[category] = file_lookup[pattern.lower()]
                    break
        return entry_points

    def _infer_capabilities(
        self,
        repo_data: Dict[str, Any],
        readme: Optional[str],
        tree: List[Dict[str, str]],
        sampled: List[Dict[str, str]],
    ) -> List[str]:
        topics = repo_data.get("topics", [])
        desc = (repo_data.get("description") or "").lower()
        readme_lower = (readme or "").lower()[:5000]
        sampled_text = " ".join(sample.get("content", "") for sample in sampled).lower()
        combined = f"{desc} {' '.join(topics)} {readme_lower} {sampled_text[:20000]}"

        return [
            cap
            for cap, signals in CAPABILITY_SIGNALS.items()
            if any(signal in combined for signal in signals)
        ]

    def _infer_framework_signals(
        self,
        repo_data: Dict[str, Any],
        sampled: List[Dict[str, str]],
    ) -> List[str]:
        topics = " ".join(repo_data.get("topics", [])).lower()
        sampled_text = " ".join(sample.get("content", "") for sample in sampled).lower()
        text = f"{topics} {sampled_text[:20000]}"
        tags: List[str] = []
        for key, signals in FRAMEWORK_SIGNALS.items():
            if any(signal in text for signal in signals):
                tags.append(key)
        return tags

    def _build_analysis_notes(
        self,
        tree: List[Dict[str, str]],
        sampled: List[Dict[str, str]],
        signal_tags: List[str],
    ) -> List[str]:
        notes: List[str] = []
        notes.append(f"file_tree_count={len(tree)}")
        notes.append(f"sampled_file_count={len(sampled)}")
        if signal_tags:
            notes.append("framework_signals=" + ",".join(signal_tags))
        if sampled:
            notes.append(
                "sampled_paths="
                + ",".join(sample.get("path", "") for sample in sampled[:5])
            )
        if not sampled:
            token_present = bool(os.getenv("GITHUB_TOKEN"))
            if token_present:
                notes.append("sample_fetch_empty_with_token=true")
            else:
                notes.append("sample_fetch_empty_without_github_token=true")
        return notes


class HERMES_BUS(Titan):
    def __init__(self) -> None:
        super().__init__("HERMES_BUS", "Repo agentization")
        self.agent_registry: Dict[str, AgentCard] = {}
        self.logger = logging.getLogger("HERMES.BUS")

    def agentize(self, discovery: Dict[str, Any]) -> AgentCard:
        if "error" in discovery:
            return AgentCard(
                name="ERROR",
                repo_url=discovery.get("url", "unknown"),
                description=discovery["error"],
                status=AgentStatus.ERROR,
            )

        name = discovery["full_name"].split("/")[-1].upper()
        card = AgentCard(
            name=name,
            repo_url=discovery["url"],
            description=discovery.get("description", ""),
            capabilities=discovery.get("capabilities", []),
            dependencies=discovery.get("dependencies", []),
            entry_points=discovery.get("entry_points", {}),
            sampled_files=discovery.get("sampled_files", []),
            signal_tags=discovery.get("signal_tags", []),
            analysis_notes=discovery.get("analysis_notes", []),
            language=discovery.get("language", "Unknown"),
            license=discovery.get("license"),
            status=AgentStatus.READY,
        )

        self.agent_registry[card.name] = card
        self.logger.info(
            f"Agentized {card.name}: {len(card.capabilities)} capabilities"
        )
        return card

    def get_agent(self, name: str) -> Optional[AgentCard]:
        return self.agent_registry.get(name)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [card.to_dict() for card in self.agent_registry.values()]

    def find_agents_for_capability(self, capability: str) -> List[AgentCard]:
        return [
            card
            for card in self.agent_registry.values()
            if capability in card.capabilities and card.status == AgentStatus.READY
        ]


class COURIER(Titan):
    def __init__(self) -> None:
        super().__init__("COURIER", "A2A message transport")
        self.message_log: List[Dict[str, Any]] = []
        self.logger = logging.getLogger("HERMES.COURIER")

    def send(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        msg = {
            "from": from_agent,
            "to": to_agent,
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
        }
        self.message_log.append(msg)
        self.logger.info(f"A2A: {from_agent} -> {to_agent} [{message_type}]")
        return msg

    def get_messages_for(self, agent_name: str) -> List[Dict[str, Any]]:
        return [m for m in self.message_log if m["to"] == agent_name]


# ═══════════════════════════════════════════════════════════════════════
# OLYMPIAN
# ═══════════════════════════════════════════════════════════════════════


class HERMES_OLYMPIAN(Olympian):
    def __init__(self) -> None:
        super().__init__(name="HERMES", domain="Communications & Integration")
        self.iris = IRIS()
        self.hermes_bus = HERMES_BUS()
        self.courier = COURIER()
        self.titans = [self.iris, self.hermes_bus, self.courier]
        self.logger = logging.getLogger("HERMES")
        self.logger.setLevel(logging.INFO)
        self.repos_agentized: int = 0

    def deploy(self, component: Component) -> bool:
        self.status = DivisionStatus.DEPLOYING
        self.current_mission = component
        titan = self._select_titan(component)
        if titan is None:
            return False

        titan.deploy(component)
        component.status = "IN_PROGRESS"
        component.progress = max(component.progress, 0.4)
        self.report_intel(
            f"{titan.name} deployed for {component.name}",
            "INFO",
            {"titan": titan.name, "component": component.name},
        )
        self.status = DivisionStatus.ACTIVE
        return True

    def agentize_repo(self, repo_url: str) -> IngestResult:
        self.logger.info(f"Agentizing repo: {repo_url}")

        discovery = self.iris.discover_repo(repo_url)
        if "error" in discovery:
            return IngestResult(
                source_type=SourceType.REPO,
                source_url=repo_url,
                status="failed",
                items_ingested=0,
                errors=[discovery["error"]],
            )

        agent_card = self.hermes_bus.agentize(discovery)

        self.courier.send(
            from_agent="HERMES",
            to_agent="ATHENA",
            message_type="AGENT_REGISTERED",
            payload=agent_card.to_dict(),
        )

        self.repos_agentized += 1
        self.report_intel(
            f"Agentized {agent_card.name}: {len(agent_card.capabilities)} capabilities",
            "INFO",
            agent_card.to_dict(),
        )

        return IngestResult(
            source_type=SourceType.REPO,
            source_url=repo_url,
            status="success",
            items_ingested=1,
            agent_card=agent_card,
        )

    def _select_titan(self, component: Component) -> Optional[Titan]:
        name = component.name.lower()
        if any(kw in name for kw in ("webhook", "event", "trigger", "discover")):
            return self.iris
        if any(kw in name for kw in ("session", "message", "channel", "transport")):
            return self.courier
        return self.hermes_bus
