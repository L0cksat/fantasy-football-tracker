from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import requests

from collector.adapters.sofascore_directory import (
    PREMIER_LEAGUE_TOURNAMENT_ID,
    fetch_premier_league_players,
    resolve_sofascore_player,
    search_sofascore_player,
)
from collector.adapters.sofascore_round import (
    apply_round_overlay,
    current_season_id,
    fetch_injured_player_ids,
    fetch_round_overlay,
)
from collector.models import (
    PickPayload,
    PlayerPayload,
    Snapshot,
    TransferPair,
    TransferPlayer,
    TransferRound,
    TransfersBatch,
)

SOURCE = "fpl"
DEFAULT_SLUG = "premier-league-fantasy"
DEFAULT_NAME = "Premier League Fantasy"
API_ROOT = "https://fantasy.premierleague.com/api"
POSITIONS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


def fpl_entry_id() -> str:
    return os.getenv("FPL_ENTRY_ID", "").strip()


def pull_fpl(
    publisher: Any,
    *,
    entry_id: str | None = None,
    gameweek: int | None = None,
    dry_run: bool = False,
    save_dir: Path | None = None,
) -> dict[str, Any]:
    """GET public FPL JSON for one team and POST snapshots + transfers."""
    team_id = (entry_id or fpl_entry_id()).strip()
    if not team_id or not team_id.isdigit():
        raise ValueError("Set FPL_ENTRY_ID to your numeric FPL team id (from /entry/{id}/event/1).")

    bootstrap = _get_json(f"{API_ROOT}/bootstrap-static/")
    entry = _get_json(f"{API_ROOT}/entry/{team_id}/")
    history = _get_json(f"{API_ROOT}/entry/{team_id}/history/")
    transfers = _get_json(f"{API_ROOT}/entry/{team_id}/transfers/")
    _save_json(save_dir, "entry", entry)
    _save_json(save_dir, "history", history)
    _save_json(save_dir, "transfers", transfers)

    catalog = catalog_from_bootstrap(bootstrap)
    catalog["sofascore_players"] = fetch_premier_league_players()
    _save_json(save_dir, "sofascore-players", catalog["sofascore_players"])
    competition = competition_payload(team_id, catalog)
    team = team_payload(entry)
    events = catalog["events"]
    current = int(entry.get("current_event") or 0)
    started = int(entry.get("started_event") or 1)
    numbers = [gameweek] if gameweek is not None else list(range(started, max(current, started) + 1))
    try:
        season_id = current_season_id(PREMIER_LEAGUE_TOURNAMENT_ID)
    except Exception:
        season_id = None

    snapshots: list[Snapshot] = []
    for number in numbers:
        event = events.get(number) or {"id": number, "name": f"Gameweek {number}"}
        picks_payload = _get_json(f"{API_ROOT}/entry/{team_id}/event/{number}/picks/", missing_ok=True)
        if not picks_payload:
            continue
        live_payload = _get_json(f"{API_ROOT}/event/{number}/live/", missing_ok=True) or {}
        _save_json(save_dir, f"picks-gw{number}", picks_payload)
        overlay = _safe_round_overlay(number, season_id)
        snapshots.append(
            snapshot_from_picks(
                picks_payload,
                live_payload,
                catalog,
                entry,
                event,
                competition,
                team,
                ratings=overlay.get("ratings"),
                injured_ids=overlay.get("injuredIds"),
            )
        )

    if not snapshots:
        raise ValueError(f"No FPL picks found for team {team_id}.")

    batch = transfers_from_fpl(transfers, history, catalog, competition, team, gameweek=gameweek)
    result: dict[str, Any] = {
        "snapshots": [item.to_dict() for item in snapshots],
        "transfers": batch.to_dict() if batch is not None else None,
        "published": None,
    }
    if dry_run:
        return result

    published: dict[str, Any] = {"snapshots": [publisher.publish(item) for item in snapshots]}
    if batch is not None:
        published["transfers"] = publisher.publish_transfers(batch)
    result["published"] = published
    return result


def catalog_from_bootstrap(bootstrap: dict[str, Any]) -> dict[str, Any]:
    teams = {int(item["id"]): item for item in bootstrap.get("teams") or [] if item.get("id") is not None}
    elements = {int(item["id"]): item for item in bootstrap.get("elements") or [] if item.get("id") is not None}
    events = {int(item["id"]): item for item in bootstrap.get("events") or [] if item.get("id") is not None}
    return {"teams": teams, "elements": elements, "events": events, "season": _season(bootstrap.get("events") or [])}


def competition_payload(entry_id: str, catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "externalId": str(entry_id),
        "name": DEFAULT_NAME,
        "season": catalog.get("season") or "2026/27",
        "slug": DEFAULT_SLUG,
    }


def team_payload(entry: dict[str, Any]) -> dict[str, Any]:
    first = str(entry.get("player_first_name") or "").strip()
    last = str(entry.get("player_last_name") or "").strip()
    manager = " ".join(part for part in (first, last) if part) or None
    return {
        "name": str(entry.get("name") or "FPL team").strip(),
        "managerName": manager,
    }


def snapshot_from_picks(
    picks_payload: dict[str, Any],
    live_payload: dict[str, Any],
    catalog: dict[str, Any],
    entry: dict[str, Any],
    event: dict[str, Any],
    competition: dict[str, Any],
    team: dict[str, Any],
    *,
    ratings: dict[str, float] | None = None,
    injured_ids: Iterable[str] | None = None,
) -> Snapshot:
    live_by_id = {
        int(item["id"]): item
        for item in live_payload.get("elements") or []
        if item.get("id") is not None
    }
    history = picks_payload.get("entry_history") or {}
    number = int(event.get("id") or history.get("event") or 1)
    picks: list[PickPayload] = []
    for item in picks_payload.get("picks") or []:
        element_id = int(item["element"])
        picks.append(_pick_from_fpl(item, catalog, live_by_id.get(element_id) or {}))
    chip = picks_payload.get("active_chip")
    deadline = str(event.get("deadline_time") or "")
    status = _event_status(event)
    marked = {str(item) for item in (injured_ids or [])}
    if status != "finished":
        marked |= _current_injured_ids(picks, catalog)
    snapshot = Snapshot(
        competition=competition,
        gameweek={
            "number": number,
            "name": event.get("name") or f"Gameweek {number}",
            "status": status,
            "startsAt": deadline[:10] if len(deadline) >= 10 else None,
        },
        team=team or team_payload(entry),
        picks=picks,
        teamPoints=_optional_float(history.get("points")),
        tripleCaptain=chip == "3xc",
        transferPenalty=_optional_float(history.get("event_transfers_cost")),
    )
    return apply_round_overlay(snapshot, ratings=ratings, injured_ids=marked)


def transfers_from_fpl(
    transfers: Any,
    history: dict[str, Any],
    catalog: dict[str, Any],
    competition: dict[str, Any],
    team: dict[str, Any],
    *,
    gameweek: int | None = None,
) -> TransfersBatch | None:
    rows = transfers if isinstance(transfers, list) else []
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        number = int(row.get("event") or 0)
        if number <= 0:
            continue
        if gameweek is not None and number != gameweek:
            continue
        grouped[number].append(row)
    if not grouped:
        return None
    penalties = {
        int(item["event"]): _optional_float(item.get("event_transfers_cost")) or 0
        for item in history.get("current") or []
        if item.get("event") is not None
    }
    rounds: list[TransferRound] = []
    for number, items in sorted(grouped.items()):
        event = catalog["events"].get(number) or {}
        rounds.append(
            TransferRound(
                number=number,
                name=str(event.get("name") or f"Gameweek {number}"),
                transferPenalty=penalties.get(number) or 0,
                transfers=[_transfer_pair(item, catalog) for item in items],
            )
        )
    return TransfersBatch(competition=competition, team=team, rounds=rounds)


def _pick_from_fpl(item: dict[str, Any], catalog: dict[str, Any], live: dict[str, Any]) -> PickPayload:
    element_id = int(item["element"])
    element = catalog["elements"].get(element_id) or {}
    club = catalog["teams"].get(int(element.get("team") or 0)) or {}
    stats = live.get("stats") or {}
    slot = int(item.get("position") or 0)
    return PickPayload(
        player=_player_from_element(element_id, element, club, catalog),
        role="starter" if slot <= 11 else "bench",
        points=float(stats.get("total_points") or 0),
        captain=bool(item.get("is_captain")),
        viceCaptain=bool(item.get("is_vice_captain")),
        price=_price(element.get("now_cost")),
        breakdown={
            "minutes": stats.get("minutes"),
            "goals": stats.get("goals_scored"),
            "assists": stats.get("assists"),
            "multiplier": item.get("multiplier"),
        },
    )


def _transfer_pair(row: dict[str, Any], catalog: dict[str, Any]) -> TransferPair:
    return TransferPair(
        playerIn=_transfer_player(row.get("element_in"), row.get("element_in_cost"), catalog),
        playerOut=_transfer_player(row.get("element_out"), row.get("element_out_cost"), catalog),
    )


def _transfer_player(element_id: Any, cost: Any, catalog: dict[str, Any]) -> TransferPlayer | None:
    if element_id is None:
        return None
    player_id = int(element_id)
    element = catalog["elements"].get(player_id) or {}
    club = catalog["teams"].get(int(element.get("team") or 0)) or {}
    player = _player_from_element(player_id, element, club, catalog)
    return TransferPlayer(
        externalId=player.externalId,
        name=player.name,
        position=player.position,
        club=player.club,
        clubExternalId=player.clubExternalId,
        price=_price(cost),
    )


def _player_from_element(element_id: int, element: dict[str, Any], club: dict[str, Any], catalog: dict[str, Any] | None = None) -> PlayerPayload:
    name = element.get("web_name") or element.get("second_name") or f"Player {element_id}"
    club_code = club.get("code")
    sofascore_id = _sofascore_player_id(element_id, element, club, catalog)
    return PlayerPayload(
        externalId=sofascore_id,
        name=str(name),
        position=POSITIONS.get(int(element.get("element_type") or 0)),
        club=club.get("name"),
        clubExternalId=str(club_code) if club_code is not None else None,
    )


def _sofascore_player_id(
    element_id: int,
    element: dict[str, Any],
    club: dict[str, Any],
    catalog: dict[str, Any] | None,
) -> str:
    directory = (catalog or {}).get("sofascore_players") or []
    cache = (catalog or {}).setdefault("_sofascore_ids", {})
    if element_id in cache:
        return cache[element_id]
    club_name = str(club.get("name") or "")
    hit = resolve_sofascore_player(
        web_name=str(element.get("web_name") or ""),
        first_name=str(element.get("first_name") or ""),
        second_name=str(element.get("second_name") or ""),
        club=club_name,
        directory=directory,
    )
    if hit is None:
        query = " ".join(part for part in (element.get("web_name"), club_name) if part)
        hit = search_sofascore_player(query)
    resolved = str(hit["playerId"]) if hit and hit.get("playerId") is not None else f"fpl-{element_id}"
    cache[element_id] = resolved
    return resolved


def _safe_round_overlay(round_number: int, season_id: int | None) -> dict[str, Any]:
    try:
        return fetch_round_overlay(PREMIER_LEAGUE_TOURNAMENT_ID, round_number, season_id=season_id)
    except Exception:
        return {"ratings": {}, "injuredIds": set()}


def _current_injured_ids(picks: list[PickPayload], catalog: dict[str, Any]) -> set[str]:
    marked: set[str] = set()
    elements = catalog.get("elements") or {}
    cache = catalog.get("_sofascore_ids") or {}
    reverse = {str(value): key for key, value in cache.items()}
    for pick in picks:
        element_id = reverse.get(str(pick.player.externalId))
        element = elements.get(element_id) if element_id is not None else {}
        if str((element or {}).get("status") or "") == "i":
            marked.add(str(pick.player.externalId))
    team_ids = []
    by_player = {
        str(row.get("playerId")): row.get("teamId")
        for row in catalog.get("sofascore_players") or []
        if row.get("playerId") is not None
    }
    for pick in picks:
        team_id = by_player.get(str(pick.player.externalId))
        if team_id is not None:
            team_ids.append(team_id)
    try:
        marked |= fetch_injured_player_ids(team_ids)
    except Exception:
        pass
    return marked


def _event_status(event: dict[str, Any]) -> str:
    if event.get("finished"):
        return "finished"
    if event.get("is_current"):
        return "live"
    return "upcoming"


def _season(events: list[dict[str, Any]]) -> str:
    deadline = str((events[0] if events else {}).get("deadline_time") or "")
    year = int(deadline[:4]) if deadline[:4].isdigit() else 2026
    return f"{year}/{str(year + 1)[2:]}"


def _price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return round(float(value) / 10.0, 1)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _get_json(url: str, *, missing_ok: bool = False) -> Any:
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        timeout=30,
    )
    if missing_ok and response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def _save_json(save_dir: Path | None, name: str, payload: Any) -> None:
    if save_dir is None or payload is None:
        return
    save_dir.mkdir(parents=True, exist_ok=True)
    path = save_dir / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
