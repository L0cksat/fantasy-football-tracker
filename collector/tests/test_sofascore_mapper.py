from collector.adapters.sofascore import snapshot_from_payload, transfers_from_payload


def test_canonical_snapshot_round_trip():
    payload = {
        "competition": {
            "source": "sofascore",
            "externalId": "17",
            "name": "Premier League",
            "season": "2026/27",
            "slug": "premier-league",
        },
        "gameweek": {"number": 1, "name": "GW1", "status": "finished"},
        "team": {"name": "Sofa Saints", "managerName": "You"},
        "teamPoints": 10,
        "picks": [
            {
                "player": {"externalId": "1", "name": "Haaland", "position": "FWD", "club": "Man City"},
                "role": "starter",
                "captain": True,
                "viceCaptain": False,
                "points": 10,
                "rating": 8.2,
                "injured": True,
                "breakdown": {"goals": 1},
            }
        ],
    }
    snapshot = snapshot_from_payload(payload)
    assert snapshot.teamPoints == 10
    assert snapshot.picks[0].captain is True
    assert snapshot.picks[0].player.name == "Haaland"
    assert snapshot.picks[0].injured is True


def test_sofascore_like_export():
    payload = {
        "competition": {"id": 17, "name": "Premier League", "slug": "premier-league", "season": "2026/27"},
        "round": {"week": 3, "status": "finished"},
        "userTeam": {"name": "Sofa Saints", "manager": "You"},
        "lineup": [
            {
                "id": "ss-haaland",
                "name": "Erling Haaland",
                "position": "F",
                "team": "Man City",
                "isCaptain": True,
                "onBench": False,
                "fantasyPoints": 9,
                "rating": 7.9,
                "stats": {"goals": 1},
            }
        ],
    }
    snapshot = snapshot_from_payload(payload)
    assert snapshot.competition["source"] == "sofascore"
    assert snapshot.gameweek["number"] == 3
    assert snapshot.picks[0].player.position == "FWD"
    assert snapshot.picks[0].role == "starter"
    assert snapshot.teamPoints == 9


def test_sofascore_official_squad_export():
    payload = {
        "squad": {
            "name": "The Inbetweeners FC",
            "players": [
                {
                    "fantasyPlayer": {
                        "player": {"id": 869792, "name": "Gabriel Magalhães", "position": "D"},
                        "team": {"id": 42, "name": "Arsenal"},
                        "goals": 0,
                        "assists": 0,
                        "averageRating": 6.83,
                    },
                    "team": {"id": 42, "name": "Arsenal"},
                    "fixtures": [{"score": 2, "playerFixtureStatus": "starter"}],
                    "substitute": False,
                    "captain": False,
                    "price": 7.9,
                    "averageRating": 6.83,
                },
                {
                    "fantasyPlayer": {
                        "player": {"id": 1, "name": "João Pedro", "position": "F"},
                        "team": {"name": "Chelsea"},
                        "goals": 2,
                        "assists": 1,
                    },
                    "team": {"name": "Chelsea"},
                    "fixtures": [{"score": 5}],
                    "substitute": False,
                    "captain": True,
                },
                {
                    "fantasyPlayer": {
                        "player": {"id": 2, "name": "Senne Lammens", "position": "G"},
                        "team": {"name": "Manchester United"},
                    },
                    "team": {"name": "Manchester United"},
                    "fixtures": [{"score": 0}],
                    "substitute": True,
                    "captain": False,
                },
            ],
        },
        "userRound": {
            "score": 59,
            "transferPenalty": 5,
            "tripleCaptainActive": True,
            "fantasyRound": {
                "name": "Round 3",
                "sequence": 3,
                "isFinalized": False,
                "startTimestamp": 1788276600,
                "endTimestamp": 1788793200,
            },
        },
    }
    meta = {
        "userCompetition": {
            "name": "The Inbetweeners FC",
            "userName": "Locksat",
            "score": 210,
            "fantasyCompetition": {
                "name": "Premier League",
                "uniqueTournament": {"id": 17, "name": "Premier League", "slug": "premier-league"},
                "season": {"year": "26/27"},
            },
        }
    }
    snapshot = snapshot_from_payload(payload, meta)
    assert snapshot.competition["externalId"] == "17"
    assert snapshot.competition["season"] == "2026/27"
    assert snapshot.gameweek["number"] == 3
    assert snapshot.gameweek["name"] == "Round 3"
    assert snapshot.team["name"] == "The Inbetweeners FC"
    assert snapshot.team["managerName"] == "Locksat"
    assert snapshot.teamPoints == 59
    assert len(snapshot.picks) == 3
    assert snapshot.tripleCaptain is True
    assert snapshot.transferPenalty == 5
    captain = next(pick for pick in snapshot.picks if pick.captain)
    assert captain.player.name == "João Pedro"
    assert captain.points == 5
    bench = next(pick for pick in snapshot.picks if pick.role == "bench")
    assert bench.player.name == "Senne Lammens"
    gabriel = next(pick for pick in snapshot.picks if pick.player.name.startswith("Gabriel"))
    assert gabriel.points == 2
    assert gabriel.price == 7.9
    assert gabriel.player.club == "Arsenal"
    assert gabriel.player.clubExternalId == "42"
    assert gabriel.injured is False


def test_sofascore_squad_prefers_fantasy_position_over_player_profile():
    """SofaScore player.position can be M while fantasyPlayer.position is F (attacking mid as FWD)."""
    payload = {
        "squad": {
            "name": "BR Test",
            "players": [
                {
                    "fantasyPlayer": {
                        "position": "F",
                        "player": {"id": 1, "name": "Luciano Acosta", "position": "M"},
                        "team": {"id": 1961, "name": "Fluminense"},
                    },
                    "team": {"id": 1961, "name": "Fluminense"},
                    "fixtures": [{"score": 2}],
                    "substitute": False,
                    "captain": False,
                },
                {
                    "fantasyPlayer": {
                        "position": "F",
                        "player": {"id": 2, "name": "Henry Mosquera", "position": "M"},
                        "team": {"id": 1999, "name": "Red Bull Bragantino"},
                    },
                    "team": {"id": 1999, "name": "Red Bull Bragantino"},
                    "fixtures": [{"score": 1}],
                    "substitute": True,
                    "captain": False,
                },
            ],
        },
        "userRound": {
            "score": 3,
            "fantasyRound": {"name": "Round 28", "sequence": 28, "isFinalized": True},
        },
    }
    meta = {
        "userCompetition": {
            "fantasyCompetition": {
                "uniqueTournament": {"id": 325, "name": "Brasileirão", "slug": "brasileirao"},
                "season": {"year": "2026"},
            }
        }
    }
    snapshot = snapshot_from_payload(payload, meta)
    by_name = {pick.player.name: pick.player.position for pick in snapshot.picks}
    assert by_name["Luciano Acosta"] == "FWD"
    assert by_name["Henry Mosquera"] == "FWD"


def test_sofascore_squad_maps_nested_injury_status():
    payload = {
        "squad": {
            "name": "The Inbetweeners FC",
            "players": [
                {
                    "fantasyPlayer": {
                        "player": {
                            "id": 941168,
                            "name": "William Saliba",
                            "position": "D",
                            "injury": {"reason": "Back Injury", "status": "out"},
                        },
                        "team": {"id": 42, "name": "Arsenal"},
                    },
                    "team": {"id": 42, "name": "Arsenal"},
                    "fixtures": [{"score": 0}],
                    "substitute": False,
                    "captain": False,
                }
            ],
        },
        "userRound": {"score": 0, "fantasyRound": {"sequence": 5, "name": "Round 5", "isFinalized": False}},
    }
    snapshot = snapshot_from_payload(payload)
    assert snapshot.picks[0].injured is True


def test_sofascore_transfers_export():
    payload = {
        "transfers": [
            {
                "roundId": 1086,
                "roundName": "Round 1",
                "roundSequence": 1,
                "transferPenalty": 0,
                "transfers": [
                    {
                        "playerIn": {"id": 979128, "name": "Rayan Cherki", "position": "M"},
                        "playerOut": {"id": 827606, "name": "Rodri", "position": "M"},
                        "priceIn": 8.5,
                        "priceOut": 6.5,
                        "teamIdIn": 17,
                        "teamIdOut": 17,
                        "teamNameCodeIn": "MCI",
                        "teamNameCodeOut": "MCI",
                    }
                ],
            }
        ]
    }
    batch = transfers_from_payload(payload)
    assert batch.rounds[0].number == 1
    assert batch.rounds[0].transfers[0].playerIn.name == "Rayan Cherki"
    assert batch.rounds[0].transfers[0].playerIn.club == "Manchester City"
    assert batch.rounds[0].transfers[0].playerIn.clubExternalId == "17"
    assert batch.rounds[0].transfers[0].playerOut.name == "Rodri"
    assert batch.rounds[0].transfers[0].playerIn.price == 8.5


def test_meta_file_alone_explains_next_step():
    try:
        snapshot_from_payload({"userCompetition": {"name": "The Inbetweeners FC"}})
    except ValueError as exc:
        assert "--meta" in str(exc)
    else:
        raise AssertionError("expected ValueError for competition-only JSON")
