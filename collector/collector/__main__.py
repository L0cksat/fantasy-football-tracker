from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from collector.adapters.file_import import FileImportAdapter
from collector.adapters.sofascore import SofaScoreAdapter, is_transfers_export, transfers_from_payload
from collector.publisher import BackendPublisher

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

    sync_cmd = sub.add_parser("sync", help="Fetch one gameweek from configured SofaScore URLs.")
    sync_cmd.add_argument("--competition", required=True, help="Competition slug, e.g. premier-league")
    sync_cmd.add_argument("--gameweek", type=int, required=True)
    sync_cmd.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    publisher = BackendPublisher()

    if args.command == "import":
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
    else:
        snapshot = SofaScoreAdapter().fetch_gameweek_scores(args.competition, args.gameweek)

    if args.dry_run:
        json.dump(snapshot.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    result = publisher.publish(snapshot)
    print(f"Ingested competition={result.get('competitionId')} gameweek={result.get('gameweek')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
