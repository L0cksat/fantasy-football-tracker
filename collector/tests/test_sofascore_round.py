from collector.adapters.sofascore_round import apply_round_overlay, overlay_from_lineups
from collector.models import PickPayload, PlayerPayload, Snapshot


def test_overlay_from_lineups_reads_ratings_injury_and_suspension():
    ratings, injured, suspended = overlay_from_lineups(
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
                    {
                        "player": {"id": 1001, "name": "Yellow Acc"},
                        "type": "missing",
                        "reason": 11,
                        "description": "yellow_card_accumulation_suspension",
                    },
                    {
                        "player": {"id": 1002, "name": "Red Card"},
                        "type": "missing",
                        "reason": 13,
                        "description": "Red card suspension",
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
                "missingPlayers": [
                    {
                        "player": {"id": 1003, "name": "Mislabelled"},
                        "type": "missing",
                        "reason": 1,
                        "description": "yellow_card_accumulation_suspension",
                    },
                    {
                        "player": {"id": 1004, "name": "Unavailable"},
                        "type": "missing",
                        "reason": 0,
                        "description": "Player unavailable",
                    },
                ],
            },
        }
    )
    assert ratings["869792"] == 6.4
    assert ratings["151545"] == 7.2
    assert injured == {"941168"}
    assert suspended == {"1001", "1002", "1003", "1004"}


def test_apply_round_overlay_sets_rating_injured_and_suspended_on_picks():
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
            PickPayload(
                player=PlayerPayload(externalId="1002", name="Suspended"),
                role="bench",
                points=0,
                injured=True,
            ),
        ],
    )
    apply_round_overlay(
        snapshot,
        ratings={"869792": 6.4},
        injured_ids={"941168", "1002"},
        suspended_ids={"1002"},
    )
    assert snapshot.picks[0].rating == 6.4
    assert snapshot.picks[0].injured is False
    assert snapshot.picks[0].suspended is False
    assert snapshot.picks[1].injured is True
    assert snapshot.picks[1].suspended is False
    assert snapshot.picks[1].rating is None
    assert snapshot.picks[2].suspended is True
    assert snapshot.picks[2].injured is False
