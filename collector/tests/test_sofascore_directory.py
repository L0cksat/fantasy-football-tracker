from collector.adapters.sofascore_directory import club_key, resolve_sofascore_player


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
