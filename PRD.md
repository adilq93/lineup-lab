# PRD: LAL Playoff "Mismatch Hunter" Engine
**Version:** 1.2  
**Status:** Approved — Ready for Implementation  
**Author:** Adil Qaisar  
**Target Season:** 2025–2026 NBA Regular Season  
**Last Updated:** 2026-04-03

---

## Project Overview

### Purpose
The Mismatch Hunter Engine is a tactical scouting dashboard that surfaces exploitable weaknesses in opponent 3-man lineup combinations. For a given opponent, it shows how their top trios perform not just overall, but specifically against contextual lineup archetypes — large lineups, shooting lineups, small-ball lineups, and clutch/pace scenarios.

The core insight is a **delta**: the drop in a trio's Net Rating under a specific matchup context. A trio at +8 overall that drops to −2 against a two-big lineup is a tactical target.

**Core question the app answers:**  
*"How does Jokic/Murray/Johnson perform when we put two players over 6'10" on the floor — and how does that compare to their baseline?"*

### Motivation
Portfolio project targeting an NBA front-office analytics/scouting engineering role. Stack (Django + PostgreSQL + React) matches the target job description. Mirrors contextual lineup analysis used by modern NBA teams for playoff preparation.

### Scope

**In scope (v1):**
- 5 opponents: Denver Nuggets, OKC Thunder, San Antonio Spurs, Minnesota Timberwolves, Houston Rockets
- 2025–2026 NBA regular season data only
- 3-man combinations with ≥ 100 possessions together
- 6 lineup archetype filters, combinable with AND logic
- Lakers roster for counter-lineup archetype recommendations
- Read-only dashboard, no auth, no export

**Out of scope (v1):** all other teams, 2-man/5-man analysis, real-time data, playoff games, mobile view, export, authentication

---

## Users & Personas

**Primary User: The Scout / Analyst**  
Preparing opponent reports before a playoff series. Needs to quickly find which opponent lineups are tactically vulnerable and under what conditions.

Goals:
- Find the opponent's most-used trios and their baseline performance
- Identify trios with the largest performance drop under specific matchup archetypes
- Search for a specific player's trios
- Determine which Lakers lineup archetype to deploy against a vulnerable trio

Technical comfort: moderate — expects a clean UI, not raw data tables.

---

## Design Language (Global)

Applied across all phases. Establish these as Tailwind CSS config tokens in Phase 4.

```
Background (page):       #0A0A0A
Card background:         #1A1A2E  (deep navy)
Sidebar background:      #111111
Primary accent:          #552583  (Lakers purple)
Secondary accent:        #FDB927  (Lakers gold)
Text primary:            #FFFFFF
Text secondary:          #A0A0B0
Border / divider:        #2A2A3E
Danger / mismatch:       #E53935  (red)
Warning:                 #FFB300  (amber)
Success:                 #43A047  (green)
Chip active fill:        #FDB927
Chip inactive fill:      #2A2A3E
```

---

## Non-Functional Requirements (Global)

| Requirement | Target |
|---|---|
| Dashboard initial load | < 2 seconds |
| Filter toggle response | < 1 second |
| Detail modal open | < 500ms |
| Trio Net Rating accuracy | Within ±1.0 of manual reference |
| Possession count accuracy | Within ±2% of official box score |
| Lineup reconstruction coverage | ≥ 98% of events with valid 5-player state |

---

## Phase 1: Data Foundation

**Goal:** Stand up the full data pipeline. By the end of this phase, the PostgreSQL database is seeded with raw PBP data for all 5 target teams, lineup state is reconstructed for every event, and boolean filter flags are tagged. No analytics or API yet — just clean, queryable data.

### 1.1 Project Setup

```
backend/
├── manage.py
├── config/
│   ├── settings.py       # env-based config (DB, API keys, DEBUG)
│   ├── urls.py
│   └── wsgi.py
├── ingestion/            # all pipeline code lives here
│   ├── management/commands/
│   ├── models.py
│   └── nba_client.py
└── analytics/            # stubbed out, populated in Phase 2
```

- Django project with PostgreSQL connection via `dj-database-url` and `.env` file
- `requirements.txt` with pinned versions for `nba_api`, `django`, `psycopg2-binary`, `djangorestframework`

### 1.2 Data Source

`nba_api` — unofficial Python wrapper for `stats.nba.com`. Free, no key required. Endpoints used:

| Endpoint | Purpose |
|---|---|
| `LeagueGameFinder` | Game IDs for all 6 tracked teams |
| `PlayByPlayV2` | Full play-by-play per game |
| `CommonPlayerInfo` | Height per player |
| `PlayerDashboardByGeneralSplits` | Season 3P% and 3PA |
| `CommonTeamRoster` | Active rosters for all 6 teams (5 opponents + Lakers) |
| `BoxScoreTraditionalV2` | Box score totals for possession count validation |

### 1.3 Rate Limiting Strategy

`stats.nba.com` blocks aggressive requests. Since this is a manually-triggered nightly batch and speed is irrelevant:

- **2.0s fixed sleep** between every API call
- **Exponential backoff** on 4xx/5xx: retry at 5s → 15s → 60s, then abort and log
- **Raw JSON cache**: every response saved to `/data/raw/{endpoint}/{id}.json` before processing. Re-runs never need to re-fetch
- **Incremental pull**: check DB for the latest `game_date` per team, only fetch games after that date
- **User-Agent spoofing**: set a browser-like `User-Agent` header on every request

Initial full-season pull: ~2–4 hours at 2s/call. Subsequent nightly runs: a few minutes for the day's new games.

**Ingestion command sequence (run manually):**
```bash
python manage.py fetch_players      # height + 3P% for all 6 rosters
python manage.py fetch_games        # new game IDs since last run
python manage.py fetch_pbp          # PBP for new games (rate-limited)
python manage.py compute_lineups    # lineup reconstruction + flag tagging
```

Each command is idempotent — safe to run twice.

### 1.4 Database Schema

```sql
-- All players across 5 opponent teams + Lakers
players (
  player_id        INTEGER PRIMARY KEY,   -- stats.nba.com ID
  full_name        TEXT NOT NULL,
  team_id          INTEGER,
  height_inches    INTEGER,               -- derived: "6-10" → 82
  position         TEXT,
  is_active        BOOLEAN DEFAULT TRUE
)

-- Season 3P% per player (for Shooters filter)
player_season_stats (
  player_id        INTEGER REFERENCES players(player_id),
  season           TEXT,                  -- "2025-26"
  three_point_pct  DECIMAL(5,3),
  three_point_att  INTEGER,               -- must be >= 82 to qualify
  updated_at       TIMESTAMP,
  PRIMARY KEY (player_id, season)
)

-- One row per game involving a tracked team
games (
  game_id                      TEXT PRIMARY KEY,
  game_date                    DATE NOT NULL,
  home_team_id                 INTEGER,
  away_team_id                 INTEGER,
  season                       TEXT,
  pace                         DECIMAL(6,2),   -- possessions per 48 min
  low_confidence_reconstruction BOOLEAN DEFAULT FALSE,
  ingested_at                  TIMESTAMP
)

-- One row per PBP event — the core analytical table
pbp_events (
  event_id           BIGSERIAL PRIMARY KEY,
  game_id            TEXT REFERENCES games(game_id),
  period             INTEGER,
  clock_seconds      INTEGER,            -- seconds remaining in period
  event_type         TEXT,              -- SHOT, REBOUND, TURNOVER, FT, SUB, etc.
  event_msg_type     INTEGER,           -- raw NBA event code
  team_id            INTEGER,
  player_id          INTEGER,
  points_scored      INTEGER DEFAULT 0,
  score_home         INTEGER,
  score_away         INTEGER,
  score_margin       INTEGER,           -- home - away (signed)
  home_lineup        JSONB,             -- sorted [player_id × 5]
  away_lineup        JSONB,             -- sorted [player_id × 5]

  -- Boolean filter flags (tagged by compute_lineups)
  opp_is_big_lineup     BOOLEAN,        -- opponent has >= 2 players >= 82 inches
  opp_is_shooter_lineup BOOLEAN,        -- opponent has >= 3 players with 3P% >= 35%
  opp_is_smallball      BOOLEAN,        -- opponent has no player >= 81 inches (6'9")
  is_clutch             BOOLEAN,        -- last 5 min 4Q/OT, ABS(score_margin) <= 5
  is_fast_game          BOOLEAN,        -- game pace > team's season-median pace
  is_slow_game          BOOLEAN         -- game pace < team's season-median pace
)

-- Indexes
CREATE INDEX idx_pbp_game_id      ON pbp_events (game_id);
CREATE INDEX idx_pbp_home_lineup  ON pbp_events USING GIN (home_lineup);
CREATE INDEX idx_pbp_away_lineup  ON pbp_events USING GIN (away_lineup);
CREATE INDEX idx_pbp_flags        ON pbp_events (
  opp_is_big_lineup, opp_is_shooter_lineup, opp_is_smallball,
  is_clutch, is_fast_game, is_slow_game
);
```

**Why boolean flags (not a materialized table):** 6 combinable filters = 2^6 = 64 combinations. Pre-computing all combinations is impractical. Tagging each event once at ingestion time means any combination is a simple multi-column AND query on indexed booleans. For 185k events this is instantaneous.

### 1.5 Lineup Reconstruction (`compute_lineups`)

Iterates each game's PBP chronologically, maintaining a live set of 5 active player IDs per team via substitution events. Tags filter flags on each event.

```python
# Pseudocode
for game in unprocessed_games:
    home_lineup = set(get_starters(game, home_team))
    away_lineup = set(get_starters(game, away_team))

    for event in game.pbp_events.order_by('period', 'clock_seconds DESC', 'event_id'):
        if event.event_type == 'SUBSTITUTION':
            lineup = home_lineup if event.team == home_team else away_lineup
            lineup.discard(event.player_out)
            lineup.add(event.player_in)

        event.home_lineup = sorted(home_lineup)
        event.away_lineup = sorted(away_lineup)

        opp_lineup = away_lineup if event.team == home_team else home_lineup
        event.opp_is_big_lineup     = count_bigs(opp_lineup) >= 2        # height >= 82
        event.opp_is_shooter_lineup = count_shooters(opp_lineup) >= 3    # 3P% >= 35%, 82+ 3PA
        event.opp_is_smallball      = max_height(opp_lineup) < 81        # no player >= 6'9"
        event.is_clutch             = (event.period >= 4
                                       and event.clock_seconds <= 300
                                       and abs(event.score_margin) <= 5)
        event.is_fast_game          = game.pace > game.team_season_median_pace
        event.is_slow_game          = game.pace < game.team_season_median_pace
        event.save()
```

**Edge cases:**
- **Missing starters**: Infer from first 5 players who appear in any period-1 event
- **Period breaks**: Reset lineup inference at the start of each new period
- **Ejections / injuries**: Treated as implicit substitution when player stops appearing
- **Low confidence**: If a reconstructed lineup has ≠ 5 players for > 2% of events in a game, set `games.low_confidence_reconstruction = TRUE` and exclude that game from analytics

### 1.6 Phase 1 Definition of Done

- [ ] Django project runs locally, connects to PostgreSQL
- [ ] All 4 models exist with migrations applied
- [ ] `fetch_players` pulls height + 3P% for all 6 rosters
- [ ] `fetch_games` pulls all 2025–26 game IDs for 5 target teams + Lakers
- [ ] `fetch_pbp` pulls and caches raw PBP JSON for all games; incremental re-runs work
- [ ] `compute_lineups` tags all 6 boolean flags on every event
- [ ] Lineup state is valid (5 players per side) for ≥ 98% of events
- [ ] Spot-check: query possession counts for 2 known trios, compare against Basketball Reference within ±2%

---

## Phase 2: Analytics Engine

**Goal:** Implement the two core engines — trio stat aggregation and filter querying. By the end of this phase, you can query any trio's ORtg/DRtg/Net Rating under any combination of the 6 filters from the Django shell. No API or UI yet.

### 2.1 Possession Calculation (Hollinger Formula)

All possession-based stats use the industry-standard Hollinger estimation applied at the aggregate level over events where the trio was on court:

```
Possessions ≈ FGA − OREB + TOV + (0.44 × FTA)
```

This is the same methodology used by Basketball Reference. Accurate to ±2% of official box score totals. Avoids the complexity of per-event ball-possession attribution.

**Pace** (possessions per 48 min) is computed per game and stored in `games.pace`. Track Meet / Grind filter thresholds use each team's own season-median pace — not the league median.

### 2.2 Trio Engine (`analytics/engines/trio_engine.py`)

Enumerates all valid 3-man combinations (≥ 100 possessions together) for a given team and computes baseline and filtered stats.

```python
def compute_trio_stats(
    team_id: int,
    trio_player_ids: list[int],
    filter_kwargs: dict
) -> dict:
    """
    Returns ORtg, DRtg, Net Rating for a trio under optional filter conditions.
    filter_kwargs is empty for baseline, or contains flag conditions for filtered view.
    """
    lineup_field = 'home_lineup' if team_is_home else 'away_lineup'

    events = PBPEvent.objects.filter(
        **{f'{lineup_field}__contains': trio_player_ids},
        **filter_kwargs
    )

    # Hollinger components — trio's offensive possessions
    fga  = events.filter(event_msg_type=SHOT).count()
    oreb = events.filter(event_msg_type=REBOUND, is_offensive=True).count()
    tov  = events.filter(event_msg_type=TURNOVER).count()
    fta  = events.filter(event_msg_type=FREE_THROW).count()
    pts  = events.aggregate(Sum('points_scored'))['points_scored__sum'] or 0

    poss = fga - oreb + tov + (0.44 * fta)
    ortg = round((pts / poss) * 100, 1) if poss > 0 else None

    # DRtg: opponent's possessions during the same on-court window
    opp_field = 'away_lineup' if team_is_home else 'home_lineup'
    opp_events = PBPEvent.objects.filter(
        **{f'{opp_field}__contains': trio_player_ids},  # trio still on court
        **filter_kwargs
    )
    # ... same Hollinger logic on opponent events
    drtg = ...

    return {
        'ortg': ortg, 'drtg': drtg,
        'net': round(ortg - drtg, 1),
        'possessions': int(poss),
    }
```

### 2.3 Filter Engine (`analytics/engines/filter_engine.py`)

Translates a list of active filter names into Django ORM kwargs. All filters are ANDed.

```python
FILTER_MAP = {
    'big':       {'opp_is_big_lineup': True},
    'shooters':  {'opp_is_shooter_lineup': True},
    'smallball': {'opp_is_smallball': True},
    'clutch':    {'is_clutch': True},
    'fast':      {'is_fast_game': True},
    'slow':      {'is_slow_game': True},
}

def build_filter_kwargs(active_filters: list[str]) -> dict:
    kwargs = {}
    for f in active_filters:
        kwargs.update(FILTER_MAP[f])
    return kwargs
```

### 2.4 The 6 Lineup Archetype Filters

| Filter | Label | Icon | Condition | Basketball Rationale |
|---|---|---|---|---|
| `big` | Wall | ⛰ | Opponent has ≥ 2 players ≥ 6'10" (82 in) | Tests if a trio collapses against physical interior pressure |
| `shooters` | Shooters | 🎯 | Opponent has ≥ 3 players with 3P% ≥ 35% and ≥ 82 3PA | Tests if a defense can close out without giving up the paint |
| `smallball` | Small Ball | ⚡ | Opponent has no player ≥ 6'9" (81 in) | Tests if big-heavy trios can defend in space and in transition |
| `clutch` | Clutch | ⏱ | Last 5 min of 4Q or OT, score margin ≤ 5 (NBA official) | Isolates high-leverage playoff moments |
| `fast` | Track Meet | 🏃 | Game pace > team's season-median pace | Reveals tempo vulnerability for half-court dominant trios |
| `slow` | Grind | 💪 | Game pace < team's season-median pace | Reveals half-court durability for run-and-gun dependent trios |

### 2.5 Counter-Lineup Recommendation Logic

Used in the detail modal (Phase 4). Determines the single biggest tactical vulnerability:

```python
ARCHETYPE_LABELS = {
    'big':       'BIG LINEUP',
    'shooters':  'SHOOTING LINEUP',
    'smallball': 'SMALL-BALL LINEUP',
    'clutch':    'CLUTCH LINEUP',
    'fast':      'FAST-PACE LINEUP',
    'slow':      'HALF-COURT LINEUP',
}

def get_counter_recommendation(trio_key: str, baseline_net: float) -> dict | None:
    worst_delta = 0
    worst_filter = None

    for filter_name in FILTER_MAP:
        result = compute_trio_stats(..., filter_kwargs=build_filter_kwargs([filter_name]))
        if result['possessions'] < 50:
            continue
        delta = result['net'] - baseline_net
        if delta < worst_delta:
            worst_delta = delta
            worst_filter = filter_name

    if worst_filter is None or worst_delta > -2:
        return None

    return {
        'archetype': ARCHETYPE_LABELS[worst_filter],
        'filter': worst_filter,
        'delta': worst_delta,
        'filtered_net': baseline_net + worst_delta,
    }
```

### 2.6 Phase 2 Definition of Done

- [ ] `trio_engine.py` enumerates all 3-man combos per team with ≥ 100 possessions
- [ ] Baseline ORtg/DRtg/Net for known trios verified within ±1.0 of manual reference
- [ ] `filter_engine.py` correctly ANDs any combination of the 6 filters
- [ ] `get_counter_recommendation` returns correct worst-delta filter for test cases
- [ ] All 6 filter flags validated against known game events

---

## Phase 3: REST API

**Goal:** Expose the analytics engine over HTTP so the React frontend can consume it. By the end of this phase, all endpoints return correct JSON and are queryable from a browser or curl.

### 3.1 Django App Structure (complete)

```
backend/
├── ingestion/          # Phase 1 — data pipeline
├── analytics/          # Phase 2 — engines and models
└── api/
    ├── views.py
    ├── serializers.py
    └── urls.py
```

### 3.2 Endpoints

| Method | Endpoint | Response |
|---|---|---|
| GET | `/api/teams/` | List of 5 teams with `team_id`, `name`, `abbreviation` |
| GET | `/api/teams/{team_id}/trios/` | All qualifying trios with baseline metrics |
| GET | `/api/trios/{trio_key}/` | Full detail: baseline + all 6 filter results pre-computed |
| GET | `/api/trios/{trio_key}/?filters=big,clutch` | Stats for a specific filter combination |
| GET | `/api/meta/freshness/` | `{"last_game_date": "...", "ingested_at": "..."}` |

**`trio_key` format:** sorted player IDs joined by underscores — `203999_1629029_1630192`. Deterministic and order-independent.

**Example response — `/api/teams/1610612743/trios/`:**
```json
[
  {
    "trio_key": "203999_1629029_1630192",
    "players": [
      {"player_id": 203999, "name": "Nikola Jokic",    "headshot_url": "https://cdn.nba.com/headshots/nba/latest/260x190/203999.png"},
      {"player_id": 1629029, "name": "Jamal Murray",   "headshot_url": "..."},
      {"player_id": 1630192, "name": "Michael Porter", "headshot_url": "..."}
    ],
    "baseline": {
      "ortg": 118.4, "drtg": 110.2, "net": 8.2, "possessions": 1240
    }
  }
]
```

**Example response — `/api/trios/{key}/?filters=big,clutch`:**
```json
{
  "trio_key": "...",
  "baseline": {"ortg": 118.4, "drtg": 110.2, "net": 8.2, "possessions": 1240},
  "filtered": {"ortg": 101.1, "drtg": 108.3, "net": -7.2, "possessions": 28},
  "delta": {"ortg": -17.3, "drtg": -1.9, "net": -15.4},
  "low_confidence": true,
  "active_filters": ["big", "clutch"]
}
```

`low_confidence: true` is set when filtered possessions < 50.

### 3.3 Phase 3 Definition of Done

- [ ] Django REST Framework installed and configured
- [ ] All 5 endpoints return correct JSON
- [ ] `low_confidence` flag correctly set when possessions < 50
- [ ] Filter combinations work correctly via query string
- [ ] CORS configured for `http://localhost:5173` (Vite dev server)
- [ ] All endpoints respond in < 1 second on local machine

---

## Phase 4: Frontend

**Goal:** Build the complete React dashboard consuming the Phase 3 API. By the end of this phase, the full user-facing product is functional locally.

### 4.1 Tech Stack

- **React 18** with functional components and hooks
- **React Router v6** — client-side routing
- **Recharts** — DeltaBarChart
- **Axios** — API calls
- **Tailwind CSS** — styled with Lakers dark mode tokens (see Design Language)
- **Vite** — build tool / dev server

### 4.2 Application Structure

```
frontend/
├── src/
│   ├── main.jsx
│   ├── App.jsx              # Router setup
│   ├── api/
│   │   └── client.js        # Axios instance + endpoint functions
│   ├── components/
│   │   ├── SplashScreen/
│   │   ├── Layout/
│   │   │   ├── Sidebar.jsx
│   │   │   └── TopBar.jsx
│   │   ├── Dashboard/
│   │   │   ├── FilterBar.jsx
│   │   │   ├── SearchInput.jsx
│   │   │   ├── TrioGrid.jsx
│   │   │   └── TrioCard.jsx
│   │   └── TrioDetail/
│   │       ├── TrioDetailModal.jsx
│   │       ├── MetricsTable.jsx
│   │       ├── DeltaBarChart.jsx
│   │       ├── CounterLineup.jsx
│   │       └── SampleSizeWarning.jsx
│   └── pages/
│       └── TeamDashboard.jsx
├── tailwind.config.js       # Lakers color tokens
├── index.html
└── package.json
```

### 4.3 Page Flow

```
First load (no team selected)
  └── SplashScreen
        └── 5 team logo cards → click any → navigate to /team/:teamId

/team/:teamId
  └── Layout
        ├── Sidebar (team list, active team highlighted in purple)
        ├── TopBar (app title + DataFreshnessBadge)
        └── TeamDashboard
              ├── SearchInput (client-side player name filter)
              ├── FilterBar (6 chips + Baseline reset)
              └── TrioGrid
                    └── TrioCard × N → click → TrioDetailModal
```

### 4.4 Component Specifications

#### SplashScreen
- App name / wordmark centered
- Tagline: *"Identify exploitable lineup mismatches before they happen."*
- 5 team logo cards as clickable entry points (team colors as card accent)

#### TrioCard
Displayed in the TrioGrid. Shows without clicking:
- 3 circular headshots (40px) from `cdn.nba.com/headshots/nba/latest/260x190/{id}.png` — fallback generic avatar on 404
- 3 player last-name pills in caps
- Net Rating (large, green if positive / red if negative)
- Possession count in secondary text
- When filter active: a Delta badge bottom-right (e.g., `vs. Wall: −13.8` in red)

#### FilterBar
```
[ Baseline ]  [ ⛰ Wall ]  [ 🎯 Shooters ]  [ ⚡ Small Ball ]  [ ⏱ Clutch ]  [ 🏃 Track Meet ]  [ 💪 Grind ]
```
- Multiple chips selectable simultaneously (AND logic)
- Active chip: gold fill (`#FDB927`), black text
- Inactive chip: dark fill (`#2A2A3E`), white text
- Selecting any filter chip triggers grid re-sort: largest negative delta first
- "Baseline" button clears all chips, restores Net Rating sort

#### SearchInput
- Plain text input above the grid
- Filters displayed trios client-side by matching any player's name substring (case-insensitive)
- Does not trigger API calls

#### TrioDetailModal
Full-screen overlay opened on card click:

1. **HeadshotRow** — 3 circular player photos (64px) + full names
2. **MetricsComparisonTable** — Baseline vs. filtered (or all 6 if no filter active):
   ```
   ┌─────────────┬──────────┬────────────┬──────────┐
   │ Metric      │ Baseline │ vs. Wall   │ Delta    │
   ├─────────────┼──────────┼────────────┼──────────┤
   │ ORtg        │  118.4   │   109.2    │  -9.2 ▼  │
   │ DRtg        │  110.2   │   114.8    │  +4.6 ▲  │
   │ Net Rating  │  +8.2    │   -5.6     │  -13.8 ▼ │
   │ Possessions │  1,240   │    312     │  —       │
   └─────────────┴──────────┴────────────┴──────────┘
   ```
   Delta color coding: red > 5pt drop, amber 2–5pt, green neutral/positive

3. **SampleSizeWarning** — rendered per-row when possessions < 50:  
   `⚠ Low confidence (18 poss)` — values shown at reduced opacity

4. **DeltaBarChart** — horizontal Recharts bar chart:
   - Y-axis: Baseline + 6 filter contexts
   - X-axis: Net Rating
   - Bar color from delta severity (green/amber/red)
   - `ReferenceLine` at baseline Net Rating value
   - Tooltip: exact Net Rating + possession count

5. **CounterLineupRecommendation** — callout box below the chart:
   ```
   ┌──────────────────────────────────────────────────┐
   │  ▲ RECOMMENDED DEPLOYMENT                        │
   │  Run a BIG LINEUP against this trio.             │
   │  Net Rating: +8.2 baseline → -5.6 vs. Wall       │
   │  Delta: -13.8  (312 possessions)                 │
   └──────────────────────────────────────────────────┘
   ```
   Hidden if no filter has ≥ 50 possessions and a negative delta > 2.

#### DataFreshnessBadge
In the TopBar. Calls `/api/meta/freshness/` on load:
- `"Data through Apr 2, 2026 · Updated 6h ago"` — green dot
- `"Last update > 48h ago"` — amber dot

### 4.5 Phase 4 Definition of Done

- [ ] Vite + React + Tailwind scaffold with Lakers color tokens
- [ ] SplashScreen with 5 team entry points
- [ ] Sidebar + TopBar layout renders on all team pages
- [ ] TrioGrid loads and displays trios from API
- [ ] TrioCards show headshots with fallback avatar
- [ ] SearchInput filters trios by player name (client-side)
- [ ] FilterBar: multi-chip toggle, AND logic, Baseline reset
- [ ] Grid re-sorts correctly when filters are active (delta desc)
- [ ] TrioDetailModal opens on card click
- [ ] MetricsComparisonTable shows correct baseline vs. filtered delta
- [ ] Delta color coding is correct (red/amber/green)
- [ ] SampleSizeWarning renders at correct opacity for < 50 poss
- [ ] DeltaBarChart renders all 7 contexts with correct bar colors
- [ ] CounterLineupRecommendation shows correct archetype label
- [ ] DataFreshnessBadge reflects live ingestion timestamp

---

## Phase 5: Polish & Portfolio

**Goal:** Validate accuracy end-to-end, clean up rough edges, and prepare the project for GitHub as a portfolio piece.

### 5.1 Accuracy Validation

- [ ] Cross-check Net Rating for 5 well-known trios (one per team) against Basketball Reference  
      Target: within ±1.0 Net Rating points
- [ ] Validate possession counts for the same trios against official box scores  
      Target: within ±2%
- [ ] Confirm all 6 filter flags fire correctly on at least 2 known game events each
- [ ] Confirm `low_confidence_reconstruction` is set correctly on any flagged games

### 5.2 UX Polish

- [ ] Loading states: skeleton cards while API responds
- [ ] Empty state: "No trios found matching your search" when search yields nothing
- [ ] Zero-data filter state: "No possessions match this combination" when filtered result is null
- [ ] Error state: graceful message if API is unreachable

### 5.3 Portfolio Preparation

- [ ] `README.md` — technical audience, assumes basketball knowledge:
  - Architecture overview with diagram
  - Local setup instructions (Python env, DB, ingestion commands)
  - Data pipeline walkthrough
  - Filter definitions with basketball rationale
  - Screenshot of the dashboard
- [ ] GIF or screen recording of the filter interaction flow (core demo clip)
- [ ] `requirements.txt` with pinned versions
- [ ] `.env.example` with all required environment variables documented

### 5.4 Phase 5 Definition of Done

- [ ] All accuracy targets met
- [ ] All empty/error states handled
- [ ] README complete and renders correctly on GitHub
- [ ] Demo GIF embedded in README
- [ ] No console errors in the browser on any core interaction

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `stats.nba.com` blocks scraping | Medium | High | Raw JSON cache means re-processing never needs re-fetching. Initial pull is the only exposure window. |
| Lineup reconstruction inaccurate (missing SUB events) | Medium | High | Flag and exclude games where reconstructed lineup ≠ 5 players for > 2% of events. Log for manual review. |
| Small sample sizes under combined filters | High | Medium | Grayed stats + ⚠ badge. Scout sees the data but visual treatment signals low confidence. |
| `nba_api` breaks due to NBA site changes | Low | High | Pin library version. Raw JSON already cached — re-parsing doesn't require re-fetching. |
| Pace filter not discriminating enough | Low | Medium | Validate pace distribution per team. If variance is too low, switch to quarter-level pace segmentation. |
| Filter combination yields 0 possessions | Medium | Low | API returns `{"possessions": 0, "result": null}`. UI shows "No data for this combination." |

---

## Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| Filter combinability | AND logic, combinable | "Clutch + Big" is more valuable than either alone for playoff prep |
| Low-sample UI | Grayed stats + ⚠ badge at < 50 poss | Visible but de-emphasized; scout decides how to weigh it |
| Counter-lineup depth | Archetype label only | The archetype signal is the insight; naming players is out of scope |
| Styling | Tailwind CSS | Faster to build; matches job description |
| Auth | None | Portfolio project; auth adds no analytical value |
| Pre-computation | Boolean flags on `pbp_events` | Supports all 64 filter combinations with simple indexed AND queries |
| Trio card content | Names + headshots + Net Rating | Clean scanning; headshots are portfolio-presentable |
| Export | None in v1 | Screenshots sufficient; v2 feature |
| Game type | Regular season only | Cleaner scope; consistent data volume |
| FilterBar design | Pill/chip toggles with icons | Visually clear multi-select state |
| Grid pagination | None | 10–30 trios per team is a small enough list to render all at once |
| Grid sort | Net Rating desc (default); delta desc (filter active) | Best trios first; exploitable trios surface when filter applied |
| Chart type | Horizontal bar chart (Recharts) | Readable, standard analytics presentation |
| Headshots | Yes, NBA CDN URL pattern | Professional visual identity; no extra API calls |
| Ingestion trigger | Manual Django commands | Sufficient for a local portfolio project |
| Player search | Yes, client-side above grid | Key scout workflow shortcut |
| Landing state | Splash screen with 5 team entry points | Good for portfolio screenshots and demos |
| Possession method | Hollinger formula | Industry standard; avoids per-event attribution complexity |
| README audience | Technical (assumes basketball knowledge) | Target reviewer is in sports analytics |
| Clutch definition | NBA official: last 5 min of 4Q/OT, margin ≤ 5 | Consistent with industry standard |
| Pace threshold | Team's own season-median | Contextualizes each team against their own baseline |
| Minimum trio possessions | 100 | Balances noise vs. rotation coverage |
