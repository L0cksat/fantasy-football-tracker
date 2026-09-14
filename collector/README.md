# Collector

Pushes normalized snapshots to `POST /api/v1/ingest/snapshots` and transfers to `POST /api/v1/ingest/transfers`.

It does **not** log in or scrape SofaScore. File import is the fallback. Live `pull` only replays JSON URLs you copied from your own logged-in Network tab, with your session cookie.

```bash
cd collector
python -m pip install -r requirements.txt

# Manual fallback (saved Network JSON)
python -m collector import path\to\premier-league-squad.json --meta path\to\premier-league.json
python -m collector import path\to\premier-league-transfers.json --meta path\to\premier-league.json

# Automated pull (URLs + cookie in repo-root or collector .env)
python -m collector pull --dry-run
python -m collector pull --competition laliga --dry-run
python -m collector pull

# Official LaLiga Fantasy (app-only: fill the Excel template)
python -m collector import-excel templates\laliga-fantasy-oficial.xlsx --dry-run
python -m collector import-excel path\to\your-copy.xlsx
```

Official LaLiga Fantasy has no website JSON. Copy `collector/templates/laliga-fantasy-oficial.xlsx`, fill **Competition**, **Squads** (starter = Team XI, squad = owned but not in XI), and **Transfers** (one Bought or Sold row per deal, with price and Market or manager name). Set **channel** to Market or Release clause paid. Mark **injured** on Squads when a player is out. Delete the yellow EXAMPLE rows, then `import-excel`. No captains or bench. That is a separate dashboard competition from SofaScore LaLiga.

## `.env` for `pull`

One `SOFASCORE_SESSION` is shared. Premier League uses the unprefixed URLs. Other leagues can use a competition JSON URL only (`SOFASCORE_LALIGA_*`, `SOFASCORE_SERIE_A_COMPETITION_URL`, `SOFASCORE_LIGUE_1_COMPETITION_URL`, `SOFASCORE_BUNDESLIGA_COMPETITION_URL`, `SOFASCORE_CHAMPIONS_LEAGUE_COMPETITION_URL`, `SOFASCORE_EUROPA_LEAGUE_COMPETITION_URL`, `SOFASCORE_MLS_COMPETITION_URL`, `SOFASCORE_BRASILEIRAO_COMPETITION_URL`) — squad and transfers URLs are derived. `pull` with no `--competition` fetches every configured league.

Set these from Firefox (logged into SofaScore Fantasy, Persist Logs + XHR):

- `SOFASCORE_SESSION` — Cookie header **value** from a Fantasy XHR (no `Cookie:` prefix). On SofaScore this may be only `g_state={...}`.
- `SOFASCORE_COMPETITION_URL` / `SOFASCORE_LALIGA_COMPETITION_URL` — meta / `userCompetition` JSON
- `SOFASCORE_SQUAD_URL` / `SOFASCORE_LALIGA_SQUAD_URL` — squad JSON. `/round/1088/` (or `{roundId}`) is rewritten to that competition’s `currentRound.id`
- `SOFASCORE_TRANSFERS_URL` / `SOFASCORE_LALIGA_TRANSFERS_URL` — transfers JSON for all rounds

Leave `SOFASCORE_GAMEWEEK_URL` empty (`sync` leftover).

`BACKEND_URL` defaults to `http://localhost:8080`. Raw responses go to `collector/cache/<slug>/` (gitignored). HTTP 401 means refresh the Cookie. `pull` uses `curl_cffi` so SofaScore does not 403 Python’s HTTP client.

## Weekly Windows task

Backend should already be running (or the task will fail until it is).

```powershell
cd collector
powershell -ExecutionPolicy Bypass -File .\register-weekly-task.ps1
```

Default: every **Monday 21:00**. Override with `-Day TUE -Time 20:00`. Logs: `collector/cache/pull.log`.
