"""Local SQLite-based memory persistence — WAL mode, zero network dependencies."""

import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class LocalCoreMemoryClient:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _initialize_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    episode_body TEXT NOT NULL,
                    reference_time TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    label_ids TEXT NOT NULL,
                    session_id TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'completed'
                )
                """
            )

    def health_check(self):
        return {
            "status": "ok",
            "mode": "local",
            "db_path": str(self.db_path),
        }

    def get_ingestion_logs(self, params: Optional[Dict[str, Any]] = None):
        limit = 100
        if params and params.get("limit") is not None:
            try:
                limit = max(1, int(params["limit"]))
            except (TypeError, ValueError):
                limit = 100

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, source, status, reference_time, created_at, session_id
                FROM episodes
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        logs = [
            {
                "id": row["id"],
                "source": row["source"],
                "status": row["status"],
                "reference_time": row["reference_time"],
                "created_at": row["created_at"],
                "session_id": row["session_id"],
            }
            for row in rows
        ]
        return {"logs": logs}

    def get_specific_log(self, log_id: str):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source, status, reference_time, created_at, session_id
                FROM episodes
                WHERE id = ?
                """,
                (log_id,),
            ).fetchone()

        if row is None:
            raise RuntimeError(f"Log not found: {log_id}")

        return {
            "id": row["id"],
            "source": row["source"],
            "status": row["status"],
            "reference_time": row["reference_time"],
            "created_at": row["created_at"],
            "session_id": row["session_id"],
        }

    def add_episode(
        self,
        episode_body: str,
        reference_time: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        label_ids: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ):
        episode_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO episodes (
                    id, episode_body, reference_time, source,
                    metadata, label_ids, session_id, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed')
                """,
                (
                    episode_id,
                    episode_body,
                    reference_time,
                    source,
                    json.dumps(metadata or {}, ensure_ascii=True),
                    json.dumps(label_ids or [], ensure_ascii=True),
                    session_id,
                    now,
                ),
            )

        return {"success": True, "id": episode_id}

    def search_knowledge_graph(
        self,
        query: str,
        limit: int = 20,
        score_threshold: float = 0.4,
        min_results: int = 1,
    ):
        terms = [term.lower() for term in re.findall(r"[a-zA-Z0-9_]+", query)]
        if not terms:
            return {"results": []}

        like_pattern = "%" + "%".join(terms[:3]) + "%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, episode_body, reference_time, source, metadata, label_ids, session_id, created_at
                FROM episodes
                WHERE lower(episode_body) LIKE ?
                ORDER BY created_at DESC
                LIMIT 500
                """,
                (like_pattern.lower(),),
            ).fetchall()

        scored = []
        total_terms = len(terms)
        for row in rows:
            body = (row["episode_body"] or "").lower()
            matches = sum(1 for term in terms if term in body)
            if matches == 0:
                continue
            score = matches / total_terms
            if score < score_threshold:
                continue

            metadata = {}
            if row["metadata"]:
                try:
                    metadata = json.loads(row["metadata"])
                except json.JSONDecodeError:
                    metadata = {}

            scored.append(
                {
                    "id": row["id"],
                    "score": score,
                    "episodeBody": row["episode_body"],
                    "referenceTime": row["reference_time"],
                    "source": row["source"],
                    "metadata": metadata,
                    "sessionId": row["session_id"],
                    "createdAt": row["created_at"],
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        results = scored[: max(1, limit)]
        if len(results) < min_results:
            return {"results": []}
        return {"results": results}
