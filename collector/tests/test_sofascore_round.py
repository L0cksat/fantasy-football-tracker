from collector.adapters.sofascore_round import apply_round_overlay, overlay_from_lineups
from collector.models import PickPayload, PlayerPayload, Snapshot


def test_overlay_from_lineups_reads_ratings_and_injury_missing():
    ratings, injured = overlay_from_lineups(
        {
            "home": {
                "players": [
                    {
                        "player": {"id": 869792, "name": "Gabriel Magalhães"},
                        "statistics": {"rating": 6.4},
                    }
                ],
                "missingPlayers": [
                    {
                        "player": {"id": 941168, "name": "William Saliba"},
                        "type": "missing",
                        "reason": 1,
                        "description": "Back Injury",
                    },
                    {
                        "player": {"id": 861315, "name": "Ephron Mason-Clark"},
                        "type": "doubtful",
                        "reason": 1,
                        "description": "Hamstring Injury",
                    },
                ],
            },
            "away": {
                "players": [
                    {
                        "player": {"id": 151545, "name": "Virgil van Dijk"},
                        "statistics": {"rating": 7.2},
                    }
                ],
                "missingPlayers": [],
            },
        }
    )
    assert ratings["869792"] == 6.4
    assert ratings["151545"] == 7.2
    assert injured == {"941168"}


def test_apply_round_overlay_sets_rating_and_injured_on_picks():
    snapshot = Snapshot(
        competition={"source": "fpl", "externalId": "4795659"},
        gameweek={"number": 1, "name": "GW1", "status": "finished"},
        team={"name": "The Inbetweeners FC"},
        picks=[
            PickPayload(
                player=PlayerPayload(externalId="869792", name="Gabriel"),
                role="starter",
                points=2,
            ),
            PickPayload(
                player=PlayerPayload(externalId="941168", name="Saliba"),
                role="bench",
                points=0,
            ),
        ],
    )
    apply_round_overlay(snapshot, ratings={"869792": 6.4}, injured_ids={"941168"})
    assert snapshot.picks[0].rating == 6.4
    assert snapshot.picks[0].injured is False
    assert snapshot.picks[1].injured is True
    assert snapshot.picks[1].rating is None
