#!/usr/bin/env python3
"""
GitHub Scout Hero - Lieutenant-level reconnaissance agent

Responsibilities:
  - Search GitHub for repositories
  - Validate licenses
  - Assess code quality
  - Extract component information
  - Report findings to Titan commanders

"Eyes in the sky. Intelligence is power."
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from urllib import request as urllib_request, error as urllib_error
from urllib.parse import urlencode, quote
import base64
import logging
import json
import os
import re
import time
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════
# GITHUB API CLIENT
# ═══════════════════════════════════════════════════════════════════════

class GitHubAPIClient:
    """GitHub REST API client using stdlib urllib.

    Follows the same pattern as CoreMemoryClient in athena.py.
    Works authenticated (GITHUB_TOKEN env) or unauthenticated (lower rate limits).
    """

    API_BASE = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.rate_limit_remaining: Optional[int] = None
        self.rate_limit_reset: Optional[int] = None
        self.search_rate_remaining: Optional[int] = None
        self.search_rate_reset: Optional[int] = None
        self.logger = logging.getLogger("GitHubAPI")

    def _request(self, path: str, params: Optional[Dict[str, str]] = None) -> Optional[Dict]:
        """Make request to GitHub API. Returns parsed JSON or None on error."""
        url = f"{self.API_BASE}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        headers = {
            "User-Agent": "ATHENA-Scout/1.0",
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        req = urllib_request.Request(url, headers=headers)

        try:
            with urllib_request.urlopen(req, timeout=15) as resp:
                self._update_rate_limits(resp.headers, is_search="/search/" in path)
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib_error.HTTPError as exc:
            if exc.code in (403, 429):
                self.logger.warning(f"Rate limited on {path} (HTTP {exc.code})")
                self._wait_for_rate_limit(exc.headers)
                # Retry once
                try:
                    retry_req = urllib_request.Request(url, headers=headers)
                    with urllib_request.urlopen(retry_req, timeout=15) as resp:
                        self._update_rate_limits(resp.headers, is_search="/search/" in path)
                        body = resp.read().decode("utf-8")
                        return json.loads(body) if body else {}
                except Exception:
                    self.logger.warning(f"Retry failed for {path}")
                    return None
            elif exc.code == 404:
                return None
            else:
                self.logger.warning(f"GitHub API HTTP {exc.code} at {path}")
                return None
        except urllib_error.URLError as exc:
            self.logger.warning(f"GitHub API network error at {path}: {exc.reason}")
            return None
        except Exception as exc:
            self.logger.warning(f"GitHub API unexpected error at {path}: {exc}")
            return None

    def _update_rate_limits(self, headers, is_search: bool = False):
        """Parse rate limit headers from GitHub response."""
        try:
            remaining = headers.get("X-RateLimit-Remaining")
            reset = headers.get("X-RateLimit-Reset")
            if remaining is not None:
                remaining = int(remaining)
                if is_search:
                    self.search_rate_remaining = remaining
                else:
                    self.rate_limit_remaining = remaining
            if reset is not None:
                reset = int(reset)
                if is_search:
                    self.search_rate_reset = reset
                else:
                    self.rate_limit_reset = reset
            if remaining is not None and remaining < 10:
                self.logger.warning(f"GitHub API rate limit low: {remaining} remaining")
        except (ValueError, TypeError):
            pass

    def _wait_for_rate_limit(self, headers):
        """Wait for rate limit reset. Capped at 60 seconds."""
        wait = 60
        retry_after = headers.get("Retry-After") if headers else None
        reset = headers.get("X-RateLimit-Reset") if headers else None

        if retry_after:
            try:
                wait = min(int(retry_after), 60)
            except (ValueError, TypeError):
                pass
        elif reset:
            try:
                wait = min(max(int(reset) - int(time.time()), 1), 60)
            except (ValueError, TypeError):
                pass

        self.logger.info(f"Rate limited. Waiting {wait}s before retry...")
        time.sleep(wait)

    @property
    def is_authenticated(self) -> bool:
        """Whether a token is configured."""
        return bool(self.token)


# ═══════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Repository:
    """GitHub repository information"""
    name: str
    full_name: str
    url: str
    description: str
    stars: int
    language: str
    license: Optional[str]
    last_updated: datetime
    topics: List[str] = field(default_factory=list)
    
    # Quality metrics
    has_tests: bool = False
    has_docs: bool = False
    has_ci: bool = False
    open_issues: int = 0
    
    # Scout assessment
    quality_score: float = 0.0
    compatible_license: bool = False
    _default_branch: str = "main"
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "url": self.url,
            "description": self.description,
            "stars": self.stars,
            "language": self.language,
            "license": self.license,
            "last_updated": self.last_updated.isoformat(),
            "topics": self.topics,
            "has_tests": self.has_tests,
            "has_docs": self.has_docs,
            "has_ci": self.has_ci,
            "open_issues": self.open_issues,
            "quality_score": self.quality_score,
            "compatible_license": self.compatible_license
        }


@dataclass
class ComponentFindings:
    """What the scout found in a repository"""
    repository: Repository
    components_found: List[str]
    file_paths: Dict[str, str]  # component_name -> file_path
    dependencies: List[str]
    integration_notes: str
    extraction_difficulty: str  # LOW, MEDIUM, HIGH
    
    def to_dict(self) -> Dict:
        return {
            "repository": self.repository.to_dict(),
            "components_found": self.components_found,
            "file_paths": self.file_paths,
            "dependencies": self.dependencies,
            "integration_notes": self.integration_notes,
            "extraction_difficulty": self.extraction_difficulty
        }


@dataclass
class ScoutReport:
    """Report from scouting mission"""
    hero_name: str
    mission: str
    repositories_scanned: int
    repositories_qualified: int
    findings: List[ComponentFindings]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "hero_name": self.hero_name,
            "mission": self.mission,
            "repositories_scanned": self.repositories_scanned,
            "repositories_qualified": self.repositories_qualified,
            "findings": [f.to_dict() for f in self.findings],
            "timestamp": self.timestamp.isoformat()
        }


# ═══════════════════════════════════════════════════════════════════════
# GITHUB SCOUT HERO
# ═══════════════════════════════════════════════════════════════════════

class GitHubScout:
    """
    Lieutenant-level Hero for GitHub reconnaissance
    
    Reports to: Titan commanders (ORPHEUS, HELIOS, etc.)
    Commands: Warrior-level code extractors
    """
    
    # Licenses compatible with commercial use
    COMPATIBLE_LICENSES = [
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "0BSD"
    ]
    
    # Licenses to avoid
    INCOMPATIBLE_LICENSES = [
        "GPL-3.0",
        "GPL-2.0",
        "AGPL-3.0",
        "LGPL-3.0"
    ]
    
    def __init__(self, name: str, specialty: str):
        self.name = name
        self.specialty = specialty
        self.status = "STANDBY"
        self.current_mission: Optional[str] = None
        
        # Combat statistics
        self.repos_scanned: int = 0
        self.repos_qualified: int = 0
        self.components_found: int = 0
        
        # API client
        self.api_client = GitHubAPIClient()
        
        # Scout cache (avoid re-scanning)
        self._cache_entries: Dict[str, Dict] = {}
        self.cache_file = Path(f"./{name}_cache.json")
        self._load_cache()
        
        self.logger = logging.getLogger(f"HERO:{name}")
        self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"⚔️  {name} Hero reporting for duty")
        self.logger.info(f"   Specialty: {specialty}")
    
    def _load_cache(self):
        """Load cached data with version check"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("version") == 2:
                    self._cache_entries = data.get("entries", {})
                else:
                    self._cache_entries = {}
            except (json.JSONDecodeError, OSError):
                self._cache_entries = {}
    
    def _save_cache(self):
        """Persist cache with version marker"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({"version": 2, "entries": self._cache_entries}, f, indent=2)
        except OSError as exc:
            self.logger.warning(f"Cache save failed: {exc}")
    
    def _get_cached(self, key: str, max_age_seconds: int = 3600) -> Optional[Any]:
        """Get cached value if not expired. Returns None if missing or stale."""
        entry = self._cache_entries.get(key)
        if entry is None:
            return None
        try:
            cached_at = datetime.fromisoformat(entry["cached_at"])
            age = (datetime.now() - cached_at).total_seconds()
            if age > max_age_seconds:
                del self._cache_entries[key]
                return None
            return entry["data"]
        except (KeyError, ValueError, TypeError):
            self._cache_entries.pop(key, None)
            return None
    
    def _set_cached(self, key: str, data: Any):
        """Cache a value with timestamp."""
        self._cache_entries[key] = {
            "data": data,
            "cached_at": datetime.now().isoformat(),
        }
        self._save_cache()
    
    # ═══════════════════════════════════════════════════════════════
    # RECONNAISSANCE OPERATIONS
    # ═══════════════════════════════════════════════════════════════
    
    def scout_repositories(
        self, 
        query: str,
        min_stars: int = 100,
        max_results: int = 10
    ) -> List[Repository]:
        """
        Scout GitHub for repositories matching criteria
        
        Args:
            query: Search query (e.g., "wake word detection python")
            min_stars: Minimum stars threshold
            max_results: Maximum repositories to return
            
        Returns:
            List of qualified repositories
        """
        self.logger.info(f"🔍 Scouting mission: '{query}'")
        self.logger.info(f"   Criteria: {min_stars}+ stars, max {max_results} results")
        
        self.status = "SCOUTING"
        self.current_mission = query
        
        repos = self._search_github(query, min_stars, max_results)
        
        self.repos_scanned += len(repos)
        
        # Filter and qualify
        qualified = []
        for repo in repos:
            if self._qualify_repository(repo):
                qualified.append(repo)
                self.repos_qualified += 1
        
        self.logger.info(f"✓ Scanned {len(repos)} repositories")
        self.logger.info(f"✓ {len(qualified)} qualified for harvest")
        
        self.status = "STANDBY"
        return qualified
    
    def _search_github(
        self,
        query: str,
        min_stars: int,
        max_results: int,
    ) -> List[Repository]:
        """Search GitHub via REST API with cache and fallback to simulation."""
        cache_key = f"search:{query.lower().strip()}:{min_stars}"
        cached = self._get_cached(cache_key, max_age_seconds=3600)
        if cached:
            self.logger.info("   Using cached search results")
            return [self._repo_from_dict(r) for r in cached]

        data = self.api_client._request(
            "/search/repositories",
            params={
                "q": f"{query} stars:>{min_stars}",
                "sort": "stars",
                "order": "desc",
                "per_page": str(min(max_results, 30)),
            },
        )
        if data is None:
            self.logger.warning("GitHub search failed, falling back to simulation")
            return self._search_fallback(query, min_stars, max_results)

        repos: List[Repository] = []
        for item in data.get("items", [])[:max_results]:
            repo = self._parse_repository(item)
            self._detect_quality_signals(repo)
            repos.append(repo)

        if repos:
            self._set_cached(cache_key, [r.to_dict() for r in repos])
        return repos

    def _parse_repository(self, item: Dict) -> Repository:
        """Parse a GitHub API repository item into a Repository dataclass."""
        license_info = item.get("license") or {}
        license_id = license_info.get("spdx_id") if isinstance(license_info, dict) else None
        if license_id == "NOASSERTION":
            license_id = None

        updated_str = item.get("updated_at", "")
        try:
            last_updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, AttributeError):
            last_updated = datetime.now()

        repo = Repository(
            name=item.get("name", ""),
            full_name=item.get("full_name", ""),
            url=item.get("html_url", ""),
            description=item.get("description") or "",
            stars=item.get("stargazers_count", 0),
            language=item.get("language") or "Unknown",
            license=license_id,
            last_updated=last_updated,
            topics=item.get("topics", []),
            open_issues=item.get("open_issues_count", 0),
        )
        repo._default_branch = item.get("default_branch", "main")
        return repo

    def _detect_quality_signals(self, repo: Repository):
        """Fetch file tree and detect tests/docs/CI from real repo structure."""
        branch = getattr(repo, "_default_branch", "main")
        cache_key = f"tree:{repo.full_name}"
        tree_paths = self._get_cached(cache_key, max_age_seconds=86400)

        if tree_paths is None:
            data = self.api_client._request(
                f"/repos/{repo.full_name}/git/trees/{branch}",
                params={"recursive": "1"},
            )
            if data and "tree" in data:
                tree_paths = [
                    {"path": e["path"], "type": e["type"]}
                    for e in data["tree"]
                ]
                self._set_cached(cache_key, tree_paths)
            else:
                return

        for entry in tree_paths:
            p = entry.get("path", "").lower()
            if not repo.has_tests and (
                p.startswith("test/") or p.startswith("tests/")
                or p.endswith("_test.py") or p.startswith("test_")
                or p in ("pytest.ini", "tox.ini", "conftest.py")
            ):
                repo.has_tests = True
            if not repo.has_docs and (
                p.startswith("docs/") or p.startswith("doc/")
                or p in ("readme.md", "contributing.md", "changelog.md")
            ):
                repo.has_docs = True
            if not repo.has_ci and (
                p.startswith(".github/workflows/")
                or p in (".travis.yml", ".circleci/config.yml",
                         "jenkinsfile", ".gitlab-ci.yml", "azure-pipelines.yml")
            ):
                repo.has_ci = True

    def _repo_from_dict(self, d: Dict) -> Repository:
        """Reconstruct a Repository from its to_dict() output."""
        try:
            last_updated = datetime.fromisoformat(d["last_updated"])
        except (KeyError, ValueError):
            last_updated = datetime.now()

        return Repository(
            name=d.get("name", ""),
            full_name=d.get("full_name", ""),
            url=d.get("url", ""),
            description=d.get("description", ""),
            stars=d.get("stars", 0),
            language=d.get("language", "Unknown"),
            license=d.get("license"),
            last_updated=last_updated,
            topics=d.get("topics", []),
            has_tests=d.get("has_tests", False),
            has_docs=d.get("has_docs", False),
            has_ci=d.get("has_ci", False),
            open_issues=d.get("open_issues", 0),
            quality_score=d.get("quality_score", 0.0),
            compatible_license=d.get("compatible_license", False),
        )

    def _search_fallback(
        self,
        query: str,
        min_stars: int,
        max_results: int,
    ) -> List[Repository]:
        """Fallback simulation data when GitHub API is unavailable."""
        if "wake word" in query.lower() or "voice" in query.lower():
            return [
                Repository(
                    name="porcupine",
                    full_name="Picovoice/porcupine",
                    url="https://github.com/Picovoice/porcupine",
                    description="On-device wake word detection",
                    stars=3247,
                    language="Python",
                    license="Apache-2.0",
                    last_updated=datetime.now() - timedelta(days=15),
                    topics=["wake-word", "voice", "ai"],
                    has_tests=True,
                    has_docs=True,
                    has_ci=True,
                    open_issues=23,
                ),
                Repository(
                    name="whisper",
                    full_name="openai/whisper",
                    url="https://github.com/openai/whisper",
                    description="Robust Speech Recognition",
                    stars=45123,
                    language="Python",
                    license="MIT",
                    last_updated=datetime.now() - timedelta(days=7),
                    topics=["speech-recognition", "ml", "ai"],
                    has_tests=True,
                    has_docs=True,
                    has_ci=True,
                    open_issues=156,
                ),
                Repository(
                    name="TTS",
                    full_name="coqui-ai/TTS",
                    url="https://github.com/coqui-ai/TTS",
                    description="Deep learning for Text to Speech",
                    stars=18234,
                    language="Python",
                    license="MPL-2.0",
                    last_updated=datetime.now() - timedelta(days=3),
                    topics=["tts", "speech-synthesis", "deep-learning"],
                    has_tests=True,
                    has_docs=True,
                    has_ci=True,
                    open_issues=89,
                ),
            ]
        return []
    
    def _qualify_repository(self, repo: Repository) -> bool:
        """
        Assess if repository meets quality standards
        
        Criteria:
          - Compatible license
          - Recent activity (< 6 months)
          - Has documentation
          - Not too many open issues
        """
        
        # Check license
        if repo.license:
            repo.compatible_license = repo.license in self.COMPATIBLE_LICENSES
            if repo.license in self.INCOMPATIBLE_LICENSES:
                self.logger.info(f"   ✗ {repo.name}: Incompatible license ({repo.license})")
                return False
        else:
            self.logger.info(f"   ✗ {repo.name}: No license")
            return False
        
        # Check activity
        age = datetime.now() - repo.last_updated
        if age > timedelta(days=180):
            self.logger.info(f"   ✗ {repo.name}: Stale (last update {age.days} days ago)")
            return False
        
        # Check documentation
        if not repo.has_docs:
            self.logger.info(f"   ⚠️  {repo.name}: No docs (proceeding anyway)")
        
        # Calculate quality score
        repo.quality_score = self._calculate_quality_score(repo)
        
        if repo.quality_score < 0.5:
            self.logger.info(f"   ✗ {repo.name}: Low quality score ({repo.quality_score:.2f})")
            return False
        
        self.logger.info(f"   ✓ {repo.name}: Qualified (score: {repo.quality_score:.2f})")
        return True
    
    def _calculate_quality_score(self, repo: Repository) -> float:
        """
        Calculate quality score (0.0 to 1.0)
        
        Factors:
          - Stars (normalized)
          - Has tests (+0.2)
          - Has docs (+0.2)
          - Has CI (+0.1)
          - Low open issues (+0.1)
          - Recent activity (+0.1)
        """
        score = 0.0
        
        # Stars (max 0.3, normalized to 10k stars)
        score += min(repo.stars / 10000, 0.3)
        
        # Test coverage
        if repo.has_tests:
            score += 0.2
        
        # Documentation
        if repo.has_docs:
            score += 0.2
        
        # CI/CD
        if repo.has_ci:
            score += 0.1
        
        # Issue management (fewer is better)
        if repo.open_issues < 50:
            score += 0.1
        
        # Recent activity
        age = datetime.now() - repo.last_updated
        if age < timedelta(days=30):
            score += 0.1
        
        return min(score, 1.0)
    
    # ═══════════════════════════════════════════════════════════════
    # COMPONENT ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    
    def analyze_components(
        self, 
        repo: Repository,
        target_components: List[str]
    ) -> ComponentFindings:
        """
        Analyze repository for specific components
        
        Args:
            repo: Repository to analyze
            target_components: What we're looking for
            
        Returns:
            Component findings report
        """
        self.logger.info(f"🔬 Analyzing {repo.name} for components...")
        
        findings = self._analyze_repo_components(repo, target_components)
        
        self.components_found += len(findings.components_found)
        
        self.logger.info(f"   Found {len(findings.components_found)} components")
        for comp in findings.components_found:
            self.logger.info(f"     - {comp}")
        
        return findings
    
    def _analyze_repo_components(
        self,
        repo: Repository,
        target_components: List[str],
    ) -> ComponentFindings:
        """Analyze real repo structure for target components with fallback."""
        tree = self._get_file_tree(repo)
        if tree is None:
            self.logger.warning(f"Could not fetch tree for {repo.full_name}, using fallback")
            return self._analysis_fallback(repo, target_components)

        found_components, file_paths = self._match_components_to_files(tree, target_components)
        dependencies = self._extract_dependencies(repo)

        relevant_file_count = len(file_paths)
        dep_count = len(dependencies)
        if relevant_file_count <= 5 and dep_count <= 5:
            difficulty = "LOW"
        elif relevant_file_count <= 20 and dep_count <= 15:
            difficulty = "MEDIUM"
        else:
            difficulty = "HIGH"

        compat = "compatible" if repo.compatible_license else "review required"
        notes = (
            f"Found {len(found_components)} relevant components in {repo.full_name}. "
            f"Requires {dep_count} dependencies. "
            f"Primary language: {repo.language}. "
            f"License: {repo.license} ({compat})."
        )

        return ComponentFindings(
            repository=repo,
            components_found=found_components,
            file_paths=file_paths,
            dependencies=dependencies,
            integration_notes=notes,
            extraction_difficulty=difficulty,
        )

    def _get_file_tree(self, repo: Repository) -> Optional[List[Dict]]:
        """Fetch repo file tree, using cache or API."""
        cache_key = f"tree:{repo.full_name}"
        cached = self._get_cached(cache_key, max_age_seconds=86400)
        if cached is not None:
            return cached

        branch = getattr(repo, "_default_branch", "main")
        for try_branch in [branch, "master"] if branch != "master" else ["master", "main"]:
            data = self.api_client._request(
                f"/repos/{repo.full_name}/git/trees/{try_branch}",
                params={"recursive": "1"},
            )
            if data and "tree" in data:
                tree_paths = [
                    {"path": e["path"], "type": e["type"]}
                    for e in data["tree"]
                ]
                self._set_cached(cache_key, tree_paths)
                return tree_paths
        return None

    def _match_components_to_files(
        self,
        tree: List[Dict],
        target_components: List[str],
    ) -> Tuple[List[str], Dict[str, str]]:
        """Match target component names against file paths in the tree."""
        found: List[str] = []
        file_paths: Dict[str, str] = {}
        code_extensions = {".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".cpp", ".rb"}

        for component in target_components:
            keywords = [kw for kw in component.lower().replace("-", "_").split("_") if len(kw) > 2]
            best_path: Optional[str] = None
            best_score = 0

            for entry in tree:
                if entry.get("type") != "blob":
                    continue
                p = entry["path"].lower()
                ext = os.path.splitext(p)[1]
                if ext not in code_extensions:
                    continue

                # Score by keyword overlap
                score = sum(1 for kw in keywords if kw in p)
                # Bonus for full component name match
                if component.lower().replace("_", "") in p.replace("_", "").replace("/", ""):
                    score += len(keywords)

                if score > best_score:
                    best_score = score
                    best_path = entry["path"]

            if best_path and best_score >= 2:
                found.append(component)
                file_paths[component] = best_path

        return found, file_paths

    def _extract_dependencies(self, repo: Repository) -> List[str]:
        """Extract dependencies from requirements.txt / setup.py / pyproject.toml."""
        cache_key = f"deps:{repo.full_name}"
        cached = self._get_cached(cache_key, max_age_seconds=86400)
        if cached is not None:
            return cached

        deps: List[str] = []

        # requirements.txt
        content = self._fetch_file_content(repo.full_name, "requirements.txt")
        if content:
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    pkg = re.split(r"[><=!~;\[]", line)[0].strip()
                    if pkg and pkg not in deps:
                        deps.append(pkg)

        # setup.py
        content = self._fetch_file_content(repo.full_name, "setup.py")
        if content:
            match = re.search(r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if match:
                for item in re.findall(r"[\"']([^\"']+)[\"']", match.group(1)):
                    pkg = re.split(r"[><=!~;\[]", item)[0].strip()
                    if pkg and pkg not in deps:
                        deps.append(pkg)

        # pyproject.toml
        content = self._fetch_file_content(repo.full_name, "pyproject.toml")
        if content:
            match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if match:
                for item in re.findall(r"[\"']([^\"']+)[\"']", match.group(1)):
                    pkg = re.split(r"[><=!~;\[]", item)[0].strip()
                    if pkg and pkg not in deps:
                        deps.append(pkg)

        self._set_cached(cache_key, deps)
        return deps

    def _fetch_file_content(self, full_name: str, path: str) -> Optional[str]:
        """Fetch a single file's content from GitHub API."""
        cache_key = f"content:{full_name}:{path}"
        cached = self._get_cached(cache_key, max_age_seconds=86400)
        if cached is not None:
            return cached

        data = self.api_client._request(f"/repos/{full_name}/contents/{quote(path)}")
        if data is None or data.get("encoding") != "base64":
            return None

        try:
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        except Exception:
            return None

        self._set_cached(cache_key, content)
        return content

    def _analysis_fallback(
        self,
        repo: Repository,
        target_components: List[str],
    ) -> ComponentFindings:
        """Fallback simulation data when repo analysis fails."""
        found_components: List[str] = []
        file_paths: Dict[str, str] = {}
        dependencies: List[str] = []

        if "porcupine" in repo.name.lower():
            found_components = ["wake_word_detection", "keyword_spotting"]
            file_paths = {
                "wake_word_detection": "porcupine/python/porcupine.py",
                "keyword_spotting": "porcupine/python/util.py",
            }
            dependencies = ["pvporcupine", "numpy"]
            difficulty = "LOW"
            notes = "Well-structured, easy to extract. Requires API key for advanced features."
        elif "whisper" in repo.name.lower():
            found_components = ["speech_to_text", "audio_transcription"]
            file_paths = {
                "speech_to_text": "whisper/transcribe.py",
                "audio_transcription": "whisper/audio.py",
            }
            dependencies = ["torch", "numpy", "ffmpeg-python"]
            difficulty = "MEDIUM"
            notes = "Requires PyTorch. Model loading can be abstracted."
        elif "TTS" in repo.name or "tts" in repo.name.lower():
            found_components = ["text_to_speech", "voice_synthesis"]
            file_paths = {
                "text_to_speech": "TTS/api.py",
                "voice_synthesis": "TTS/utils/synthesizer.py",
            }
            dependencies = ["TTS", "torch", "soundfile"]
            difficulty = "MEDIUM"
            notes = "Powerful but complex. Consider using high-level API."
        else:
            difficulty = "UNKNOWN"
            notes = "Repository requires manual analysis."

        return ComponentFindings(
            repository=repo,
            components_found=found_components,
            file_paths=file_paths,
            dependencies=dependencies,
            integration_notes=notes,
            extraction_difficulty=difficulty,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # MISSION REPORTING
    # ═══════════════════════════════════════════════════════════════
    
    def generate_scout_report(
        self,
        query: str,
        qualified_repos: List[Repository],
        findings: List[ComponentFindings]
    ) -> ScoutReport:
        """Generate comprehensive scout report"""
        
        report = ScoutReport(
            hero_name=self.name,
            mission=query,
            repositories_scanned=self.repos_scanned,
            repositories_qualified=len(qualified_repos),
            findings=findings
        )
        
        return report
    
    def get_status(self) -> Dict:
        """Get current status"""
        return {
            "name": self.name,
            "specialty": self.specialty,
            "status": self.status,
            "current_mission": self.current_mission,
            "stats": {
                "repos_scanned": self.repos_scanned,
                "repos_qualified": self.repos_qualified,
                "components_found": self.components_found
            }
        }


# ═══════════════════════════════════════════════════════════════════════
# SPECIALIZED SCOUTS
# ═══════════════════════════════════════════════════════════════════════

class ACHILLES(GitHubScout):
    """Fast execution - focuses on performance-critical code"""
    def __init__(self):
        super().__init__("ACHILLES", "High-performance components")


class ODYSSEUS(GitHubScout):
    """Problem solver - finds creative solutions"""
    def __init__(self):
        super().__init__("ODYSSEUS", "Complex integration patterns")


class PERSEUS(GitHubScout):
    """Bug slayer - finds robust, well-tested code"""
    def __init__(self):
        super().__init__("PERSEUS", "Battle-tested components")


# ═══════════════════════════════════════════════════════════════════════
# DEMONSTRATION
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                    ⚔️  GITHUB SCOUT HEROES  ⚔️                            ║
║                                                                           ║
║                    "Intelligence is power"                                ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize heroes
    achilles = ACHILLES()
    odysseus = ODYSSEUS()
    perseus = PERSEUS()
    
    print("\n⚔️  Heroes deployed:")
    print(f"   - {achilles.name} ({achilles.specialty})")
    print(f"   - {odysseus.name} ({odysseus.specialty})")
    print(f"   - {perseus.name} ({perseus.specialty})")
    
    # Scout mission
    print("\n" + "=" * 70)
    print("MISSION: Scout voice recognition repositories")
    print("=" * 70)
    
    repos = achilles.scout_repositories(
        query="wake word detection voice recognition",
        min_stars=1000,
        max_results=5
    )
    
    # Analyze components
    print("\n" + "=" * 70)
    print("COMPONENT ANALYSIS")
    print("=" * 70)
    
    target_components = ["wake_word_detection", "speech_to_text", "text_to_speech"]
    findings = []
    
    for repo in repos:
        result = achilles.analyze_components(repo, target_components)
        findings.append(result)
    
    # Generate report
    report = achilles.generate_scout_report(
        query="wake word detection voice recognition",
        qualified_repos=repos,
        findings=findings
    )
    
    # Display report
    print("\n" + "=" * 70)
    print("SCOUT REPORT")
    print("=" * 70)
    print(f"Hero: {report.hero_name}")
    print(f"Mission: {report.mission}")
    print(f"Repositories Scanned: {report.repositories_scanned}")
    print(f"Repositories Qualified: {report.repositories_qualified}")
    print(f"Components Found: {sum(len(f.components_found) for f in report.findings)}")
    
    print("\nFindings:")
    for finding in report.findings:
        print(f"\n  📦 {finding.repository.name}")
        print(f"     License: {finding.repository.license}")
        print(f"     Quality: {finding.repository.quality_score:.0%}")
        print(f"     Components: {', '.join(finding.components_found)}")
        print(f"     Difficulty: {finding.extraction_difficulty}")
        print(f"     Notes: {finding.integration_notes}")
    
    print("\n✓ Scout mission complete")
    print(f"   Total stats: {achilles.get_status()['stats']}")
