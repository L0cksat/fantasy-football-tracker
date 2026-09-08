# Fantasy Football Tracker

Personal SofaScore Fantasy tracker: Python collector → Spring Boot + MySQL → Angular dashboard.

The dashboard shows your squad, captain chips, club crests, player portraits, week-vs-week compare, season totals, and transfers.

## Layout

- `backend/` — Spring Boot 3.5 API (`/api/v1`)
- `frontend/` — Angular 21 dashboard
- `collector/` — Python ingest CLI (local Network JSON, optional SofaScore URLs)
- `sql/schema.sql` — MySQL schema (gameweeks are **rows**, not tables)

`.env` and `.env.example` are gitignored. Keep a local `.env.example` as a template and copy it to `.env` for tokens or SofaScore session values. Never commit `.env` or personal SofaScore JSON.

## Run locally

Personal data lives in MySQL (XAMPP / MariaDB on port **3307**, database `fantasy_tracker`). Do not start XAMPP Tomcat on 8080 — it conflicts with Spring Boot.

```bash
mysql -u root -P 3307 < sql/schema.sql
cd backend
mvn spring-boot:run -Dspring-boot.run.profiles=mysql
```

```bash
cd frontend
npm start
```

Dashboard: http://localhost:4200  
API: http://localhost:8080/api/v1/competitions

H2 + seed JSON (`Sofa Saints`) is still the default if you run the backend with no profile. That path is for tests / a first boot without MySQL.

## Collector

Copy Firefox Network JSON from your own logged-in SofaScore Fantasy session (Persist Logs + XHR), **or** paste those same XHR URLs plus your session cookie into `.env` and run `pull`.

```bash
cd collector
python -m pip install -r requirements.txt

python -m collector import path\to\premier-league-squad.json --meta path\to\premier-league.json
python -m collector import path\to\premier-league-transfers.json --meta path\to\premier-league.json

python -m collector pull --dry-run
python -m collector pull --competition laliga --dry-run
python -m collector pull
```

Weekly Windows task (Monday 21:00): `powershell -ExecutionPolicy Bypass -File collector\register-weekly-task.ps1`

The collector POSTs to Spring Boot. It does not log in or scrape the site. `pull` fetches every competition that has URLs in `.env` (Premier League, LaLiga, Serie A, Ligue 1, Bundesliga, Champions League, Europa League, MLS, Brasileirão). HTTP 401 means refresh `SOFASCORE_SESSION`. Official LaLiga Fantasy is app-only: fill `collector/templates/laliga-fantasy-oficial.xlsx` and run `python -m collector import-excel`.

## Scoring and media

- SofaScore `fixtures[].score` is **raw**. Captain display is ×2, triple captain is ×3. Team week totals stay SofaScore’s `userRound.score` (already includes the chip).
- Crests: `https://img.sofascore.com/api/v1/team/{id}/image`
- Portraits: `https://img.sofascore.com/api/v1/player/{id}/image`
- Competition logos: `https://img.sofascore.com/api/v1/unique-tournament/{id}/image` (same endpoint the main SofaScore tournament page uses; Champions League is 7, Europa League is 679, MLS is 242, Brasileirão is 325)
- Transfers: official SofaScore transfers JSON (paired in/out per round). Squad-diff is only a fallback if a week has no official rows.

## API

- `POST /api/v1/ingest/snapshots`
- `POST /api/v1/ingest/transfers`
- `GET /api/v1/competitions`
- `GET /api/v1/competitions/{id}/team?gameweek=`
- `GET /api/v1/competitions/{id}/gameweeks/{n}`
- `GET /api/v1/competitions/{id}/compare?from=1&to=2`
- `GET /api/v1/competitions/{id}/totals`
