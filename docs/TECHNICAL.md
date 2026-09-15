# Fantasy Football Tracker — technical reference

Personal tracker: **Python collector** POSTs snapshots into **Spring Boot 3.5 + MySQL**, and **Angular 21** GETs a dashboard. The frontend never writes. Gameweeks are **rows**, not tables.

**Sources**

| `source` | Slug example | How data arrives |
|---|---|---|
| `sofascore` | `premier-league`, `laliga`, … | Logged-in SofaScore Fantasy XHRs + `SOFASCORE_SESSION` |
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
frontend  GET /api/v1/competitions…
        → CompetitionQueryService + branding/crests/portraits
```

Captain **display** is always ×2 (×3 if triple captain). Ingest stores **raw** points. Official WSL `totalPoints` already includes ×2, so the collector divides the captain’s value by 2 before POST.

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

### HTTP — read (`CompetitionController`)

Frontend-only surface.

| Method | Path | Why |
|---|---|---|
| **`list`** | `GET /api/v1/competitions` | Dropdown: name, season, branding, gameweek numbers. |
| **`team`** | `GET /api/v1/competitions/{id}/team?gameweek=` | Squad for a week (latest if omitted). |
| **`gameweek`** | `GET /api/v1/competitions/{id}/gameweeks/{n}` | Same payload keyed by week number. |
| **`compare`** | `GET /api/v1/competitions/{id}/compare?from=&to=` | Week-vs-week player deltas. |
| **`totals`** | `GET /api/v1/competitions/{id}/totals` | Season sum of team week scores. |

### `IngestService`

Why it exists: one upsert path for SofaScore, FPL, WSL, and Excel so the dashboard schema stays stable.

- **`upsertSnapshot`** — competition, gameweek, team, picks, player scores; drops stale picks for that week; team points from the request or from starter points after `CaptainScoring.effective`.
- **`upsertTransfers`** — replaces that week’s transfer rows; applies `transferPenalty` onto `TeamGameweekScore`.
- **`removeSeedPlayers`** — cleanup for `seed-*` ids.
- **`findAllCompetitions`** — used by tests/tooling.
- **`upsertCompetition` / `upsertGameweek` / `upsertTeam` / `upsertPlayer` / `upsertPick` / `upsertPlayerScore` / `upsertTeamScore`** — idempotent writes keyed by source+external id (or team+player+week).
- **`upsertGameweekForTransfers` / `applyTransferPenalty`** — transfers can arrive for a week that has no squad yet.
- **`removeStalePicks`** — a new XI replaces last week’s leftover rows.
- **`toJson`** — stores pick `breakdown` (minutes, goals, …) as JSON text.

### `CompetitionQueryService`

Why it exists: GET payloads include derived media (crest, portrait, colours) and captain **display** points without the frontend knowing chips.

- **`listCompetitions`** — all competitions with branding + distinct gameweek numbers.
- **`teamView` / `gameweekView`** — same builder; `teamView` picks latest week if unspecified.
- **`compare`** — players in either week; points use captain multiplier per week’s triple-captain flag.
- **`totals`** — ordered week scores + season total.
- **`buildTeamView`** — starters/bench, portraits, crests, transfers, transfer-market summary.
- **`buildTransfers`** — stored `gameweek_transfer` rows if present; otherwise **squad-diff** against the previous week (WSL and gaps in official feeds).
- **`toTransfer` (overloads)** — maps a player + price + counterpart into the dashboard transfer card.
- **`buildTransferMarket` / `summarizeMarket` / `toCounterpartGroups` / `Accumulator`** — LaLiga market vs release-clause totals (week + season).
- **`previousGameweek` / `tripleCaptain` / `pickComparator` / `positionOrder`** — GK→DEF→MID→FWD, starters before bench.
- **`indexPicks` / `indexScores` / `pointsOf` / `resolveGameweek` / `requireCompetition` / `requireTeam` / `requireGameweek`** — lookups that 404 as 404-style failures.

### Scoring and media helpers

#### `CaptainScoring`

- **`multiplier`** — 1, 2, or 3.
- **`effective`** — raw × multiplier. Created so SofaScore/FPL/WSL all store raw and display chips the same way.

#### `CompetitionBranding`

Maps `source` + `externalId` onto SofaScore unique-tournament ids (17 PL, 8 LaLiga, 23 Serie A, 34 Ligue 1, 35 Bundesliga, 7 UCL, 679 UEL, 242 MLS, 325 Brasileirão, **1044 WSL**). Official FPL/LaLiga/WSL reuse those ids even though `source` is not `sofascore`.

- **`logoUrl` / `logoDarkUrl` / `flagUrl` / `countryName` / `primaryColor` / `secondaryColor`**
- **`brandingTournamentId` / `numericId` / `country` / `colors`** — private mapping.

#### `ClubCrests.url`

FPL uses Premier League badge CDN `t{code}.png`. Everyone else uses `img.sofascore.com/api/v1/team/{id}/image`, with name fallbacks for PL/LaLiga clubs when the id is missing. WSL is **not** mapped through men’s PL names (Chelsea Women must keep a SofaScore women’s team id).

#### `PlayerPortraits.url`

Numeric SofaScore player id → `img.sofascore.com/api/v1/player/{id}/image`. Non-numeric ids (unresolved WSL `wsl-…`, FPL `fpl-…`) get no portrait.

#### `TransferChannels`

- **`isMarket` / `channel`** — blank/“Market” vs any other counterpart = release clause. Exists for official LaLiga Excel deals.

### Entities (JPA)

Lombok `@Data`. Tables match `sql/schema.sql`.

| Entity | Role |
|---|---|
| **`Competition`** | Unique `(source, externalId, season)`. |
| **`Gameweek`** | Week **row** (`number`, `status`, dates). |
| **`FantasyTeam`** | One team per competition. |
| **`Player`** | Unique `(source, externalId)`; `externalId` is the SofaScore player id when resolved. |
| **`SquadPick`** | Role, captain/VC, price, injured flag. |
| **`PlayerGameweekScore`** | Raw `points`, optional `rating` + `breakdown`. |
| **`TeamGameweekScore`** | Week total, triple-captain flag, transfer penalty. |
| **`GameweekTransfer`** | Nullable in/out players, prices, counterpart, channel, sort order. |

### Repositories

Spring Data query methods — no custom SQL. They exist so ingest and GET stay indexed on natural keys.

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
- **`CompetitionResponse`** — list item including branding URLs/colours.
- **`TeamViewResponse`** — dashboard squad: picks, transfers, transfer-market summary, captain display fields (`points`, `basePoints`, `captainMultiplier`).
- **`CompareResponse` / `PlayerDelta`**
- **`TotalsResponse` / `GameweekTotal`**

### Tests

- **`ApiSliceTest`** — MockMvc slice: SofaScore chips, LaLiga market, FPL badges, WSL branding (tournament 1044), captain display.
- **`BackendApplicationTests`** — context load.

---

## Frontend (Angular 21)

Standalone components, signals, `HttpClient`. One route: the dashboard.

### Bootstrap

- **`main.ts`** — `bootstrapApplication(App, appConfig)`.
- **`appConfig`** — router, HTTP, global error listeners.
- **`routes`** — `''` → `DashboardComponent`; wildcard redirects home.
- **`App`** — shell with `<router-outlet>`. No logic; the dashboard is the product.

### `CompetitionService`

Thin GET client at `http://localhost:8080/api/v1/competitions`. Created so the UI never POSTs.

- **`getCompetitions`**
- **`getTeam(id, gameweek?)`**
- **`getGameweek(id, n)`** — available but dashboard uses `getTeam`.
- **`compare` / `totals`**

### `tracker.ts` models

TypeScript mirrors of GET JSON: `Competition`, `TeamView`, `PickView`, `TransferView`, `TransferMarket*`, `CompareView`, `PlayerDelta`, `TotalsView`. Exist so templates stay typed.

### `DashboardComponent`

Why: one page for every league — branding, XI, bench/squad, transfers, compare, totals.

**Signals:** `competitions`, `selectedId`, `gameweek`, `fromGw`, `toGw`, `teamView`, `compareView`, `totalsView`, `error`, `loading`.

**Computed**

- **`selectedCompetition`** — current dropdown row.
- **`pageBrand`** — CSS variables from API primary/secondary + logo (page background).
- **`starters` / `bench`** — split on `role === 'starter'` (LaLiga “squad” still uses non-starter role).
- **`isOfficialLaLiga` / `isOfficialFpl`** — copy and FPL neon classes (`#01fc84`, `#39a1f9`, `#8c46ff` mixed with PL purple/pink).
- **`reserveHeading`** — “Squad” vs “Bench”.
- **`showTransferCounterpart`** — LaLiga or any move with a counterpart.

**Methods**

- **`constructor`** — loads competitions; selects the first.
- **`selectCompetition`** — latest week, compare from first→latest, refresh all three GETs.
- **`onCompetitionChange` / `onGameweekChange` / `onCompareChange`** — template bindings.
- **`transferLabel` / `priceFormat` / `counterpartLabel` / `hasMarketDeals`** — LaLiga market wording and 6-decimal prices (Purić-style).
- **`hideImage`** — hide broken crest/portrait (no alt junk).
- **`signed`** — `+n` / `n` for compare deltas.
- **`refreshAll` / `loadTeam` / `loadCompare` / `loadTotals`** — parallel-ish HTTP; errors set `error`.

Templates/styles: `dashboard.html` (branded page, FPL extra classes), `dashboard.css` (league colours + FPL neon overlay).

---

## Python collector

Package `collector`, CLI `python -m collector`. Loads repo-root then `collector/.env`. Raw JSON goes to `collector/cache/<slug>/` (gitignored).

### CLI (`__main__.py`)

- **`main`** — subcommands `import`, `import-excel`, `sync`, `pull`.
- **`_run_import`** — local JSON (squad or transfers export).
- **`_run_import_excel`** — official LaLiga workbook.
- **`_run_sync`** — legacy single-GW SofaScore URL.
- **`_run_pull_command`** — every SofaScore target in `.env`, plus FPL if `FPL_ENTRY_ID`, plus WSL if gameplay id + game token. `--competition` selects one slug (`premier-league-fantasy`, `wsl-fantasy`, …).

### Canonical models (`models.py`)

- **`PlayerPayload` / `PickPayload` / `Snapshot`** — POST `/ingest/snapshots`. `Snapshot.to_dict` omits null team points.
- **`TransferPlayer` / `TransferPair` / `TransferRound` / `TransfersBatch`** — POST `/ingest/transfers`.
- **`FantasyAdapter`** — old interface (`fetch_competitions` / `fetch_squad` / `fetch_gameweek_scores`); SofaScore and file import still implement it. FPL/WSL use dedicated `pull_*` functions instead.

### `BackendPublisher`

- **`publish` / `publish_transfers`** — POST with optional `X-Ingest-Token`. `BACKEND_URL` defaults to `http://localhost:8080`.

### Pull orchestration (`pull.py`)

- **`PullTarget`** — slug + competition/squad/transfers/gameweek URLs.
- **`pull_targets_from_env`** — Premier League unprefixed `SOFASCORE_*` or `SOFASCORE_PREMIER_LEAGUE_*`; other leagues `SOFASCORE_LALIGA_*`, `SERIE_A`, `LIGUE_1`, `BUNDESLIGA`, `CHAMPIONS_LEAGUE`, `EUROPA_LEAGUE`, `MLS`, `BRASILEIRAO`.
- **`complete_target`** — from a Fantasy `…/competition/{id}` URL, derive `/transfers` and `/round/{roundId}/squad`.
- **`_target_from_prefix`** — env → `PullTarget`.
- **`adapter_for_target`** — `SofaScoreAdapter` for that target.
- **`run_pull`** — meta + rounds → `currentRound.id` (or `--gameweek` sequence) → squad → injury overlay → optional transfers → POST (unless `--dry-run`).
- **`_save_json`** — cache dump.

### SofaScore Fantasy adapter (`adapters/sofascore.py`)

Why: replay **your** Network JSON URLs with your cookie; impersonate Chrome (`curl_cffi`) because Python `requests` was WAF 403.

- **`normalize_position`**
- **`snapshot_from_payload`** — canonical snapshot, SofaScore squad, or “sofascore-like” shapes.
- **`is_transfers_export` / `transfers_from_payload`**
- **`_from_canonical` / `_from_sofascore_squad` / `_from_sofascore_like`**
- **`_injured_from_sofascore` / `_first_unique_tournament` / `_normalize_season` / `_date_from_timestamp`**
- **`_transfer_player` / `_club_external_id` / `_optional_float`**
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
- **`overlay_from_lineups`** — ratings + injured from `missingPlayers` (not doubtful).
- **`fetch_round_overlay`** — all events in a round.
- **`fetch_injured_player_ids`** — live `injury.status == out`.
- **`apply_round_overlay` / `annotate_snapshot_injuries`**
- **`_injured_for_team` / `_is_injured_missing` / `_player_id` / `_optional_int`**

### Player directory (`adapters/sofascore_directory.py`)

Why: official FPL/WSL ids are not SofaScore ids; portraits need numeric player ids.

- **`fold_name` / `club_key`** — accents, FC/Women/Lionesses, Brighton & Hove, Man Utd aliases.
- **`fetch_tournament_players` / `fetch_premier_league_players`**
- **`resolve_sofascore_player`** — club then name tokens.
- **`search_sofascore_player`** — `search/all` fallback (same family as LaLiga id fill).
- **`_tokens_match`**

Tournament constants: PL **17**, WSL **1044**, WSL2 **10553**. Unique-tournament **44** is 2. Bundesliga, not WSL.

### Official FPL (`adapters/fpl.py`)

Public `fantasy.premierleague.com/api`. No cookie.

- **`fpl_entry_id` / `pull_fpl`** — bootstrap, entry, history, transfers, per-GW picks + live; SofaScore overlay on tournament 17.
- **`catalog_from_bootstrap` / `competition_payload` / `team_payload` / `snapshot_from_picks` / `transfers_from_fpl`**
- **`_pick_from_fpl` / `_transfer_pair` / `_transfer_player` / `_player_from_element` / `_sofascore_player_id`**
- **`_safe_round_overlay` / `_current_injured_ids`** — FPL status `i` + SofaScore missing/out.
- **`_event_status` / `_season` / `_price`** — prices in tenths of a million.
- **`_optional_float` / `_get_json` / `_save_json`**

Captain live points are **raw**; dashboard ×2.

### Official WSL (`adapters/wsl.py`)

Auth is request header **`x-game-token`** (env `WSL_GAME_TOKEN`, fallback `WSL_BEARER`). Auth0 Bearer is identity, not my-team. Public config/feeds discovered from official `configurations.json` / mixApi (not invented gameplay paths).

- **`wsl_game_token` / `wsl_gameplay_id` / `wsl_configured` / `pull_wsl`**
- **`competition_payload` / `team_payload` / `snapshot_from_my_team` / `transfers_from_squads`** — transfers are week-to-week `arrTeam` diffs (no official transfers XHR).
- **`_pick_from_wsl` / `_player_from_row` / `_sofascore_player_id` / `_transfer_player`**
- **`_current_injured_ids` / `_safe_round_overlay` / `_safe_wsl_players`** — overlay 1044 + 10553.
- **`_gameweek_status` / `_starts_at` / `_season`**
- **`_raw_points`** — my-team `totalPoints` **already includes captain ×2**; store half so the API does not double again.
- **`_team_points` / `_position_name` / `_short_id` / `_index` / `_optional_float` / `_feed_value` / `_get_json` / `_save_json`**

Feeds used: `/fantasy/services/gameplay/{id}/{week}/my-team`, `/feeds/tour/details/1.json`, `/feeds/players/matchday_en_1_{week}.json`, `/feeds/fixtures/fixtures_en_1.json`.

### Official LaLiga Excel (`adapters/excel_laliga.py`)

App-only game (100M€ market, XI + unused squad, unpaired buys/sells, no captains).

- **`load_workbook_payloads`** — snapshots + transfer batch.
- **`_competition_and_team` / `_snapshots_from_squads` / `_transfers_from_sheet`**
- **`_pick_from_row` / `_deal_from_row` / `_transfer_player`**
- **`_key_values` / `_table_rows` / `_id_or_slug` / `_slug` / `_digits` / `_int` / `_optional_float` / `_optional_text` / `_position` / `_action` / `_injured` / `_role`**

Yellow EXAMPLE rows are skipped. Do not overwrite the empty template with personal GW data.

### File import (`adapters/file_import.py`)

- **`FileImportAdapter.fetch_competitions` / `fetch_squad` / `fetch_gameweek_scores` / `_load`** — saved Network JSON when URLs are unavailable.

### Excel template builder (`templates/build_laliga_fantasy_workbook.py`)

- **`build`** — writes `laliga-fantasy-oficial.xlsx`.
- **`_readme` / `_competition` / `_squads` / `_transfers` / `_clubs` / `_header_row` / `_fill_row` / `_list`** — styling and dropdowns so the importer has a stable schema.

### Collector tests

`test_fpl`, `test_wsl`, `test_pull`, `test_sofascore_*`, `test_excel_laliga`, `test_sofascore_directory` — mapping and env targeting without printing secrets.

---

## Environment (gitignored)

| Variable | Purpose |
|---|---|
| `SOFASCORE_SESSION` | Cookie value from a Fantasy XHR |
| `SOFASCORE_*` / `SOFASCORE_<LEAGUE>_*` | Competition / squad / transfers URLs |
| `FPL_ENTRY_ID` | Public FPL team id |
| `WSL_GAMEPLAY_ID` | Gameplay UUID in my-team path |
| `WSL_GAME_TOKEN` (or `WSL_BEARER`) | `x-game-token` header (~24h). Not Auth0. |
| `BACKEND_URL` / `INGEST_TOKEN` | Publisher target |

Never log tokens. HTTP 401 on SofaScore → refresh cookie. HTTP 401 on WSL → copy a fresh `x-game-token`.
