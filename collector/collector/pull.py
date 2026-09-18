from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from collector.adapters.sofascore import (
    SofaScoreAdapter,
    round_id_from_meta,
    snapshot_from_payload,
    transfers_from_payload,
)
from collector.adapters.sofascore_round import annotate_snapshot_injuries
from collector.publisher import BackendPublisher


@dataclass(frozen=True)
class PullTarget:
    slug: str
    competition_url: str = ""
    squad_url: str = ""
    transfers_url: str = ""
    gameweek_url: str = ""


_FANTASY_COMPETITION_URL = re.compile(
    r"^(https://www\.sofascore\.com/api/v1/fantasy/user/[^/]+)/competition/\d+/?$",
    re.IGNORECASE,
)


def pull_targets_from_env() -> list[PullTarget]:
    """Premier League uses unprefixed SOFASCORE_* (or SOFASCORE_PREMIER_LEAGUE_*).

    Other leagues use SOFASCORE_LALIGA_*, SOFASCORE_SERIE_A_*, SOFASCORE_LIGUE_1_*,
    SOFASCORE_BUNDESLIGA_*, SOFASCORE_CHAMPIONS_LEAGUE_*, SOFASCORE_EUROPA_LEAGUE_*,
    SOFASCORE_NATIONS_LEAGUE_*, SOFASCORE_MLS_*, SOFASCORE_BRASILEIRAO_*.
    A competition JSON URL is enough: squad and transfers URLs are derived from it.
    A concrete /round/{id}/squad URL alone is also enough for the first ingest.
    """
    premier = _target_from_prefix("premier-league", "SOFASCORE_PREMIER_LEAGUE_")
    if not premier.squad_url and not premier.competition_url:
        premier = PullTarget(
            slug="premier-league",
            competition_url=os.getenv("SOFASCORE_COMPETITION_URL", "").strip(),
            squad_url=os.getenv("SOFASCORE_SQUAD_URL", "").strip(),
            transfers_url=os.getenv("SOFASCORE_TRANSFERS_URL", "").strip(),
            gameweek_url=os.getenv("SOFASCORE_GAMEWEEK_URL", "").strip(),
        )
    named = [
        ("laliga", "SOFASCORE_LALIGA_"),
        ("serie-a", "SOFASCORE_SERIE_A_"),
        ("ligue-1", "SOFASCORE_LIGUE_1_"),
        ("bundesliga", "SOFASCORE_BUNDESLIGA_"),
        ("champions-league", "SOFASCORE_CHAMPIONS_LEAGUE_"),
        ("europa-league", "SOFASCORE_EUROPA_LEAGUE_"),
        ("nations-league", "SOFASCORE_NATIONS_LEAGUE_"),
        ("mls", "SOFASCORE_MLS_"),
        ("brasileirao", "SOFASCORE_BRASILEIRAO_"),
    ]
    targets = [complete_target(premier)]
    targets.extend(complete_target(_target_from_prefix(slug, prefix)) for slug, prefix in named)
    return [item for item in targets if item.squad_url]


def complete_target(target: PullTarget) -> PullTarget:
    """Fill squad/transfers from a Fantasy competition XHR URL when those fields are empty."""
    competition = target.competition_url.rstrip("/")
    match = _FANTASY_COMPETITION_URL.match(competition)
    transfers = target.transfers_url
    squad = target.squad_url
    if match:
        if not transfers:
            transfers = f"{competition}/transfers"
        if not squad:
            squad = f"{match.group(1)}/round/{{roundId}}/squad"
    return replace(target, competition_url=competition, transfers_url=transfers, squad_url=squad)


def _target_from_prefix(slug: str, prefix: str) -> PullTarget:
    return PullTarget(
        slug=slug,
        competition_url=os.getenv(f"{prefix}COMPETITION_URL", "").strip(),
        squad_url=os.getenv(f"{prefix}SQUAD_URL", "").strip(),
        transfers_url=os.getenv(f"{prefix}TRANSFERS_URL", "").strip(),
        gameweek_url=os.getenv(f"{prefix}GAMEWEEK_URL", "").strip(),
    )


def adapter_for_target(target: PullTarget) -> SofaScoreAdapter:
    return SofaScoreAdapter(
        competition_url=target.competition_url,
        squad_url=target.squad_url,
        transfers_url=target.transfers_url,
        gameweek_url=target.gameweek_url,
    )


def run_pull(
    adapter: SofaScoreAdapter,
    publisher: BackendPublisher,
    *,
    competition: str = "premier-league",
    gameweek: int | None = None,
    dry_run: bool = False,
    save_dir: Path | None = None,
) -> dict[str, Any]:
    """GET configured SofaScore Fantasy URLs, map them, POST to the backend."""
    if not adapter.squad_url:
        raise ValueError(
            "Squad URL is empty. Set SOFASCORE_SQUAD_URL and/or SOFASCORE_LALIGA_SQUAD_URL "
            "from your Network tab."
        )

    meta = adapter.fetch_meta()
    _save_json(save_dir, "competition", meta)
    rounds_payload = adapter.fetch_rounds()
    if rounds_payload:
        _save_json(save_dir, "rounds", rounds_payload)
        if meta is None:
            meta = rounds_payload
        elif rounds_payload.get("userRounds"):
            meta = dict(meta)
            meta["userRounds"] = rounds_payload["userRounds"]
    round_id = round_id_from_meta(meta, gameweek=gameweek)

    squad_payload = adapter.fetch_squad(competition, gameweek, round_id=round_id)
    _save_json(save_dir, "squad", squad_payload)
    snapshot = annotate_snapshot_injuries(snapshot_from_payload(squad_payload, meta))

    batch = None
    if adapter.transfers_url:
        transfers_payload = adapter.fetch_transfers(
            competition, gameweek, round_id=round_id, missing_ok=True
        )
        if transfers_payload:
            _save_json(save_dir, "transfers", transfers_payload)
            batch = transfers_from_payload(transfers_payload, meta)

    result: dict[str, Any] = {
        "snapshot": snapshot.to_dict(),
        "transfers": batch.to_dict() if batch is not None else None,
        "published": None,
    }
    if dry_run:
        return result

    published: dict[str, Any] = {"snapshot": publisher.publish(snapshot)}
    if batch is not None:
        published["transfers"] = publisher.publish_transfers(batch)
    result["published"] = published
    return result


def _save_json(save_dir: Path | None, name: str, payload: Any) -> None:
    if save_dir is None or payload is None:
        return
    save_dir.mkdir(parents=True, exist_ok=True)
    path = save_dir / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
