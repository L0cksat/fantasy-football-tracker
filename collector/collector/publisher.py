from __future__ import annotations

import os
from typing import Any

import requests

from collector.models import Snapshot, TransfersBatch


class BackendPublisher:
    def __init__(self, base_url: str | None = None, token: str | None = None, timeout: int = 20) -> None:
        self.base_url = (base_url or os.getenv("BACKEND_URL") or "http://localhost:8080").rstrip("/")
        self.token = token if token is not None else os.getenv("INGEST_TOKEN", "")
        self.timeout = timeout

    def publish(self, snapshot: Snapshot) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Ingest-Token"] = self.token
        response = requests.post(
            f"{self.base_url}/api/v1/ingest/snapshots",
            json=snapshot.to_dict(),
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def publish_transfers(self, batch: TransfersBatch) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Ingest-Token"] = self.token
        response = requests.post(
            f"{self.base_url}/api/v1/ingest/transfers",
            json=batch.to_dict(),
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
