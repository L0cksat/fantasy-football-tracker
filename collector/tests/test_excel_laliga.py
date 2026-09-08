from pathlib import Path

from openpyxl import Workbook

from collector.adapters.excel_laliga import load_workbook_payloads


def test_example_rows_are_skipped(tmp_path: Path):
    path = tmp_path / "examples.xlsx"
    book = Workbook()
    book.active.title = "Read me"
    competition = book.create_sheet("Competition")
    competition["A2"] = "teamName"
    competition["B2"] = "Los Oficiales"
    squads = book.create_sheet("Squads")
    squads.append(
        [
            "gameweek",
            "gameweekName",
            "status",
            "teamPoints",
            "tripleCaptain",
            "transferPenalty",
            "playerName",
            "position",
            "club",
            "role",
            "captain",
            "viceCaptain",
            "points",
            "rating",
            "price",
            "sofaScorePlayerId",
            "sofaScoreClubId",
        ]
    )
    squads.append(
        [1, "GW1", "finished", 10, False, 0, "EXAMPLE — delete this row", "FWD", "Sevilla", "starter", True, False, 4, None, None, "", ""]
    )
    book.save(path)
    try:
        load_workbook_payloads(path)
        raise AssertionError("example-only workbook should not import")
    except ValueError as exc:
        assert "No squad rows" in str(exc)


def test_import_excel_maps_squad_and_transfers(tmp_path: Path):
    path = tmp_path / "week.xlsx"
    book = Workbook()
    readme = book.active
    readme.title = "Read me"
    competition = book.create_sheet("Competition")
    competition["A2"] = "teamName"
    competition["B2"] = "Los Oficiales"
    competition["A3"] = "managerName"
    competition["B3"] = "Locksat"
    competition["A4"] = "season"
    competition["B4"] = "2026/27"
    squads = book.create_sheet("Squads")
    squads.append(
        [
            "gameweek",
            "gameweekName",
            "status",
            "teamPoints",
            "tripleCaptain",
            "transferPenalty",
            "playerName",
            "position",
            "club",
            "role",
            "captain",
            "viceCaptain",
            "points",
            "rating",
            "price",
            "sofaScorePlayerId",
            "sofaScoreClubId",
        ]
    )
    squads.append(
        [1, "GW1", "finished", 71, False, 0, "EXAMPLE — skip", "FWD", "Real Madrid", "starter", True, False, 9, 7, 12, "", ""]
    )
    squads.append(
        [1, "GW1", "finished", 71, False, 0, "Kylian Mbappé", "FWD", "Real Madrid", "starter", True, False, 14, 8.1, 20, 823944, 2829]
    )
    squads.append(
        [1, "GW1", "finished", 71, False, 0, "Pedri", "MID", "Barcelona", "bench", False, True, 3, 6.8, 12, "", ""]
    )
    transfers = book.create_sheet("Transfers")
    transfers.append(
        [
            "gameweek",
            "gameweekName",
            "playerIn",
            "clubIn",
            "positionIn",
            "priceIn",
            "sofaScorePlayerIdIn",
            "sofaScoreClubIdIn",
            "playerOut",
            "clubOut",
            "positionOut",
            "priceOut",
            "sofaScorePlayerIdOut",
            "sofaScoreClubIdOut",
            "transferPenalty",
        ]
    )
    transfers.append(
        [2, "GW2", "Lamine Yamal", "Barcelona", "FWD", 18, 1399376, 2817, "Joselu", "Real Madrid", "FWD", 9, "", 2829, 4]
    )
    book.save(path)

    snapshots, batch = load_workbook_payloads(path)
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.competition["source"] == "laliga-fantasy"
    assert snapshot.competition["slug"] == "laliga-fantasy-oficial"
    assert snapshot.team["name"] == "Los Oficiales"
    assert snapshot.gameweek["number"] == 1
    assert snapshot.teamPoints == 71
    assert [pick.player.name for pick in snapshot.picks] == ["Kylian Mbappé", "Pedri"]
    assert snapshot.picks[0].captain is True
    assert snapshot.picks[0].player.externalId == "823944"
    assert snapshot.picks[0].player.clubExternalId == "2829"
    assert snapshot.picks[1].player.externalId == "pedri-barcelona"
    assert batch is not None
    assert batch.rounds[0].number == 2
    assert batch.rounds[0].transferPenalty == 4
    assert batch.rounds[0].transfers[0].playerIn.name == "Lamine Yamal"


def test_import_excel_can_filter_gameweek(tmp_path: Path):
    path = tmp_path / "weeks.xlsx"
    book = Workbook()
    book.active.title = "Read me"
    competition = book.create_sheet("Competition")
    competition["A2"] = "teamName"
    competition["B2"] = "Los Oficiales"
    squads = book.create_sheet("Squads")
    squads.append(
        [
            "gameweek",
            "gameweekName",
            "status",
            "teamPoints",
            "tripleCaptain",
            "transferPenalty",
            "playerName",
            "position",
            "club",
            "role",
            "captain",
            "viceCaptain",
            "points",
            "rating",
            "price",
            "sofaScorePlayerId",
            "sofaScoreClubId",
        ]
    )
    squads.append([1, "GW1", "finished", 10, False, 0, "A", "FWD", "Sevilla", "starter", True, False, 4, None, None, "", ""])
    squads.append([2, "GW2", "finished", 20, False, 0, "B", "MID", "Sevilla", "starter", True, False, 6, None, None, "", ""])
    book.save(path)

    snapshots, batch = load_workbook_payloads(path, gameweek=2)
    assert [item.gameweek["number"] for item in snapshots] == [2]
    assert snapshots[0].teamPoints == 20
    assert batch is None
