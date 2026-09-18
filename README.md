# Fantasy Football Tracker

[![Angular](https://img.shields.io/badge/Angular-21-DD0031?logo=angular&logoColor=white)](https://angular.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.5-6DB33F?logo=springboot&logoColor=white)](https://spring.io/projects/spring-boot)
[![Java](https://img.shields.io/badge/Java-21-ED8B00?logo=openjdk&logoColor=white)](https://openjdk.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GSAP](https://img.shields.io/badge/GSAP-3-88CE02?logo=greensock&logoColor=black)](https://gsap.com/)

Personal SofaScore Fantasy tracker: Python collector → Spring Boot + MySQL → Angular dashboard.

The dashboard shows your squad, captain chips, club crests, player portraits, week-vs-week compare, season totals, transfers, **Injured** / **Suspended** status chips, and season high/low gameweek cards. Official LaLiga Fantasy also highlights your most expensive purchase and highest sale.

## Screenshots

Homepage with MVP and competition wash:

![Homepage — players of the week](docs/screenshots/home.png)

Competition dashboard (squad, totals, player of the week):

![Competition dashboard](docs/screenshots/leagues.png)

Players of the week marquee (GSAP — pauses on hover):

![Players of the week marquee](docs/screenshots/potw-marquee.gif)

Injured / Suspended chips on the squad (per gameweek, from SofaScore lineups):

![Squad status badges](docs/screenshots/squad-status-badges.png)

Highest and lowest scoring gameweeks (season extremes, beside Compare weeks):

![Highest and lowest scoring gameweeks](docs/screenshots/score-extremes.png)

Official LaLiga — most expensive purchase and highest sale (POTW-style cards in Transfers):

![LaLiga transfer highlights](docs/screenshots/laliga-transfer-highlights.png)

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
python -m collector pull --competition premier-league-fantasy
python -m collector pull
```

Weekly Windows task (Monday 21:00): `powershell -ExecutionPolicy Bypass -File collector\register-weekly-task.ps1`

The collector POSTs to Spring Boot. It does not log in or scrape the site. `pull` fetches every competition that has URLs in `.env` (Premier League, LaLiga, Serie A, Ligue 1, Bundesliga, Champions League, Europa League, Nations League, MLS, Brasileirão) plus official Premier League Fantasy when `FPL_ENTRY_ID` is set and official WSL Fantasy when `WSL_GAME_TOKEN` + `WSL_GAMEPLAY_ID` are set. HTTP 401 means refresh `SOFASCORE_SESSION` (SofaScore) or `WSL_GAME_TOKEN` (`x-game-token` from the my-team XHR, not Auth0 Bearer). Official FPL uses the public JSON API (team id from `/entry/{id}/event/1`); no cookie. Official LaLiga Fantasy is app-only (100M€ market, starting XI + squad, independent buys/sells, no captains): fill `collector/templates/laliga-fantasy-oficial.xlsx` and run `python -m collector import-excel`.

## Scoring and media

- SofaScore `fixtures[].score` is **raw**. Captain display is ×2, triple captain is ×3. Team week totals stay SofaScore’s `userRound.score` (already includes the chip). Official WSL `totalPoints` already includes captain ×2; the collector stores the raw half so the dashboard does not double it again.
- Crests: SofaScore `https://img.sofascore.com/api/v1/team/{id}/image`; official FPL uses Premier League badge `t{code}.png`
- Portraits: SofaScore `https://img.sofascore.com/api/v1/player/{id}/image` (official FPL maps names onto the Premier League season player list; official WSL maps onto unique-tournament 1044)
- Competition logos: `https://img.sofascore.com/api/v1/unique-tournament/{id}/image` (same endpoint the main SofaScore tournament page uses; Champions League is 7, Europa League is 679, Nations League is 10783, MLS is 242, Brasileirão is 325, WSL is 1044)
- Transfers: official SofaScore transfers JSON (paired in/out per round). Squad-diff is only a fallback if a week has no official rows.
- **Injured / Suspended:** per-GW from SofaScore event lineups `missingPlayers` (injury vs yellow accumulation / red card / unavailable). Stored on `squad_pick` and shown as chips next to the player name.
- **Season extremes:** Highest / Lowest Scoring Gameweek cards are derived from `GET …/totals` on the competition page.
- **Official LaLiga deal highlights:** season max `priceIn` / `priceOut` from `gameweek_transfer` (Most expensive player purchase / Highest player sale).

## API

- `GET /api/v1/home`
- `POST /api/v1/ingest/snapshots`
- `POST /api/v1/ingest/transfers`
- `GET /api/v1/competitions`
- `GET /api/v1/competitions/{id}/team?gameweek=`
- `GET /api/v1/competitions/{id}/gameweeks/{n}`
- `GET /api/v1/competitions/{id}/compare?from=1&to=2`
- `GET /api/v1/competitions/{id}/totals`
