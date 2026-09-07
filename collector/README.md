# Collector

Pushes normalized snapshots to `POST /api/v1/ingest/snapshots`.

```bash
python -m pip install -r requirements.txt
python -m collector import samples/pl-gw3.json --dry-run
python -m collector import samples/pl-gw3.json

# Real SofaScore Network exports (squad + optional competition meta)
python -m collector import path\to\premier-league-squad.json --meta path\to\premier-league.json --dry-run
python -m collector import path\to\premier-league-squad.json --meta path\to\premier-league.json
```

`sync` only works after you set `SOFASCORE_*` URLs (and optionally `SOFASCORE_SESSION`) in `.env` from your own logged-in browser Network tab.
