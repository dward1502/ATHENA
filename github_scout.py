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
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path


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
        
        # Scout cache (avoid re-scanning)
        self.cache: Dict[str, Repository] = {}
        self.cache_file = Path(f"./{name}_cache.json")
        self._load_cache()
        
        self.logger = logging.getLogger(f"HERO:{name}")
        self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"⚔️  {name} Hero reporting for duty")
        self.logger.info(f"   Specialty: {specialty}")
    
    def _load_cache(self):
        """Load cached repository data"""
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                data = json.load(f)
                # Convert back to Repository objects (simplified for demo)
                self.cache = data
    
    def _save_cache(self):
        """Persist cache"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
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
        
        # DEMO MODE: Return simulated results
        # In production: Use GitHub API (requests to api.github.com)
        repos = self._simulate_github_search(query, min_stars, max_results)
        
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
    
    def _simulate_github_search(
        self, 
        query: str, 
        min_stars: int,
        max_results: int
    ) -> List[Repository]:
        """
        Simulate GitHub API search
        
        In production, replace with actual GitHub API calls:
        
        import requests
        
        url = "https://api.github.com/search/repositories"
        params = {
            "q": f"{query} stars:>{min_stars}",
            "sort": "stars",
            "per_page": max_results
        }
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        """
        
        # Simulated results based on query
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
                    open_issues=23
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
                    open_issues=156
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
                    open_issues=89
                )
            ]
        
        # Default empty results
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
        
        # DEMO MODE: Simulated analysis
        # In production: Clone repo, parse files, extract components
        
        findings = self._simulate_component_analysis(repo, target_components)
        
        self.components_found += len(findings.components_found)
        
        self.logger.info(f"   Found {len(findings.components_found)} components")
        for comp in findings.components_found:
            self.logger.info(f"     - {comp}")
        
        return findings
    
    def _simulate_component_analysis(
        self,
        repo: Repository,
        target_components: List[str]
    ) -> ComponentFindings:
        """Simulate component analysis"""
        
        # Simplified logic based on repo name
        found_components = []
        file_paths = {}
        dependencies = []
        
        if "porcupine" in repo.name.lower():
            found_components = ["wake_word_detection", "keyword_spotting"]
            file_paths = {
                "wake_word_detection": "porcupine/python/porcupine.py",
                "keyword_spotting": "porcupine/python/util.py"
            }
            dependencies = ["pvporcupine", "numpy"]
            difficulty = "LOW"
            notes = "Well-structured, easy to extract. Requires API key for advanced features."
            
        elif "whisper" in repo.name.lower():
            found_components = ["speech_to_text", "audio_transcription"]
            file_paths = {
                "speech_to_text": "whisper/transcribe.py",
                "audio_transcription": "whisper/audio.py"
            }
            dependencies = ["torch", "numpy", "ffmpeg-python"]
            difficulty = "MEDIUM"
            notes = "Requires PyTorch. Model loading can be abstracted."
            
        elif "TTS" in repo.name or "tts" in repo.name.lower():
            found_components = ["text_to_speech", "voice_synthesis"]
            file_paths = {
                "text_to_speech": "TTS/api.py",
                "voice_synthesis": "TTS/utils/synthesizer.py"
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
            extraction_difficulty=difficulty
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
