from unittest.mock import patch

from collector.adapters.wsl import (
    competition_payload,
    snapshot_from_my_team,
    team_payload,
    transfers_from_squads,
)


def _catalog():
    return {
        "players": {
            "wpll::Football_Player::gk1": {
                "playerId": "wpll::Football_Player::gk1",
                "skillId": 1,
                "skillName": "gk",
                "mediaFirstName": "Hannah",
                "mediaLastName": "Hampton",
                "mediaShortName": "H. Hampton",
                "teamOfficialName": "Chelsea",
                "teamShortName": "Chelsea",
                "valuation": 5.5,
                "availabilityStatus": 1,
            },
            "wpll::Football_Player::mid1": {
                "playerId": "wpll::Football_Player::mid1",
                "skillId": 3,
                "skillName": "mid",
                "mediaFirstName": "Alexia",
                "mediaLastName": "Putellas",
                "mediaShortName": "Alexia Putellas",
                "teamOfficialName": "London City Lionesses",
                "teamShortName": "London City",
                "valuation": 8.5,
                "availabilityStatus": 1,
            },
            "wpll::Football_Player::fwd1": {
                "playerId": "wpll::Football_Player::fwd1",
                "skillId": 4,
                "skillName": "fwd",
                "mediaFirstName": "Alessia",
                "mediaLastName": "Russo",
                "mediaShortName": "A. Russo",
                "teamOfficialName": "Arsenal",
                "teamShortName": "Arsenal",
                "valuation": 11.5,
                "availabilityStatus": 4,
            },
            "wpll::Football_Player::fwd2": {
                "playerId": "wpll::Football_Player::fwd2",
                "skillId": 4,
                "skillName": "fwd",
                "mediaFirstName": "Agnes",
                "mediaLastName": "Beever-Jones",
                "mediaShortName": "Beever-Jones",
                "teamOfficialName": "Chelsea",
                "teamShortName": "Chelsea",
                "valuation": 6.5,
                "availabilityStatus": 1,
            },
        },
        "sofascore_players": [
            {"playerId": 111, "playerName": "Hannah Hampton", "teamName": "Chelsea Women", "teamId": 9001},
            {"playerId": 222, "playerName": "Alexia Putellas", "teamName": "London City Lionesses", "teamId": 9002},
            {"playerId": 333, "playerName": "Alessia Russo", "teamName": "Arsenal Women", "teamId": 9003},
            {"playerId": 444, "playerName": "Agnes Beever-Jones", "teamName": "Chelsea Women", "teamId": 9001},
        ],
        "tour": {
            "tourName": "WSL Fantasy",
            "currMatchdayId": 3,
            "lpMatchdayId": 2,
            "deadlineDate": "2026-09-18T18:00:00",
            "scenarioCode": "TRANS",
        },
        "fixtures": [
            {"matchdayId": 1, "matchdayStatus": 5, "matchDateTimeUtc": "2026-09-04T18:00:00"},
            {"matchdayId": 3, "matchdayStatus": 1, "matchDateTimeUtc": "2026-09-18T18:00:00"},
        ],
    }


def _my_team(*, matchday_id=1, matchday_status=5, russo_id="wpll::Football_Player::fwd1"):
    return {
        "matchdayId": matchday_id,
        "teamName": "The Inbetweeners FC",
        "userName": "Jack Sparrownx",
        "captainId": "wpll::Football_Player::mid1",
        "arrTeam": [
            "wpll::Football_Player::gk1",
            "wpll::Football_Player::mid1",
            russo_id,
        ],
        "arrBenchPosition": [0, 0, 1],
        "totalPoints": [3.0, 4.0, 2.0],
        "availabilityStatus": [1, 1, 1],
        "matchdayStatus": [matchday_status, matchday_status, matchday_status],
        "teamValue": 97.5,
        "teamBalance": 2.5,
    }


def test_wsl_snapshot_maps_captain_raw_points_and_sofascore_ids():
    catalog = _catalog()
    snapshot = snapshot_from_my_team(
        _my_team(),
        catalog,
        competition_payload("gameplay-1", catalog["tour"]),
        team_payload(_my_team()),
        catalog["fixtures"],
    )
    assert snapshot.competition["source"] == "wsl"
    assert snapshot.competition["slug"] == "wsl-fantasy"
    assert snapshot.gameweek["status"] == "finished"
    assert snapshot.gameweek["startsAt"] == "2026-09-04"
    assert snapshot.picks[0].role == "starter"
    assert snapshot.picks[0].player.externalId == "111"
    assert snapshot.picks[0].player.name == "Hannah Hampton"
    assert snapshot.picks[0].player.clubExternalId == "9001"
    assert snapshot.picks[1].captain is True
    assert snapshot.picks[1].points == 2
    assert snapshot.picks[1].player.externalId == "222"
    assert snapshot.picks[1].player.name == "Alexia Putellas"
    assert snapshot.picks[1].player.position == "MID"
    assert snapshot.picks[2].role == "bench"
    assert snapshot.picks[2].player.name == "Alessia Russo"
    assert snapshot.teamPoints == 7
    assert snapshot.tripleCaptain is False


def test_wsl_snapshot_applies_sofascore_rating_and_current_injury():
    catalog = _catalog()
    value = _my_team(matchday_id=3, matchday_status=1)
    value["availabilityStatus"] = [1, 1, 4]
    with patch("collector.adapters.wsl.fetch_injured_player_ids", return_value=set()):
        snapshot = snapshot_from_my_team(
            value,
            catalog,
            competition_payload("gameplay-1", catalog["tour"]),
            team_payload(value),
            catalog["fixtures"],
            ratings={"222": 8.2},
            injured_ids={"111"},
        )
    assert snapshot.gameweek["status"] == "upcoming"
    by_id = {pick.player.externalId: pick for pick in snapshot.picks}
    assert by_id["222"].rating == 8.2
    assert by_id["111"].injured is True
    assert by_id["333"].injured is True


def test_wsl_transfers_come_from_week_to_week_squad_diff():
    catalog = _catalog()
    batch = transfers_from_squads(
        {
            2: _my_team(matchday_id=2),
            3: _my_team(matchday_id=3, russo_id="wpll::Football_Player::fwd2"),
        },
        catalog,
        competition_payload("gameplay-1", catalog["tour"]),
        team_payload(_my_team()),
    )
    assert batch is not None
    assert batch.rounds[0].number == 3
    pair = batch.rounds[0].transfers[0]
    assert pair.playerOut is not None and pair.playerOut.externalId == "333"
    assert pair.playerIn is not None and pair.playerIn.externalId == "444"
    assert pair.playerOut.price == 11.5
    assert pair.playerIn.price == 6.5
