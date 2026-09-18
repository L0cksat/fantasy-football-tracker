from unittest.mock import Mock, patch
import os

from collector.adapters.sofascore import (
    SofaScoreAdapter,
    SofaScoreSessionError,
    _format_url,
    _normalize_session_cookie,
    round_id_from_meta,
)
from collector.pull import pull_targets_from_env, run_pull


def test_format_url_fills_gameweek_placeholder():
    url = "https://example.test/squad/{gameweek}"
    assert _format_url(url, gameweek=3) == "https://example.test/squad/3"
    assert _format_url("https://example.test/squad") == "https://example.test/squad"


def test_format_url_swaps_round_id_in_path_and_placeholder():
    network = "https://www.sofascore.com/api/v1/fantasy/user/abc/round/1089/squad"
    assert _format_url(network, round_id=1088).endswith("/round/1088/squad")
    assert (
        _format_url("https://example.test/round/{roundId}/squad", round_id=1088)
        == "https://example.test/round/1088/squad"
    )


def test_round_id_from_meta_uses_current_or_sequence():
    meta = {
        "userCompetition": {
            "fantasyCompetition": {
                "currentRound": {"id": 1088, "sequence": 3, "name": "Round 3"},
                "nextRound": {"id": 1089, "sequence": 4, "name": "Round 4"},
                "previousRound": {"id": 1087, "sequence": 2, "name": "Round 2"},
            }
        }
    }
    assert round_id_from_meta(meta) == 1088
    assert round_id_from_meta(meta, gameweek=4) == 1089
    assert round_id_from_meta(None) is None


def test_round_id_from_meta_uses_user_rounds_calendar():
    meta = {
        "userCompetition": {
            "fantasyCompetition": {
                "currentRound": {"id": 1066, "sequence": 24, "name": "Round 24"},
            }
        },
        "userRounds": [
            {"fantasyRound": {"id": 896, "sequence": 7, "name": "Gameweek 7"}},
            {"fantasyRound": {"id": 897, "sequence": 8, "name": "Gameweek 8"}},
        ],
    }
    assert round_id_from_meta(meta, gameweek=8) == 897
    assert round_id_from_meta(meta, gameweek=24) == 1066


def test_normalize_session_cookie_strips_header_name():
    assert _normalize_session_cookie('Cookie:g_state={"i_l":1}; sid=abc') == 'g_state={"i_l":1}; sid=abc'
    assert _normalize_session_cookie('Cookie: session=xyz') == "session=xyz"


def test_pull_targets_legacy_premier_and_laliga():
    env = {
        "SOFASCORE_COMPETITION_URL": "https://example.test/pl/meta",
        "SOFASCORE_SQUAD_URL": "https://example.test/pl/squad",
        "SOFASCORE_TRANSFERS_URL": "https://example.test/pl/transfers",
        "SOFASCORE_GAMEWEEK_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_LALIGA_SQUAD_URL": "https://example.test/ll/squad",
        "SOFASCORE_LALIGA_COMPETITION_URL": "https://example.test/ll/meta",
        "SOFASCORE_LALIGA_TRANSFERS_URL": "https://example.test/ll/transfers",
        "SOFASCORE_LALIGA_GAMEWEEK_URL": "",
        "SOFASCORE_SERIE_A_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_SQUAD_URL": "",
        "SOFASCORE_SERIE_A_TRANSFERS_URL": "",
        "SOFASCORE_LIGUE_1_COMPETITION_URL": "",
        "SOFASCORE_LIGUE_1_SQUAD_URL": "",
        "SOFASCORE_LIGUE_1_TRANSFERS_URL": "",
        "SOFASCORE_BUNDESLIGA_COMPETITION_URL": "",
        "SOFASCORE_BUNDESLIGA_SQUAD_URL": "",
        "SOFASCORE_BUNDESLIGA_TRANSFERS_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_MLS_COMPETITION_URL": "",
        "SOFASCORE_MLS_SQUAD_URL": "",
        "SOFASCORE_MLS_TRANSFERS_URL": "",
        "SOFASCORE_BRASILEIRAO_COMPETITION_URL": "",
        "SOFASCORE_BRASILEIRAO_SQUAD_URL": "",
        "SOFASCORE_BRASILEIRAO_TRANSFERS_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_TRANSFERS_URL": "",
    }
    with patch.dict(os.environ, env, clear=False):
        targets = pull_targets_from_env()
    assert [item.slug for item in targets] == ["premier-league", "laliga"]
    assert targets[0].squad_url.endswith("/pl/squad")
    assert targets[1].competition_url.endswith("/ll/meta")


def test_pull_target_derives_squad_and_transfers_from_competition_url():
    env = {
        "SOFASCORE_SQUAD_URL": "",
        "SOFASCORE_COMPETITION_URL": "",
        "SOFASCORE_TRANSFERS_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_LALIGA_SQUAD_URL": "",
        "SOFASCORE_LALIGA_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_COMPETITION_URL": (
            "https://www.sofascore.com/api/v1/fantasy/user/abc/competition/161"
        ),
        "SOFASCORE_SERIE_A_SQUAD_URL": "",
        "SOFASCORE_SERIE_A_TRANSFERS_URL": "",
        "SOFASCORE_LIGUE_1_COMPETITION_URL": "",
        "SOFASCORE_LIGUE_1_SQUAD_URL": "",
        "SOFASCORE_LIGUE_1_TRANSFERS_URL": "",
        "SOFASCORE_BUNDESLIGA_COMPETITION_URL": "",
        "SOFASCORE_BUNDESLIGA_SQUAD_URL": "",
        "SOFASCORE_BUNDESLIGA_TRANSFERS_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_MLS_COMPETITION_URL": "",
        "SOFASCORE_MLS_SQUAD_URL": "",
        "SOFASCORE_MLS_TRANSFERS_URL": "",
        "SOFASCORE_BRASILEIRAO_COMPETITION_URL": "",
        "SOFASCORE_BRASILEIRAO_SQUAD_URL": "",
        "SOFASCORE_BRASILEIRAO_TRANSFERS_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_TRANSFERS_URL": "",
    }
    with patch.dict(os.environ, env, clear=False):
        targets = pull_targets_from_env()
    assert [item.slug for item in targets] == ["serie-a"]
    assert targets[0].transfers_url.endswith("/competition/161/transfers")
    assert targets[0].squad_url.endswith("/round/{roundId}/squad")


def test_pull_target_derives_champions_league_from_competition_url():
    env = {
        "SOFASCORE_SQUAD_URL": "",
        "SOFASCORE_COMPETITION_URL": "",
        "SOFASCORE_TRANSFERS_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_LALIGA_SQUAD_URL": "",
        "SOFASCORE_LALIGA_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_SQUAD_URL": "",
        "SOFASCORE_SERIE_A_TRANSFERS_URL": "",
        "SOFASCORE_LIGUE_1_COMPETITION_URL": "",
        "SOFASCORE_LIGUE_1_SQUAD_URL": "",
        "SOFASCORE_LIGUE_1_TRANSFERS_URL": "",
        "SOFASCORE_BUNDESLIGA_COMPETITION_URL": "",
        "SOFASCORE_BUNDESLIGA_SQUAD_URL": "",
        "SOFASCORE_BUNDESLIGA_TRANSFERS_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_COMPETITION_URL": (
            "https://www.sofascore.com/api/v1/fantasy/user/abc/competition/169"
        ),
        "SOFASCORE_CHAMPIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_MLS_COMPETITION_URL": "",
        "SOFASCORE_MLS_SQUAD_URL": "",
        "SOFASCORE_MLS_TRANSFERS_URL": "",
        "SOFASCORE_BRASILEIRAO_COMPETITION_URL": "",
        "SOFASCORE_BRASILEIRAO_SQUAD_URL": "",
        "SOFASCORE_BRASILEIRAO_TRANSFERS_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_TRANSFERS_URL": "",
    }
    with patch.dict(os.environ, env, clear=False):
        targets = pull_targets_from_env()
    assert [item.slug for item in targets] == ["champions-league"]
    assert targets[0].transfers_url.endswith("/competition/169/transfers")
    assert targets[0].squad_url.endswith("/round/{roundId}/squad")


def test_pull_target_derives_europa_league_from_competition_url():
    env = {
        "SOFASCORE_SQUAD_URL": "",
        "SOFASCORE_COMPETITION_URL": "",
        "SOFASCORE_TRANSFERS_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_LALIGA_SQUAD_URL": "",
        "SOFASCORE_LALIGA_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_SQUAD_URL": "",
        "SOFASCORE_SERIE_A_TRANSFERS_URL": "",
        "SOFASCORE_LIGUE_1_COMPETITION_URL": "",
        "SOFASCORE_LIGUE_1_SQUAD_URL": "",
        "SOFASCORE_LIGUE_1_TRANSFERS_URL": "",
        "SOFASCORE_BUNDESLIGA_COMPETITION_URL": "",
        "SOFASCORE_BUNDESLIGA_SQUAD_URL": "",
        "SOFASCORE_BUNDESLIGA_TRANSFERS_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_COMPETITION_URL": (
            "https://www.sofascore.com/api/v1/fantasy/user/abc/competition/170"
        ),
        "SOFASCORE_EUROPA_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_MLS_COMPETITION_URL": "",
        "SOFASCORE_MLS_SQUAD_URL": "",
        "SOFASCORE_MLS_TRANSFERS_URL": "",
        "SOFASCORE_BRASILEIRAO_COMPETITION_URL": "",
        "SOFASCORE_BRASILEIRAO_SQUAD_URL": "",
        "SOFASCORE_BRASILEIRAO_TRANSFERS_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_TRANSFERS_URL": "",
    }
    with patch.dict(os.environ, env, clear=False):
        targets = pull_targets_from_env()
    assert [item.slug for item in targets] == ["europa-league"]
    assert targets[0].transfers_url.endswith("/competition/170/transfers")
    assert targets[0].squad_url.endswith("/round/{roundId}/squad")


def test_pull_target_derives_mls_from_competition_url():
    env = {
        "SOFASCORE_SQUAD_URL": "",
        "SOFASCORE_COMPETITION_URL": "",
        "SOFASCORE_TRANSFERS_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_LALIGA_SQUAD_URL": "",
        "SOFASCORE_LALIGA_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_SQUAD_URL": "",
        "SOFASCORE_SERIE_A_TRANSFERS_URL": "",
        "SOFASCORE_LIGUE_1_COMPETITION_URL": "",
        "SOFASCORE_LIGUE_1_SQUAD_URL": "",
        "SOFASCORE_LIGUE_1_TRANSFERS_URL": "",
        "SOFASCORE_BUNDESLIGA_COMPETITION_URL": "",
        "SOFASCORE_BUNDESLIGA_SQUAD_URL": "",
        "SOFASCORE_BUNDESLIGA_TRANSFERS_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_MLS_COMPETITION_URL": (
            "https://www.sofascore.com/api/v1/fantasy/user/abc/competition/143"
        ),
        "SOFASCORE_MLS_SQUAD_URL": "",
        "SOFASCORE_MLS_TRANSFERS_URL": "",
        "SOFASCORE_BRASILEIRAO_COMPETITION_URL": "",
        "SOFASCORE_BRASILEIRAO_SQUAD_URL": "",
        "SOFASCORE_BRASILEIRAO_TRANSFERS_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_TRANSFERS_URL": "",
    }
    with patch.dict(os.environ, env, clear=False):
        targets = pull_targets_from_env()
    assert [item.slug for item in targets] == ["mls"]
    assert targets[0].transfers_url.endswith("/competition/143/transfers")
    assert targets[0].squad_url.endswith("/round/{roundId}/squad")


def test_pull_target_derives_brasileirao_from_competition_url():
    env = {
        "SOFASCORE_SQUAD_URL": "",
        "SOFASCORE_COMPETITION_URL": "",
        "SOFASCORE_TRANSFERS_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_LALIGA_SQUAD_URL": "",
        "SOFASCORE_LALIGA_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_SQUAD_URL": "",
        "SOFASCORE_SERIE_A_TRANSFERS_URL": "",
        "SOFASCORE_LIGUE_1_COMPETITION_URL": "",
        "SOFASCORE_LIGUE_1_SQUAD_URL": "",
        "SOFASCORE_LIGUE_1_TRANSFERS_URL": "",
        "SOFASCORE_BUNDESLIGA_COMPETITION_URL": "",
        "SOFASCORE_BUNDESLIGA_SQUAD_URL": "",
        "SOFASCORE_BUNDESLIGA_TRANSFERS_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_MLS_COMPETITION_URL": "",
        "SOFASCORE_MLS_SQUAD_URL": "",
        "SOFASCORE_MLS_TRANSFERS_URL": "",
        "SOFASCORE_BRASILEIRAO_COMPETITION_URL": (
            "https://www.sofascore.com/api/v1/fantasy/user/abc/competition/140"
        ),
        "SOFASCORE_BRASILEIRAO_SQUAD_URL": "",
        "SOFASCORE_BRASILEIRAO_TRANSFERS_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_TRANSFERS_URL": "",
    }
    with patch.dict(os.environ, env, clear=False):
        targets = pull_targets_from_env()
    assert [item.slug for item in targets] == ["brasileirao"]
    assert targets[0].transfers_url.endswith("/competition/140/transfers")
    assert targets[0].squad_url.endswith("/round/{roundId}/squad")


def test_pull_target_accepts_nations_league_squad_url():
    env = {
        "SOFASCORE_SQUAD_URL": "",
        "SOFASCORE_COMPETITION_URL": "",
        "SOFASCORE_TRANSFERS_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_PREMIER_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_LALIGA_SQUAD_URL": "",
        "SOFASCORE_LALIGA_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_COMPETITION_URL": "",
        "SOFASCORE_SERIE_A_SQUAD_URL": "",
        "SOFASCORE_SERIE_A_TRANSFERS_URL": "",
        "SOFASCORE_LIGUE_1_COMPETITION_URL": "",
        "SOFASCORE_LIGUE_1_SQUAD_URL": "",
        "SOFASCORE_LIGUE_1_TRANSFERS_URL": "",
        "SOFASCORE_BUNDESLIGA_COMPETITION_URL": "",
        "SOFASCORE_BUNDESLIGA_SQUAD_URL": "",
        "SOFASCORE_BUNDESLIGA_TRANSFERS_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_CHAMPIONS_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_SQUAD_URL": "",
        "SOFASCORE_EUROPA_LEAGUE_TRANSFERS_URL": "",
        "SOFASCORE_MLS_COMPETITION_URL": "",
        "SOFASCORE_MLS_SQUAD_URL": "",
        "SOFASCORE_MLS_TRANSFERS_URL": "",
        "SOFASCORE_BRASILEIRAO_COMPETITION_URL": "",
        "SOFASCORE_BRASILEIRAO_SQUAD_URL": "",
        "SOFASCORE_BRASILEIRAO_TRANSFERS_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_COMPETITION_URL": "",
        "SOFASCORE_NATIONS_LEAGUE_SQUAD_URL": (
            "https://www.sofascore.com/api/v1/fantasy/user/abc/round/1176/squad"
        ),
        "SOFASCORE_NATIONS_LEAGUE_TRANSFERS_URL": "",
    }
    with patch.dict(os.environ, env, clear=False):
        targets = pull_targets_from_env()
    assert [item.slug for item in targets] == ["nations-league"]
    assert targets[0].squad_url.endswith("/round/1176/squad")
    assert targets[0].transfers_url == ""


def test_get_json_401_raises_session_error():
    adapter = SofaScoreAdapter(session_cookie="session=test")
    adapter.squad_url = "https://example.test/squad"
    fake = Mock()
    fake.status_code = 401
    with patch("collector.adapters.sofascore._http_get", return_value=fake):
        try:
            adapter.fetch_squad("premier-league")
            raise AssertionError("expected SofaScoreSessionError")
        except SofaScoreSessionError as exc:
            assert exc.status == 401


def test_fetch_transfers_404_is_skipped():
    adapter = SofaScoreAdapter()
    adapter.transfers_url = "https://example.test/transfers"
    fake = Mock()
    fake.status_code = 404
    with patch("collector.adapters.sofascore._http_get", return_value=fake):
        assert adapter.fetch_transfers("bundesliga", missing_ok=True) is None


@patch("collector.pull.annotate_snapshot_injuries", side_effect=lambda snapshot: snapshot)
def test_run_pull_passes_current_round_id(_annotate):
    adapter = SofaScoreAdapter()
    adapter.squad_url = "https://example.test/round/1089/squad"
    adapter.competition_url = "https://example.test/meta"
    adapter.transfers_url = ""
    adapter.fetch_meta = Mock(
        return_value={
            "userCompetition": {
                "fantasyCompetition": {"currentRound": {"id": 1088, "sequence": 3}}
            }
        }
    )
    adapter.fetch_rounds = Mock(return_value=None)
    adapter.fetch_squad = Mock(
        return_value={
            "competition": {
                "source": "sofascore",
                "externalId": "17",
                "name": "Premier League",
                "season": "2026/27",
                "slug": "premier-league",
            },
            "gameweek": {"number": 3, "name": "GW3", "status": "live"},
            "team": {"name": "The Inbetweeners FC", "managerName": "Locksat"},
            "teamPoints": 59,
            "picks": [
                {
                    "player": {"externalId": "1", "name": "Joao Pedro", "position": "FWD", "club": "Chelsea"},
                    "role": "starter",
                    "captain": True,
                    "viceCaptain": False,
                    "points": 5,
                }
            ],
        }
    )
    result = run_pull(adapter, Mock(), competition="premier-league", dry_run=True)
    assert result["snapshot"]["gameweek"]["number"] == 3
    assert adapter.fetch_squad.call_args.kwargs["round_id"] == 1088


@patch("collector.pull.annotate_snapshot_injuries", side_effect=lambda snapshot: snapshot)
def test_run_pull_publishes_snapshot_and_transfers(_annotate):
    adapter = SofaScoreAdapter()
    adapter.squad_url = "https://example.test/squad"
    adapter.competition_url = "https://example.test/meta"
    adapter.transfers_url = "https://example.test/transfers"
    adapter.fetch_meta = Mock(return_value=None)
    adapter.fetch_rounds = Mock(return_value=None)
    adapter.fetch_squad = Mock(
        return_value={
            "competition": {
                "source": "sofascore",
                "externalId": "17",
                "name": "Premier League",
                "season": "2026/27",
                "slug": "premier-league",
            },
            "gameweek": {"number": 3, "name": "GW3", "status": "live"},
            "team": {"name": "The Inbetweeners FC", "managerName": "Locksat"},
            "teamPoints": 59,
            "picks": [
                {
                    "player": {"externalId": "1", "name": "Joao Pedro", "position": "FWD", "club": "Chelsea"},
                    "role": "starter",
                    "captain": True,
                    "viceCaptain": False,
                    "points": 5,
                }
            ],
        }
    )
    adapter.fetch_transfers = Mock(
        return_value={
            "transfers": [
                {
                    "roundSequence": 2,
                    "roundName": "GW2",
                    "transferPenalty": 5,
                    "transfers": [
                        {
                            "playerIn": {"id": 10, "name": "In", "position": "M"},
                            "playerOut": {"id": 11, "name": "Out", "position": "M"},
                            "priceIn": 8.0,
                            "priceOut": 7.0,
                            "teamIdIn": 17,
                            "teamIdOut": 42,
                            "teamNameCodeIn": "MCI",
                            "teamNameCodeOut": "ARS",
                        }
                    ],
                }
            ]
        }
    )
    publisher = Mock()
    publisher.publish = Mock(return_value={"competitionId": 1, "gameweek": 3})
    publisher.publish_transfers = Mock(return_value={"competitionId": 1, "rounds": 1})

    result = run_pull(adapter, publisher, competition="premier-league")
    assert result["published"]["snapshot"]["gameweek"] == 3
    publisher.publish.assert_called_once()
    publisher.publish_transfers.assert_called_once()
