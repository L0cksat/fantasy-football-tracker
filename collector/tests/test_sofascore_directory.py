from collector.adapters.sofascore_directory import (
    club_key,
    normalize_tournament_player,
    resolve_sofascore_player,
)


DIRECTORY = [
    {"playerId": 975079, "playerName": "João Pedro", "teamName": "Chelsea"},
    {"playerId": 151545, "playerName": "Virgil van Dijk", "teamName": "Liverpool FC"},
    {"playerId": 869856, "playerName": "Dominik Szoboszlai", "teamName": "Liverpool FC"},
    {"playerId": 913654, "playerName": "Pedro Porro", "teamName": "Tottenham Hotspur"},
    {"playerId": 869792, "playerName": "Gabriel Magalhães", "teamName": "Arsenal"},
]


def test_club_key_normalizes_fpl_and_sofascore_names():
    assert club_key("Man Utd") == club_key("Manchester United")
    assert club_key("Spurs") == club_key("Tottenham Hotspur")
    assert club_key("Liverpool") == club_key("Liverpool FC")
    assert club_key("Man City") == club_key("Manchester City")
    assert club_key("Man Utd") == club_key("Manchester United Women")
    assert club_key("Brighton & Hove Albion") == club_key("Brighton")


def test_resolve_matches_web_name_and_club():
    joao = resolve_sofascore_player(
        web_name="João Pedro",
        first_name="João Pedro",
        second_name="Junqueira de Jesus",
        club="Chelsea",
        directory=DIRECTORY,
    )
    virgil = resolve_sofascore_player(
        web_name="Virgil",
        first_name="Virgil",
        second_name="van Dijk",
        club="Liverpool",
        directory=DIRECTORY,
    )
    porro = resolve_sofascore_player(
        web_name="Pedro Porro",
        first_name="Pedro",
        second_name="Porro Sauceda",
        club="Spurs",
        directory=DIRECTORY,
    )
    gabriel = resolve_sofascore_player(
        web_name="Gabriel",
        first_name="Gabriel",
        second_name="Magalhães",
        club="Arsenal",
        directory=DIRECTORY,
    )
    assert joao is not None and joao["playerId"] == 975079
    assert virgil is not None and virgil["playerId"] == 151545
    assert porro is not None and porro["playerId"] == 913654
    assert gabriel is not None and gabriel["playerId"] == 869792


def test_resolve_matches_unique_surname_token():
    directory = [
        {"playerId": 824959, "playerName": "Mapi León", "teamName": "London City Lionesses"},
        {"playerId": 98110, "playerName": "Alexia Putellas", "teamName": "London City Lionesses"},
    ]
    hit = resolve_sofascore_player(
        web_name="M. León",
        first_name="Maria Pilar",
        second_name="León Cebrián",
        club="London City Lionesses",
        directory=directory,
    )
    assert hit is not None and hit["playerId"] == 824959


def test_normalize_flattens_nested_tournament_player_rows():
    nested = {
        "player": {"id": 964753, "name": "Senne Lammens", "shortName": "S. Lammens"},
        "team": {"id": 35, "name": "Manchester United"},
    }
    assert normalize_tournament_player(nested) == {
        "playerId": 964753,
        "playerName": "Senne Lammens",
        "teamId": 35,
        "teamName": "Manchester United",
    }


def test_resolve_matches_nested_man_utd_directory_rows():
    directory = [
        {
            "player": {"id": 964753, "name": "Senne Lammens"},
            "team": {"id": 35, "name": "Manchester United"},
        },
        {
            "player": {"id": 886363, "name": "Matheus Cunha"},
            "team": {"id": 35, "name": "Manchester United"},
        },
    ]
    lammens = resolve_sofascore_player(
        web_name="Lammens",
        first_name="Senne",
        second_name="Lammens",
        club="Man Utd",
        directory=directory,
    )
    cunha = resolve_sofascore_player(
        web_name="Cunha",
        first_name="Matheus",
        second_name="Cunha",
        club="Man Utd",
        directory=directory,
    )
    assert lammens is not None and lammens["playerId"] == 964753
    assert cunha is not None and cunha["playerId"] == 886363
