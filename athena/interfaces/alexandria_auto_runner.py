import argparse
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List

from athena.interfaces.alexandria_pipeline import AlexandriaPipeline
from athena.interfaces.ceo_bridge import CEOCommand


class AlexandriaAutoRunner:
    def __init__(self, root: Path):
        self.pipeline = AlexandriaPipeline(root)
        self.root = root
        self.archive_dir = self.root / "archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def run_cycle(self, limit: int = 5) -> Dict[str, Any]:
        ceo = CEOCommand()
        ingest = self._process_queue(
            queue_path=self.pipeline.ingest_queue_path,
            mode="ingest",
            limit=limit,
            execute_fn=ceo.execute,
        )
        digest = self._process_queue(
            queue_path=self.pipeline.digest_queue_path,
            mode="digest",
            limit=limit,
            execute_fn=ceo.execute,
        )
        self.pipeline.rebuild_library_artifacts()
        status = self.pipeline_status()
        self._write_pipeline_status_report(status)
        return {"ingest": ingest, "digest": digest, "status": status}

    def run_pods(
        self,
        queue_mode: str = "digest",
        pod_size: int = 5,
        max_pods: int = 4,
        pause_seconds: float = 1.0,
    ) -> Dict[str, Any]:
        if queue_mode not in {"ingest", "digest"}:
            raise ValueError("queue_mode must be 'ingest' or 'digest'")

        ceo = CEOCommand()
        queue_path = (
            self.pipeline.ingest_queue_path
            if queue_mode == "ingest"
            else self.pipeline.digest_queue_path
        )

        pods_run = 0
        total_processed = 0
        pod_results: List[Dict[str, Any]] = []

        while pods_run < max_pods:
            result = self._process_queue(
                queue_path=queue_path,
                mode=queue_mode,
                limit=pod_size,
                execute_fn=ceo.execute,
            )
            processed = int(result.get("processed", 0))
            if processed <= 0:
                break

            pods_run += 1
            total_processed += processed
            pod_results.append({"pod": pods_run, "processed": processed})

            if pause_seconds > 0:
                time.sleep(pause_seconds)

        self.pipeline.rebuild_library_artifacts()
        status = self.pipeline_status()
        self._write_pipeline_status_report(status)
        return {
            "queue_mode": queue_mode,
            "pod_size": pod_size,
            "max_pods": max_pods,
            "pods_run": pods_run,
            "total_processed": total_processed,
            "pod_results": pod_results,
            "status": status,
        }

    def pipeline_status(self) -> Dict[str, Any]:
        ingest_payload = self.pipeline._read_json(self.pipeline.ingest_queue_path)
        digest_payload = self.pipeline._read_json(self.pipeline.digest_queue_path)
        quick_payload = self.pipeline._read_json(self.pipeline.quick_access_path)

        ingest_tasks = (
            ingest_payload.get("tasks", []) if isinstance(ingest_payload, dict) else []
        )
        digest_tasks = (
            digest_payload.get("tasks", []) if isinstance(digest_payload, dict) else []
        )
        quick_entries = (
            quick_payload.get("entries", []) if isinstance(quick_payload, dict) else []
        )

        repo_entries = [
            row
            for row in quick_entries
            if isinstance(row, dict) and row.get("source_type") == "repo"
        ]

        def _status_counts(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
            counts: Dict[str, int] = {}
            for task in tasks:
                status = str(task.get("status", "unknown"))
                counts[status] = counts.get(status, 0) + 1
            return counts

        ingest_status = _status_counts(ingest_tasks)
        digest_status = _status_counts(digest_tasks)

        completed_ingest_urls = {
            str(task.get("source_url", ""))
            for task in ingest_tasks
            if str(task.get("status", "")) == "completed"
        }
        scouted_repo_urls = {
            str(entry.get("source_url", ""))
            for entry in repo_entries
            if str(entry.get("source_url", ""))
        }

        return {
            "generated_at": datetime.now().replace(microsecond=0).isoformat(),
            "scout": {
                "repo_entries": len(scouted_repo_urls),
                "backlog_to_ingest": max(
                    0, len(scouted_repo_urls - completed_ingest_urls)
                ),
            },
            "ingest": {
                "total_tasks": len(ingest_tasks),
                "status_counts": ingest_status,
                "backlog": ingest_status.get("queued", 0)
                + ingest_status.get("scheduled", 0)
                + ingest_status.get("in_progress", 0),
            },
            "digest": {
                "total_tasks": len(digest_tasks),
                "status_counts": digest_status,
                "backlog": digest_status.get("queued", 0)
                + digest_status.get("scheduled", 0)
                + digest_status.get("in_progress", 0),
            },
        }

    def _write_pipeline_status_report(self, status: Dict[str, Any]) -> None:
        json_path = self.pipeline.reports_dir / "pipeline_status.json"
        md_path = self.pipeline.reports_dir / "pipeline_status.md"

        json_path.write_text(json.dumps(status, indent=2) + "\n")

        lines = [
            "# Alexandria Pipeline Status",
            "",
            f"- generated_at: {status.get('generated_at', '')}",
            f"- scout_repo_entries: {status.get('scout', {}).get('repo_entries', 0)}",
            f"- scout_backlog_to_ingest: {status.get('scout', {}).get('backlog_to_ingest', 0)}",
            f"- ingest_backlog: {status.get('ingest', {}).get('backlog', 0)}",
            f"- digest_backlog: {status.get('digest', {}).get('backlog', 0)}",
            "",
            "## Ingest Status Counts",
        ]
        ingest_counts = status.get("ingest", {}).get("status_counts", {})
        for key in sorted(ingest_counts.keys()):
            lines.append(f"- {key}: {ingest_counts[key]}")

        lines.extend(["", "## Digest Status Counts"])
        digest_counts = status.get("digest", {}).get("status_counts", {})
        for key in sorted(digest_counts.keys()):
            lines.append(f"- {key}: {digest_counts[key]}")

        md_path.write_text("\n".join(lines).rstrip() + "\n")

    def _process_queue(
        self,
        queue_path: Path,
        mode: str,
        limit: int,
        execute_fn: Callable[[str, str], Dict[str, Any]],
    ) -> Dict[str, Any]:
        payload = self.pipeline._read_json(queue_path)
        tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
        now = datetime.now()
        processed = 0

        for task in tasks:
            if processed >= limit:
                break
            if str(task.get("status", "")) not in {"queued", "scheduled"}:
                continue
            scheduled_for = str(task.get("scheduled_for", ""))
            if scheduled_for:
                try:
                    due = datetime.fromisoformat(scheduled_for)
                    if due > now:
                        continue
                except ValueError:
                    pass

            url = str(task.get("source_url", "")).strip()
            if not url:
                continue

            task["status"] = "in_progress"
            task["started_at"] = datetime.now().replace(microsecond=0).isoformat()

            try:
                if mode == "ingest":
                    objective = (
                        "Execute now: ingest and digest this repository for Alexandria evaluation "
                        + url
                    )
                else:
                    objective = (
                        "Digest queued Alexandria repository with synopsis and validation (force digest): "
                        + url
                    )

                deadline = (
                    (datetime.now() + timedelta(hours=2))
                    .replace(microsecond=0)
                    .isoformat()
                )
                result = execute_fn(objective, deadline)

                task["status"] = "completed"
                task["processed_at"] = datetime.now().replace(microsecond=0).isoformat()
                task["mission_id"] = result.get("mission_id")
                task["completion_status"] = result.get("completion_status")
                task["completion_note"] = f"{mode} processed via AlexandriaAutoRunner"

                self._write_run_artifact(task, result)
                processed += 1
            except Exception as exc:
                task["status"] = "failed"
                task["processed_at"] = datetime.now().replace(microsecond=0).isoformat()
                task["error"] = str(exc)

        queue_path.write_text(
            json.dumps({"version": 1, "tasks": tasks}, indent=2) + "\n"
        )
        return {"processed": processed, "queue_path": str(queue_path)}

    def _write_run_artifact(self, task: Dict[str, Any], result: Dict[str, Any]) -> None:
        task_id = str(task.get("task_id", "unknown"))
        run_path = self.pipeline.runs_dir / f"run_{task_id}.json"
        payload = {
            "task": task,
            "result": {
                "mission_id": result.get("mission_id"),
                "routed_execution": result.get("routed_execution"),
                "ingest_count": len(result.get("ingest", [])),
                "validation_count": len(result.get("validation", [])),
                "phase6_gate": result.get("phase6_gate"),
                "completion_status": result.get("completion_status"),
            },
        }
        run_path.write_text(json.dumps(payload, indent=2) + "\n")
        self._update_repo_book_from_result(task, result)

    def _update_repo_book_from_result(
        self, task: Dict[str, Any], result: Dict[str, Any]
    ) -> None:
        source_url = str(task.get("source_url", "")).strip()
        if not source_url or "github.com/" not in source_url:
            return

        slug = self.pipeline._repo_slug(source_url)
        if not slug:
            return

        book_dir = self.pipeline.analysis_books_dir / slug
        book_dir.mkdir(parents=True, exist_ok=True)
        book_json_path = book_dir / "book.json"
        try:
            loaded = json.loads(book_json_path.read_text())
            book_json: Dict[str, Any] = loaded if isinstance(loaded, dict) else {}
        except Exception:
            book_json = {
                "version": 1,
                "repo_slug": slug,
                "source_url": source_url,
                "source_type": "repo",
            }

        book_json["last_digest_task_id"] = task.get("task_id")
        book_json["last_digest_mission_id"] = task.get("mission_id")
        book_json["last_digest_processed_at"] = task.get("processed_at")
        book_json["last_completion_status"] = task.get("completion_status")
        book_json["last_phase6_gate"] = result.get("phase6_gate", {})
        book_json["last_routed_execution"] = result.get("routed_execution", {})

        ingest = result.get("ingest", [])
        first_ingest = ingest[0] if isinstance(ingest, list) and ingest else {}
        agent_card = (
            first_ingest.get("agent_card", {}) if isinstance(first_ingest, dict) else {}
        )
        if isinstance(agent_card, dict) and agent_card:
            book_json["agent_card"] = agent_card

        book_json["analysis_status"] = (
            "digested"
            if isinstance(first_ingest, dict) and first_ingest
            else "reused_context"
        )
        book_json_path.write_text(json.dumps(book_json, indent=2) + "\n")

        md_lines = [
            f"# Repo Book: {slug}",
            "",
            f"- source_url: {source_url}",
            f"- last_digest_mission_id: {book_json.get('last_digest_mission_id', '')}",
            f"- analysis_status: {book_json.get('analysis_status', '')}",
            f"- completion_status: {book_json.get('last_completion_status', '')}",
            "",
            "## Digest Snapshot",
            f"- routed_execution: {json.dumps(book_json.get('last_routed_execution', {}), sort_keys=True)}",
            f"- phase6_gate: {json.dumps(book_json.get('last_phase6_gate', {}), sort_keys=True)}",
            "",
        ]

        agent_card_md = book_json.get("agent_card", {})
        if isinstance(agent_card_md, dict) and agent_card_md:
            md_lines.extend(
                [
                    "## Agent Card",
                    f"- name: {agent_card_md.get('name', '')}",
                    f"- language: {agent_card_md.get('language', '')}",
                    f"- capabilities: {', '.join(agent_card_md.get('capabilities', []))}",
                    f"- dependencies: {', '.join(agent_card_md.get('dependencies', []))}",
                    f"- sampled_files: {', '.join(agent_card_md.get('sampled_files', []))}",
                    f"- signal_tags: {', '.join(agent_card_md.get('signal_tags', []))}",
                    "",
                ]
            )

        (book_dir / "book.md").write_text("\n".join(md_lines).rstrip() + "\n")

    def apply_retention(self, days: int = 14) -> Dict[str, Any]:
        cutoff = datetime.now() - timedelta(days=days)
        moved = 0

        for folder in (self.pipeline.runs_dir, self.pipeline.reports_dir):
            for item in folder.glob("*"):
                if not item.is_file():
                    continue
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime >= cutoff:
                    continue
                target = self.archive_dir / item.name
                if target.exists():
                    target.unlink()
                item.replace(target)
                moved += 1

        return {"retention_days": days, "moved_to_archive": moved}


def main() -> None:
    parser = argparse.ArgumentParser(description="Alexandria automation runner")
    parser.add_argument(
        "--root",
        default=str(
            Path(__file__).resolve().parents[3]
            / "athena-garrison"
            / "armoury"
            / "alexandria"
        ),
    )
    parser.add_argument(
        "--mode", choices=["cycle", "pods", "retention", "status"], default="cycle"
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--queue-mode", choices=["ingest", "digest"], default="digest")
    parser.add_argument("--pod-size", type=int, default=5)
    parser.add_argument("--max-pods", type=int, default=4)
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    parser.add_argument("--retention-days", type=int, default=14)
    args = parser.parse_args()

    runner = AlexandriaAutoRunner(Path(args.root))
    if args.mode == "cycle":
        output = runner.run_cycle(limit=args.limit)
    elif args.mode == "pods":
        output = runner.run_pods(
            queue_mode=args.queue_mode,
            pod_size=args.pod_size,
            max_pods=args.max_pods,
            pause_seconds=args.pause_seconds,
        )
    elif args.mode == "retention":
        output = runner.apply_retention(days=args.retention_days)
    else:
        output = runner.pipeline_status()
        runner._write_pipeline_status_report(output)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
