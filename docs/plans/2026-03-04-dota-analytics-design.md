# Dota 2 Friend Group Analytics — Design Document

## Overview

Build a data-driven analytics platform for a group of 11 Dota 2 friends that scrapes all available data from the OpenDota API, performs EDA and ML analysis, and presents fun + competitive insights via an interactive HTML playground.

## Players

| Name | OpenDota Account ID |
|------|-------------------|
| bread | 107007554 |
| cremfresh | 1254415 |
| Breaze | 99686578 |
| Freecss | 110926483 |
| Maegix | 107872884 |
| Imi bne | 140869118 |
| Kob | 139410877 |
| harry ron | 107969010 |
| rabbs | 482479226 |
| Saic | 138451133 |
| Bartolomeo | 86098817 |

Primary user: harry ron (107969010), but all analysis is group-centric.

## Architecture: Python + Playground

- **Data collection**: Python scripts using `requests` to fetch from OpenDota API
- **Storage**: Raw JSON in `data/raw/`, processed CSV/Parquet in `data/processed/`
- **Analysis**: Python with pandas, numpy, scikit-learn
- **Frontend**: Playground skill — interactive single-file HTML dashboard with embedded JSON data

## Data Collection

### Per-player endpoints (all-time, no filters):
1. `/players/{id}` — profile, rank, avatar
2. `/players/{id}/wl` — win/loss totals
3. `/players/{id}/heroes` — per-hero games/wins
4. `/players/{id}/matches` — full match history (All Pick + Turbo filtered)
5. `/players/{id}/peers` — peer win rates (with/against)
6. `/players/{id}/totals` — aggregate stats (kills, deaths, GPM, etc.)
7. `/players/{id}/counts` — breakdowns by game mode, region, lane role
8. `/players/{id}/rankings` — hero percentile rankings
9. `/players/{id}/recentMatches` — last 20 matches with rich data
10. `/players/{id}/wardmap` — ward placement patterns
11. `/players/{id}/wordcloud` — chat word frequency
12. `/players/{id}/histograms/{field}` — stat distributions

### Shared match data:
- Cross-reference match histories to find all matches where 2+ friends played together
- Fetch full match details (`/matches/{id}`) for shared matches — items, timelines, benchmarks, teamfights

### Reference data:
- `/heroes` — hero list with attributes and roles
- `/heroStats` — global pick/win rates by bracket
- `/heroes/{id}/matchups` — hero vs hero win rates

### Rate limiting:
- Free tier: 60 req/min, 50K/month
- Implement 1-second delay between calls
- Cache all responses to avoid re-fetching

## Analysis Plan

### Time Tiers
All analysis runs at three time windows for comparison:
- **All-time** — historical bragging rights
- **Last 2 years** — semi-relevant meta
- **Last 1 year** — current form

### Individual Player Insights
- Hero mastery profiles (signature heroes, comfort picks, win rates)
- Role tendencies (carry/support/mid flexibility)
- Performance trends over time
- Stat distributions (kills, deaths, GPM, XPM)

### Superlatives & Awards (data-backed memes)
- "The Feeder" — highest average deaths
- "One Trick Pony" — most games on a single hero
- "Tryhard" — most ranked games played
- "Late Night Warrior" — highest % of games after midnight
- "Comeback King" — most wins from behind
- "First Blood Magnet" — most first deaths
- "The Carry" — highest avg GPM
- "Ward Bot" — most observer wards placed
- "GG Go Next" — shortest average game duration
- "Toxic Chat" — most all-chat messages
- "Hero Hopper" — most unique heroes played
- "Cliff Jungler" — longest average game with a loss
- And more discovered during EDA

### Pair/Duo Insights
- Win rate heatmap for every friend pair
- Best/worst duo combos
- Hero synergies per duo (Player A on hero X + Player B on hero Y)
- "Carry Me" index — who benefits most from a specific teammate
- Complementary playstyle analysis

### Team/Group Insights
- Optimal 5-stack composition (friends + heroes)
- Role coverage matrix — can the group fill all 5 positions?
- Party size effect on win rate (2-stack vs 3-stack vs 5-stack)
- Time-of-day performance patterns
- Day-of-week performance patterns
- Win streaks and loss streaks when playing together

### ML Models
- **Win prediction**: Given 5 friends + their hero picks → predicted win probability
- **Hero recommendation**: Given 4 picks, recommend the 5th hero
- **Feature importance**: What factors matter most for winning (GPM? deaths? hero synergy?)
- Features: player hero win rates, hero global win rates, hero synergy scores, player pair chemistry scores, role balance, time-of-day, party size

## Frontend (Playground)

### Sections:
1. **Group Overview** — Baseball card display for all 11 players (rank, top 3 heroes, win rate, avatar)
2. **Superlatives & Awards** — Fun data-backed awards with stat evidence
3. **Duo Chemistry** — Heatmap of pair win rates, click to drill into hero combos
4. **Dream Team Builder** — Select 5 friends, see recommended heroes + win prediction
5. **Hero Pool Explorer** — Per-player hero stats, recommendations
6. **Timeline** — Performance trends over time, streaks
7. **Head-to-Head** — Compare any two friends on all stats

### Implementation:
- Pre-compute all insights in Python
- Embed results as JSON in the HTML file
- Interactive controls (dropdowns, filters) powered by vanilla JS
- Charts via Chart.js or similar (embedded CDN)
- Responsive design for sharing with friends

## Project Structure

```
dota-analytics/
├── friends-steam-id.md
├── docs/plans/
├── data/
│   ├── raw/           # Raw API JSON responses
│   └── processed/     # Cleaned CSV/Parquet DataFrames
├── scripts/
│   ├── scrape.py      # Data collection from OpenDota API
│   ├── process.py     # Data cleaning and transformation
│   ├── eda.py         # Exploratory data analysis
│   ├── insights.py    # Generate computed insights
│   └── model.py       # ML model training
├── playground/        # Generated HTML playground(s)
└── requirements.txt
```
