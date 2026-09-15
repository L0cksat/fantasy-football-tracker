from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import quote

from collector.adapters.sofascore import _browser_headers, _http_get

PREMIER_LEAGUE_TOURNAMENT_ID = 17
WSL_TOURNAMENT_ID = 1044
WSL2_TOURNAMENT_ID = 10553

_CLUB_ALIASES = {
    "man utd": "manchester united",
    "man city": "manchester city",
    "spurs": "tottenham",
    "nottm forest": "nottingham forest",
    "wolves": "wolverhampton",
    "newcastle": "newcastle united",
    "west ham": "west ham united",
    "brighton": "brighton",
    "brighton hove albion": "brighton",
    "leeds": "leeds united",
    "bournemouth": "bournemouth",
    "afc bournemouth": "bournemouth",
    "london city": "london city",
}


def fold_name(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def club_key(name: Any) -> str:
    folded = fold_name(name)
    folded = re.sub(r"\b(fc|afc|wfc|women|ladies|hotspur|wanderers|lionesses)\b", "", folded)
    folded = re.sub(r"\b((and )?hove albion)\b", "", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    return _CLUB_ALIASES.get(folded, folded)


def fetch_tournament_players(tournament_id: int) -> list[dict[str, Any]]:
    """SofaScore unique-tournament/{id} current-season player list (same path family as LaLiga 8)."""
    headers = _browser_headers("")
    seasons_payload = _http_get(
        f"https://www.sofascore.com/api/v1/unique-tournament/{tournament_id}/seasons",
        headers=headers,
        timeout=20,
    )
    seasons_payload.raise_for_status()
    seasons = (seasons_payload.json() or {}).get("seasons") or []
    if not seasons or seasons[0].get("id") is None:
        raise ValueError(f"SofaScore unique-tournament/{tournament_id} seasons JSON had no current season.")
    season_id = int(seasons[0]["id"])
    players_payload = _http_get(
        f"https://www.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{season_id}/players",
        headers=headers,
        timeout=30,
    )
    players_payload.raise_for_status()
    return list((players_payload.json() or {}).get("players") or [])


def fetch_premier_league_players() -> list[dict[str, Any]]:
    return fetch_tournament_players(PREMIER_LEAGUE_TOURNAMENT_ID)


def resolve_sofascore_player(
    *,
    web_name: str,
    first_name: str = "",
    second_name: str = "",
    club: str = "",
    directory: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Match an FPL player to a SofaScore Premier League catalog row."""
    club_fold = club_key(club)
    candidates = [item for item in directory if club_key(item.get("teamName")) == club_fold]
    if not candidates:
        return None
    full = fold_name(f"{first_name} {second_name}")
    web = fold_name(web_name)
    second = fold_name(second_name)
    for item in candidates:
        if fold_name(item.get("playerName")) == full and full:
            return item
    for item in candidates:
        if web and fold_name(item.get("playerName")) == web:
            return item
    token_hits = [item for item in candidates if _tokens_match(web, fold_name(item.get("playerName")))]
    if len(token_hits) == 1:
        return token_hits[0]
    last_hits = [item for item in candidates if second and second in fold_name(item.get("playerName")).split()]
    if len(last_hits) == 1:
        return last_hits[0]
    return None


def search_sofascore_player(query: str) -> dict[str, Any] | None:
    """Fallback: SofaScore search/all, same path used for official LaLiga IDs."""
    q = (query or "").strip()
    if not q:
        return None
    response = _http_get(
        f"https://www.sofascore.com/api/v1/search/all?q={quote(q)}",
        headers=_browser_headers(""),
        timeout=20,
    )
    if response.status_code != 200:
        return None
    for row in (response.json() or {}).get("results") or []:
        if row.get("type") != "player":
            continue
        entity = row.get("entity") or {}
        if entity.get("id") is None:
            continue
        return {
            "playerId": entity.get("id"),
            "playerName": entity.get("name"),
            "teamId": (entity.get("team") or {}).get("id"),
            "teamName": (entity.get("team") or {}).get("name"),
        }
    return None


def _tokens_match(needle: str, haystack: str) -> bool:
    tokens = [part for part in needle.split() if part]
    names = haystack.split()
    if not tokens or not names:
        return False
    if len(tokens) == 1:
        return tokens[0] in names
    return all(part in names for part in tokens)
