from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

import requests

from collector.adapters.sofascore import _browser_headers, _http_get
from collector.adapters.sofascore_directory import (
    WSL2_TOURNAMENT_ID,
    WSL_TOURNAMENT_ID,
    fetch_tournament_players,
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

SOURCE = "wsl"
DEFAULT_SLUG = "wsl-fantasy"
DEFAULT_NAME = "WSL Fantasy"
API_ROOT = "https://gaming.wslfootball.com"
DEFAULT_TOUR_ID = 1
POSITIONS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
AVAILABLE_STATUS = {1}


def wsl_game_token() -> str:
    raw = (os.getenv("WSL_GAME_TOKEN") or os.getenv("WSL_BEARER") or "").strip()
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    return raw


def wsl_gameplay_id() -> str:
    return os.getenv("WSL_GAMEPLAY_ID", "").strip()


def wsl_configured() -> bool:
    return bool(wsl_game_token() and wsl_gameplay_id())


def pull_wsl(
    publisher: Any,
    *,
    gameweek: int | None = None,
    dry_run: bool = False,
    save_dir: Path | None = None,
) -> dict[str, Any]:
    """GET official WSL Fantasy my-team + public player feeds, then POST snapshots."""
    token = wsl_game_token()
    gameplay_id = wsl_gameplay_id()
    if not token or not gameplay_id:
        raise ValueError(
            "Set WSL_GAMEPLAY_ID and WSL_GAME_TOKEN (x-game-token from the my-team request headers). "
            "WSL_BEARER is accepted as a fallback for the same game token."
        )

    tour = _feed_value(_get_json(f"{API_ROOT}/feeds/tour/details/{DEFAULT_TOUR_ID}.json")) or {}
    fixtures = _feed_value(_get_json(f"{API_ROOT}/feeds/fixtures/fixtures_en_{DEFAULT_TOUR_ID}.json?v=3")) or []
    _save_json(save_dir, "tour", {"Data": {"Value": tour}})
    _save_json(save_dir, "fixtures", {"Data": {"Value": fixtures}})

    catalog: dict[str, Any] = {
        "players": {},
        "sofascore_players": _safe_wsl_players(),
        "tour": tour,
        "fixtures": fixtures,
    }
    _save_json(save_dir, "sofascore-players", catalog["sofascore_players"])
    competition = competition_payload(gameplay_id, tour)
    current = int(tour.get("currMatchdayId") or 1)
    numbers = [gameweek] if gameweek is not None else list(range(1, current + 1))

    try:
        season_id = current_season_id(WSL_TOURNAMENT_ID)
    except Exception:
        season_id = None

    snapshots: list[Snapshot] = []
    squads: dict[int, dict[str, Any]] = {}
    team: dict[str, Any] | None = None
    for number in numbers:
        my_team = _get_json(
            f"{API_ROOT}/fantasy/services/gameplay/{gameplay_id}/{number}/my-team",
            token=token,
            missing_ok=True,
        )
        if not my_team:
            continue
        _save_json(save_dir, f"my-team-gw{number}", my_team)
        value = _feed_value(my_team)
        if not isinstance(value, dict):
            continue
        listing = _get_json(
            f"{API_ROOT}/feeds/players/matchday_en_{DEFAULT_TOUR_ID}_{number}.json?v=3",
            missing_ok=True,
        )
        players = _feed_value(listing) if listing else []
        if isinstance(players, list):
            catalog["players"].update({str(item.get("playerId")): item for item in players if item.get("playerId")})
            _save_json(save_dir, f"players-gw{number}", listing)
        team = team or team_payload(value)
        overlay = _safe_round_overlay(number, season_id)
        snapshot = snapshot_from_my_team(
            value,
            catalog,
            competition,
            team,
            fixtures,
            ratings=overlay.get("ratings"),
            injured_ids=overlay.get("injuredIds"),
        )
        snapshots.append(snapshot)
        squads[number] = value

    if not snapshots:
        raise ValueError("No WSL my-team JSON found for the configured gameplay id.")

    batch = transfers_from_squads(squads, catalog, competition, team or {})
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


def competition_payload(gameplay_id: str, tour: dict[str, Any] | None = None) -> dict[str, Any]:
    tour = tour or {}
    return {
        "source": SOURCE,
        "externalId": str(gameplay_id),
        "name": str(tour.get("tourName") or DEFAULT_NAME),
        "season": _season(tour),
        "slug": DEFAULT_SLUG,
    }


def team_payload(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(value.get("teamName") or "WSL team").strip(),
        "managerName": str(value.get("userName") or "").strip() or None,
    }


def snapshot_from_my_team(
    value: dict[str, Any],
    catalog: dict[str, Any],
    competition: dict[str, Any],
    team: dict[str, Any],
    fixtures: list[dict[str, Any]] | None = None,
    *,
    ratings: dict[str, float] | None = None,
    injured_ids: Iterable[str] | None = None,
) -> Snapshot:
    number = int(value.get("matchdayId") or value.get("gamedayId") or 1)
    ids = [str(item) for item in (value.get("arrTeam") or []) if item]
    benches = list(value.get("arrBenchPosition") or [])
    points = list(value.get("totalPoints") or [])
    availability = list(value.get("availabilityStatus") or [])
    captain_id = str(value.get("captainId") or "")
    picks: list[PickPayload] = []
    for index, player_id in enumerate(ids):
        bench = _index(benches, index, 0)
        picks.append(
            _pick_from_wsl(
                player_id,
                catalog,
                role="starter" if int(bench or 0) == 0 else "bench",
                points=_index(points, index, 0) or 0,
                captain=player_id == captain_id,
                availability=_index(availability, index, 1),
            )
        )
    status = _gameweek_status(number, value, catalog.get("tour") or {}, fixtures or catalog.get("fixtures") or [])
    marked = {str(item) for item in (injured_ids or [])}
    if status != "finished":
        marked |= _current_injured_ids(picks, catalog)
        marked |= {
            pick.player.externalId
            for index, pick in enumerate(picks)
            if _index(availability, index, 1) not in AVAILABLE_STATUS
        }
    snapshot = Snapshot(
        competition=competition,
        gameweek={
            "number": number,
            "name": f"Gameweek {number}",
            "status": status,
            "startsAt": _starts_at(number, fixtures or catalog.get("fixtures") or []),
        },
        team=team or team_payload(value),
        picks=picks,
        teamPoints=_team_points(picks),
        tripleCaptain=False,
        transferPenalty=0,
    )
    return apply_round_overlay(snapshot, ratings=ratings, injured_ids=marked)


def transfers_from_squads(
    squads: dict[int, dict[str, Any]],
    catalog: dict[str, Any],
    competition: dict[str, Any],
    team: dict[str, Any],
) -> TransfersBatch | None:
    numbers = sorted(squads)
    rounds: list[TransferRound] = []
    for previous, current in zip(numbers, numbers[1:]):
        before = {str(item) for item in (squads[previous].get("arrTeam") or []) if item}
        after = {str(item) for item in (squads[current].get("arrTeam") or []) if item}
        outgoing = sorted(before - after)
        incoming = sorted(after - before)
        if not outgoing and not incoming:
            continue
        pairs: list[TransferPair] = []
        for index in range(max(len(outgoing), len(incoming))):
            player_out = outgoing[index] if index < len(outgoing) else None
            player_in = incoming[index] if index < len(incoming) else None
            pairs.append(
                TransferPair(
                    playerIn=_transfer_player(player_in, catalog) if player_in else None,
                    playerOut=_transfer_player(player_out, catalog) if player_out else None,
                )
            )
        rounds.append(
            TransferRound(
                number=current,
                name=f"Gameweek {current}",
                transferPenalty=0,
                transfers=pairs,
            )
        )
    if not rounds:
        return None
    return TransfersBatch(competition=competition, team=team, rounds=rounds)


def _pick_from_wsl(
    player_id: str,
    catalog: dict[str, Any],
    *,
    role: str,
    points: Any,
    captain: bool,
    availability: Any,
) -> PickPayload:
    row = (catalog.get("players") or {}).get(player_id) or {}
    return PickPayload(
        player=_player_from_row(player_id, row, catalog),
        role=role,
        points=_raw_points(points, captain),
        captain=captain,
        price=_optional_float(row.get("valuation")),
        breakdown={
            "availabilityStatus": availability,
            "skillId": row.get("skillId"),
        },
    )


def _player_from_row(player_id: str, row: dict[str, Any], catalog: dict[str, Any]) -> PlayerPayload:
    first = str(row.get("mediaFirstName") or "").strip()
    last = str(row.get("mediaLastName") or "").strip()
    name = str(row.get("mediaShortName") or "").strip() or " ".join(part for part in (first, last) if part) or player_id
    club = str(row.get("teamOfficialName") or row.get("teamShortName") or "").strip() or None
    sofascore = _sofascore_player_id(player_id, row, catalog)
    club_id = sofascore.get("teamId") if sofascore else None
    return PlayerPayload(
        externalId=str(sofascore["playerId"]) if sofascore and sofascore.get("playerId") is not None else f"wsl-{_short_id(player_id)}",
        name=name,
        position=POSITIONS.get(int(row.get("skillId") or 0)) or _position_name(row.get("skillName")),
        club=club,
        clubExternalId=str(club_id) if club_id is not None else None,
        shirtNumber=_shirt_number_from_sofascore(sofascore, catalog),
    )


def _shirt_number_from_sofascore(sofascore: dict[str, Any] | None, catalog: dict[str, Any]) -> int | None:
    """Jersey from SofaScore player profile (tournament player lists omit shirt numbers)."""
    if not sofascore or sofascore.get("playerId") is None:
        return None
    player_id = str(sofascore["playerId"])
    cache = catalog.setdefault("_shirt_numbers", {})
    if player_id in cache:
        return cache[player_id]
    for key in ("jerseyNumber", "shirtNumber"):
        raw = sofascore.get(key)
        if raw is not None and str(raw).strip() != "":
            try:
                cache[player_id] = int(float(raw))
                return cache[player_id]
            except (TypeError, ValueError):
                pass
    try:
        response = _http_get(
            f"https://www.sofascore.com/api/v1/player/{player_id}",
            headers=_browser_headers(""),
            timeout=12,
        )
        if response.status_code == 200:
            player = (response.json() or {}).get("player") or {}
            raw = player.get("jerseyNumber") if player.get("jerseyNumber") is not None else player.get("shirtNumber")
            if raw is not None and str(raw).strip() != "":
                cache[player_id] = int(float(raw))
                return cache[player_id]
    except Exception:
        pass
    cache[player_id] = None
    return None


def _sofascore_player_id(player_id: str, row: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any] | None:
    cache = catalog.setdefault("_sofascore_ids", {})
    if player_id in cache:
        return cache[player_id]
    directory = catalog.get("sofascore_players") or []
    club = str(row.get("teamOfficialName") or row.get("teamShortName") or "")
    hit = resolve_sofascore_player(
        web_name=str(row.get("mediaShortName") or row.get("mediaLastName") or ""),
        first_name=str(row.get("mediaFirstName") or ""),
        second_name=str(row.get("mediaLastName") or ""),
        club=club,
        directory=directory,
    )
    if hit is None:
        queries = [
            " ".join(part for part in (row.get("mediaFirstName"), row.get("mediaLastName")) if part),
            str(row.get("mediaShortName") or ""),
        ]
        for query in queries:
            hit = search_sofascore_player(query)
            if hit:
                break
    cache[player_id] = hit
    return hit


def _transfer_player(player_id: str, catalog: dict[str, Any]) -> TransferPlayer:
    row = (catalog.get("players") or {}).get(player_id) or {}
    player = _player_from_row(player_id, row, catalog)
    return TransferPlayer(
        externalId=player.externalId,
        name=player.name,
        position=player.position,
        club=player.club,
        clubExternalId=player.clubExternalId,
        price=_optional_float(row.get("valuation")),
    )


def _current_injured_ids(picks: list[PickPayload], catalog: dict[str, Any]) -> set[str]:
    marked: set[str] = set()
    by_player = {
        str(row.get("playerId")): row.get("teamId")
        for row in catalog.get("sofascore_players") or []
        if row.get("playerId") is not None
    }
    team_ids = [by_player.get(str(pick.player.externalId)) for pick in picks]
    try:
        marked |= fetch_injured_player_ids(team_ids)
    except Exception:
        pass
    return marked


def _safe_round_overlay(round_number: int, season_id: int | None) -> dict[str, Any]:
    ratings: dict[str, float] = {}
    injured: set[str] = set()
    for tournament_id in (WSL_TOURNAMENT_ID, WSL2_TOURNAMENT_ID):
        try:
            overlay = fetch_round_overlay(
                tournament_id,
                round_number,
                season_id=season_id if tournament_id == WSL_TOURNAMENT_ID else None,
            )
        except Exception:
            continue
        injured |= {str(item) for item in overlay.get("injuredIds") or []}
        for player_id, rating in (overlay.get("ratings") or {}).items():
            ratings[str(player_id)] = rating
    return {"ratings": ratings, "injuredIds": injured}


def _safe_wsl_players() -> list[dict[str, Any]]:
    players: list[dict[str, Any]] = []
    for tournament_id in (WSL_TOURNAMENT_ID, WSL2_TOURNAMENT_ID):
        try:
            players.extend(fetch_tournament_players(tournament_id))
        except Exception:
            continue
    return players


def _gameweek_status(
    number: int,
    value: dict[str, Any],
    tour: dict[str, Any],
    fixtures: list[dict[str, Any]],
) -> str:
    statuses = [int(item) for item in (value.get("matchdayStatus") or []) if str(item).isdigit()]
    if statuses and all(item == 5 for item in statuses):
        return "finished"
    last_played = _optional_float(tour.get("lpMatchdayId"))
    if last_played is not None and number <= int(last_played):
        return "finished"
    current = int(tour.get("currMatchdayId") or 0)
    scenario = str(tour.get("scenarioCode") or "").upper()
    if number == current and scenario in {"LIVE", "INPLAY", "SCORING"}:
        return "live"
    rows = [item for item in fixtures if int(item.get("matchdayId") or 0) == number]
    if rows and all(int(item.get("matchdayStatus") or 0) == 5 for item in rows):
        return "finished"
    return "upcoming"


def _starts_at(number: int, fixtures: list[dict[str, Any]]) -> str | None:
    dates = [
        str(item.get("matchDateTimeUtc") or "")[:10]
        for item in fixtures
        if int(item.get("matchdayId") or 0) == number and item.get("matchDateTimeUtc")
    ]
    return min(dates) if dates else None


def _season(tour: dict[str, Any]) -> str:
    deadline = str(tour.get("deadlineDate") or "")
    year = int(deadline[:4]) if deadline[:4].isdigit() else 2026
    return f"{year}/{str(year + 1)[2:]}"


def _raw_points(value: Any, captain: bool) -> float:
    """WSL my-team totalPoints already includes captain ×2; ingest stores the raw half."""
    points = float(value or 0)
    if captain and points:
        return points / 2.0
    return points


def _team_points(picks: list[PickPayload]) -> float:
    total = 0.0
    for pick in picks:
        if pick.role != "starter":
            continue
        total += pick.points * (2 if pick.captain else 1)
    return total


def _position_name(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    mapping = {"gk": "GK", "goal_keeper": "GK", "def": "DEF", "defender": "DEF", "mid": "MID", "midfielder": "MID", "fwd": "FWD", "forward": "FWD"}
    return mapping.get(text)


def _short_id(player_id: str) -> str:
    return player_id.rsplit("::", 1)[-1][:12]


def _index(values: list[Any], index: int, default: Any) -> Any:
    if index < 0 or index >= len(values):
        return default
    return values[index]


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _feed_value(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    data = payload.get("Data")
    if isinstance(data, dict) and "Value" in data:
        return data.get("Value")
    return payload.get("Value", payload)


def _get_json(url: str, *, token: str | None = None, missing_ok: bool = False) -> Any:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Origin": "https://www.wslfootball.com",
        "Referer": "https://www.wslfootball.com/fantasy/",
    }
    if token:
        headers["x-game-token"] = token
    response = requests.get(url, headers=headers, timeout=30)
    if missing_ok and response.status_code in {403, 404}:
        return None
    if response.status_code in {401, 403} and token:
        raise ValueError(
            "WSL x-game-token was rejected. Copy the x-game-token request header from the my-team XHR into WSL_GAME_TOKEN."
        )
    response.raise_for_status()
    payload = response.json()
    if token and isinstance(payload, dict):
        meta = payload.get("Meta") or {}
        if meta.get("Success") is False:
            if missing_ok:
                return None
            raise ValueError(str(meta.get("Message") or "WSL my-team request failed."))
    return payload


def _save_json(save_dir: Path | None, name: str, payload: Any) -> None:
    if save_dir is None or payload is None:
        return
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / f"{name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
