"""APOLLO — Frontend, Creative & Research Ingestion Division."""

import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib import error as urllib_error, request as urllib_request
from urllib.parse import quote_plus, urlencode

from athena.olympians.base import Olympian, Titan, TitanReport
from athena.types import (
    Component,
    DivisionStatus,
    IngestResult,
    ResearchArticle,
    SourceType,
)


class HELIOS(Titan):
    def __init__(self):
        super().__init__("HELIOS", "UI Component Systems")
        self.target_repos = [
            "shadcn/ui",
            "chakra-ui/chakra-ui",
            "mui/material-ui",
            "radix-ui/primitives",
            "tailwindlabs/tailwindcss",
        ]
        self.component_types = [
            "button",
            "input",
            "modal",
            "dropdown",
            "card",
            "table",
            "form",
            "navigation",
            "layout",
        ]

    def scout_repositories(self) -> List[str]:
        return self.target_repos

    def extract_components(self, repo: str) -> List[Dict[str, Any]]:
        return [
            {
                "name": f"{comp}_component",
                "repo": repo,
                "type": comp,
                "quality_score": 0.85,
            }
            for comp in self.component_types[:3]
        ]


class SELENE(Titan):
    def __init__(self):
        super().__init__("SELENE", "Theming & Visual Design")
        self.target_patterns = [
            "dark_mode_toggle",
            "theme_provider",
            "color_scheme_generator",
            "css_variables_system",
        ]


class MNEMOSYNE(Titan):
    def __init__(self):
        super().__init__("MNEMOSYNE", "State Management")
        self.target_repos = [
            "pmndrs/zustand",
            "pmndrs/jotai",
            "reduxjs/redux",
            "statelyai/xstate",
        ]


class CALLIOPE(Titan):
    def __init__(self):
        super().__init__("CALLIOPE", "Content Systems")


class TERPSICHORE(Titan):
    def __init__(self):
        super().__init__("TERPSICHORE", "Animation & Motion")
        self.target_repos = [
            "framer/motion",
            "greensock/GSAP",
            "pmndrs/react-spring",
        ]


class ORPHEUS(Titan):
    def __init__(self):
        super().__init__("ORPHEUS", "Voice & Audio Systems")
        self.scout: Optional[Any] = None
        try:
            from athena.agents.github_scout import GitHubScout

            self.scout = GitHubScout("ORPHEUS_SCOUT", "Voice & Audio Systems")
        except ImportError:
            pass
        self.target_repos = [
            "Picovoice/porcupine",
            "openai/whisper",
            "coqui-ai/TTS",
            "speechbrain/speechbrain",
            "MycroftAI/mycroft-precise",
        ]
        self.voice_components = [
            "wake_word_detection",
            "speech_to_text",
            "text_to_speech",
            "audio_preprocessing",
            "voice_activity_detection",
            "noise_cancellation",
        ]

    def scout_voice_repos(self) -> List[Dict[str, Any]]:
        if not self.scout:
            return []
        repos = self.scout.scout_repositories(
            query="voice recognition wake word speech python",
            min_stars=500,
            max_results=5,
        )

        results = []
        for repo in repos:
            findings = self.scout.analyze_components(repo, self.voice_components)
            results.append(
                {
                    "repo": repo.full_name,
                    "license": repo.license,
                    "components": findings.components_found,
                    "quality_score": repo.quality_score,
                    "dependencies": findings.dependencies,
                }
            )
        return results


# ═══════════════════════════════════════════════════════════════════════
# RESEARCH INGESTION TITANS
# ═══════════════════════════════════════════════════════════════════════

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


class SCHOLAR(Titan):
    ARXIV_API = "http://export.arxiv.org/api/query"

    def __init__(self) -> None:
        super().__init__("SCHOLAR", "ArXiv paper ingestion")
        self.logger = logging.getLogger("APOLLO.SCHOLAR")

    def search_arxiv(self, query: str, max_results: int = 5) -> List[ResearchArticle]:
        params = urlencode(
            {
                "search_query": f"all:{query}",
                "start": "0",
                "max_results": str(max_results),
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
        )
        url = f"{self.ARXIV_API}?{params}"

        xml_text = self._fetch_url(url)
        if not xml_text:
            return []

        return self._parse_atom_feed(xml_text)

    def fetch_paper(self, arxiv_url: str) -> Optional[ResearchArticle]:
        arxiv_id = self._extract_arxiv_id(arxiv_url)
        if not arxiv_id:
            self.logger.warning(f"Could not parse arxiv ID from: {arxiv_url}")
            return None

        url = f"{self.ARXIV_API}?id_list={arxiv_id}"
        xml_text = self._fetch_url(url)
        if not xml_text:
            return None

        articles = self._parse_atom_feed(xml_text)
        return articles[0] if articles else None

    def _extract_arxiv_id(self, url_or_id: str) -> Optional[str]:
        # https://arxiv.org/abs/2509.08088v1 or /html/ or /pdf/
        match = re.search(r"arxiv\.org/(?:abs|html|pdf)/(\d+\.\d+(?:v\d+)?)", url_or_id)
        if match:
            return match.group(1)
        # bare id like "2509.08088v1"
        match = re.match(r"^(\d+\.\d+(?:v\d+)?)$", url_or_id.strip())
        if match:
            return match.group(1)
        return None

    def _fetch_url(self, url: str) -> Optional[str]:
        req = urllib_request.Request(url, headers={"User-Agent": "ATHENA-SCHOLAR/1.0"})
        try:
            with urllib_request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib_error.HTTPError, urllib_error.URLError, Exception) as exc:
            self.logger.warning(f"Fetch failed for {url}: {exc}")
            return None

    def _parse_atom_feed(self, xml_text: str) -> List[ResearchArticle]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            self.logger.warning(f"XML parse error: {exc}")
            return []

        articles: List[ResearchArticle] = []
        for entry in root.findall(f"{ATOM_NS}entry"):
            title = (entry.findtext(f"{ATOM_NS}title") or "").strip()
            title = re.sub(r"\s+", " ", title)

            abstract = (entry.findtext(f"{ATOM_NS}summary") or "").strip()
            abstract = re.sub(r"\s+", " ", abstract)

            authors = [
                (a.findtext(f"{ATOM_NS}name") or "").strip()
                for a in entry.findall(f"{ATOM_NS}author")
            ]

            published = entry.findtext(f"{ATOM_NS}published")

            arxiv_id_el = entry.findtext(f"{ATOM_NS}id") or ""
            arxiv_id = arxiv_id_el.split("/abs/")[-1] if "/abs/" in arxiv_id_el else ""

            categories = [
                c.get("term", "") for c in entry.findall(f"{ARXIV_NS}primary_category")
            ]
            categories += [
                c.get("term", "")
                for c in entry.findall(f"{ATOM_NS}category")
                if c.get("term", "") not in categories
            ]

            link_el = entry.find(f"{ATOM_NS}id")
            source_url = (
                link_el.text.strip() if link_el is not None and link_el.text else ""
            )

            if title:
                articles.append(
                    ResearchArticle(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        source_url=source_url,
                        source="arxiv",
                        published_date=published,
                        arxiv_id=arxiv_id,
                        categories=[c for c in categories if c],
                    )
                )

        return articles


class NAVIGATOR(Titan):
    def __init__(self) -> None:
        super().__init__("NAVIGATOR", "Web content fetching")
        self.logger = logging.getLogger("APOLLO.NAVIGATOR")

    def fetch_url(self, url: str) -> Optional[Dict[str, Any]]:
        req = urllib_request.Request(
            url,
            headers={
                "User-Agent": "ATHENA-NAVIGATOR/1.0",
                "Accept": "text/html,application/xhtml+xml,*/*",
            },
        )
        try:
            with urllib_request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except (urllib_error.HTTPError, urllib_error.URLError, Exception) as exc:
            self.logger.warning(f"Fetch failed for {url}: {exc}")
            return None

        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL
        )
        title = title_match.group(1).strip() if title_match else ""

        text = re.sub(
            r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(
            r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return {
            "url": url,
            "title": re.sub(r"\s+", " ", title),
            "content_excerpt": text[:5000],
            "content_length": len(text),
            "fetched_at": datetime.now().isoformat(),
        }


class SCRIBE(Titan):
    def __init__(self) -> None:
        super().__init__("SCRIBE", "Document text processing")
        self.logger = logging.getLogger("APOLLO.SCRIBE")

    def process_text(self, text: str, source_url: str) -> ResearchArticle:
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        title = lines[0] if lines else "Untitled"

        authors: List[str] = []
        for line in lines[:10]:
            author_match = re.match(r"(?:by|authors?:?)\s+(.+)", line, re.IGNORECASE)
            if author_match:
                raw = author_match.group(1)
                authors = [a.strip() for a in re.split(r"[,;&]", raw) if a.strip()]
                break

        abstract = text[:1000].strip()

        return ResearchArticle(
            title=title[:200],
            authors=authors,
            abstract=abstract,
            source_url=source_url,
            source="document",
        )


# ═══════════════════════════════════════════════════════════════════════
# OLYMPIAN
# ═══════════════════════════════════════════════════════════════════════


class APOLLO_OLYMPIAN(Olympian):
    def __init__(self) -> None:
        super().__init__(name="APOLLO", domain="Frontend & Creative")

        self.helios = HELIOS()
        self.selene = SELENE()
        self.mnemosyne = MNEMOSYNE()
        self.calliope = CALLIOPE()
        self.terpsichore = TERPSICHORE()
        self.orpheus = ORPHEUS()
        self.scholar = SCHOLAR()
        self.navigator = NAVIGATOR()
        self.scribe = SCRIBE()

        self.titans = [
            self.helios,
            self.selene,
            self.mnemosyne,
            self.calliope,
            self.terpsichore,
            self.orpheus,
            self.scholar,
            self.navigator,
            self.scribe,
        ]

        self.logger = logging.getLogger("APOLLO")
        self.logger.setLevel(logging.INFO)

        self.repos_scouted: int = 0
        self.components_harvested: int = 0
        self.integrations_created: int = 0
        self.papers_ingested: int = 0
        self.urls_ingested: int = 0

    def deploy(self, component: Component) -> bool:
        self.status = DivisionStatus.DEPLOYING
        self.current_mission = component

        titan = self._select_titan(component)

        if titan:
            titan.deploy(component)
            self.report_intel(
                f"{titan.name} deployed for {component.name}",
                "INFO",
                {"titan": titan.name, "component": component.name},
            )
            self.status = DivisionStatus.ACTIVE
            self._execute_scouting(titan, component)
            return True
        else:
            self.report_intel(f"No suitable Titan for {component.name}", "WARNING")
            return False

    def ingest_arxiv(self, query: str, max_results: int = 5) -> IngestResult:
        self.logger.info(f"ArXiv search: {query}")
        articles = self.scholar.search_arxiv(query, max_results)
        self.papers_ingested += len(articles)

        return IngestResult(
            source_type=SourceType.ARTICLE,
            source_url=f"arxiv:search:{query}",
            status="success" if articles else "failed",
            items_ingested=len(articles),
            articles=articles,
        )

    def ingest_paper(self, arxiv_url: str) -> IngestResult:
        self.logger.info(f"Fetching paper: {arxiv_url}")
        article = self.scholar.fetch_paper(arxiv_url)

        if article:
            self.papers_ingested += 1
            return IngestResult(
                source_type=SourceType.ARTICLE,
                source_url=arxiv_url,
                status="success",
                items_ingested=1,
                articles=[article],
            )

        return IngestResult(
            source_type=SourceType.ARTICLE,
            source_url=arxiv_url,
            status="failed",
            items_ingested=0,
            errors=[f"Could not fetch paper: {arxiv_url}"],
        )

    def ingest_url(self, url: str) -> IngestResult:
        self.logger.info(f"Fetching URL: {url}")
        page = self.navigator.fetch_url(url)

        if not page:
            return IngestResult(
                source_type=SourceType.WEB,
                source_url=url,
                status="failed",
                items_ingested=0,
                errors=[f"Could not fetch URL: {url}"],
            )

        article = self.scribe.process_text(page["content_excerpt"], url)
        if page["title"]:
            article.title = page["title"]
        article.source = "web"

        self.urls_ingested += 1
        return IngestResult(
            source_type=SourceType.WEB,
            source_url=url,
            status="success",
            items_ingested=1,
            articles=[article],
        )

    def _select_titan(self, component: Component) -> Optional[Titan]:
        component_name = component.name.lower()

        research_keywords = [
            "research",
            "paper",
            "arxiv",
            "article",
            "ingest",
            "scholar",
        ]
        if any(kw in component_name for kw in research_keywords):
            return self.scholar

        fetch_keywords = ["fetch", "url", "web", "navigate", "crawl"]
        if any(kw in component_name for kw in fetch_keywords):
            return self.navigator

        document_keywords = ["document", "parse", "scribe", "extract", "pdf"]
        if any(kw in component_name for kw in document_keywords):
            return self.scribe

        voice_keywords = ["voice", "audio", "speech", "wake", "stt", "tts", "sound"]
        if any(kw in component_name for kw in voice_keywords):
            return self.orpheus

        ui_keywords = ["ui", "component", "button", "input", "form", "layout"]
        if any(kw in component_name for kw in ui_keywords):
            return self.helios

        theme_keywords = ["theme", "dark", "color", "style"]
        if any(kw in component_name for kw in theme_keywords):
            return self.selene

        state_keywords = ["state", "store", "context", "redux"]
        if any(kw in component_name for kw in state_keywords):
            return self.mnemosyne

        anim_keywords = ["animation", "motion", "transition", "animate"]
        if any(kw in component_name for kw in anim_keywords):
            return self.terpsichore

        content_keywords = ["content", "text", "copy", "i18n", "translation"]
        if any(kw in component_name for kw in content_keywords):
            return self.calliope

        return self.helios

    def _execute_scouting(self, titan: Titan, component: Component) -> None:
        if isinstance(titan, ORPHEUS):
            repos = titan.scout_voice_repos()
            self.repos_scouted += len(repos)
            self.components_harvested += sum(len(r["components"]) for r in repos)
        elif isinstance(titan, HELIOS):
            repos = titan.scout_repositories()
            self.repos_scouted += len(repos)

        titan.progress = 0.5
        component.status = "SCOUTING"
        component.progress = 0.3
