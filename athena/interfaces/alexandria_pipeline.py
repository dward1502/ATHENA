import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from urllib import error as urllib_error, request as urllib_request


class AlexandriaPipeline:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

        self.queues_dir = self.root / "queues"
        self.index_dir = self.root / "index"
        self.runs_dir = self.root / "runs"
        self.reports_dir = self.root / "reports"
        self.reference_dir = self.root / "reference"
        self.analysis_dir = self.root / "analysis"
        self.analysis_books_dir = self.analysis_dir / "books"
        self.analysis_index_path = self.analysis_dir / "index.json"
        self.library_playbook_path = self.reports_dir / "athena_library_playbook.json"

        self.documentation_path = self.reference_dir / "documentation.md"
        self.quick_access_path = self.index_dir / "quick_access_index.json"
        self.ingest_queue_path = self.queues_dir / "ingest_queue.json"
        self.digest_queue_path = self.queues_dir / "digest_queue.json"

        self._legacy_documentation_path = self.root / "documentation.md"
        self._legacy_quick_access_path = self.root / "quick_access_index.json"
        self._legacy_ingest_queue_path = self.root / "ingest_queue.json"
        self._legacy_digest_queue_path = self.root / "digest_queue.json"

        self._ensure_layout()
        self._migrate_legacy_layout()
        self._ensure_files()

    def _ensure_layout(self) -> None:
        for path in (
            self.queues_dir,
            self.index_dir,
            self.runs_dir,
            self.reports_dir,
            self.reference_dir,
            self.analysis_dir,
            self.analysis_books_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def _migrate_legacy_layout(self) -> None:
        self._migrate_legacy_text_file(
            self._legacy_documentation_path,
            self.documentation_path,
            "# Alexandria Documentation Links\n",
        )
        self._migrate_legacy_json_list_file(
            self._legacy_quick_access_path,
            self.quick_access_path,
            key="entries",
            dedupe_keys=["source_url"],
        )
        self._migrate_legacy_json_list_file(
            self._legacy_ingest_queue_path,
            self.ingest_queue_path,
            key="tasks",
            dedupe_keys=["source_url", "phase", "decision"],
        )
        self._migrate_legacy_json_list_file(
            self._legacy_digest_queue_path,
            self.digest_queue_path,
            key="tasks",
            dedupe_keys=["source_url", "phase", "decision"],
        )

    def _migrate_legacy_text_file(
        self,
        legacy_path: Path,
        new_path: Path,
        default_content: str,
    ) -> None:
        if not legacy_path.exists():
            return
        if not new_path.exists():
            legacy_path.replace(new_path)
            return

        legacy_text = legacy_path.read_text()
        current_text = new_path.read_text()
        merged = current_text
        if legacy_text.strip() and legacy_text.strip() not in current_text:
            merged = current_text.rstrip() + "\n\n" + legacy_text.strip() + "\n"
        if not merged.strip():
            merged = default_content
        new_path.write_text(merged)
        legacy_path.unlink(missing_ok=True)

    def _migrate_legacy_json_list_file(
        self,
        legacy_path: Path,
        new_path: Path,
        key: str,
        dedupe_keys: List[str],
    ) -> None:
        if not legacy_path.exists():
            return

        legacy_payload = self._read_json(legacy_path)
        legacy_items = (
            legacy_payload.get(key, []) if isinstance(legacy_payload, dict) else []
        )

        if not new_path.exists():
            new_path.write_text(json.dumps({"version": 1, key: legacy_items}, indent=2))
            legacy_path.unlink(missing_ok=True)
            return

        current_payload = self._read_json(new_path)
        current_items = (
            current_payload.get(key, []) if isinstance(current_payload, dict) else []
        )

        merged_map: Dict[str, Dict[str, Any]] = {}
        for item in list(current_items) + list(legacy_items):
            if not isinstance(item, dict):
                continue
            marker = "|".join(str(item.get(k, "")) for k in dedupe_keys)
            merged_map[marker] = item

        merged_items = list(merged_map.values())
        new_path.write_text(json.dumps({"version": 1, key: merged_items}, indent=2))
        legacy_path.unlink(missing_ok=True)

    def _ensure_files(self) -> None:
        if not self.documentation_path.exists():
            self.documentation_path.write_text("# Alexandria Documentation Links\n")
        if not self.quick_access_path.exists():
            self.quick_access_path.write_text('{"version": 1, "entries": []}\n')
        if not self.ingest_queue_path.exists():
            self.ingest_queue_path.write_text('{"version": 1, "tasks": []}\n')
        if not self.digest_queue_path.exists():
            self.digest_queue_path.write_text('{"version": 1, "tasks": []}\n')
        if not self.analysis_index_path.exists():
            self.analysis_index_path.write_text('{"version": 1, "repos": []}\n')
        if not self.library_playbook_path.exists():
            self.library_playbook_path.write_text('{"version": 1, "workstreams": []}\n')

    def scout_and_plan(
        self,
        urls: List[str],
        mission_id: str,
        decision: str,
    ) -> Dict[str, Any]:
        entries: List[Dict[str, Any]] = []
        for url in urls:
            source_type = self._source_type(url)
            docs_links = self.discover_docs_links(url) if source_type == "repo" else []
            entry = {
                "source_url": url,
                "source_type": source_type,
                "docs_links": docs_links,
                "scouted_at": datetime.now().isoformat(),
                "mission_id": mission_id,
                "decision": decision,
                "digest_plan": {
                    "extract_snippets": True,
                    "extract_concepts": True,
                    "allow_full_package_import": True,
                },
                "status": "scouted",
            }
            entries.append(entry)

        self._update_quick_access(entries)
        self._update_documentation(entries)
        self.rebuild_library_artifacts()
        queue_summary = self._enqueue_digest_tasks(entries, decision)

        return {
            "entries": len(entries),
            "repos": len([e for e in entries if e["source_type"] == "repo"]),
            "queue": queue_summary,
            "documentation_path": str(self.documentation_path),
            "quick_access_path": str(self.quick_access_path),
            "analysis_index_path": str(self.analysis_index_path),
            "library_playbook_path": str(self.library_playbook_path),
        }

    def rebuild_repo_books(self) -> Dict[str, Any]:
        return self._rebuild_repo_books_index()

    def rebuild_library_artifacts(self) -> Dict[str, Any]:
        books = self._rebuild_repo_books_index()
        playbook = self._rebuild_library_playbook()
        return {"books": books, "playbook": playbook}

    def _rebuild_library_playbook(self) -> Dict[str, Any]:
        index_payload = self._read_json(self.analysis_index_path)
        repos = (
            index_payload.get("repos", []) if isinstance(index_payload, dict) else []
        )

        prioritized = {
            "microsoft__autogen": "W1_orchestration_intelligence",
            "crewaiinc__crewai": "W1_orchestration_intelligence",
            "kyegomez__swarms": "W1_orchestration_intelligence",
            "openbmb__repoagent": "W2_repository_intelligence",
            "ms-teja__code-archeologist": "W2_repository_intelligence",
            "forcedotcom__code-analyzer": "W3_quality_gates",
            "open-webui__open-webui": "W4_operator_surface",
            "redplanethq__core-cli": "W4_operator_surface",
            "conway-research__automaton": "W5_advanced_autonomy_module",
        }

        workstreams: Dict[str, Dict[str, Any]] = {}
        for repo in repos:
            if not isinstance(repo, dict):
                continue
            slug = str(repo.get("repo_slug", ""))
            if not slug:
                continue

            stream = prioritized.get(slug, "W0_general_library")
            if stream not in workstreams:
                workstreams[stream] = {"name": stream, "repos": []}

            book_path = Path(str(repo.get("book_json_path", "")))
            card: Dict[str, Any] = {}
            if book_path.exists():
                payload = self._read_json(book_path)
                if isinstance(payload, dict):
                    loaded = payload.get("agent_card", {})
                    card = loaded if isinstance(loaded, dict) else {}

            workstreams[stream]["repos"].append(
                {
                    "repo_slug": slug,
                    "source_url": repo.get("source_url", ""),
                    "mission_id": repo.get("mission_id", ""),
                    "status": repo.get("status", ""),
                    "signal_tags": card.get("signal_tags", []),
                    "capabilities": card.get("capabilities", []),
                }
            )

        workstream_rows = sorted(workstreams.values(), key=lambda item: item["name"])

        payload = {
            "version": 1,
            "generated_at": datetime.now().replace(microsecond=0).isoformat(),
            "workstreams": workstream_rows,
        }
        self.library_playbook_path.write_text(json.dumps(payload, indent=2) + "\n")
        return {
            "workstreams": len(workstream_rows),
            "library_playbook_path": str(self.library_playbook_path),
        }

    def _rebuild_repo_books_index(self) -> Dict[str, Any]:
        payload = self._read_json(self.quick_access_path)
        entries = payload.get("entries", []) if isinstance(payload, dict) else []

        repo_entries = [
            entry
            for entry in entries
            if isinstance(entry, dict) and entry.get("source_type") == "repo"
        ]

        index_rows: List[Dict[str, Any]] = []
        generated = 0
        for entry in repo_entries:
            source_url = str(entry.get("source_url", "")).strip()
            slug = self._repo_slug(source_url)
            if not slug:
                continue

            book_dir = self.analysis_books_dir / slug
            book_dir.mkdir(parents=True, exist_ok=True)
            book_json_path = book_dir / "book.json"

            docs_links = entry.get("docs_links", []) if isinstance(entry, dict) else []
            docs_links = [str(link) for link in docs_links if isinstance(link, str)]

            existing_book: Dict[str, Any] = {}
            if book_json_path.exists():
                loaded = self._read_json(book_json_path)
                if isinstance(loaded, dict):
                    existing_book = loaded

            book_json = {
                "version": 1,
                "repo_slug": slug,
                "source_url": source_url,
                "source_type": entry.get("source_type", "repo"),
                "mission_id": entry.get("mission_id", ""),
                "decision": entry.get("decision", ""),
                "status": entry.get("status", "scouted"),
                "scouted_at": entry.get("scouted_at", ""),
                "docs_links": docs_links,
                "digest_plan": entry.get("digest_plan", {}),
            }
            book_json = {**existing_book, **book_json}
            book_json_path.write_text(json.dumps(book_json, indent=2) + "\n")

            lines = [
                f"# Repo Book: {slug}",
                "",
                f"- source_url: {source_url}",
                f"- mission_id: {book_json['mission_id']}",
                f"- decision: {book_json['decision']}",
                f"- status: {book_json['status']}",
                f"- scouted_at: {book_json['scouted_at']}",
                "",
                "## Documentation Links",
            ]
            for link in docs_links:
                lines.append(f"- {link}")
            lines.append("")
            (book_dir / "book.md").write_text("\n".join(lines))

            index_rows.append(
                {
                    "repo_slug": slug,
                    "source_url": source_url,
                    "book_json_path": str(book_json_path),
                    "book_md_path": str(book_dir / "book.md"),
                    "status": str(
                        book_json.get(
                            "analysis_status", book_json.get("status", "scouted")
                        )
                    ),
                    "mission_id": str(
                        book_json.get(
                            "last_digest_mission_id",
                            book_json.get("mission_id", ""),
                        )
                    ),
                }
            )
            generated += 1

        index_rows.sort(key=lambda row: row["repo_slug"])
        self.analysis_index_path.write_text(
            json.dumps({"version": 1, "repos": index_rows}, indent=2) + "\n"
        )
        return {
            "repos_indexed": generated,
            "analysis_index_path": str(self.analysis_index_path),
        }

    def _repo_slug(self, repo_url: str) -> str:
        match = re.match(r"https://github.com/([^/]+)/([^/\s]+)", repo_url)
        if not match:
            return ""
        owner = match.group(1).strip().lower()
        repo = match.group(2).strip().lower()
        return f"{owner}__{repo}"

    def _source_type(self, url: str) -> str:
        if "github.com/" in url:
            return "repo"
        if "arxiv.org/" in url:
            return "article"
        return "web"

    def discover_docs_links(self, repo_url: str) -> List[str]:
        match = re.match(r"https://github.com/([^/]+)/([^/\s]+)", repo_url)
        if not match:
            return [repo_url]

        owner, repo = match.group(1), match.group(2)
        headers = {
            "User-Agent": "ATHENA-Alexandria/1.0",
            "Accept": "application/vnd.github+json",
        }
        links: List[str] = [f"{repo_url}#readme"]

        repo_api = f"https://api.github.com/repos/{owner}/{repo}"
        repo_meta: Dict[str, Any] = {}
        try:
            repo_meta = self._fetch_json(repo_api, headers)
        except Exception:
            return links

        homepage = str(repo_meta.get("homepage") or "").strip()
        if homepage:
            links.append(homepage)

        if bool(repo_meta.get("has_wiki", False)):
            links.append(f"{repo_url}/wiki")

        default_branch = str(repo_meta.get("default_branch") or "main")
        for docs_dir in ("docs", "documentation", "doc"):
            api_url = (
                f"https://api.github.com/repos/{owner}/{repo}/contents/{docs_dir}"
                + f"?ref={default_branch}"
            )
            try:
                self._fetch_json(api_url, headers)
                links.append(f"{repo_url}/tree/{default_branch}/{docs_dir}")
            except Exception:
                pass

        out: List[str] = []
        seen = set()
        for link in links:
            if link not in seen:
                seen.add(link)
                out.append(link)
        return out

    def _fetch_json(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        req = urllib_request.Request(url, headers=headers)
        with urllib_request.urlopen(req, timeout=20) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)

    def _update_quick_access(self, entries: List[Dict[str, Any]]) -> None:
        payload = self._read_json(self.quick_access_path)
        current = payload.get("entries", []) if isinstance(payload, dict) else []
        existing = {
            str(entry.get("source_url")): entry
            for entry in current
            if isinstance(entry, dict)
        }

        for entry in entries:
            existing[str(entry.get("source_url"))] = entry

        merged = list(existing.values())
        merged.sort(key=lambda e: str(e.get("source_url", "")))
        self.quick_access_path.write_text(
            json.dumps({"version": 1, "entries": merged}, indent=2)
        )

    def _update_documentation(self, entries: List[Dict[str, Any]]) -> None:
        text = self.documentation_path.read_text()
        lines = [text.rstrip(), "", "## GitHub Repo Documentation"]

        existing_blocks = set()
        for line in text.splitlines():
            if line.startswith("### "):
                existing_blocks.add(line.strip())

        for entry in entries:
            if entry.get("source_type") != "repo":
                continue
            repo_url = str(entry.get("source_url", ""))
            match = re.match(r"https://github.com/([^/]+)/([^/\s]+)", repo_url)
            if not match:
                continue
            name = f"{match.group(1)}/{match.group(2)}"
            heading = f"### {name}"
            if heading in existing_blocks:
                continue
            lines.append(heading)
            for link in entry.get("docs_links", []):
                lines.append(f"- {link}")
            lines.append("")

        merged = "\n".join(lines).strip() + "\n"
        self.documentation_path.write_text(merged)

    def _enqueue_digest_tasks(
        self,
        entries: List[Dict[str, Any]],
        decision: str,
    ) -> Dict[str, int]:
        ingest = self._read_json(self.ingest_queue_path)
        digest = self._read_json(self.digest_queue_path)

        ingest_tasks = ingest.get("tasks", []) if isinstance(ingest, dict) else []
        digest_tasks = digest.get("tasks", []) if isinstance(digest, dict) else []

        ingest_count = 0
        digest_count = 0

        for entry in entries:
            task = self._build_task(entry, decision)
            if decision == "immediate":
                if not self._has_task(ingest_tasks, task):
                    ingest_tasks.append(task)
                    ingest_count += 1
            else:
                if not self._has_task(digest_tasks, task):
                    digest_tasks.append(task)
                    digest_count += 1

        self.ingest_queue_path.write_text(
            json.dumps({"version": 1, "tasks": ingest_tasks}, indent=2)
        )
        self.digest_queue_path.write_text(
            json.dumps({"version": 1, "tasks": digest_tasks}, indent=2)
        )
        return {"ingest_added": ingest_count, "digest_added": digest_count}

    def _build_task(self, entry: Dict[str, Any], decision: str) -> Dict[str, Any]:
        now = datetime.now()
        if decision == "immediate":
            scheduled_for = now.isoformat()
            status = "queued"
        else:
            nightly = (now + timedelta(days=1)).replace(
                hour=2, minute=0, second=0, microsecond=0
            )
            scheduled_for = nightly.isoformat()
            status = "scheduled"

        return {
            "task_id": f"ALX-{now.strftime('%Y%m%d%H%M%S%f')}",
            "source_url": entry.get("source_url", ""),
            "source_type": entry.get("source_type", "web"),
            "decision": decision,
            "phase": "digest",
            "status": status,
            "scheduled_for": scheduled_for,
            "created_at": now.isoformat(),
            "plan": entry.get("digest_plan", {}),
        }

    def _has_task(self, tasks: List[Dict[str, Any]], new_task: Dict[str, Any]) -> bool:
        src = str(new_task.get("source_url", ""))
        phase = str(new_task.get("phase", ""))
        decision = str(new_task.get("decision", ""))
        for task in tasks:
            if (
                str(task.get("source_url", "")) == src
                and str(task.get("phase", "")) == phase
                and str(task.get("decision", "")) == decision
            ):
                return True
        return False

    def _read_json(self, path: Path) -> Dict[str, Any]:
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError, urllib_error.URLError):
            return {}
