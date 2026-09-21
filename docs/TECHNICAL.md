# Fantasy Football Tracker — technical reference

Personal tracker: **Python collector** POSTs snapshots into **Spring Boot 3.5 + MySQL**, and **Angular 21** GETs a homepage + dashboard. The frontend never writes. Gameweeks are **rows**, not tables.

**Sources**

| `source` | Slug example | How data arrives |
|---|---|---|
| `sofascore` | `premier-league`, `laliga`, `nations-league`, … | Logged-in SofaScore Fantasy XHRs + `SOFASCORE_SESSION` |
| `fpl` | `premier-league-fantasy` | Public FPL JSON (`FPL_ENTRY_ID`) |
| `laliga-fantasy` | `laliga-fantasy-oficial` | Excel workbook (`import-excel`) |
| `wsl` | `wsl-fantasy` | Official my-team XHR (`x-game-token`) + public feeds |

**Constraints that shaped the code:** collector POSTs / frontend only GETs; MySQL on 3307; never commit `.env`, cookies, or tokens; do not invent SofaScore API paths or scrape HTML; do not reverse official LaLiga/WSL apps; one process on port 8080.

---

## Architecture

```
collector (pull / import / import-excel)
    POST /api/v1/ingest/snapshots
    POST /api/v1/ingest/transfers
        → IngestService upserts entities
frontend  GET /api/v1/home
        → HomePageService (brands + Players of the Week)
frontend  GET /api/v1/competitions…
        → CompetitionQueryService + branding/crests/portraits
```

Captain **display** is always ×2 (×3 if triple captain). Ingest stores **raw** points. Official WSL `totalPoints` already includes ×2, so the collector divides the captain’s value by 2 before POST.

**Club vs national team:** the same SofaScore player id can appear as a club side (e.g. FC Barcelona in LaLiga) and a national side (Spain in Nations League). Club name, crest id, and shirt number for display are stored on **`squad_pick`** (competition context), not only on the shared `player` row.

---

## Backend (Spring Boot)

Package: `com.fantasytracker.backend`. Profile `mysql` uses XAMPP MariaDB on 3307 (`fantasy_tracker`). Default profile is H2 + seed JSON for tests.

### `BackendApplication`

- **`main`** — boots Spring. Created as the single process that owns port 8080.

### Config

#### `WebConfig.addCorsMappings`

Allows the Angular origin (`fantasy.cors.allowed-origins`, default `http://localhost:4200`) on `/api/**`. Exists so the dashboard can GET localhost:8080 from localhost:4200.

#### `SeedRunner.run`

`ApplicationRunner` (on unless `fantasy.seed.enabled=false`). If the competition table is empty, ingests `seed/pl-gw1.json` and `seed/pl-gw2.json` so H2/demo boots with “Sofa Saints”. Skipped on a populated MySQL database.

### HTTP — ingest (`IngestController`)

Optional header `X-Ingest-Token` when `fantasy.ingest.token` is set.

| Method | Path | Why |
|---|---|---|
| **`ingest`** | `POST /api/v1/ingest/snapshots` | Collector (and Excel/FPL/WSL adapters) upsert one gameweek squad + scores. |
| **`ingestTransfers`** | `POST /api/v1/ingest/transfers` | Official transfer rows (paired in/out, or unpaired LaLiga buys/sells). |
| **`cleanupSeed`** | `POST /api/v1/ingest/cleanup-seed` | Removes players whose `externalId` starts with `seed-` after switching to live data. |

### HTTP — homepage (`HomeController`)

| Method | Path | Why |
|---|---|---|
| **`home`** | `GET /api/v1/home` | League brand wash + Players of the Week for the landing page. |

### HTTP — read (`CompetitionController`)

Frontend-only surface for the leagues dashboard.

| Method | Path | Why |
|---|---|---|
| **`list`** | `GET /api/v1/competitions` | Dropdown: name, season, branding, gameweek numbers. |
| **`team`** | `GET /api/v1/competitions/{id}/team?gameweek=` | Squad for a week (latest if omitted). |
| **`gameweek`** | `GET /api/v1/competitions/{id}/gameweeks/{n}` | Same payload keyed by week number. |
| **`compare`** | `GET /api/v1/competitions/{id}/compare?from=&to=` | Week-vs-week player deltas. |
| **`totals`** | `GET /api/v1/competitions/{id}/totals` | Season sum of team week scores. |

### `HomePageService`

Why it exists: one read model for the homepage so Angular does not assemble brands/POTW/standings from many competition calls.

- **`homePage`** — all competitions; default prefers SofaScore `premier-league`; unique `LeagueBrand`s keyed by `CompetitionBranding.brandKey`; one `PlayerOfTheWeek` per competition that has a scored squad; three ranked standings lists (latest week, Europe season, Americas season).
- **`playerOfTheWeek(Competition)`** — resolves latest scored gameweek; picks the squad row with max `CaptainScoring.effective(raw, captain, tripleCaptain)`; club / shirt / crest prefer **pick-scoped** fields, then fall back to `Player`.
- **`latestWeekStanding` / `seasonTotalStanding` / `rankStandings`** — build `LeagueStanding` rows (logo + brand colours + points); season totals only sum weeks that pass `isScoringComplete`; Americas vs Europe via `CompetitionBranding.isAmericas` (MLS + Brasileirão).
- **`resolveLatestScoredGameweek`** — prefer latest week that is scoring-complete with picks; else latest team score with points &gt; 0; else last score row. SofaScore often leaves prior rounds as `live` until the season finalises, so **points &gt; 0 counts as complete**.
- **`isScoringComplete`** — `status=finished` **or** team points &gt; 0 (keeps open 0-pt shells out of POTW / standings / low-week math).
- **`displayBrandName`** — short labels for the brand wash (`"10783"` → `"Nations League"`, etc.).

#### Players of the Week vs MVP

| Concept | Where | Rule |
|---|---|---|
| **POTW** | Backend `HomePageService` | Per competition: highest captain-effective points in that competition’s resolved latest GW (**your squad only**). |
| **MVP** | Frontend `HomeComponent.topPlayerOfTheWeek` | Highest `points` across the returned `playersOfTheWeek` list (cross-competition). |
| **GW card** | Frontend `DashboardComponent.playerOfTheWeek` | Highest `pick.points` in the **selected** competition gameweek. |
| **Season high / low GW** | Frontend from `totals` | Max across all weeks; **min only among scoring-complete weeks** (finished or points &gt; 0). |
| **Homepage standings** | `latestWeekStandings` / `europeTotalStandings` / `americasTotalStandings` | Ranked by latest scored GW points, or season sum of complete weeks. |
| **LaLiga buy / sale cards** | `transferMarket.mostExpensivePurchase` / `highestSale` | Season max `priceIn` / `priceOut` across official transfer rows. |
| **Longest serving (Desafío)** | `longestServingPlayer` | Most starter GWs; tie-break total starter points. |

### `IngestService`

Why it exists: one upsert path for SofaScore, FPL, WSL, and Excel so the dashboard schema stays stable.

- **`upsertSnapshot`** — competition, gameweek, team, picks, player scores; drops stale picks for that week; team points from the request or from starter points after `CaptainScoring.effective`.
- **`upsertTransfers`** — replaces that week’s transfer rows; applies `transferPenalty` onto `TeamGameweekScore`.
- **`removeSeedPlayers`** — cleanup for `seed-*` ids.
- **`findAllCompetitions`** — used by tests/tooling.
- **`upsertCompetition` / `upsertGameweek` / `upsertTeam` / `upsertPlayer` / `upsertPick` / `upsertPlayerScore` / `upsertTeamScore`** — idempotent writes keyed by source+external id (or team+player+week).
- **`upsertPick`** — also writes **pick-scoped** `club`, `clubExternalId`, `shirtNumber`, plus `injured` / `suspended` from the snapshot payload.
- **`upsertGameweekForTransfers` / `applyTransferPenalty`** — transfers can arrive for a week that has no squad yet.
- **`removeStalePicks`** — a new XI replaces last week’s leftover rows.
- **`toJson` / `blankToNull`** — stores pick `breakdown` as JSON text; normalises empty club ids.

### `CompetitionQueryService`

Why it exists: GET payloads include derived media (crest, portrait, colours) and captain **display** points without the frontend knowing chips.

- **`listCompetitions`** — all competitions with branding + distinct gameweek numbers.
- **`teamView` / `gameweekView`** — same builder; `teamView` picks latest week if unspecified.
- **`compare`** — players in either week; points use captain multiplier per week’s triple-captain flag; club via `clubOf`.
- **`totals`** — ordered week scores + season total; each `GameweekTotal` includes **`status`** so the UI can filter unfinished open shells for lowest-week.
- **`buildTeamView`** — starters/bench, portraits, crests (pick-scoped club), transfers, transfer-market summary (incl. LaLiga season extremes), optional **`longestServingPlayer`** for Official LaLiga.
- **`findLongestServingPlayer`** — count `role=starter` GWs per player; ties broken by sum of starter points; crest/portrait/shirt from pick-scoped fields.
- **`buildTransfers`** — stored `gameweek_transfer` rows if present; otherwise **squad-diff** against the previous week (WSL and gaps in official feeds).
- **`toTransfer` (overloads)** — maps a player + price + counterpart into the dashboard transfer card; the `SquadPick` overload uses pick-scoped club.
- **`clubOf` / `clubExternalIdOf` / `shirtNumberOf`** — prefer pick fields, else `Player` (legacy rows before migration).
- **`buildTransferMarket` / `summarizeMarket` / `toCounterpartGroups` / `Accumulator`** — LaLiga market vs release-clause totals (week + season). Frontend sums market + release-clause sides into **Total sold / Total bought**.
- **`findMostExpensivePurchase` / `findHighestSale` / `toHighlight`** — season-wide max buy / max sale from `gameweek_transfer` prices for POTW-style cards on Official LaLiga.
- **`previousGameweek` / `tripleCaptain` / `pickComparator` / `positionOrder`** — GK→DEF→MID→FWD, starters before bench.
- **`indexPicks` / `indexScores` / `pointsOf` / `resolveGameweek` / `requireCompetition` / `requireTeam` / `requireGameweek`** — lookups that 404 as 404-style failures.

### Scoring and media helpers

#### `CaptainScoring`

- **`multiplier`** — 1, 2, or 3.
- **`effective`** — raw × multiplier. Created so SofaScore/FPL/WSL all store raw and display chips the same way.

#### `CompetitionBranding`

Maps `source` + `externalId` onto SofaScore unique-tournament ids. Official FPL / LaLiga Fantasy / WSL reuse those ids even though `source` is not `sofascore`.

**Public**

| Method | Purpose |
|---|---|
| **`logoUrl` / `logoDarkUrl`** | Tournament image (homepage prefers dark). |
| **`flagUrl` / `countryName`** | Category flag + label. |
| **`primaryColor` / `secondaryColor`** | CSS brand colours for wash / cards / headers. |
| **`brandKey`** | Shared visual key so FPL↔PL and Official LaLiga↔SofaScore LaLiga share one logo slot. |
| **`isAmericas`** | True for MLS (`242`) and Brasileirão (`325`) — homepage Americas season table. |

**Private:** `brandingTournamentId` (remaps `laliga-fantasy`→`8`, `fpl`→`17`, `wsl`→`1044`; else SofaScore numeric id), `numericId`, `country`, `colors`.

**Brand keys**

| Key | League | Primary / secondary |
|---|---|---|
| `17` | Premier League | `#3c1c5a` / `#f80158` |
| `8` | LaLiga | `#2f4a89` / `#f4a32e` |
| `23` | Serie A | `#09519e` / `#008fd7` |
| `34` | Ligue 1 | `#091c3e` / `#a9c011` |
| `35` | Bundesliga | `#e2080e` / `#8e0902` |
| `7` | Champions League | `#062b5c` / `#086aab` |
| `679` | Europa League | `#3d1a08` / `#f37d25` |
| `10783` | Nations League | `#3a4179` / `#e5a422` |
| `242` | MLS | `#e2231a` / `#062f69` |
| `325` | Brasileirão | `#C7FF00` / `#969696` |
| `1044` | WSL | `#06121e` / `#00c2cb` |

#### `ClubCrests.url`

FPL uses Premier League badge CDN `t{code}.png`. Everyone else uses `img.sofascore.com/api/v1/team/{id}/image`, with name fallbacks for PL/LaLiga clubs when the id is missing. WSL is **not** mapped through men’s PL names.

#### `PlayerPortraits.url`

Numeric SofaScore player id → `img.sofascore.com/api/v1/player/{id}/image`. Non-numeric ids (unresolved WSL `wsl-…`, FPL `fpl-…`) get no portrait.

#### `TransferChannels`

- **`isMarket` / `channel`** — blank/“Market” vs any other counterpart = release clause. Exists for official LaLiga Excel deals.

### Entities (JPA)

Lombok `@Data`. Tables match `sql/schema.sql`. Migrations: `sql/migrate-squad-pick-club-context.sql`, `sql/migrate-squad-pick-suspended.sql` (also applied via `spring.jpa.hibernate.ddl-auto=update` locally).

| Entity | Role |
|---|---|
| **`Competition`** | Unique `(source, externalId, season)`. |
| **`Gameweek`** | Week **row** (`number`, `status`, dates). |
| **`FantasyTeam`** | One team per competition. |
| **`Player`** | Unique `(source, externalId)`; shared identity (name, portrait id). Club fields are a soft cache / transfer fallback. |
| **`SquadPick`** | Role, captain/VC, price, **`injured`**, **`suspended`**; **plus pick-scoped `club`, `clubExternalId`, `shirtNumber`**. |
| **`PlayerGameweekScore`** | Raw `points`, optional `rating` + `breakdown`. |
| **`TeamGameweekScore`** | Week total, triple-captain flag, transfer penalty. |
| **`GameweekTransfer`** | Nullable in/out players, prices, counterpart, channel, sort order. |

### Repositories

Spring Data query methods — no custom SQL.

- **`CompetitionRepository.findBySourceAndExternalIdAndSeason`**
- **`GameweekRepository.findByCompetition_IdAndNumber`**, **`findByCompetition_IdOrderByNumberAsc`**
- **`FantasyTeamRepository.findByCompetition_Id`**
- **`PlayerRepository.findBySourceAndExternalId`**, **`findByExternalIdStartingWith`** (seed cleanup)
- **`SquadPickRepository.findByFantasyTeam_IdAndGameweek_Id`**, **`findByFantasyTeam_IdAndPlayer_IdAndGameweek_Id`**, **`deleteByPlayer_Id`**
- **`PlayerGameweekScoreRepository.findByPlayer_IdAndGameweek_Id`**, **`findByGameweek_IdAndPlayer_IdIn`**, **`deleteByPlayer_Id`**
- **`TeamGameweekScoreRepository.findByFantasyTeam_IdAndGameweek_Id`**, **`findByFantasyTeam_IdOrderByGameweek_NumberAsc`**
- **`GameweekTransferRepository.findByFantasyTeam_IdAndGameweek_IdOrderBySortOrderAsc`**, **`findByFantasyTeam_IdOrderByGameweek_NumberAscSortOrderAsc`**, **`deleteByFantasyTeam_IdAndGameweek_Id`**

### DTOs (records)

- **`SnapshotRequest`** (+ nested competition/gameweek/team/player/pick) — ingest body.
- **`TransfersRequest`** (+ round + pair) — ingest transfers; in/out may be null for LaLiga.
- **`HomePageResponse`** — `defaultCompetitionId` / `defaultCompetitionSlug`, `LeagueBrand` list, `PlayerOfTheWeek` list, `latestWeekStandings` / `europeTotalStandings` / `americasTotalStandings` (`LeagueStanding`).
- **`CompetitionResponse`** — list item including branding URLs/colours.
- **`TeamViewResponse`** — dashboard squad: picks (`injured` / `suspended`), transfers, transfer-market summary (`mostExpensivePurchase` / `highestSale` highlights), optional `longestServingPlayer`, captain display fields (`points`, `basePoints`, `captainMultiplier`).
- **`CompareResponse` / `PlayerDelta`**
- **`TotalsResponse` / `GameweekTotal`** — `GameweekTotal` carries `number`, `name`, **`status`**, `points`.

### Tests

- **`ApiSliceTest`** — MockMvc slice: SofaScore chips, LaLiga market + transfer highlights + longest-serving, FPL badges, WSL branding (tournament 1044), captain display, injured/suspended flags. Forces H2 via `@TestPropertySource` so a local `SPRING_PROFILES_ACTIVE=mysql` cannot wipe the live MySQL DB.
- **`BackendApplicationTests`** — context load.

---

## Frontend (Angular 21)

Standalone components, signals, `HttpClient`. Routes: homepage + leagues dashboard. GSAP is used only for the homepage POTW marquee.

### Bootstrap

- **`main.ts`** — `bootstrapApplication(App, appConfig)`.
- **`appConfig`** — router, HTTP, global error listeners.
- **`routes` (`app.routes.ts`)** — `''` → `HomeComponent`; `leagues` → `DashboardComponent`; wildcard → `''`.
- **`App`** — shell with `<router-outlet>`.

### `HomeService`

Thin GET client at `http://localhost:8080/api/v1/home`.

- **`getHome()`** — returns `HomePage`.

### `CompetitionService`

Thin GET client at `http://localhost:8080/api/v1/competitions`. Created so the UI never POSTs.

- **`getCompetitions`**
- **`getTeam(id, gameweek?)`**
- **`getGameweek(id, n)`** — available but dashboard uses `getTeam`.
- **`compare` / `totals`**

### `tracker.ts` models

TypeScript mirrors of GET JSON: `HomePage` (incl. `LeagueStanding` lists), `LeagueBrand`, `PlayerOfTheWeek`, `Competition`, `TeamView` (incl. `LongestServingPlayer`), `PickView` (`injured` / `suspended`), `TransferView`, `TransferHighlight`, `TransferMarket*` (incl. season extremes), `CompareView`, `PlayerDelta`, `TotalsView` (`GameweekTotal.status`).

### `HomeComponent` — landing page

Why: brand-first homepage with league wash, MVP card, a sliding Players of the Week rail, and league standings tables.

**Signals:** `home`, `error`, `loading`.

**Computed**

- **`colorMix`** — builds `--home-mix` gradient from every `leagueBrands` primary/secondary pair.
- **`leaguesHref` / `leaguesQuery`** — CTA to `/leagues` with optional `?competition=` from `defaultCompetitionId`.
- **`topPlayerOfTheWeek`** — cross-competition MVP (max `points` in `playersOfTheWeek`).
- **`marqueePlayers`** — `[...players, ...players]` so GSAP can loop seamlessly on half the track width.

**Lifecycle / marquee**

- **constructor** — `HomeService.getHome()`; `afterRenderEffect` calls `setupMarquee` when `#marqueeTrack` exists; `DestroyRef` → `killMarquee`.
- **`setupMarquee(track)`** — GSAP `fromTo` `x: 0 → -scrollWidth/2`, ease `none`, `repeat: -1`, ~28 px/s; skips rebuild when distance unchanged; preserves pause state.
- **`killMarquee`** — kills tween; clears transform.
- **`pauseMarquee` / `resumeMarquee`** — bound to marquee `mouseenter` / `mouseleave`.

**Helpers:** `hideImage`, `shirtLabel`, `isTopPlayer` (MVP highlight on duplicated marquee cards).

Standings UI: three tables under POTW — **Latest week**, **Europe (season)**, **Americas (season)** — each row uses competition logo + brand CSS vars from the API.

#### Homepage POTW / MVP styling (`home.css`)

| Class / token | Purpose |
|---|---|
| `.home`, `.home-wash` | Full-page atmosphere; wash uses `--home-mix` + soft radials. |
| `.home-logos`, `.home-logo`, `.home-logo-0`…`-10` | Floating competition logos; **one unique slot each** (no `i % 5` overlap). |
| `.home-content`, `.home-hero`, `.eyebrow`, `.lede`, `.cta`, `.banner` | Hero copy + CTA. |
| `.mvp`, `.mvp-badge`, `.mvp-badge-compact` | Featured Top player of the week + MVP chip. |
| `.potw`, `.potw-head` | Section title for the rail. |
| `.potw-marquee` | Overflow hidden + edge fade mask. |
| `.potw-rail` | Flex `width: max-content` track GSAP translates. |
| `.potw-card` | Card chrome; `--potw-primary` / `--potw-secondary` from API. |
| `.potw-card-mvp` | Lime border + stronger glow for the MVP duplicate. |
| `.potw-meta`, `.comp-logo`, `.comp-name` | Competition row on the card. |
| `.portrait-stage`, `.portrait`, `.portrait-fallback`, `.crest` | Portrait plane + club crest overlay. |
| `.player-copy`, `.shirt`, `.name`, `.club`, `.gw-label` | Shirt, name, club, `Round N · X pts`. |

Template: `home.html` — wash, logo field, hero, MVP `ng-template` card, marquee of cards sharing `#playerCard`.

### `DashboardComponent` — leagues page

Why: one page for every league — branding, XI, bench/squad, GW standout card, status chips, season high/low weeks, transfers (LaLiga deal cards + market totals), longest-serving card, compare, totals.

**Signals:** `competitions`, `selectedId`, `gameweek`, `fromGw`, `toGw`, `teamView`, `compareView`, `totalsView`, `error`, `loading`.

**Computed**

- **`selectedCompetition`** — current dropdown row.
- **`pageBrand`** — CSS variables from API primary/secondary + logo (page background).
- **`starters` / `bench`** — split on `role === 'starter'` (LaLiga “squad” still uses non-starter role).
- **`isOfficialLaLiga` / `isOfficialFpl`** — copy and FPL neon classes.
- **`reserveHeading`** — “Squad” vs “Bench”.
- **`showTransferCounterpart`** — LaLiga or any move with a counterpart.
- **`playerOfTheWeek`** — max `pick.points` in the current `teamView` (GW card).
- **`highestScoringGameweek` / `lowestScoringGameweek`** — season extremes from `totalsView.gameweeks`; lowest filters with `isScoringComplete` (finished or points &gt; 0).
- **`mostExpensivePurchase` / `highestPlayerSale`** — Official LaLiga only; from `transferMarket` season highlights.
- **`longestServingPlayer`** — Official LaLiga only; from `teamView.longestServingPlayer`.

**Methods**

- **`constructor`** — loads competitions; honour `?competition=` query; selects default.
- **`selectCompetition`** — latest week, compare from first→latest, refresh all three GETs.
- **`onCompetitionChange` / `onGameweekChange` / `onCompareChange`** — template bindings.
- **`transferLabel` / `priceFormat` / `counterpartLabel` / `hasMarketDeals`** — LaLiga market wording and prices.
- **`totalSold` / `totalBought` / `counterpartTotals`** — combine market + release-clause deal groups; footer totals on manager counterpart tables.
- **`shirtLabel` / `transferHighlightShirt` / `longestServingShirt` / `transferHighlightMeta`** — shirt / GW+counterpart for POTW-style cards.
- **`isInjured` / `isSuspended`** — status chips on squad rows.
- **`hideImage`** — hide broken crest/portrait.
- **`signed`** — `+n` / `n` for compare deltas.
- **`refreshAll` / `loadTeam` / `loadCompare` / `loadTotals`** — HTTP; errors set `error`.

#### Competition-page GW POTW card styling (`dashboard.css`)

Same visual language as homepage cards, scoped under the competition view:

| Class | Purpose |
|---|---|
| `.gw-potw`, `.gw-potw-head` | Centered “Player of the week” block above the squad. |
| `.potw-card` (+ nested portrait / crest / copy) | Card using `--potw-primary` / `--potw-secondary` from the selected competition. |
| `.potw-meta`, `.potw-comp-logo`, `.potw-comp-name` | Competition header on the GW card. |
| `.chip-injured` / `.chip-suspended` | Amber / red outline chips next to player names. |
| `.score-extremes` | Two-column Season-total-style cards for best/worst GW. |
| `.transfer-highlights`, `.transfer-highlights-grid` | Side-by-side LaLiga purchase/sale POTW cards in Transfers. |
| `.longest-serving` | Centered veteran card between squad and transfers. |
| `.market-totals` / table `tfoot` | Total sold/bought chips + manager-table footers. |

Also: `.page-brand`, `.page-brand-fpl`, `.panel-head-branded`, FPL neon overlays — competition header theming (not POTW-specific).

Templates/styles: `dashboard.html`, `dashboard.css`.

---

## Python collector

Package `collector`, CLI `python -m collector`. Loads repo-root then `collector/.env`. Raw JSON goes to `collector/cache/<slug>/` (gitignored).

### CLI (`__main__.py`)

- **`main`** — subcommands `import`, `import-excel`, `sync`, `pull`.
- **`_run_import`** — local JSON (squad or transfers export).
- **`_run_import_excel`** — official LaLiga workbook.
- **`_run_sync`** — legacy single-GW SofaScore URL.
- **`_run_pull_command`** — every SofaScore target in `.env`, plus FPL if `FPL_ENTRY_ID`, plus WSL if gameplay id + game token. `--competition` selects one slug (`premier-league-fantasy`, `nations-league`, `wsl-fantasy`, …).

### Canonical models (`models.py`)

- **`PlayerPayload` / `PickPayload` / `Snapshot`** — POST `/ingest/snapshots`. `PickPayload` carries `injured` / `suspended`. `Snapshot.to_dict` omits null team points.
- **`TransferPlayer` / `TransferPair` / `TransferRound` / `TransfersBatch`** — POST `/ingest/transfers`.
- **`FantasyAdapter`** — old interface (`fetch_competitions` / `fetch_squad` / `fetch_gameweek_scores`); SofaScore and file import still implement it. FPL/WSL use dedicated `pull_*` functions instead.

### `BackendPublisher`

- **`publish` / `publish_transfers`** — POST with optional `X-Ingest-Token`. `BACKEND_URL` defaults to `http://localhost:8080`.

### Pull orchestration (`pull.py`)

- **`PullTarget`** — slug + competition/squad/transfers/gameweek URLs.
- **`pull_targets_from_env`** — Premier League unprefixed `SOFASCORE_*` or `SOFASCORE_PREMIER_LEAGUE_*`; other leagues `SOFASCORE_LALIGA_*`, `SERIE_A`, `LIGUE_1`, `BUNDESLIGA`, `CHAMPIONS_LEAGUE`, `EUROPA_LEAGUE`, **`NATIONS_LEAGUE`**, `MLS`, `BRASILEIRAO`. A concrete `/round/{id}/squad` URL alone is enough for a first Nations League ingest.
- **`complete_target`** — from a Fantasy `…/competition/{id}` URL, derive `/transfers` and `/round/{roundId}/squad`.
- **`_target_from_prefix`** — env → `PullTarget`.
- **`adapter_for_target`** — `SofaScoreAdapter` for that target.
- **`run_pull`** — meta + rounds → `currentRound.id` (or `--gameweek` sequence) → squad → injury/suspension overlay → optional transfers → POST (unless `--dry-run`).
- **`_save_json`** — cache dump.

### SofaScore Fantasy adapter (`adapters/sofascore.py`)

Why: replay **your** Network JSON URLs with your cookie; impersonate Chrome (`curl_cffi`) because Python `requests` was WAF 403.

- **`CLUB_BY_ID` / `CLUB_BY_CODE`** — expand abbreviations to full club names (PL includes Sunderland `41`/`SUN`, AFC Bournemouth `60`/`BOU`, Liverpool, Spurs, …; plus LaLiga/Ligue 1/Serie A/MLS/Brasileirão). Transfers often only send `teamId` + `nameCode`.
- **`resolve_club_name`** — prefer `CLUB_BY_ID`, then **full API `name`**, then `CLUB_BY_CODE`. Full names win over codes so national `ESP` → Spain is not rewritten to Espanyol.
- **`normalize_position`**
- **`snapshot_from_payload`** — canonical snapshot, SofaScore squad, or “sofascore-like” shapes.
- **`is_transfers_export` / `transfers_from_payload`**
- **`_from_canonical` / `_from_sofascore_squad` / `_from_sofascore_like`**
- **`_injured_from_sofascore` / `_first_unique_tournament` / `_normalize_season` / `_date_from_timestamp`**
- **`_transfer_player` / `_club_external_id` / `_optional_float` / `_optional_int`**
- **`SofaScoreSessionError`** — 401 → refresh `SOFASCORE_SESSION`.
- **`SofaScoreAdapter`**
  - **`fetch_competitions` / `fetch_meta` / `fetch_rounds` / `fetch_squad` / `fetch_transfers` / `fetch_gameweek_scores`**
  - **`_get_json` / `_require_round_id`**
- **`round_id_from_meta`** — current/next/previous or `userRounds` calendar by sequence.
- **`_browser_headers` / `_http_get` / `_env_or` / `_normalize_session_cookie` / `_format_url`** — strip `Cookie:` prefix; rewrite `/round/{digits}/`.
- **`load_snapshot_file`**

### Round overlay (`adapters/sofascore_round.py`)

Uses **known** SofaScore paths only: `unique-tournament/{id}/seasons`, `…/season/{id}/players`, `…/events/round/{n}`, `event/{id}/lineups`, `team/{id}/players`.

- **`current_season_id`** — first season in the list (current).
- **`overlay_from_lineups`** — ratings + **injured** + **suspended** ids from `missingPlayers` (skips `doubtful`). Suspension wins over injury when both could match.
- **`fetch_round_overlay`** — all events in a round (`injuredIds` / `suspendedIds`).
- **`fetch_injured_player_ids`** — live `injury.status == out` (upcoming/live weeks).
- **`apply_round_overlay` / `annotate_snapshot_injuries`** — also sets `pick.suspended` (clears `injured` when suspended).
- **`_is_suspended_missing`** — SofaScore reasons **3** (FA/improper conduct), **11** (yellow accumulation), **12** (yellow/red), **13** (red), plus description tokens (`suspension`, `unavail`, …).
- **`_is_injured_missing`** — injury-like missing rows that are **not** suspensions (reason `1` / `"injur…"`).
- **`_injured_for_team` / `_player_id` / `_optional_int`**

### Player directory (`adapters/sofascore_directory.py`)

Why: official FPL/WSL ids are not SofaScore ids; portraits (and FPL display names) need numeric player ids / SofaScore `playerName`.

- **`fold_name` / `club_key`** — accents, FC/Women/Lionesses, Brighton & Hove, Man Utd aliases.
- **`fetch_tournament_players` / `fetch_premier_league_players`**
- **`resolve_sofascore_player`** — club then name tokens.
- **`search_sofascore_player`** — `search/all` fallback.
- **`_tokens_match`**

Tournament constants: PL **17**, WSL **1044**, WSL2 **10553**. Nations League branding tournament id **10783**.

### Official FPL (`adapters/fpl.py`)

Public `fantasy.premierleague.com/api`. No cookie.

- **`fpl_entry_id` / `pull_fpl`** — bootstrap, entry, history, transfers, per-GW picks + live; SofaScore overlay on tournament 17.
- **`catalog_from_bootstrap` / `competition_payload` / `team_payload` / `snapshot_from_picks` / `transfers_from_fpl`**
- **`_pick_from_fpl` / `_transfer_pair` / `_transfer_player` / `_player_from_element`**
- **`_display_name`** — prefer SofaScore `playerName`, then FPL `first_name` + `second_name`, then `web_name` (dashboard shows full names, not “Virgil” / “Gabriel”).
- **`_resolve_sofascore_player` / `_sofascore_player_id`** — cache hit rows for id + name; legacy id cache kept for injury overlays.
- **`_optional_shirt` / `_safe_round_overlay` / `_current_injured_ids`**
- **`_event_status` / `_season` / `_price`** — prices in tenths of a million.
- **`_optional_float` / `_get_json` / `_save_json`**

Captain live points are **raw**; dashboard ×2.

### Official WSL (`adapters/wsl.py`)

Auth is request header **`x-game-token`** (env `WSL_GAME_TOKEN`, fallback `WSL_BEARER`). Auth0 Bearer is identity, not my-team.

- **`wsl_game_token` / `wsl_gameplay_id` / `wsl_configured` / `pull_wsl`**
- **`competition_payload` / `team_payload` / `snapshot_from_my_team` / `transfers_from_squads`** — transfers are week-to-week `arrTeam` diffs.
- **`_pick_from_wsl` / `_player_from_row` / `_sofascore_player_id` / `_transfer_player`**
- **`_display_name`** — prefer SofaScore `playerName` from the unique-tournament cache when present (WSL feed often has short/incomplete names).
- **`_current_injured_ids` / `_safe_round_overlay` / `_safe_wsl_players`** — overlay 1044 + 10553.
- **`_gameweek_status` / `_starts_at` / `_season`**
- **`_raw_points`** — my-team `totalPoints` **already includes captain ×2**; store half so the API does not double again.
- **`_team_points` / `_position_name` / `_short_id` / `_index` / `_optional_float` / `_feed_value` / `_get_json` / `_save_json`**

### Official LaLiga Excel (`adapters/excel_laliga.py`)

App-only game (100M€ market, XI + unused squad, unpaired buys/sells, no captains).

- **`load_workbook_payloads`** — snapshots + transfer batch.
- **`_competition_and_team` / `_snapshots_from_squads` / `_transfers_from_sheet`**
- **`_pick_from_row` / `_deal_from_row` / `_transfer_player`**
- **`_fetch_sofascore_shirt`** — when the sheet has a numeric SofaScore player id, GET `player/{id}` and store `jerseyNumber` as `shirtNumber`.
- **`_key_values` / `_table_rows` / `_id_or_slug` / `_slug` / `_digits` / `_int` / `_optional_float` / `_optional_text` / `_position` / `_action` / `_injured` / `_role`**

### File import (`adapters/file_import.py`)

- **`FileImportAdapter.fetch_competitions` / `fetch_squad` / `fetch_gameweek_scores` / `_load`** — saved Network JSON when URLs are unavailable.

### Excel template builder (`templates/build_laliga_fantasy_workbook.py`)

- **`build`** — writes `laliga-fantasy-oficial.xlsx`.
- **`_readme` / `_competition` / `_squads` / `_transfers` / `_clubs` / `_header_row` / `_fill_row` / `_list`**

### Collector tests

`test_fpl`, `test_wsl`, `test_pull` (includes Nations League squad-only target), `test_sofascore_*`, `test_excel_laliga`, `test_sofascore_directory` — mapping and env targeting without printing secrets.

---

## Environment (gitignored)

| Variable | Purpose |
|---|---|
| `SOFASCORE_SESSION` | Cookie value from a Fantasy XHR |
| `SOFASCORE_*` / `SOFASCORE_<LEAGUE>_*` | Competition / squad / transfers URLs (incl. `SOFASCORE_NATIONS_LEAGUE_*`) |
| `FPL_ENTRY_ID` | Public FPL team id |
| `WSL_GAMEPLAY_ID` | Gameplay UUID in my-team path |
| `WSL_GAME_TOKEN` (or `WSL_BEARER`) | `x-game-token` header (~24h). Not Auth0. |
| `BACKEND_URL` / `INGEST_TOKEN` | Publisher target |

Never log tokens. HTTP 401 on SofaScore → refresh cookie. HTTP 401 on WSL → copy a fresh `x-game-token`.

---

## Docs / screenshots

- **`docs/TECHNICAL.md`** — this file.
- **`docs/screenshots/`** — README media (`home.png`, `leagues.png`, `potw-marquee.gif`, `squad-status-badges.png`, `score-extremes.png`, `laliga-transfer-highlights.png`).
