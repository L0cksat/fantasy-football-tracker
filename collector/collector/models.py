from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PlayerPayload:
    externalId: str
    name: str
    position: str | None = None
    club: str | None = None
    clubExternalId: str | None = None


@dataclass
class PickPayload:
    player: PlayerPayload
    role: str
    points: float
    captain: bool = False
    viceCaptain: bool = False
    rating: float | None = None
    price: float | None = None
    breakdown: dict[str, Any] = field(default_factory=dict)


@dataclass
class Snapshot:
    competition: dict[str, Any]
    gameweek: dict[str, Any]
    team: dict[str, Any]
    picks: list[PickPayload]
    teamPoints: float | None = None
    tripleCaptain: bool = False
    transferPenalty: float | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "competition": self.competition,
            "gameweek": self.gameweek,
            "team": self.team,
            "picks": [asdict(pick) for pick in self.picks],
            "tripleCaptain": self.tripleCaptain,
        }
        if self.teamPoints is not None:
            payload["teamPoints"] = self.teamPoints
        if self.transferPenalty is not None:
            payload["transferPenalty"] = self.transferPenalty
        return payload


@dataclass
class TransferPlayer:
    externalId: str
    name: str
    position: str | None = None
    club: str | None = None
    clubExternalId: str | None = None
    price: float | None = None


@dataclass
class TransferPair:
    playerIn: TransferPlayer
    playerOut: TransferPlayer


@dataclass
class TransferRound:
    number: int
    name: str
    transferPenalty: float = 0
    transfers: list[TransferPair] = field(default_factory=list)


@dataclass
class TransfersBatch:
    competition: dict[str, Any]
    team: dict[str, Any]
    rounds: list[TransferRound]

    def to_dict(self) -> dict[str, Any]:
        return {
            "competition": self.competition,
            "team": self.team,
            "rounds": [
                {
                    "number": round_.number,
                    "name": round_.name,
                    "transferPenalty": round_.transferPenalty,
                    "transfers": [
                        {
                            "playerIn": {
                                "externalId": pair.playerIn.externalId,
                                "name": pair.playerIn.name,
                                "position": pair.playerIn.position,
                                "club": pair.playerIn.club,
                                "clubExternalId": pair.playerIn.clubExternalId,
                            },
                            "playerOut": {
                                "externalId": pair.playerOut.externalId,
                                "name": pair.playerOut.name,
                                "position": pair.playerOut.position,
                                "club": pair.playerOut.club,
                                "clubExternalId": pair.playerOut.clubExternalId,
                            },
                            "priceIn": pair.playerIn.price,
                            "priceOut": pair.playerOut.price,
                        }
                        for pair in round_.transfers
                    ],
                }
                for round_ in self.rounds
            ],
        }


class FantasyAdapter:
    """Contract for later FPL / LaLiga / WSL adapters."""

    def fetch_competitions(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_squad(self, competition_slug: str) -> dict[str, Any]:
        raise NotImplementedError

    def fetch_gameweek_scores(self, competition_slug: str, gameweek: int) -> Snapshot:
        raise NotImplementedError
