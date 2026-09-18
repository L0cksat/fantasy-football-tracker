from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from collector.adapters.sofascore import _browser_headers, _http_get
from collector.models import Snapshot

_SEASON_CACHE: dict[int, int] = {}
_TEAM_INJURED_CACHE: dict[int, set[str]] = {}

# SofaScore missingPlayers.reason codes seen in live lineups:
# 3 = FA / improper conduct ban, 11 = yellow accumulation, 12 = yellow/red, 13 = red card.
_SUSPENSION_REASONS = {3, 11, 12, 13}


def current_season_id(tournament_id: int) -> int:
    cached = _SEASON_CACHE.get(tournament_id)
    if cached is not None:
        return cached
    response = _http_get(
        f"https://www.sofascore.com/api/v1/unique-tournament/{tournament_id}/seasons",
        headers=_browser_headers(""),
        timeout=20,
    )
    response.raise_for_status()
    seasons = (response.json() or {}).get("seasons") or []
    if not seasons or seasons[0].get("id") is None:
        raise ValueError(f"SofaScore unique-tournament/{tournament_id} seasons JSON had no current season.")
    season_id = int(seasons[0]["id"])
    _SEASON_CACHE[tournament_id] = season_id
    return season_id


def overlay_from_lineups(payload: dict[str, Any]) -> tuple[dict[str, float], set[str], set[str]]:
    """Parse event/{id}/lineups JSON into ratings, injured ids, and suspended ids."""
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    injured: set[str] = set()
    suspended: set[str] = set()
    for side in ("home", "away"):
        block = payload.get(side) or {}
        for row in block.get("players") or []:
            player_id = _player_id(row.get("player") or row)
            rating = (row.get("statistics") or {}).get("rating")
            if rating is None:
                rating = row.get("rating")
            if player_id is None or rating is None or rating == "":
                continue
            sums[player_id] += float(rating)
            counts[player_id] += 1
        for row in block.get("missingPlayers") or []:
            player_id = _player_id(row.get("player") or row)
            if player_id is None:
                continue
            if _is_suspended_missing(row):
                suspended.add(player_id)
            elif _is_injured_missing(row):
                injured.add(player_id)
    ratings = {key: round(sums[key] / counts[key], 1) for key in sums}
    return ratings, injured, suspended


def fetch_round_overlay(
    tournament_id: int,
    round_number: int,
    *,
    season_id: int | None = None,
) -> dict[str, Any]:
    """unique-tournament/{id}/season/{id}/events/round/{n} + event/{id}/lineups."""
    ratings: dict[str, float] = {}
    injured: set[str] = set()
    suspended: set[str] = set()
    season = season_id if season_id is not None else current_season_id(tournament_id)
    response = _http_get(
        f"https://www.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{season}/events/round/{round_number}",
        headers=_browser_headers(""),
        timeout=30,
    )
    if response.status_code == 404:
        return {"ratings": ratings, "injuredIds": injured, "suspendedIds": suspended}
    response.raise_for_status()
    events = (response.json() or {}).get("events") or []
    for event in events:
        event_id = event.get("id")
        if event_id is None:
            continue
        lineups = _http_get(
            f"https://www.sofascore.com/api/v1/event/{event_id}/lineups",
            headers=_browser_headers(""),
            timeout=20,
        )
        if lineups.status_code != 200:
            continue
        event_ratings, event_injured, event_suspended = overlay_from_lineups(lineups.json() or {})
        injured |= event_injured
        suspended |= event_suspended
        for player_id, rating in event_ratings.items():
            if player_id in ratings:
                ratings[player_id] = round((ratings[player_id] + rating) / 2, 1)
            else:
                ratings[player_id] = rating
    return {"ratings": ratings, "injuredIds": injured, "suspendedIds": suspended}


def fetch_injured_player_ids(team_ids: Iterable[Any]) -> set[str]:
    """team/{id}/players — players with injury.status == out."""
    injured: set[str] = set()
    for raw in team_ids:
        try:
            team_id = int(str(raw).strip())
        except (TypeError, ValueError):
            continue
        if team_id <= 0:
            continue
        cached = _TEAM_INJURED_CACHE.get(team_id)
        if cached is None:
            cached = _injured_for_team(team_id)
            _TEAM_INJURED_CACHE[team_id] = cached
        injured |= cached
    return injured


def apply_round_overlay(
    snapshot: Snapshot,
    *,
    ratings: dict[str, float] | None = None,
    injured_ids: Iterable[str] | None = None,
    suspended_ids: Iterable[str] | None = None,
) -> Snapshot:
    rating_map = ratings or {}
    injured = {str(item) for item in (injured_ids or [])}
    suspended = {str(item) for item in (suspended_ids or [])}
    for pick in snapshot.picks:
        player_id = str(pick.player.externalId)
        if player_id in rating_map:
            pick.rating = rating_map[player_id]
        if player_id in suspended:
            pick.suspended = True
            pick.injured = False
        elif player_id in injured:
            pick.injured = True
    return snapshot


def annotate_snapshot_injuries(snapshot: Snapshot) -> Snapshot:
    """Mark Injured / Suspended from this GW's SofaScore missingPlayers (+ live injuries)."""
    tournament_id = _optional_int(snapshot.competition.get("externalId"))
    round_number = _optional_int((snapshot.gameweek or {}).get("number"))
    if tournament_id is None or round_number is None:
        return snapshot
    injured: set[str] = set()
    suspended: set[str] = set()
    try:
        overlay = fetch_round_overlay(tournament_id, round_number)
        injured |= {str(item) for item in overlay.get("injuredIds") or []}
        suspended |= {str(item) for item in overlay.get("suspendedIds") or []}
    except Exception:
        overlay = {"ratings": {}, "injuredIds": set(), "suspendedIds": set()}
    status = str((snapshot.gameweek or {}).get("status") or "")
    if status in {"live", "upcoming"}:
        team_ids = [pick.player.clubExternalId for pick in snapshot.picks]
        try:
            injured |= fetch_injured_player_ids(team_ids) - suspended
        except Exception:
            pass
    return apply_round_overlay(snapshot, injured_ids=injured, suspended_ids=suspended)


def _injured_for_team(team_id: int) -> set[str]:
    response = _http_get(
        f"https://www.sofascore.com/api/v1/team/{team_id}/players",
        headers=_browser_headers(""),
        timeout=20,
    )
    if response.status_code != 200:
        return set()
    injured: set[str] = set()
    for row in (response.json() or {}).get("players") or []:
        player = row.get("player") or {}
        injury = player.get("injury") or {}
        if str(injury.get("status") or "").lower() != "out":
            continue
        player_id = _player_id(player)
        if player_id is not None:
            injured.add(player_id)
    return injured


def _is_suspended_missing(row: dict[str, Any]) -> bool:
    """Yellow accumulation, red card, disciplinary ban, or explicit unavailable."""
    kind = str(row.get("type") or "").lower()
    if kind == "doubtful":
        return False
    description = str(row.get("description") or "").lower()
    normalized = description.replace(" ", "_")
    reason = _optional_int(row.get("reason"))
    if reason in _SUSPENSION_REASONS:
        return True
    if any(
        token in normalized
        for token in (
            "suspension",
            "yellow_card_accumulation",
            "red_card",
            "yellow_or_red",
            "unavail",
        )
    ):
        return True
    if "unavailable" in description:
        return True
    return False


def _is_injured_missing(row: dict[str, Any]) -> bool:
    kind = str(row.get("type") or "").lower()
    if kind == "doubtful":
        return False
    if _is_suspended_missing(row):
        return False
    description = str(row.get("description") or "").lower()
    if "injur" in description:
        return True
    return kind == "missing" and row.get("reason") == 1


def _player_id(player: dict[str, Any] | None) -> str | None:
    if not player or player.get("id") is None:
        return None
    return str(player["id"])


def _optional_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
