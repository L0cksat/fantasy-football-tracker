from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from collector.adapters.excel_laliga import load_workbook_payloads
from collector.adapters.file_import import FileImportAdapter
from collector.adapters.sofascore import (
    SofaScoreAdapter,
    SofaScoreSessionError,
    is_transfers_export,
    transfers_from_payload,
)
from collector.publisher import BackendPublisher
from collector.adapters.fpl import fpl_entry_id, pull_fpl
from collector.adapters.wsl import pull_wsl, wsl_configured
from collector.pull import adapter_for_target, pull_targets_from_env, run_pull

FPL_SLUG = "premier-league-fantasy"
WSL_SLUG = "wsl-fantasy"

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Push SofaScore Fantasy snapshots to the tracker backend.")
    sub = parser.add_subparsers(dest="command", required=True)

    import_cmd = sub.add_parser("import", help="Import a local JSON snapshot (manual fallback).")
    import_cmd.add_argument("file", type=Path, help="Path to squad or snapshot JSON")
    import_cmd.add_argument(
        "--meta",
        type=Path,
        help="Optional SofaScore competition JSON (userCompetition) for season and manager name",
    )
    import_cmd.add_argument("--dry-run", action="store_true")

    excel_cmd = sub.add_parser(
        "import-excel",
        help="Import the official LaLiga Fantasy workbook (collector/templates/laliga-fantasy-oficial.xlsx).",
    )
    excel_cmd.add_argument("file", type=Path, help="Path to a filled copy of the LaLiga Fantasy workbook")
    excel_cmd.add_argument("--gameweek", type=int, help="Import only this gameweek")
    excel_cmd.add_argument("--dry-run", action="store_true")

    sync_cmd = sub.add_parser("sync", help="Fetch one gameweek from SOFASCORE_GAMEWEEK_URL (legacy).")
    sync_cmd.add_argument("--competition", required=True, help="Competition slug, e.g. premier-league")
    sync_cmd.add_argument("--gameweek", type=int, required=True)
    sync_cmd.add_argument("--dry-run", action="store_true")

    pull_cmd = sub.add_parser("pull", help="Fetch squad + transfers (+ meta) from SOFASCORE_* URLs and ingest.")
    pull_cmd.add_argument(
        "--competition",
        default=None,
        help="Competition slug (premier-league, laliga, premier-league-fantasy, wsl-fantasy, …). Default: every configured competition",
    )
    pull_cmd.add_argument(
        "--gameweek",
        type=int,
        help="Optional round sequence (1, 2, 3…). Default is currentRound.id from competition JSON",
    )
    pull_cmd.add_argument("--dry-run", action="store_true")
    pull_cmd.add_argument(
        "--no-save",
        action="store_true",
        help="Do not write raw JSON under collector/cache/",
    )
    pull_cmd.add_argument(
        "--save-dir",
        type=Path,
        help="Directory for raw JSON dumps (default: collector/cache)",
    )

    args = parser.parse_args(argv)
    publisher = BackendPublisher()

    try:
        if args.command == "import":
            return _run_import(args, publisher)
        if args.command == "import-excel":
            return _run_import_excel(args, publisher)
        if args.command == "sync":
            return _run_sync(args, publisher)
        return _run_pull_command(args, publisher)
    except SofaScoreSessionError as exc:
        print(exc, file=sys.stderr)
        return 2
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1


def _run_import(args: argparse.Namespace, publisher: BackendPublisher) -> int:
    payload = json.loads(args.file.read_text(encoding="utf-8"))
    meta = None
    if getattr(args, "meta", None):
        meta = json.loads(args.meta.read_text(encoding="utf-8"))
    if is_transfers_export(payload):
        batch = transfers_from_payload(payload, meta)
        if args.dry_run:
            json.dump(batch.to_dict(), sys.stdout, indent=2)
            sys.stdout.write("\n")
            return 0
        result = publisher.publish_transfers(batch)
        print(
            f"Ingested transfers competition={result.get('competitionId')} "
            f"rounds={result.get('rounds')}"
        )
        return 0
    snapshot = FileImportAdapter(args.file, getattr(args, "meta", None))._load()
    if args.dry_run:
        json.dump(snapshot.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    result = publisher.publish(snapshot)
    print(f"Ingested competition={result.get('competitionId')} gameweek={result.get('gameweek')}")
    return 0


def _run_import_excel(args: argparse.Namespace, publisher: BackendPublisher) -> int:
    snapshots, batch = load_workbook_payloads(args.file, gameweek=args.gameweek)
    if args.dry_run:
        json.dump(
            {
                "snapshots": [item.to_dict() for item in snapshots],
                "transfers": batch.to_dict() if batch is not None else None,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0
    for snapshot in snapshots:
        result = publisher.publish(snapshot)
        print(
            f"laliga-fantasy-oficial: ingested competition={result.get('competitionId')} "
            f"gameweek={result.get('gameweek')}"
        )
    if batch is not None:
        result = publisher.publish_transfers(batch)
        print(
            f"laliga-fantasy-oficial: ingested transfers competition={result.get('competitionId')} "
            f"rounds={result.get('rounds')}"
        )
    return 0


def _run_sync(args: argparse.Namespace, publisher: BackendPublisher) -> int:
    snapshot = SofaScoreAdapter().fetch_gameweek_scores(args.competition, args.gameweek)
    if args.dry_run:
        json.dump(snapshot.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    result = publisher.publish(snapshot)
    print(f"Ingested competition={result.get('competitionId')} gameweek={result.get('gameweek')}")
    return 0


def _run_pull_command(args: argparse.Namespace, publisher: BackendPublisher) -> int:
    save_root = None
    if not args.no_save:
        save_root = args.save_dir or (ROOT / "cache")
    targets = pull_targets_from_env()
    want_fpl = bool(fpl_entry_id())
    want_wsl = wsl_configured()
    if args.competition:
        if args.competition == FPL_SLUG:
            targets = []
            want_fpl = True
            want_wsl = False
            if not fpl_entry_id():
                raise ValueError("No FPL team id in .env. Set FPL_ENTRY_ID from /entry/{id}/event/1.")
        elif args.competition == WSL_SLUG:
            targets = []
            want_fpl = False
            want_wsl = True
            if not wsl_configured():
                raise ValueError(
                    "No WSL credentials in .env. Set WSL_GAMEPLAY_ID and WSL_GAME_TOKEN "
                    "(x-game-token from the my-team request headers)."
                )
        else:
            want_fpl = False
            want_wsl = False
            targets = [item for item in targets if item.slug == args.competition]
            if not targets:
                raise ValueError(
                    f"No squad URL in .env for {args.competition}. "
                    "Set a competition or squad URL (SOFASCORE_* / SOFASCORE_LALIGA_* / "
                    "SOFASCORE_SERIE_A_* / SOFASCORE_LIGUE_1_*), or use premier-league-fantasy / "
                    "wsl-fantasy with their env credentials."
                )
    if not targets and not want_fpl and not want_wsl:
        raise ValueError(
            "No squad URL in .env. Set SOFASCORE_SQUAD_URL, SOFASCORE_LALIGA_*, "
            "SOFASCORE_SERIE_A_COMPETITION_URL, SOFASCORE_LIGUE_1_COMPETITION_URL, "
            "FPL_ENTRY_ID, or WSL_GAME_TOKEN + WSL_GAMEPLAY_ID."
        )

    pulls: list[dict] = []
    for target in targets:
        save_dir = (save_root / target.slug) if save_root is not None else None
        result = run_pull(
            adapter_for_target(target),
            publisher,
            competition=target.slug,
            gameweek=args.gameweek,
            dry_run=args.dry_run,
            save_dir=save_dir,
        )
        pulls.append(
            {
                "competition": target.slug,
                "snapshot": result["snapshot"],
                "transfers": result["transfers"],
                "published": result.get("published"),
            }
        )
        if args.dry_run:
            continue
        published = result.get("published") or {}
        snapshot_result = published.get("snapshot") or {}
        print(
            f"{target.slug}: ingested competition={snapshot_result.get('competitionId')} "
            f"gameweek={snapshot_result.get('gameweek')}"
        )
        transfers_result = published.get("transfers")
        if transfers_result:
            print(
                f"{target.slug}: ingested transfers competition={transfers_result.get('competitionId')} "
                f"rounds={transfers_result.get('rounds')}"
            )
        elif not target.transfers_url:
            print(f"{target.slug}: transfers URL is empty; skipped transfers pull.")

    if want_fpl:
        fpl_dir = (save_root / FPL_SLUG) if save_root is not None else None
        fpl_result = pull_fpl(
            publisher,
            gameweek=args.gameweek,
            dry_run=args.dry_run,
            save_dir=fpl_dir,
        )
        pulls.append(
            {
                "competition": FPL_SLUG,
                "snapshots": fpl_result["snapshots"],
                "transfers": fpl_result["transfers"],
                "published": fpl_result.get("published"),
            }
        )
        if not args.dry_run:
            published = fpl_result.get("published") or {}
            for snapshot_result in published.get("snapshots") or []:
                print(
                    f"{FPL_SLUG}: ingested competition={snapshot_result.get('competitionId')} "
                    f"gameweek={snapshot_result.get('gameweek')}"
                )
            transfers_result = published.get("transfers")
            if transfers_result:
                print(
                    f"{FPL_SLUG}: ingested transfers competition={transfers_result.get('competitionId')} "
                    f"rounds={transfers_result.get('rounds')}"
                )

    if want_wsl:
        wsl_dir = (save_root / WSL_SLUG) if save_root is not None else None
        wsl_result = pull_wsl(
            publisher,
            gameweek=args.gameweek,
            dry_run=args.dry_run,
            save_dir=wsl_dir,
        )
        pulls.append(
            {
                "competition": WSL_SLUG,
                "snapshots": wsl_result["snapshots"],
                "transfers": wsl_result["transfers"],
                "published": wsl_result.get("published"),
            }
        )
        if not args.dry_run:
            published = wsl_result.get("published") or {}
            for snapshot_result in published.get("snapshots") or []:
                print(
                    f"{WSL_SLUG}: ingested competition={snapshot_result.get('competitionId')} "
                    f"gameweek={snapshot_result.get('gameweek')}"
                )
            transfers_result = published.get("transfers")
            if transfers_result:
                print(
                    f"{WSL_SLUG}: ingested transfers competition={transfers_result.get('competitionId')} "
                    f"rounds={transfers_result.get('rounds')}"
                )

    if args.dry_run:
        if len(pulls) == 1:
            only = pulls[0]
            if "snapshots" in only:
                payload = {"snapshots": only["snapshots"], "transfers": only["transfers"]}
            else:
                payload = {"snapshot": only["snapshot"], "transfers": only["transfers"]}
        else:
            payload = {
                "pulls": [
                    {
                        "competition": item["competition"],
                        "snapshot": item.get("snapshot"),
                        "snapshots": item.get("snapshots"),
                        "transfers": item["transfers"],
                    }
                    for item in pulls
                ]
            }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
