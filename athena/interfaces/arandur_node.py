import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArandurCentralNode:
    def __init__(
        self,
        base_path: Path,
        jw_log_path: Optional[Path] = None,
        operations_queue_path: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
    ):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.queue_path = self.base_path / "central_queue.json"
        self.armoury_path = self.base_path / "armoury_catalog.jsonl"
        self.index_path = self.base_path / "armoury_index.json"
        self.mesh_assessment_path = self.base_path / "mesh_assessment.jsonl"
        self.rollup_state_path = self.base_path / "mesh_rollup_state.json"
        self.jw_log_path = jw_log_path
        self.operations_queue_path = operations_queue_path
        self.reports_dir = reports_dir
        self._ensure_files()

    def _ensure_files(self) -> None:
        if not self.queue_path.exists():
            self._write_json(self.queue_path, {"version": 1, "tasks": []})
        if not self.index_path.exists():
            self._write_json(
                self.index_path,
                {
                    "version": 1,
                    "entries": 0,
                    "by_source_type": {},
                    "last_updated": datetime.now().isoformat(),
                },
            )
        if not self.armoury_path.exists():
            self.armoury_path.touch()
        if not self.mesh_assessment_path.exists():
            self.mesh_assessment_path.touch()
        if not self.rollup_state_path.exists():
            self._write_json(
                self.rollup_state_path,
                {
                    "version": 1,
                    "last_generated_at": "",
                    "last_event_count": 0,
                },
            )
        if self.jw_log_path is not None and not self.jw_log_path.exists():
            self.jw_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.jw_log_path, "w") as f:
                f.write("version: 1\nentries: []\n")
        if (
            self.operations_queue_path is not None
            and not self.operations_queue_path.exists()
        ):
            self.operations_queue_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.operations_queue_path, "w") as f:
                f.write("version: 1\nqueue: []\n")
        if self.reports_dir is not None:
            self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _read_json(self, path: Path) -> Dict[str, Any]:
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)

    def enqueue_task(
        self,
        title: str,
        objective: str,
        deadline: str,
        source: str = "ATHENA",
        owner: str = "ARANDUR",
    ) -> Dict[str, Any]:
        queue_data = self._read_json(self.queue_path) or {"version": 1, "tasks": []}
        tasks = queue_data.setdefault("tasks", [])
        task_id = f"NP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(tasks) + 1}"
        task = {
            "task_id": task_id,
            "title": title,
            "objective": objective,
            "deadline": deadline,
            "source": source,
            "owner": owner,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "completion_note": "",
        }
        tasks.append(task)
        self._write_json(self.queue_path, queue_data)
        return task

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        queue_data = self._read_json(self.queue_path) or {"tasks": []}
        tasks = queue_data.get("tasks", [])
        if status is None:
            return tasks
        return [t for t in tasks if t.get("status") == status]

    def complete_task(self, task_id: str, completion_note: str = "") -> Dict[str, Any]:
        queue_data = self._read_json(self.queue_path) or {"version": 1, "tasks": []}
        tasks = queue_data.get("tasks", [])

        completed: Optional[Dict[str, Any]] = None
        for task in tasks:
            if task.get("task_id") == task_id:
                task["status"] = "done"
                task["completion_note"] = completion_note
                task["completed_at"] = datetime.now().isoformat()
                completed = task
                break

        self._write_json(self.queue_path, queue_data)

        if completed is None:
            return {"status": "not_found", "task_id": task_id}

        next_task = next((t for t in tasks if t.get("status") == "queued"), None)
        if next_task is None:
            next_task = self.enqueue_task(
                title="Define next Numenor company objective",
                objective="Generate next queued objective from latest ATHENA mission outcomes",
                deadline=datetime.now().replace(microsecond=0).isoformat(),
                source="AUTO_FOLLOW_ON",
            )

        return {
            "status": "completed",
            "completed_task": completed,
            "next_task": next_task,
            "queue_size": len(self.list_tasks()),
        }

    def catalog_finding(
        self,
        source_type: str,
        source_url: str,
        summary: str,
        code_refs: Optional[List[str]] = None,
        concepts: Optional[List[str]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entry = {
            "entry_id": f"ARM-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "source_type": source_type,
            "source_url": source_url,
            "summary": summary,
            "code_refs": code_refs or [],
            "concepts": concepts or [],
            "payload": payload or {},
            "cataloged_at": datetime.now().isoformat(),
        }
        with open(self.armoury_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        index = self._read_json(self.index_path) or {
            "version": 1,
            "entries": 0,
            "by_source_type": {},
        }
        index["entries"] = int(index.get("entries", 0)) + 1
        by_source = index.setdefault("by_source_type", {})
        by_source[source_type] = int(by_source.get(source_type, 0)) + 1
        index["last_updated"] = datetime.now().isoformat()
        self._write_json(self.index_path, index)
        return entry

    def log_mesh_delegation_assessment(
        self,
        mission_id: str,
        task_id: str,
        delegation: Dict[str, Any],
        node: Dict[str, Any],
        model_routing: Dict[str, Any],
        result: str,
        report_paths: Optional[List[str]] = None,
        code_refs: Optional[List[str]] = None,
        error: str = "",
    ) -> Dict[str, Any]:
        timestamp = datetime.now().isoformat()
        event_id = f"MESH-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        started_at = timestamp
        ended_at = datetime.now().isoformat()

        duration_ms = 0.0
        source_type = str(node.get("name", "manual"))
        source_of_truth = "manifest" if source_type != "manual" else "manual"
        mode = str(delegation.get("mode", "local_primary"))

        assessment = {
            "event_id": event_id,
            "timestamp": timestamp,
            "mission_id": mission_id,
            "task_id": task_id,
            "delegation_mode": mode,
            "node": {
                "name": str(node.get("name", "")),
                "role": str(node.get("role", "")),
                "tailscale_host": str(node.get("tailscale_host", "")),
                "tailscale_ip": str(node.get("tailscale_ip", "")),
                "reachable": bool(node.get("reachable", False)),
            },
            "policy": {
                "node_soul_file": str(node.get("soul_file", "")),
                "node_capabilities_file": str(node.get("capabilities_file", "")),
                "source_of_truth": source_of_truth,
            },
            "execution": {
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_ms": duration_ms,
                "result": result,
                "error": error,
            },
            "model_routing": {
                "provider": str(model_routing.get("provider", "")),
                "model": str(model_routing.get("model_id", "")),
                "fallback_used": bool(model_routing.get("fallback_used", False)),
                "rate_limit_bounce": bool(
                    model_routing.get("rate_limit_bounce", False)
                ),
            },
            "energy": {
                "device": "pi5" if "pi5" in mode or "mesh" in mode else "other",
                "estimated_joules": 0.0,
                "jw_estimate": 0.0,
            },
            "artifacts": {
                "armoury_entry_id": "",
                "report_paths": report_paths or [],
                "code_refs": code_refs or [],
            },
        }

        with open(self.mesh_assessment_path, "a") as f:
            f.write(json.dumps(assessment) + "\n")

        armoury_entry = self.catalog_finding(
            source_type="mesh_delegation",
            source_url=f"mission:{mission_id}",
            summary=f"Mesh delegation {mode} for task {task_id}",
            code_refs=code_refs or [],
            concepts=[mode, str(node.get("role", ""))],
            payload=assessment,
        )
        artifacts = assessment.get("artifacts")
        if isinstance(artifacts, dict):
            artifacts["armoury_entry_id"] = armoury_entry["entry_id"]

        jw_entry = self._append_jw_ledger_entry(
            event_id=event_id,
            task_id=task_id,
            model_routing=model_routing,
            mode=mode,
            report_paths=report_paths or [],
        )
        assessment["jw_entry_id"] = jw_entry.get("entry_id", "")

        report_path = self._write_mesh_assessment_report(assessment)
        if report_path:
            artifacts = assessment.get("artifacts")
            if isinstance(artifacts, dict):
                paths = artifacts.get("report_paths")
                if isinstance(paths, list):
                    paths.append(report_path)

        queue_task_id = self._append_operations_queue_entry(
            mission_id=mission_id,
            task_id=task_id,
            assessment=assessment,
        )
        assessment["operations_queue_task_id"] = queue_task_id
        return assessment

    def _append_jw_ledger_entry(
        self,
        event_id: str,
        task_id: str,
        model_routing: Dict[str, Any],
        mode: str,
        report_paths: List[str],
    ) -> Dict[str, Any]:
        provider = str(model_routing.get("provider", "local"))
        model_id = str(model_routing.get("model_id", ""))
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        device = "pi5" if "mesh" in mode else "other"
        entry_id = f"JW-{datetime.now().strftime('%Y%m%d-%H%M%S')}-MESH"

        entry = {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "task_id": task_id,
            "agent": "CEO",
            "device": device,
            "model": f"api:{provider}/{model_id}" if provider else model_id,
            "mode": "act",
            "E_joules_est": 0,
            "kappa": 1.0,
            "W_score_0_1": 0.0,
            "JW": 0,
            "deliverables": report_paths,
            "notes": f"Mesh delegation assessment event: {event_id}",
        }

        if self.jw_log_path is None:
            return entry

        with open(self.jw_log_path, "a") as f:
            f.write("\n---\n")
            f.write("jw_entries_append_mesh_runtime:\n")
            f.write(f"  - entry_id: {entry['entry_id']}\n")
            f.write(f'    timestamp: "{entry["timestamp"]}"\n')
            f.write(f"    task_id: {entry['task_id']}\n")
            f.write(f"    agent: {entry['agent']}\n")
            f.write(f"    device: {entry['device']}\n")
            f.write(f"    model: {entry['model']}\n")
            f.write(f"    mode: {entry['mode']}\n")
            f.write(f"    E_joules_est: {entry['E_joules_est']}\n")
            f.write(f"    kappa: {entry['kappa']}\n")
            f.write(f"    W_score_0_1: {entry['W_score_0_1']}\n")
            f.write(f"    JW: {entry['JW']}\n")
            f.write("    deliverables:\n")
            for path in report_paths:
                f.write(f"      - {path}\n")
            f.write(f'    notes: "{entry["notes"]}"\n')

        return entry

    def _append_operations_queue_entry(
        self,
        mission_id: str,
        task_id: str,
        assessment: Dict[str, Any],
    ) -> str:
        if self.operations_queue_path is None:
            return ""

        timestamp = datetime.now().strftime("%Y-%m-%d")
        queue_task_id = f"NP-ACT-MESH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        mode = str(assessment.get("delegation_mode", "local_primary"))
        result = str((assessment.get("execution") or {}).get("result", "partial"))

        with open(self.operations_queue_path, "a") as f:
            f.write("\n---\n")
            f.write("mesh_assessment_entries:\n")
            f.write(f"  - task_id: {queue_task_id}\n")
            f.write(f'    created_at: "{timestamp}"\n')
            f.write("    created_by: CEO\n")
            f.write("    mode: act\n")
            f.write(
                f'    objective: "Record mesh delegation assessment for mission {mission_id}"\n'
            )
            f.write("    acceptance_criteria:\n")
            f.write('      - "Assessment event persisted in armoury and ledger."\n')
            f.write(
                '      - "Delegation outcome is reviewable in Operations reports."\n'
            )
            f.write("    artifacts_to_produce:\n")
            f.write(f"      - {self.mesh_assessment_path}\n")
            f.write("    risk_level: low\n")
            f.write("    requires_triad: false\n")
            f.write("    status: done\n")
            f.write(
                f'    notes: "source_task={task_id}; mode={mode}; result={result}"\n'
            )

        return queue_task_id

    def _write_mesh_assessment_report(self, assessment: Dict[str, Any]) -> str:
        if self.reports_dir is None:
            return ""
        event_id = str(assessment.get("event_id", "MESH-UNKNOWN"))
        report_name = (
            f"mesh_assessment_{datetime.now().strftime('%Y-%m-%d')}_{event_id}.md"
        )
        report_path = self.reports_dir / report_name

        mission_id = str(assessment.get("mission_id", ""))
        task_id = str(assessment.get("task_id", ""))
        mode = str(assessment.get("delegation_mode", ""))
        node = assessment.get("node", {})
        execution = assessment.get("execution", {})

        lines = [
            f"# Mesh Assessment {event_id}",
            "",
            f"- mission_id: {mission_id}",
            f"- task_id: {task_id}",
            f"- delegation_mode: {mode}",
            f"- node: {node.get('name', '')} ({node.get('tailscale_host', '')})",
            f"- result: {execution.get('result', '')}",
            "",
            "## Payload",
            "",
            "```json",
            json.dumps(assessment, indent=2),
            "```",
            "",
        ]
        report_path.write_text("\n".join(lines))
        return str(report_path)

    def generate_mesh_assessment_rollup(self, limit: int = 50) -> Dict[str, Any]:
        events = self._read_mesh_assessment_events(limit=limit)

        total = len(events)
        success = 0
        partial = 0
        failed = 0
        fallback_used = 0
        by_node: Dict[str, int] = {}
        by_mode: Dict[str, int] = {}
        failures: Dict[str, int] = {}

        for event in events:
            execution = event.get("execution", {})
            result = str(execution.get("result", "partial"))
            if result == "success":
                success += 1
            elif result == "failed":
                failed += 1
            else:
                partial += 1

            model_routing = event.get("model_routing", {})
            if bool(model_routing.get("fallback_used", False)):
                fallback_used += 1

            node = event.get("node", {})
            node_name = str(node.get("name", "unknown"))
            by_node[node_name] = by_node.get(node_name, 0) + 1

            mode = str(event.get("delegation_mode", "unknown"))
            by_mode[mode] = by_mode.get(mode, 0) + 1

            error_text = str(execution.get("error", "")).strip()
            if error_text:
                failures[error_text] = failures.get(error_text, 0) + 1

        success_rate = (success / total) if total else 0.0
        fallback_rate = (fallback_used / total) if total else 0.0

        top_failure_causes = sorted(
            failures.items(), key=lambda item: item[1], reverse=True
        )[:5]

        rollup = {
            "generated_at": datetime.now().isoformat(),
            "window_events": total,
            "success_rate": round(success_rate, 4),
            "result_counts": {
                "success": success,
                "partial": partial,
                "failed": failed,
            },
            "fallback_frequency": {
                "count": fallback_used,
                "rate": round(fallback_rate, 4),
            },
            "node_utilization": by_node,
            "delegation_modes": by_mode,
            "top_failure_causes": [
                {"error": err, "count": count} for err, count in top_failure_causes
            ],
        }

        report_path = self._write_mesh_rollup_report(rollup)
        rollup["report_path"] = report_path
        self._save_rollup_state(
            total_events=len(self._read_mesh_assessment_events(limit=0))
        )
        return rollup

    def maybe_generate_mesh_assessment_rollup(
        self,
        cadence_events: int = 10,
        cadence_hours: int = 24,
        limit: int = 100,
        force: bool = False,
    ) -> Dict[str, Any]:
        total_events = len(self._read_mesh_assessment_events(limit=0))
        state = self._load_rollup_state()
        last_generated_at = str(state.get("last_generated_at", ""))
        last_event_count = int(state.get("last_event_count", 0))

        has_new_events = total_events > last_event_count
        events_delta = total_events - last_event_count

        should_publish = force
        reason = "forced" if force else "none"

        if not force and has_new_events and events_delta >= cadence_events:
            should_publish = True
            reason = "event_threshold"

        if not force and has_new_events and not should_publish:
            if not last_generated_at:
                should_publish = True
                reason = "first_rollup"
            else:
                try:
                    last_ts = datetime.fromisoformat(last_generated_at)
                    if datetime.now() - last_ts >= timedelta(
                        hours=max(1, cadence_hours)
                    ):
                        should_publish = True
                        reason = "daily_window"
                except ValueError:
                    should_publish = True
                    reason = "invalid_state_timestamp"

        if should_publish:
            rollup = self.generate_mesh_assessment_rollup(limit=limit)
            return {
                "published": True,
                "reason": reason,
                "total_events": total_events,
                "events_delta": events_delta,
                "rollup": rollup,
            }

        return {
            "published": False,
            "reason": reason,
            "total_events": total_events,
            "events_delta": events_delta,
            "rollup": None,
        }

    def _read_mesh_assessment_events(self, limit: int) -> List[Dict[str, Any]]:
        if not self.mesh_assessment_path.exists():
            return []

        rows: List[Dict[str, Any]] = []
        with open(self.mesh_assessment_path) as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)

        if limit <= 0:
            return rows
        return rows[-limit:]

    def _write_mesh_rollup_report(self, rollup: Dict[str, Any]) -> str:
        if self.reports_dir is None:
            return ""
        name = f"mesh_assessment_rollup_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.md"
        report_path = self.reports_dir / name

        lines = [
            "# Mesh Assessment Rollup",
            "",
            f"- generated_at: {rollup.get('generated_at', '')}",
            f"- window_events: {rollup.get('window_events', 0)}",
            f"- success_rate: {rollup.get('success_rate', 0.0)}",
            f"- fallback_frequency: {rollup.get('fallback_frequency', {}).get('rate', 0.0)}",
            "",
            "## Result Counts",
            "",
            f"- success: {rollup.get('result_counts', {}).get('success', 0)}",
            f"- partial: {rollup.get('result_counts', {}).get('partial', 0)}",
            f"- failed: {rollup.get('result_counts', {}).get('failed', 0)}",
            "",
            "## Node Utilization",
            "",
        ]

        node_util = rollup.get("node_utilization", {})
        if isinstance(node_util, dict):
            for node_name, count in node_util.items():
                lines.append(f"- {node_name}: {count}")

        lines.extend(
            [
                "",
                "## Top Failure Causes",
                "",
            ]
        )
        failures = rollup.get("top_failure_causes", [])
        if isinstance(failures, list) and failures:
            for failure in failures:
                if isinstance(failure, dict):
                    lines.append(
                        f"- {failure.get('error', '')}: {failure.get('count', 0)}"
                    )
        else:
            lines.append("- none")

        report_path.write_text("\n".join(lines) + "\n")
        return str(report_path)

    def _load_rollup_state(self) -> Dict[str, Any]:
        payload = self._read_json(self.rollup_state_path)
        if payload:
            return payload
        return {
            "version": 1,
            "last_generated_at": "",
            "last_event_count": 0,
        }

    def _save_rollup_state(self, total_events: int) -> None:
        self._write_json(
            self.rollup_state_path,
            {
                "version": 1,
                "last_generated_at": datetime.now().isoformat(),
                "last_event_count": total_events,
            },
        )

    def rollup_cadence_status(self) -> Dict[str, Any]:
        state = self._load_rollup_state()
        total_events = len(self._read_mesh_assessment_events(limit=0))
        last_event_count = int(state.get("last_event_count", 0))
        pending_delta = max(0, total_events - last_event_count)
        return {
            "last_generated_at": str(state.get("last_generated_at", "")),
            "last_event_count": last_event_count,
            "total_events": total_events,
            "pending_delta": pending_delta,
        }

    def snapshot(self) -> Dict[str, Any]:
        tasks = self.list_tasks()
        index = self._read_json(self.index_path)
        mesh_events = 0
        if self.mesh_assessment_path.exists():
            with open(self.mesh_assessment_path) as f:
                mesh_events = len([line for line in f if line.strip()])
        return {
            "node_path": str(self.base_path),
            "queue_path": str(self.queue_path),
            "armoury_catalog_path": str(self.armoury_path),
            "armoury_index_path": str(self.index_path),
            "mesh_assessment_path": str(self.mesh_assessment_path),
            "queued_tasks": len([t for t in tasks if t.get("status") == "queued"]),
            "done_tasks": len([t for t in tasks if t.get("status") == "done"]),
            "armoury_entries": int((index or {}).get("entries", 0)),
            "mesh_assessment_events": mesh_events,
        }
