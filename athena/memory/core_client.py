"""RedPlanet Core API client — HTTP-based remote memory persistence."""

import json
from typing import Any, Dict, List, Optional
from urllib import error, request
from urllib.parse import urlencode


class CoreMemoryClient:
    """Minimal RedPlanet Core API client."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(
        self, method: str, path: str, payload: Optional[Dict[str, Any]] = None
    ):
        url = f"{self.base_url}{path}"
        data = None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = request.Request(
            url=url, data=data, method=method.upper(), headers=headers
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Core API HTTP {exc.code} at {path}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(
                f"Core API network error at {path}: {exc.reason}"
            ) from exc

    def health_check(self):
        return self._request("GET", "/api/profile")

    def get_ingestion_logs(self, params: Optional[Dict[str, Any]] = None):
        path = "/api/v1/logs"
        if params:
            query = urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                path = f"{path}?{query}"
        return self._request("GET", path)

    def get_specific_log(self, log_id: str):
        return self._request("GET", f"/api/v1/logs/{log_id}")

    def add_episode(
        self,
        episode_body: str,
        reference_time: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        label_ids: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ):
        payload: Dict[str, Any] = {
            "episodeBody": episode_body,
            "referenceTime": reference_time,
            "source": source,
            "metadata": metadata or {},
        }
        if label_ids is not None:
            payload["labelIds"] = label_ids
        if session_id:
            payload["sessionId"] = session_id
        return self._request("POST", "/api/v1/add", payload)

    def search_knowledge_graph(
        self,
        query: str,
        limit: int = 20,
        score_threshold: float = 0.4,
        min_results: int = 1,
    ):
        payload = {
            "query": query,
            "limit": limit,
            "scoreThreshold": score_threshold,
            "minResults": min_results,
        }
        return self._request("POST", "/api/v1/search", payload)
