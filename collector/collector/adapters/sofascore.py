from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from collector.models import (
    FantasyAdapter,
    PickPayload,
    PlayerPayload,
    Snapshot,
    TransferPair,
    TransferPlayer,
    TransferRound,
    TransfersBatch,
)

CLUB_BY_ID = {
    "17": "Manchester City",
    "30": "Brighton & Hove Albion",
    "32": "Ipswich Town",
    "35": "Manchester United",
    "38": "Chelsea",
    "42": "Arsenal",
    "96": "Hull City",
}
CLUB_BY_CODE = {
    "ARS": "Arsenal",
    "BHA": "Brighton & Hove Albion",
    "CHE": "Chelsea",
    "HUL": "Hull City",
    "IPS": "Ipswich Town",
    "MCI": "Manchester City",
    "MUN": "Manchester United",
}

POSITION_MAP = {
    "G": "GK",
    "GK": "GK",
    "GOALKEEPER": "GK",
    "D": "DEF",
    "DEF": "DEF",
    "DEFENDER": "DEF",
    "M": "MID",
    "MID": "MID",
    "MIDFIELDER": "MID",
    "F": "FWD",
    "FWD": "FWD",
    "FORWARD": "FWD",
}


def normalize_position(value: str | None) -> str | None:
    if not value:
        return None
    return POSITION_MAP.get(value.strip().upper(), value.strip().upper())


def snapshot_from_payload(payload: dict[str, Any], meta: dict[str, Any] | None = None) -> Snapshot:
    """Accept our snapshot DTO or a SofaScore Fantasy Network export."""
    merged = dict(payload)
    if meta:
        if "userCompetition" in meta:
            merged["userCompetition"] = meta["userCompetition"]
        elif "fantasyCompetition" in meta:
            merged["userCompetition"] = meta
    if "picks" in merged and "competition" in merged:
        return _from_canonical(merged)
    if isinstance(merged.get("squad"), dict) and merged["squad"].get("players"):
        return _from_sofascore_squad(merged)
    if "lineup" in merged or "userTeam" in merged:
        return _from_sofascore_like(merged)
    if is_transfers_export(merged):
        raise ValueError(
            "This looks like the SofaScore transfers export. Import it the same way; "
            "the collector will send it to /api/v1/ingest/transfers."
        )
    if "userCompetition" in merged:
        raise ValueError(
            "This looks like the competition/meta file (userCompetition), not the squad. "
            "Import the squad JSON and pass this file with --meta."
        )
    raise ValueError("Unrecognized snapshot JSON. Use a SofaScore squad export or the canonical ingest shape.")


def is_transfers_export(payload: dict[str, Any]) -> bool:
    rounds = payload.get("transfers")
    return isinstance(rounds, list) and any(isinstance(item, dict) and "roundSequence" in item for item in rounds)


def transfers_from_payload(payload: dict[str, Any], meta: dict[str, Any] | None = None) -> TransfersBatch:
    merged = dict(payload)
    if meta:
        if "userCompetition" in meta:
            merged["userCompetition"] = meta["userCompetition"]
        elif "fantasyCompetition" in meta:
            merged["userCompetition"] = meta
    if not is_transfers_export(merged):
        raise ValueError("Unrecognized transfers JSON. Expected a SofaScore transfers export.")
    user_comp = merged.get("userCompetition") or {}
    fantasy_comp = user_comp.get("fantasyCompetition") or {}
    unique = fantasy_comp.get("uniqueTournament") or {}
    season_src = fantasy_comp.get("season") or {}
    rounds: list[TransferRound] = []
    for item in merged.get("transfers") or []:
        pairs = []
        for raw in item.get("transfers") or []:
            player_in = raw.get("playerIn") or {}
            player_out = raw.get("playerOut") or {}
            pairs.append(
                TransferPair(
                    playerIn=_transfer_player(
                        player_in,
                        raw.get("priceIn"),
                        raw.get("teamIdIn"),
                        raw.get("teamNameCodeIn"),
                    ),
                    playerOut=_transfer_player(
                        player_out,
                        raw.get("priceOut"),
                        raw.get("teamIdOut"),
                        raw.get("teamNameCodeOut"),
                    ),
                )
            )
        rounds.append(
            TransferRound(
                number=int(item.get("roundSequence") or 0),
                name=item.get("roundName") or f"GW{item.get('roundSequence')}",
                transferPenalty=float(item.get("transferPenalty") or 0),
                transfers=pairs,
            )
        )
    return TransfersBatch(
        competition={
            "source": "sofascore",
            "externalId": str(unique.get("id") or fantasy_comp.get("id") or "17"),
            "name": unique.get("name") or fantasy_comp.get("name") or "Premier League",
            "season": _normalize_season(season_src.get("year") if isinstance(season_src, dict) else season_src),
            "slug": unique.get("slug") or fantasy_comp.get("slug") or "premier-league",
        },
        team={
            "name": user_comp.get("name") or "My SofaScore team",
            "managerName": user_comp.get("userName"),
        },
        rounds=rounds,
    )


def _transfer_player(player_src: dict[str, Any], price: Any, team_id: Any, team_code: Any) -> TransferPlayer:
    club_id = str(team_id) if team_id is not None else None
    return TransferPlayer(
        externalId=str(player_src.get("id") or ""),
        name=player_src.get("name") or player_src.get("shortName") or "Unknown",
        position=normalize_position(player_src.get("position")),
        club=CLUB_BY_ID.get(club_id or "") or CLUB_BY_CODE.get(str(team_code or "").upper()) or team_code,
        clubExternalId=club_id,
        price=_optional_float(price),
    )


def _from_canonical(payload: dict[str, Any]) -> Snapshot:
    picks = [
        PickPayload(
            player=PlayerPayload(**pick["player"]),
            role=pick.get("role", "starter"),
            points=float(pick.get("points") or 0),
            captain=bool(pick.get("captain")),
            viceCaptain=bool(pick.get("viceCaptain")),
            rating=_optional_float(pick.get("rating")),
            price=_optional_float(pick.get("price")),
            breakdown=pick.get("breakdown") or {},
        )
        for pick in payload["picks"]
    ]
    return Snapshot(
        competition=payload["competition"],
        gameweek=payload["gameweek"],
        team=payload["team"],
        picks=picks,
        teamPoints=_optional_float(payload.get("teamPoints")),
        tripleCaptain=bool(payload.get("tripleCaptain")),
        transferPenalty=_optional_float(payload.get("transferPenalty")),
    )


def _from_sofascore_squad(payload: dict[str, Any]) -> Snapshot:
    """Map SofaScore Fantasy Network squad + userRound JSON."""
    squad = payload["squad"]
    user_round = payload.get("userRound") or {}
    fantasy_round = user_round.get("fantasyRound") or {}
    user_comp = payload.get("userCompetition") or {}
    fantasy_comp = user_comp.get("fantasyCompetition") or {}
    unique = fantasy_comp.get("uniqueTournament") or _first_unique_tournament(squad)
    season_src = fantasy_comp.get("season") or {}

    number = int(fantasy_round.get("sequence") or 1)
    finalized = bool(fantasy_round.get("isFinalized"))
    status = "finished" if finalized else "live"

    picks: list[PickPayload] = []
    for item in squad.get("players") or []:
        fantasy_player = item.get("fantasyPlayer") or {}
        player_src = fantasy_player.get("player") or {}
        team_src = item.get("team") or fantasy_player.get("team") or {}
        fixtures = item.get("fixtures") or []
        points = sum(float(fixture.get("score") or 0) for fixture in fixtures)
        rating = _optional_float(item.get("averageRating") or fantasy_player.get("averageRating"))
        picks.append(
            PickPayload(
                player=PlayerPayload(
                    externalId=str(player_src.get("id") or fantasy_player.get("id") or item.get("id")),
                    name=player_src.get("name") or player_src.get("shortName") or "Unknown",
                    position=normalize_position(
                        player_src.get("position") or fantasy_player.get("position")
                    ),
                    club=team_src.get("name") if isinstance(team_src, dict) else None,
                    clubExternalId=_club_external_id(team_src, item),
                ),
                role="bench" if item.get("substitute") else "starter",
                points=points,
                captain=bool(item.get("captain")),
                viceCaptain=False,
                rating=rating,
                price=_optional_float(item.get("price") if item.get("price") is not None else fantasy_player.get("price")),
                breakdown={"goals": fantasy_player.get("goals"), "assists": fantasy_player.get("assists")},
            )
        )

    triple_captain = bool(user_round.get("tripleCaptainActive") or payload.get("tripleCaptain"))
    team_points = _optional_float(user_round.get("score"))
    if team_points is None:
        team_points = sum(
            pick.points * (3 if pick.captain and triple_captain else 2 if pick.captain else 1)
            for pick in picks
            if pick.role == "starter"
        )

    return Snapshot(
        competition={
            "source": "sofascore",
            "externalId": str(unique.get("id") or fantasy_comp.get("id") or "17"),
            "name": unique.get("name") or fantasy_comp.get("name") or "Premier League",
            "season": _normalize_season(season_src.get("year") if isinstance(season_src, dict) else season_src),
            "slug": unique.get("slug") or fantasy_comp.get("slug") or "premier-league",
        },
        gameweek={
            "number": number,
            "name": fantasy_round.get("name") or f"GW{number}",
            "status": status,
            "startsAt": _date_from_timestamp(fantasy_round.get("startTimestamp")),
            "endsAt": _date_from_timestamp(fantasy_round.get("endTimestamp")),
        },
        team={
            "name": squad.get("name") or user_comp.get("name") or "My SofaScore team",
            "managerName": user_comp.get("userName"),
        },
        picks=picks,
        teamPoints=team_points,
        tripleCaptain=triple_captain,
        transferPenalty=_optional_float(user_round.get("transferPenalty")),
    )


def _first_unique_tournament(squad: dict[str, Any]) -> dict[str, Any]:
    for item in squad.get("players") or []:
        for fixture in item.get("fixtures") or []:
            unique = ((fixture.get("tournament") or {}).get("uniqueTournament")) or {}
            if unique:
                return unique
    return {}


def _normalize_season(year: Any) -> str:
    if not year:
        return "2026/27"
    text = str(year)
    parts = text.split("/")
    if len(parts) == 2 and len(parts[0]) == 2 and parts[0].isdigit():
        return f"20{parts[0]}/{parts[1]}"
    return text


def _date_from_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc).date().isoformat()


def _from_sofascore_like(payload: dict[str, Any]) -> Snapshot:
    competition_src = payload.get("competition") or payload.get("uniqueTournament") or {}
    season = payload.get("season") or competition_src.get("season") or "2026/27"
    if isinstance(season, dict):
        season = season.get("year") or season.get("name") or "2026/27"
    name = competition_src.get("name") or "Premier League"
    external_id = str(competition_src.get("id") or competition_src.get("externalId") or "17")
    slug = competition_src.get("slug") or name.lower().replace(" ", "-")

    round_src = payload.get("round") or payload.get("gameweek") or {}
    number = int(round_src.get("week") or round_src.get("number") or payload.get("gameweekNumber") or 1)
    team_src = payload.get("userTeam") or payload.get("team") or {}
    lineup = payload.get("lineup") or payload.get("picks") or []

    picks: list[PickPayload] = []
    starter_points = 0.0
    for item in lineup:
        player_src = item.get("player") or item
        position = normalize_position(player_src.get("position") or item.get("position"))
        on_bench = bool(item.get("onBench") or item.get("bench"))
        points = float(item.get("fantasyPoints") if item.get("fantasyPoints") is not None else item.get("points") or 0)
        role = "bench" if on_bench else item.get("role", "starter")
        pick = PickPayload(
            player=PlayerPayload(
                externalId=str(player_src.get("id") or player_src.get("externalId")),
                name=player_src.get("name") or player_src.get("shortName") or "Unknown",
                position=position,
                club=(player_src.get("team") or {}).get("name") if isinstance(player_src.get("team"), dict) else player_src.get("club") or player_src.get("team"),
                clubExternalId=_club_external_id(player_src.get("team") if isinstance(player_src.get("team"), dict) else None, item),
            ),
            role=role,
            points=points,
            captain=bool(item.get("isCaptain") or item.get("captain")),
            viceCaptain=bool(item.get("isViceCaptain") or item.get("viceCaptain")),
            rating=_optional_float(item.get("rating")),
            price=_optional_float(item.get("price") or item.get("fantasyPrice")),
            breakdown=item.get("stats") or item.get("breakdown") or {},
        )
        picks.append(pick)
        if pick.role == "starter":
            starter_points += pick.points

    team_points = _optional_float(payload.get("teamPoints") or team_src.get("points")) or starter_points
    return Snapshot(
        competition={
            "source": "sofascore",
            "externalId": external_id,
            "name": name,
            "season": str(season),
            "slug": slug,
        },
        gameweek={
            "number": number,
            "name": round_src.get("name") or f"GW{number}",
            "status": round_src.get("status") or "finished",
            "startsAt": round_src.get("startsAt"),
            "endsAt": round_src.get("endsAt"),
        },
        team={
            "name": team_src.get("name") or "My SofaScore team",
            "managerName": team_src.get("manager") or team_src.get("managerName"),
        },
        picks=picks,
        teamPoints=team_points,
        tripleCaptain=bool(payload.get("tripleCaptain")),
        transferPenalty=_optional_float(payload.get("transferPenalty")),
    )


def _club_external_id(team_src: Any, item: dict[str, Any]) -> str | None:
    if isinstance(team_src, dict) and team_src.get("id") is not None:
        return str(team_src["id"])
    for key in ("clubExternalId", "clubId", "teamId"):
        if item.get(key) is not None:
            return str(item[key])
    return None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


class SofaScoreAdapter(FantasyAdapter):
    """Loads SofaScore Fantasy data from a local export, or from URLs you paste.

    Does not log in or bypass access controls. If you want live pulls, copy a
    session cookie from your own browser and set SOFASCORE_* URLs in .env.
    """

    def __init__(self, session_cookie: str | None = None, timeout: int = 20) -> None:
        self.session_cookie = session_cookie or os.getenv("SOFASCORE_SESSION", "")
        self.timeout = timeout
        self.competition_url = os.getenv("SOFASCORE_COMPETITION_URL", "")
        self.squad_url = os.getenv("SOFASCORE_SQUAD_URL", "")
        self.gameweek_url = os.getenv("SOFASCORE_GAMEWEEK_URL", "")

    def fetch_competitions(self) -> list[dict[str, Any]]:
        if not self.competition_url:
            return []
        payload = self._get_json(self.competition_url)
        if isinstance(payload, list):
            return payload
        return [payload]

    def fetch_squad(self, competition_slug: str) -> dict[str, Any]:
        if not self.squad_url:
            raise ValueError("SOFASCORE_SQUAD_URL is empty. Use file import or set the URL from your Network tab.")
        return self._get_json(self.squad_url)

    def fetch_gameweek_scores(self, competition_slug: str, gameweek: int) -> Snapshot:
        if not self.gameweek_url:
            raise ValueError("SOFASCORE_GAMEWEEK_URL is empty. Use `python -m collector import <file.json>` instead.")
        url = self.gameweek_url.format(competition=competition_slug, gameweek=gameweek)
        return snapshot_from_payload(self._get_json(url))

    def _get_json(self, url: str) -> Any:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http(s) URLs are allowed")
        headers = {"Accept": "application/json", "User-Agent": "fantasy-football-tracker-collector/0.1"}
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


def load_snapshot_file(path: str) -> Snapshot:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return snapshot_from_payload(payload)
