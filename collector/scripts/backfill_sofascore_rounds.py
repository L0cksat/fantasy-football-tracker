"""Pull every scored / finalized SofaScore Fantasy round for each configured league.

Default `python -m collector pull` only fetches currentRound, which skips gaps
(e.g. Brasileirão GW30) and leaves empty shells for future weeks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

load_dotenv(REPO / ".env")
load_dotenv(ROOT / ".env")

from collector.adapters.sofascore import SofaScoreSessionError  # noqa: E402
from collector.publisher import BackendPublisher  # noqa: E402
from collector.pull import adapter_for_target, pull_targets_from_env, run_pull  # noqa: E402


def _plan_gameweeks(user_rounds: list) -> tuple[list[int], int | None]:
    scored: list[int] = []
    entries: list[tuple[int, object, bool, bool]] = []
    for item in user_rounds:
        fr = item.get("fantasyRound") or {}
        seq = fr.get("sequence")
        if seq is None:
            continue
        seq_i = int(seq)
        score = item.get("score")
        entries.append(
            (
                seq_i,
                score,
                bool(fr.get("isFinalized")),
                bool(fr.get("isPlaceholderRound")),
            )
        )
        if score is not None:
            scored.append(seq_i)
    if not entries:
        return [], None
    entries.sort(key=lambda row: row[0])
    last_scored = max(scored) if scored else None
    to_pull: set[int] = set()
    for seq, score, finalized, placeholder in entries:
        if placeholder:
            continue
        if score is not None or finalized or (last_scored is not None and seq <= last_scored):
            to_pull.add(seq)
    if last_scored is not None:
        for seq, _score, _finalized, placeholder in entries:
            if seq == last_scored + 1 and not placeholder:
                to_pull.add(seq)
    return sorted(to_pull), last_scored


def main() -> int:
    publisher = BackendPublisher()
    targets = pull_targets_from_env()
    print("targets", [t.slug for t in targets], flush=True)
    if not targets:
        print("No SofaScore targets in .env", file=sys.stderr, flush=True)
        return 1

    for target in targets:
        print(f"\n==== {target.slug} ====", flush=True)
        try:
            adapter = adapter_for_target(target)
            meta = adapter.fetch_meta()
            rounds_payload = adapter.fetch_rounds() or {}
            cache = ROOT / "cache" / target.slug
            cache.mkdir(parents=True, exist_ok=True)
            if meta is not None:
                (cache / "competition.json").write_text(
                    json.dumps(meta, indent=2), encoding="utf-8"
                )
            if rounds_payload:
                (cache / "rounds.json").write_text(
                    json.dumps(rounds_payload, indent=2), encoding="utf-8"
                )
            user_rounds = rounds_payload.get("userRounds") or []
            if meta and not user_rounds:
                user_rounds = meta.get("userRounds") or []
            to_pull, last_scored = _plan_gameweeks(user_rounds)
            if not to_pull:
                print("  no rounds — skip", flush=True)
                continue
            print(f"  plan gameweeks: {to_pull} (last_scored={last_scored})", flush=True)
            for gw in to_pull:
                try:
                    result = run_pull(
                        adapter,
                        publisher,
                        competition=target.slug,
                        gameweek=gw,
                        dry_run=False,
                        save_dir=cache,
                    )
                    pub = (result.get("published") or {}).get("snapshot") or {}
                    print(
                        f"  OK gw={gw} -> competition={pub.get('competitionId')} "
                        f"gameweek={pub.get('gameweek')}",
                        flush=True,
                    )
                except SofaScoreSessionError as exc:
                    print(f"  AUTH FAIL gw={gw}: {exc}", flush=True)
                    return 2
                except Exception as exc:  # noqa: BLE001 — keep backfilling other weeks
                    print(f"  FAIL gw={gw}: {exc}", flush=True)
        except SofaScoreSessionError as exc:
            print(f"  AUTH: {exc}", flush=True)
            return 2
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}", flush=True)
    print("\nDONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
