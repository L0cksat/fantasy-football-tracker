from __future__ import annotations

import json
import os
import re
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
    # Premier League
    "17": "Manchester City",
    "30": "Brighton & Hove Albion",
    "32": "Ipswich Town",
    "35": "Manchester United",
    "38": "Chelsea",
    "42": "Arsenal",
    "96": "Hull City",
    # LaLiga
    "2814": "Espanyol",
    "2816": "Real Betis",
    "2817": "FC Barcelona",
    "2818": "Rayo Vallecano",
    "2819": "Villarreal",
    "2820": "Osasuna",
    "2821": "Celta Vigo",
    "2824": "Real Sociedad",
    "2825": "Athletic Club",
    "2828": "Valencia",
    "2829": "Real Madrid",
    "2830": "Málaga",
    "2832": "Deportivo de La Coruña",
    "2833": "Sevilla",
    "2835": "Racing Santander",
    "2836": "Atlético Madrid",
    "2846": "Elche",
    "2849": "Levante",
    "2859": "Getafe",
    "2885": "Deportivo Alavés",
    # Ligue 1
    "1641": "Olympique de Marseille",
    "1643": "Lille",
    "1644": "Paris Saint-Germain",
    "1646": "Auxerre",
    "1648": "RC Lens",
    "1649": "Olympique Lyonnais",
    "1653": "AS Monaco",
    "1658": "Stade Rennais",
    "1659": "RC Strasbourg",
    "1661": "Nice",
    "1681": "Toulouse",
    "6070": "Paris FC",
    # Serie A
    "2685": "Bologna",
    "2686": "Atalanta",
    "2687": "Juventus",
    "2689": "Lecce",
    "2692": "AC Milan",
    "2693": "Fiorentina",
    "2695": "Udinese",
    "2697": "Inter",
    "2702": "AS Roma",
    "2704": "Como",
    "2714": "SSC Napoli",
    "2793": "Sassuolo",
    "2801": "Frosinone",
    # MLS
    "2508": "Houston Dynamo",
    "2510": "Colorado Rapids",
    "2511": "New England Revolution",
    "2512": "FC Dallas",
    "2513": "LA Galaxy",
    "7080": "Toronto FC",
    "21825": "San Jose Earthquakes",
    "52237": "Orlando City SC",
    "187643": "New York City FC",
    "274650": "Los Angeles FC",
    "337602": "Inter Miami CF",
    "337612": "Nashville SC",
    "404108": "Charlotte FC",
    "1043961": "San Diego FC",
    # Brasileirão
    "1954": "Cruzeiro",
    "1955": "Bahia",
    "1961": "Fluminense",
    "1962": "Vitória",
    "1963": "Palmeiras",
    "1966": "Internacional",
    "1967": "Athletico",
    "1974": "Vasco da Gama",
    "1977": "Atlético Mineiro",
    "1981": "São Paulo",
    "1982": "Coritiba",
    "1999": "Red Bull Bragantino",
    "5981": "Flamengo",
}
CLUB_BY_CODE = {
    # Premier League
    "ARS": "Arsenal",
    "BHA": "Brighton & Hove Albion",
    "CHE": "Chelsea",
    "HUL": "Hull City",
    "IPS": "Ipswich Town",
    "MCI": "Manchester City",
    "MUN": "Manchester United",
    # LaLiga
    "ALA": "Deportivo Alavés",
    "ATM": "Atlético Madrid",
    "ATH": "Athletic Club",
    "BAR": "FC Barcelona",
    "BET": "Real Betis",
    "CEL": "Celta Vigo",
    "DEP": "Deportivo de La Coruña",
    "ELC": "Elche",
    "ESP": "Espanyol",
    "GET": "Getafe",
    "LEV": "Levante",
    "MAL": "Málaga",
    "OSA": "Osasuna",
    "RAY": "Rayo Vallecano",
    "RMA": "Real Madrid",
    "RSO": "Real Sociedad",
    "SAN": "Racing Santander",
    "SEV": "Sevilla",
    "VAL": "Valencia",
    "VIL": "Villarreal",
    # Ligue 1
    "AJA": "Auxerre",
    "ASM": "AS Monaco",
    "LIL": "Lille",
    "OGC": "Nice",
    "OL": "Olympique Lyonnais",
    "OM": "Olympique de Marseille",
    "PFC": "Paris FC",
    "PSG": "Paris Saint-Germain",
    "RCL": "RC Lens",
    "SR": "Stade Rennais",
    "STR": "RC Strasbourg",
    "TFC": "Toulouse",
    # Serie A
    "ACM": "AC Milan",
    "ASR": "AS Roma",
    "ATA": "Atalanta",
    "BOL": "Bologna",
    "COM": "Como",
    "FIO": "Fiorentina",
    "FRO": "Frosinone",
    "INT": "Inter",
    "JUV": "Juventus",
    "LEC": "Lecce",
    "NAP": "SSC Napoli",
    "SAS": "Sassuolo",
    "UDI": "Udinese",
    # MLS
    "CLT": "Charlotte FC",
    "COL": "Colorado Rapids",
    "DAL": "FC Dallas",
    "HOU": "Houston Dynamo",
    "LA": "LA Galaxy",
    "LAFC": "Los Angeles FC",
    "MIA": "Inter Miami CF",
    "NE": "New England Revolution",
    "NSH": "Nashville SC",
    "NYC": "New York City FC",
    "ORL": "Orlando City SC",
    "SD": "San Diego FC",
    "SJ": "San Jose Earthquakes",
    "TOR": "Toronto FC",
    # Brasileirão (INT left to Serie A Inter; Internacional resolves via club id 1966)
    "BAH": "Bahia",
    "BRA": "Red Bull Bragantino",
    "CAM": "Atlético Mineiro",
    "CAP": "Athletico",
    "CFC": "Coritiba",
    "CRU": "Cruzeiro",
    "FLA": "Flamengo",
    "FLU": "Fluminense",
    "PAL": "Palmeiras",
    "SPA": "São Paulo",
    "VAS": "Vasco da Gama",
    "VIT": "Vitória",
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

_ROUND_PATH = re.compile(r"/round/\d+(?=/|$)")


def normalize_position(value: str | None) -> str | None:
    if not value:
        return None
    return POSITION_MAP.get(value.strip().upper(), value.strip().upper())


def resolve_club_name(
    *,
    club_id: str | None = None,
    name: Any = None,
    name_code: Any = None,
) -> str | None:
    """Prefer full club names; map SofaScore nameCode / short abbreviations (e.g. BET → Real Betis)."""
    code = str(name_code).strip().upper() if name_code not in (None, "") else ""
    label = str(name).strip() if name not in (None, "") else ""
    if label and re.fullmatch(r"[A-Za-z]{2,4}", label):
        code = label.upper()
        label = ""
    if club_id:
        mapped = CLUB_BY_ID.get(str(club_id).strip())
        if mapped:
            return mapped
    if code:
        mapped = CLUB_BY_CODE.get(code)
        if mapped:
            return mapped
    return label or (code or None)


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
        club=resolve_club_name(club_id=club_id, name=None, name_code=team_code),
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
            injured=bool(pick.get("injured")),
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
                    club=resolve_club_name(
                        club_id=_club_external_id(team_src, item),
                        name=team_src.get("name") if isinstance(team_src, dict) else None,
                        name_code=team_src.get("nameCode") if isinstance(team_src, dict) else None,
                    ),
                    clubExternalId=_club_external_id(team_src, item),
                    shirtNumber=_optional_int(player_src.get("jerseyNumber") or player_src.get("shirtNumber")),
                ),
                role="bench" if item.get("substitute") else "starter",
                points=points,
                captain=bool(item.get("captain")),
                viceCaptain=False,
                rating=rating,
                price=_optional_float(item.get("price") if item.get("price") is not None else fantasy_player.get("price")),
                injured=_injured_from_sofascore(item, fantasy_player, player_src),
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


def _injured_from_sofascore(item: dict[str, Any], fantasy_player: dict[str, Any], player_src: dict[str, Any]) -> bool:
    if item.get("injured") or fantasy_player.get("injured") or player_src.get("injured"):
        return True
    injury = player_src.get("injury") or fantasy_player.get("injury") or {}
    if isinstance(injury, dict) and str(injury.get("status") or "").lower() == "out":
        return True
    return False


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
            injured=bool(item.get("injured") or player_src.get("injured")),
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


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class SofaScoreSessionError(RuntimeError):
    """Cookie missing, expired, or rejected. Refresh SOFASCORE_SESSION from the browser."""

    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(
            f"SofaScore returned HTTP {status}. Open Firefox while logged into Fantasy, "
            "copy the Cookie header from a Fantasy XHR, set SOFASCORE_SESSION in .env, and rerun pull."
        )


class SofaScoreAdapter(FantasyAdapter):
    """Loads SofaScore Fantasy data from a local export, or from URLs you paste.

    Does not log in or bypass access controls. If you want live pulls, copy a
    session cookie from your own browser and set SOFASCORE_* URLs in .env.
    """

    def __init__(
        self,
        session_cookie: str | None = None,
        timeout: int = 20,
        *,
        competition_url: str | None = None,
        squad_url: str | None = None,
        gameweek_url: str | None = None,
        transfers_url: str | None = None,
    ) -> None:
        self.session_cookie = _normalize_session_cookie(
            session_cookie if session_cookie is not None else os.getenv("SOFASCORE_SESSION", "")
        )
        self.timeout = timeout
        self.competition_url = _env_or(competition_url, "SOFASCORE_COMPETITION_URL")
        self.squad_url = _env_or(squad_url, "SOFASCORE_SQUAD_URL")
        self.gameweek_url = _env_or(gameweek_url, "SOFASCORE_GAMEWEEK_URL")
        self.transfers_url = _env_or(transfers_url, "SOFASCORE_TRANSFERS_URL")

    def fetch_competitions(self) -> list[dict[str, Any]]:
        if not self.competition_url:
            return []
        payload = self._get_json(self.competition_url)
        if isinstance(payload, list):
            return payload
        return [payload]

    def fetch_meta(self) -> dict[str, Any] | None:
        payloads = self.fetch_competitions()
        if not payloads:
            return None
        first = payloads[0]
        return first if isinstance(first, dict) else None

    def fetch_rounds(self) -> dict[str, Any] | None:
        if not self.competition_url:
            return None
        url = self.competition_url.rstrip("/") + "/rounds"
        payload = self._get_json(url, missing_ok=True)
        return payload if isinstance(payload, dict) else None

    def fetch_squad(
        self,
        competition_slug: str,
        gameweek: int | None = None,
        *,
        round_id: int | None = None,
    ) -> dict[str, Any]:
        if not self.squad_url:
            raise ValueError("SOFASCORE_SQUAD_URL is empty. Set it from your Network tab, or use file import.")
        self._require_round_id(self.squad_url, round_id)
        return self._get_json(
            self.squad_url,
            competition=competition_slug,
            gameweek=gameweek,
            round_id=round_id,
        )

    def fetch_transfers(
        self,
        competition_slug: str | None = None,
        gameweek: int | None = None,
        *,
        round_id: int | None = None,
        missing_ok: bool = False,
    ) -> dict[str, Any] | None:
        if not self.transfers_url:
            raise ValueError(
                "SOFASCORE_TRANSFERS_URL is empty. Set it from your Network tab, or import transfers JSON."
            )
        return self._get_json(
            self.transfers_url,
            competition=competition_slug,
            gameweek=gameweek,
            round_id=round_id,
            missing_ok=missing_ok,
        )

    def fetch_gameweek_scores(self, competition_slug: str, gameweek: int) -> Snapshot:
        if not self.gameweek_url:
            raise ValueError("SOFASCORE_GAMEWEEK_URL is empty. Use `python -m collector pull` or `import`.")
        return snapshot_from_payload(
            self._get_json(self.gameweek_url, competition=competition_slug, gameweek=gameweek)
        )

    def _get_json(
        self,
        url: str,
        competition: str | None = None,
        gameweek: int | None = None,
        round_id: int | None = None,
        missing_ok: bool = False,
    ) -> Any:
        resolved = _format_url(url, competition=competition, gameweek=gameweek, round_id=round_id)
        parsed = urlparse(resolved)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http(s) URLs are allowed")
        response = _http_get(resolved, headers=_browser_headers(self.session_cookie), timeout=self.timeout)
        if response.status_code in {401, 403}:
            raise SofaScoreSessionError(response.status_code)
        if missing_ok and response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _require_round_id(url: str, round_id: int | None) -> None:
        if round_id is not None:
            return
        if "{roundId}" in url or "{round_id}" in url:
            raise ValueError(
                "SOFASCORE_SQUAD_URL has {roundId} but competition JSON has no currentRound.id. "
                "Paste a /round/1088/ squad URL, or check SOFASCORE_COMPETITION_URL."
            )


def round_id_from_meta(meta: dict[str, Any] | None, gameweek: int | None = None) -> int | None:
    """SofaScore round id: currentRound, or the round whose sequence matches --gameweek."""
    if not meta:
        return None
    user_comp = meta.get("userCompetition") or {}
    fantasy = user_comp.get("fantasyCompetition") or {}
    if not fantasy and "fantasyCompetition" in meta:
        fantasy = meta.get("fantasyCompetition") or {}
        user_comp = meta if "joinedInRound" in meta or "name" in meta else user_comp
    rounds = [
        fantasy.get("currentRound"),
        fantasy.get("nextRound"),
        fantasy.get("previousRound"),
        user_comp.get("joinedInRound"),
    ]
    named = [item for item in rounds if isinstance(item, dict) and item.get("id") is not None]
    for item in meta.get("userRounds") or []:
        if not isinstance(item, dict):
            continue
        fantasy_round = item.get("fantasyRound") if isinstance(item.get("fantasyRound"), dict) else item
        if fantasy_round.get("id") is not None:
            named.append(fantasy_round)
    if gameweek is not None:
        for item in named:
            if item.get("sequence") == gameweek:
                return int(item["id"])
        known = ", ".join(
            f"{item.get('sequence')}→{item.get('id')}" for item in named if item.get("sequence") is not None
        )
        raise ValueError(
            f"No SofaScore round with sequence {gameweek} in competition JSON"
            + (f" (known: {known})" if known else "")
            + "."
        )
    current = fantasy.get("currentRound") or {}
    if current.get("id") is not None:
        return int(current["id"])
    return None


def _browser_headers(session_cookie: str) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en-GB,en;q=0.9",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/fantasy",
        "X-Requested-With": "XMLHttpRequest",
    }
    if session_cookie:
        headers["Cookie"] = session_cookie
    return headers


def _http_get(url: str, headers: dict[str, str], timeout: int) -> Any:
    """GET JSON like the site XHR. Prefer curl_cffi so SofaScore does not 403 Python's TLS."""
    try:
        from curl_cffi import requests as curl_requests

        return curl_requests.get(url, headers=headers, timeout=timeout, impersonate="chrome")
    except ImportError:
        merged = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            **headers,
        }
        return requests.get(url, headers=merged, timeout=timeout)


def _env_or(explicit: str | None, key: str) -> str:
    if explicit is not None:
        return explicit
    return os.getenv(key, "")


def _normalize_session_cookie(raw: str | None) -> str:
    text = (raw or "").strip()
    if text.lower().startswith("cookie:"):
        text = text[7:].strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1]
    return text


def _format_url(
    url: str,
    competition: str | None = None,
    gameweek: int | None = None,
    round_id: int | None = None,
) -> str:
    values: dict[str, Any] = {
        "competition": competition or "",
        "gameweek": "" if gameweek is None else gameweek,
    }
    if round_id is not None:
        values["roundId"] = round_id
        values["round_id"] = round_id
    try:
        formatted = url.format(**values)
    except (KeyError, IndexError, ValueError):
        formatted = url
    if round_id is not None:
        formatted = _ROUND_PATH.sub(f"/round/{round_id}", formatted)
    return formatted


def load_snapshot_file(path: str) -> Snapshot:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return snapshot_from_payload(payload)
