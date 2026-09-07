from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from collector.adapters.sofascore import snapshot_from_payload
from collector.models import FantasyAdapter, Snapshot


class FileImportAdapter(FantasyAdapter):
    """Manual fallback: ingest a JSON export you saved from SofaScore or wrote by hand."""

    def __init__(self, path: str | Path, meta_path: str | Path | None = None) -> None:
        self.path = Path(path)
        self.meta_path = Path(meta_path) if meta_path else None

    def fetch_competitions(self) -> list[dict[str, Any]]:
        snapshot = self._load()
        return [snapshot.competition]

    def fetch_squad(self, competition_slug: str) -> dict[str, Any]:
        snapshot = self._load()
        return snapshot.team

    def fetch_gameweek_scores(self, competition_slug: str, gameweek: int) -> Snapshot:
        snapshot = self._load()
        if snapshot.gameweek.get("number") != gameweek:
            raise ValueError(
                f"{self.path} is gameweek {snapshot.gameweek.get('number')}, not {gameweek}"
            )
        return snapshot

    def _load(self) -> Snapshot:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        meta = json.loads(self.meta_path.read_text(encoding="utf-8")) if self.meta_path else None
        return snapshot_from_payload(payload, meta)
