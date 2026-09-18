from collector.adapters.fpl import (
    catalog_from_bootstrap,
    competition_payload,
    snapshot_from_picks,
    team_payload,
    transfers_from_fpl,
)


def _catalog():
    catalog = catalog_from_bootstrap(
        {
            "teams": [{"id": 1, "name": "Arsenal", "code": 3}, {"id": 8, "name": "Chelsea", "code": 8}],
            "elements": [
                {
                    "id": 10,
                    "web_name": "Saka",
                    "first_name": "Bukayo",
                    "second_name": "Saka",
                    "element_type": 3,
                    "team": 1,
                    "now_cost": 100,
                },
                {
                    "id": 20,
                    "web_name": "João Pedro",
                    "first_name": "João Pedro",
                    "second_name": "Junqueira de Jesus",
                    "element_type": 4,
                    "team": 8,
                    "now_cost": 75,
                },
                {
                    "id": 30,
                    "web_name": "Raya",
                    "first_name": "David",
                    "second_name": "Raya",
                    "element_type": 1,
                    "team": 1,
                    "now_cost": 55,
                },
            ],
            "events": [
                {
                    "id": 1,
                    "name": "Gameweek 1",
                    "finished": True,
                    "is_current": False,
                    "deadline_time": "2026-08-21T17:30:00Z",
                }
            ],
        }
    )
    catalog["sofascore_players"] = [
        {"playerId": 934641, "playerName": "Bukayo Saka", "teamName": "Arsenal", "teamId": 42},
        {"playerId": 975079, "playerName": "João Pedro", "teamName": "Chelsea", "teamId": 38},
        {"playerId": 365409, "playerName": "David Raya", "teamName": "Arsenal", "teamId": 42},
    ]
    return catalog


def test_fpl_snapshot_maps_captain_raw_points_and_badge_code():
    catalog = _catalog()
    snapshot = snapshot_from_picks(
        {
            "active_chip": None,
            "entry_history": {"event": 1, "points": 28, "event_transfers_cost": 0},
            "picks": [
                {
                    "element": 30,
                    "position": 1,
                    "multiplier": 1,
                    "is_captain": False,
                    "is_vice_captain": True,
                    "element_type": 1,
                },
                {
                    "element": 20,
                    "position": 11,
                    "multiplier": 2,
                    "is_captain": True,
                    "is_vice_captain": False,
                    "element_type": 4,
                },
                {
                    "element": 10,
                    "position": 12,
                    "multiplier": 0,
                    "is_captain": False,
                    "is_vice_captain": False,
                    "element_type": 3,
                },
            ],
        },
        {
            "elements": [
                {"id": 30, "stats": {"total_points": 6, "minutes": 90, "goals_scored": 0, "assists": 0}},
                {"id": 20, "stats": {"total_points": 11, "minutes": 90, "goals_scored": 1, "assists": 0}},
                {"id": 10, "stats": {"total_points": 2, "minutes": 20, "goals_scored": 0, "assists": 0}},
            ]
        },
        catalog,
        {"name": "The Inbetweeners FC", "player_first_name": "Nicky", "player_last_name": "Jones"},
        catalog["events"][1],
        competition_payload("4795659", catalog),
        team_payload({"name": "The Inbetweeners FC", "player_first_name": "Nicky", "player_last_name": "Jones"}),
    )
    assert snapshot.competition["source"] == "fpl"
    assert snapshot.competition["slug"] == "premier-league-fantasy"
    assert snapshot.competition["externalId"] == "4795659"
    assert snapshot.gameweek["status"] == "finished"
    assert snapshot.teamPoints == 28
    assert snapshot.tripleCaptain is False
    assert snapshot.picks[0].viceCaptain is True
    assert snapshot.picks[0].role == "starter"
    assert snapshot.picks[1].captain is True
    assert snapshot.picks[1].points == 11
    assert snapshot.picks[1].player.club == "Chelsea"
    assert snapshot.picks[1].player.clubExternalId == "8"
    assert snapshot.picks[1].player.externalId == "975079"
    assert snapshot.picks[1].player.name == "João Pedro"
    assert snapshot.picks[0].player.name == "David Raya"
    assert snapshot.picks[2].player.name == "Bukayo Saka"
    assert snapshot.picks[1].rating is None
    assert snapshot.picks[1].injured is False
    assert snapshot.picks[2].role == "bench"
    assert snapshot.picks[2].player.externalId == "934641"


def test_fpl_snapshot_applies_sofascore_gw_rating_and_injury():
    catalog = _catalog()
    catalog["elements"][30]["status"] = "i"
    snapshot = snapshot_from_picks(
        {
            "active_chip": None,
            "entry_history": {"event": 1, "points": 28, "event_transfers_cost": 0},
            "picks": [
                {
                    "element": 30,
                    "position": 1,
                    "multiplier": 1,
                    "is_captain": False,
                    "is_vice_captain": True,
                    "element_type": 1,
                },
                {
                    "element": 20,
                    "position": 11,
                    "multiplier": 2,
                    "is_captain": True,
                    "is_vice_captain": False,
                    "element_type": 4,
                },
            ],
        },
        {
            "elements": [
                {"id": 30, "stats": {"total_points": 6, "minutes": 90}},
                {"id": 20, "stats": {"total_points": 11, "minutes": 90}},
            ]
        },
        catalog,
        {"name": "The Inbetweeners FC"},
        catalog["events"][1],
        competition_payload("4795659", catalog),
        team_payload({"name": "The Inbetweeners FC"}),
        ratings={"975079": 7.4, "365409": 6.8},
        injured_ids={"365409"},
    )
    by_id = {pick.player.externalId: pick for pick in snapshot.picks}
    assert by_id["975079"].rating == 7.4
    assert by_id["365409"].rating == 6.8
    assert by_id["365409"].injured is True
    assert by_id["975079"].injured is False


def test_fpl_live_event_marks_bootstrap_injured_status():
    catalog = _catalog()
    catalog["events"][1]["finished"] = False
    catalog["events"][1]["is_current"] = True
    catalog["elements"][20]["status"] = "i"
    catalog["sofascore_players"] = [
        {"playerId": 934641, "playerName": "Bukayo Saka", "teamName": "Arsenal"},
        {"playerId": 975079, "playerName": "João Pedro", "teamName": "Chelsea"},
        {"playerId": 365409, "playerName": "David Raya", "teamName": "Arsenal"},
    ]
    snapshot = snapshot_from_picks(
        {
            "active_chip": None,
            "entry_history": {"event": 1, "points": 28, "event_transfers_cost": 0},
            "picks": [
                {
                    "element": 20,
                    "position": 11,
                    "multiplier": 2,
                    "is_captain": True,
                    "is_vice_captain": False,
                    "element_type": 4,
                }
            ],
        },
        {"elements": [{"id": 20, "stats": {"total_points": 11, "minutes": 0}}]},
        catalog,
        {"name": "The Inbetweeners FC"},
        catalog["events"][1],
        competition_payload("4795659", catalog),
        team_payload({"name": "The Inbetweeners FC"}),
    )
    assert snapshot.gameweek["status"] == "live"
    assert snapshot.picks[0].injured is True


def test_fpl_transfers_convert_tenths_of_a_million():
    catalog = _catalog()
    batch = transfers_from_fpl(
        [
            {
                "element_in": 10,
                "element_in_cost": 100,
                "element_out": 30,
                "element_out_cost": 55,
                "event": 3,
            }
        ],
        {"current": [{"event": 3, "event_transfers_cost": 4}]},
        catalog,
        competition_payload("4795659", catalog),
        team_payload({"name": "The Inbetweeners FC"}),
    )
    assert batch is not None
    assert batch.rounds[0].number == 3
    assert batch.rounds[0].transferPenalty == 4
    pair = batch.rounds[0].transfers[0]
    assert pair.playerIn is not None and pair.playerIn.name == "Bukayo Saka"
    assert pair.playerIn.price == 10.0
    assert pair.playerOut is not None and pair.playerOut.name == "David Raya"
    assert pair.playerOut.price == 5.5
