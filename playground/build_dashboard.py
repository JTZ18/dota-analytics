#!/usr/bin/env python3
"""Build the Dota 2 Analytics Dashboard HTML file with embedded data."""
import json
import os

# Read the data
data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'frontend_data.min.json')
with open(data_path) as f:
    raw_json = f.read().strip()

# Verify it parses
data = json.loads(raw_json)
print(f"Data loaded: {len(raw_json)} bytes, {len(data.keys())} top-level keys")

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dota 2 Party Analytics</title>
<style>
/* ===== RESET & BASE ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 15px; }
body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #0f0f1a;
  color: #e0e0e0;
  min-height: 100vh;
  overflow-x: hidden;
}
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #1a1a2e; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #555; }

/* ===== HEADER ===== */
.header {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-bottom: 2px solid #d4a64e;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.header h1 {
  font-size: 1.4rem;
  color: #d4a64e;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  white-space: nowrap;
}
.header .subtitle {
  color: #888;
  font-size: 0.8rem;
  white-space: nowrap;
}

/* ===== TABS ===== */
.tabs {
  display: flex;
  gap: 2px;
  flex-wrap: wrap;
  flex: 1;
  justify-content: center;
}
.tab-btn {
  background: transparent;
  color: #aaa;
  border: none;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 6px 6px 0 0;
  transition: all 0.2s;
  white-space: nowrap;
}
.tab-btn:hover { color: #d4a64e; background: rgba(212,166,78,0.1); }
.tab-btn.active { color: #d4a64e; background: #16213e; border-bottom: 2px solid #d4a64e; }

/* ===== TIER SELECTOR ===== */
.tier-selector {
  display: flex;
  gap: 4px;
  margin: 16px 24px 0;
}
.tier-btn {
  background: #16213e;
  color: #aaa;
  border: 1px solid #333;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 0.8rem;
  border-radius: 4px;
  transition: all 0.2s;
}
.tier-btn:hover { border-color: #d4a64e; color: #d4a64e; }
.tier-btn.active { background: #d4a64e; color: #0f0f1a; border-color: #d4a64e; font-weight: 700; }

/* ===== CONTENT ===== */
.content {
  padding: 16px 24px 40px;
  max-width: 1600px;
  margin: 0 auto;
}
.tab-content { display: none; animation: fadeIn 0.3s ease; }
.tab-content.active { display: block; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.section-title {
  font-size: 1.6rem;
  color: #d4a64e;
  margin: 0 0 16px 0;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.section-desc {
  color: #888;
  margin-bottom: 20px;
  font-size: 0.9rem;
}

/* ===== CARDS ===== */
.card {
  background: #16213e;
  border-radius: 10px;
  border: 1px solid #222;
  padding: 16px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

/* ===== PLAYER CARDS GRID ===== */
.player-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.player-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.player-card .top-row {
  display: flex;
  gap: 12px;
  align-items: center;
}
.player-card .avatar {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  border: 2px solid #d4a64e;
  object-fit: cover;
  flex-shrink: 0;
}
.player-card .info { flex: 1; }
.player-card .name {
  font-size: 1.1rem;
  font-weight: 700;
  color: #fff;
}
.player-card .medal {
  font-size: 0.75rem;
  color: #d4a64e;
  margin-top: 2px;
}
.player-card .stats-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.stat-box {
  background: rgba(0,0,0,0.25);
  border-radius: 6px;
  padding: 6px 10px;
  text-align: center;
  flex: 1;
  min-width: 60px;
}
.stat-box .stat-label {
  font-size: 0.65rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.stat-box .stat-value {
  font-size: 1rem;
  font-weight: 700;
  font-family: 'Courier New', monospace;
}
.hero-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.hero-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  padding: 3px 8px;
  background: rgba(0,0,0,0.15);
  border-radius: 4px;
}
.hero-row .hero-name { color: #ccc; }
.hero-row .hero-stats { font-family: monospace; }

/* ===== WIN RATE COLORS ===== */
.wr-great { color: #4caf50; }
.wr-good { color: #7cb342; }
.wr-ok { color: #e88; }
.wr-bad { color: #f44336; }

/* ===== AWARD CARDS ===== */
.awards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.award-card {
  text-align: center;
  padding: 20px 16px;
  position: relative;
  overflow: hidden;
}
.award-card::before {
  content: '';
  position: absolute;
  top: -2px; left: -2px; right: -2px;
  height: 4px;
  background: linear-gradient(90deg, #d4a64e, #f0c674, #d4a64e);
  border-radius: 10px 10px 0 0;
}
.award-icon {
  font-size: 2.2rem;
  margin-bottom: 8px;
  display: block;
}
.award-title {
  font-size: 1rem;
  font-weight: 700;
  color: #d4a64e;
  margin-bottom: 4px;
}
.award-player {
  font-size: 1.2rem;
  font-weight: 800;
  color: #fff;
  margin-bottom: 4px;
}
.award-value {
  font-size: 1.4rem;
  font-weight: 700;
  font-family: monospace;
  color: #f0c674;
  margin-bottom: 4px;
}
.award-desc {
  font-size: 0.75rem;
  color: #888;
}

/* ===== HEATMAP ===== */
.heatmap-container {
  overflow-x: auto;
  margin-bottom: 24px;
}
.heatmap-table {
  border-collapse: collapse;
  margin: 0 auto;
}
.heatmap-table th {
  padding: 6px 4px;
  font-size: 0.7rem;
  color: #d4a64e;
  font-weight: 600;
  min-width: 52px;
}
.heatmap-table th.row-header {
  text-align: right;
  padding-right: 10px;
  min-width: 90px;
  color: #ccc;
}
.heatmap-table td {
  width: 52px;
  height: 42px;
  text-align: center;
  font-size: 0.75rem;
  font-family: monospace;
  font-weight: 700;
  border: 1px solid rgba(0,0,0,0.3);
  cursor: default;
  position: relative;
  transition: transform 0.1s;
}
.heatmap-table td:hover {
  outline: 2px solid #d4a64e;
  z-index: 1;
}
.heatmap-table td.diag {
  background: #1a1a2e !important;
  color: #444;
}
.duo-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-top: 24px;
}
.duo-section h3 {
  color: #d4a64e;
  margin-bottom: 10px;
  font-size: 1rem;
}
.duo-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 4px;
  margin-bottom: 4px;
  font-size: 0.85rem;
}
.duo-row:nth-child(even) { background: rgba(0,0,0,0.15); }
.duo-names { color: #ccc; }
.duo-stats { font-family: monospace; font-weight: 700; }

/* ===== TABLE ===== */
.data-table-wrapper { overflow-x: auto; }
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.data-table th {
  background: #1a1a2e;
  color: #d4a64e;
  padding: 10px 12px;
  text-align: left;
  font-weight: 700;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  position: sticky;
  top: 0;
}
.data-table th:hover { color: #f0c674; }
.data-table th .sort-arrow { margin-left: 4px; font-size: 0.7rem; }
.data-table td {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.data-table tr:hover td { background: rgba(212,166,78,0.06); }
.filter-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.filter-row label { color: #aaa; font-size: 0.85rem; }
.filter-select, .filter-input {
  background: #16213e;
  color: #e0e0e0;
  border: 1px solid #333;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
}

/* ===== CHART CONTAINERS ===== */
.chart-container {
  background: #16213e;
  border-radius: 10px;
  border: 1px solid #222;
  padding: 20px;
  margin-bottom: 20px;
}
.chart-title {
  color: #d4a64e;
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 12px;
}
svg text { font-family: system-ui, sans-serif; }

/* ===== TRENDS ===== */
.legend-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.8rem;
  background: rgba(0,0,0,0.2);
  transition: opacity 0.2s;
}
.legend-item.hidden { opacity: 0.3; }
.legend-swatch {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  flex-shrink: 0;
}

/* ===== HEAD TO HEAD ===== */
.h2h-selectors {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  align-items: center;
  flex-wrap: wrap;
}
.h2h-selectors label { color: #d4a64e; font-weight: 700; }
.h2h-vs {
  font-size: 1.6rem;
  color: #d4a64e;
  font-weight: 800;
}
.h2h-grid {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 0;
  align-items: start;
}
.h2h-player {
  text-align: center;
}
.h2h-player .h2h-avatar {
  width: 80px; height: 80px;
  border-radius: 50%;
  border: 3px solid #d4a64e;
  margin-bottom: 8px;
}
.h2h-player .h2h-name {
  font-size: 1.2rem; font-weight: 700; color: #fff;
}
.h2h-stats-col {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 16px;
  min-width: 120px;
  align-items: center;
}
.h2h-stat-label {
  font-size: 0.75rem;
  color: #888;
  text-transform: uppercase;
}
.h2h-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 0;
  align-items: center;
  width: 100%;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.h2h-val {
  font-family: monospace;
  font-size: 1.1rem;
  font-weight: 700;
  padding: 0 16px;
}
.h2h-val.left { text-align: right; }
.h2h-val.right { text-align: left; }
.h2h-val.winner { color: #4caf50; }
.h2h-val.loser { color: #888; }
.h2h-label {
  font-size: 0.75rem;
  color: #d4a64e;
  text-align: center;
  min-width: 100px;
  text-transform: uppercase;
  font-weight: 700;
}

/* ===== ROLE BAR ===== */
.role-bar-container {
  margin-top: 10px;
}
.role-bar-row {
  display: flex;
  align-items: center;
  margin-bottom: 3px;
  font-size: 0.75rem;
}
.role-bar-label {
  width: 70px;
  color: #aaa;
  text-align: right;
  padding-right: 8px;
  flex-shrink: 0;
}
.role-bar-track {
  flex: 1;
  height: 14px;
  background: rgba(0,0,0,0.3);
  border-radius: 3px;
  overflow: hidden;
}
.role-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s;
}

/* ===== WORD CLOUD ===== */
.wordcloud-area {
  min-height: 350px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px 14px;
  padding: 30px;
  background: rgba(0,0,0,0.2);
  border-radius: 10px;
}
.wc-word {
  display: inline-block;
  transition: transform 0.2s, color 0.2s;
  cursor: default;
  line-height: 1.2;
}
.wc-word:hover { transform: scale(1.15); }

/* ===== TOOLTIP ===== */
.tooltip {
  position: fixed;
  background: #222;
  color: #e0e0e0;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  pointer-events: none;
  z-index: 1000;
  border: 1px solid #d4a64e;
  display: none;
  max-width: 250px;
}

/* ===== ML SECTION ===== */
.ml-metrics {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.ml-metric-card {
  background: rgba(0,0,0,0.25);
  border-radius: 8px;
  padding: 16px 24px;
  text-align: center;
}
.ml-metric-card .metric-val {
  font-size: 1.8rem;
  font-weight: 800;
  font-family: monospace;
  color: #d4a64e;
}
.ml-metric-card .metric-label {
  font-size: 0.75rem;
  color: #888;
  text-transform: uppercase;
  margin-top: 4px;
}
.rec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.rec-card { padding: 14px; }
.rec-card .rec-player {
  font-size: 1rem;
  font-weight: 700;
  color: #d4a64e;
  margin-bottom: 8px;
}
.rec-hero-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 0.82rem;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.rec-hero-name { color: #ccc; }
.rec-hero-wr { font-family: monospace; font-weight: 700; }
.rec-hero-games { color: #888; font-size: 0.75rem; font-family: monospace; }

/* ===== RESPONSIVE ===== */
@media (max-width: 1200px) {
  .player-grid { grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
  .duo-section { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<div class="tooltip" id="tooltip"></div>

<div class="header">
  <h1>Dota 2 Analytics</h1>
  <span class="subtitle">Party Dashboard</span>
  <nav class="tabs" id="tabs">
    <button class="tab-btn active" data-tab="overview">Overview</button>
    <button class="tab-btn" data-tab="awards">Awards</button>
    <button class="tab-btn" data-tab="duo">Duo Chemistry</button>
    <button class="tab-btn" data-tab="synergies">Hero Synergies</button>
    <button class="tab-btn" data-tab="dreamteam">Dream Team</button>
    <button class="tab-btn" data-tab="trends">Trends</button>
    <button class="tab-btn" data-tab="time">Time Analysis</button>
    <button class="tab-btn" data-tab="h2h">Head to Head</button>
    <button class="tab-btn" data-tab="wordcloud">Word Cloud</button>
  </nav>
</div>

<div class="tier-selector" id="tierSelector">
  <button class="tier-btn active" data-tier="all">All Time</button>
  <button class="tier-btn" data-tier="2y">Last 2 Years</button>
  <button class="tier-btn" data-tier="1y">Last 1 Year</button>
</div>

<div class="content">
  <!-- OVERVIEW -->
  <div class="tab-content active" id="tab-overview">
    <h2 class="section-title">Player Overview</h2>
    <p class="section-desc">Baseball cards for the whole squad. Stats update based on selected time period.</p>
    <div class="player-grid" id="playerGrid"></div>
  </div>

  <!-- AWARDS -->
  <div class="tab-content" id="tab-awards">
    <h2 class="section-title">Superlatives &amp; Awards</h2>
    <p class="section-desc">Who stands out? Achievement badges based on career stats.</p>
    <div class="awards-grid" id="awardsGrid"></div>
  </div>

  <!-- DUO CHEMISTRY -->
  <div class="tab-content" id="tab-duo">
    <h2 class="section-title">Duo Chemistry</h2>
    <p class="section-desc">Win rate heatmap for every player pair. Hover for game counts.</p>
    <div class="heatmap-container" id="heatmapContainer"></div>
    <div class="duo-section" id="duoSection"></div>
  </div>

  <!-- HERO SYNERGIES -->
  <div class="tab-content" id="tab-synergies">
    <h2 class="section-title">Hero Synergies</h2>
    <p class="section-desc">Top 100 hero combos by two players. Filter by player, sort by column.</p>
    <div class="filter-row" id="synergyFilters"></div>
    <div class="data-table-wrapper">
      <table class="data-table" id="synergyTable">
        <thead><tr>
          <th data-col="player1">Player 1 <span class="sort-arrow"></span></th>
          <th data-col="hero1">Hero 1 <span class="sort-arrow"></span></th>
          <th data-col="player2">Player 2 <span class="sort-arrow"></span></th>
          <th data-col="hero2">Hero 2 <span class="sort-arrow"></span></th>
          <th data-col="games">Games <span class="sort-arrow"></span></th>
          <th data-col="wins">Wins <span class="sort-arrow"></span></th>
          <th data-col="win_rate">Win Rate <span class="sort-arrow"></span></th>
        </tr></thead>
        <tbody id="synergyBody"></tbody>
      </table>
    </div>
  </div>

  <!-- DREAM TEAM -->
  <div class="tab-content" id="tab-dreamteam">
    <h2 class="section-title">Dream Team &mdash; ML Insights</h2>
    <p class="section-desc">Machine learning model for win prediction and hero recommendations.</p>
    <div class="ml-metrics" id="mlMetrics"></div>
    <div class="chart-container">
      <div class="chart-title">Feature Importances</div>
      <div id="featureChart"></div>
    </div>
    <h3 style="color:#d4a64e;margin:20px 0 12px;">Hero Recommendations Per Player</h3>
    <div class="rec-grid" id="recGrid"></div>
  </div>

  <!-- TRENDS -->
  <div class="tab-content" id="tab-trends">
    <h2 class="section-title">Performance Trends</h2>
    <p class="section-desc">Monthly win rate over time. Toggle players to compare.</p>
    <div class="legend-grid" id="trendsLegend"></div>
    <div class="chart-container">
      <div id="trendsChart"></div>
    </div>
  </div>

  <!-- TIME ANALYSIS -->
  <div class="tab-content" id="tab-time">
    <h2 class="section-title">Time Analysis</h2>
    <p class="section-desc">When does the squad play best? Win rate by hour and day of week.</p>
    <div class="chart-container">
      <div class="chart-title">Win Rate by Hour of Day</div>
      <div id="hourChart"></div>
    </div>
    <div class="chart-container">
      <div class="chart-title">Win Rate by Day of Week</div>
      <div id="dayChart"></div>
    </div>
  </div>

  <!-- HEAD TO HEAD -->
  <div class="tab-content" id="tab-h2h">
    <h2 class="section-title">Head to Head</h2>
    <p class="section-desc">Compare any two players side by side.</p>
    <div class="h2h-selectors" id="h2hSelectors"></div>
    <div id="h2hContent"></div>
  </div>

  <!-- WORD CLOUD -->
  <div class="tab-content" id="tab-wordcloud">
    <h2 class="section-title">Word Cloud</h2>
    <p class="section-desc">Top chat words for each player.</p>
    <div class="filter-row" id="wcSelector"></div>
    <div class="wordcloud-area" id="wcArea"></div>
  </div>
</div>

<script>
// ===== EMBEDDED DATA =====
const DATA = %%DATA_PLACEHOLDER%%;

// ===== GLOBALS =====
let currentTier = 'all';
let currentTab = 'overview';
let synergySort = { col: 'win_rate', asc: false };
let trendsVisible = {};
const PLAYER_COLORS = [
  '#e6194b','#3cb44b','#ffe119','#4363d8','#f58231',
  '#911eb4','#42d4f4','#f032e6','#bfef45','#fabed4','#469990'
];

// ===== UTILITY =====
function wrClass(wr) {
  if (wr >= 0.55) return 'wr-great';
  if (wr >= 0.50) return 'wr-good';
  if (wr >= 0.45) return 'wr-ok';
  return 'wr-bad';
}
function pct(v) { return (v * 100).toFixed(1) + '%'; }
function dec(v, d=2) { return Number(v).toFixed(d); }

function medalName(rt) {
  if (rt == null || rt === 'None' || rt === '') return 'Uncalibrated';
  const n = Math.round(Number(rt));
  if (isNaN(n) || n <= 0) return 'Uncalibrated';
  const medals = { 1:'Herald',2:'Guardian',3:'Crusader',4:'Archon',5:'Legend',6:'Ancient',7:'Divine',8:'Immortal' };
  const tier = Math.floor(n / 10);
  const stars = n % 10;
  const m = medals[tier] || '?';
  if (tier === 8) return m;
  return m + ' ' + stars;
}

function showTooltip(e, html) {
  const t = document.getElementById('tooltip');
  t.innerHTML = html;
  t.style.display = 'block';
  t.style.left = (e.clientX + 12) + 'px';
  t.style.top = (e.clientY - 10) + 'px';
}
function hideTooltip() {
  document.getElementById('tooltip').style.display = 'none';
}

function wrColor(wr) {
  if (wr >= 0.55) return '#4caf50';
  if (wr >= 0.52) return '#7cb342';
  if (wr >= 0.50) return '#a0a040';
  if (wr >= 0.48) return '#c87040';
  if (wr >= 0.45) return '#e88';
  return '#f44336';
}

function heatColor(wr) {
  // red(0.3) -> yellow(0.5) -> green(0.7)
  if (wr == null) return '#1a1a2e';
  const clamped = Math.max(0.3, Math.min(0.7, wr));
  const t = (clamped - 0.3) / 0.4; // 0..1
  let r, g, b;
  if (t < 0.5) {
    const u = t / 0.5;
    r = 200;
    g = Math.round(60 + 140 * u);
    b = 60;
  } else {
    const u = (t - 0.5) / 0.5;
    r = Math.round(200 - 140 * u);
    g = 200;
    b = 60;
  }
  return `rgb(${r},${g},${b})`;
}

// ===== TAB SWITCHING =====
document.getElementById('tabs').addEventListener('click', e => {
  const btn = e.target.closest('.tab-btn');
  if (!btn) return;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const tab = btn.dataset.tab;
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  currentTab = tab;
});

// ===== TIER SWITCHING =====
document.getElementById('tierSelector').addEventListener('click', e => {
  const btn = e.target.closest('.tier-btn');
  if (!btn) return;
  document.querySelectorAll('.tier-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentTier = btn.dataset.tier;
  renderOverview();
  renderAwards();
  renderTimeAnalysis();
});

// ===== 1. OVERVIEW =====
function renderOverview() {
  const grid = document.getElementById('playerGrid');
  grid.innerHTML = '';
  DATA.player_cards.forEach(p => {
    const t = p.tiers[currentTier];
    if (!t) return;
    const topH = (t.top_heroes || []).slice(0, 3);
    const card = document.createElement('div');
    card.className = 'card player-card';
    card.innerHTML = `
      <div class="top-row">
        <img class="avatar" src="${p.avatar}" alt="${p.name}" loading="lazy" onerror="this.style.display='none'">
        <div class="info">
          <div class="name">${p.name}</div>
          <div class="medal">${medalName(p.rank_tier)}</div>
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-box">
          <div class="stat-label">Games</div>
          <div class="stat-value">${t.total_games}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Win Rate</div>
          <div class="stat-value ${wrClass(t.win_rate)}">${pct(t.win_rate)}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">K/D/A</div>
          <div class="stat-value">${dec(t.avg_kills,1)}/${dec(t.avg_deaths,1)}/${dec(t.avg_assists,1)}</div>
        </div>
      </div>
      <div class="hero-list">
        ${topH.map(h => `
          <div class="hero-row">
            <span class="hero-name">${h.hero_name}</span>
            <span class="hero-stats ${wrClass(h.win_rate)}">${h.games}g ${pct(h.win_rate)}</span>
          </div>
        `).join('')}
      </div>
    `;
    grid.appendChild(card);
  });
}

// ===== 2. AWARDS =====
const awardIcons = {
  'The Feeder':'💀','Kill Stealer':'🗡️','The Supporter':'🤝','Iron Wall':'🛡️',
  'Glass Cannon':'💥','Party Animal':'🎉','Lone Wolf':'🐺','Biggest Winner':'🏆',
  'Biggest Loser':'📉','Hero Specialist':'🦸','Hero Dabbler':'🎲','KDA King':'👑',
  'Late Night Gamer':'🌙','Most Improved':'📈','Consistency King':'📊',
  'The Carry':'⚔️','Win Streak Hero':'🔥','Default':'🏅'
};
function getAwardIcon(title) {
  for (const [k,v] of Object.entries(awardIcons)) {
    if (title.toLowerCase().includes(k.toLowerCase())) return v;
  }
  return awardIcons.Default;
}
function renderAwards() {
  const grid = document.getElementById('awardsGrid');
  grid.innerHTML = '';
  const tierData = DATA.superlatives.find(s => s.tier === currentTier);
  if (!tierData) return;
  tierData.awards.forEach(a => {
    const card = document.createElement('div');
    card.className = 'card award-card';
    let valStr = typeof a.value === 'number' ?
      (a.stat && a.stat.includes('rate') ? pct(a.value) : dec(a.value, 2)) :
      String(a.value);
    card.innerHTML = `
      <span class="award-icon">${getAwardIcon(a.title)}</span>
      <div class="award-title">${a.title}</div>
      <div class="award-player">${a.player}</div>
      <div class="award-value">${valStr}</div>
      <div class="award-desc">${a.description}</div>
    `;
    grid.appendChild(card);
  });
}

// ===== 3. DUO CHEMISTRY =====
function renderDuo() {
  const container = document.getElementById('heatmapContainer');
  const hm = DATA.duo_chemistry.heatmap;
  const players = Object.keys(hm);

  let html = '<table class="heatmap-table"><thead><tr><th></th>';
  players.forEach(p => { html += `<th>${p}</th>`; });
  html += '</tr></thead><tbody>';

  players.forEach(p1 => {
    html += `<tr><th class="row-header">${p1}</th>`;
    players.forEach(p2 => {
      if (p1 === p2) {
        html += '<td class="diag">&mdash;</td>';
      } else {
        const d = hm[p1] && hm[p1][p2];
        if (d && d.with_games > 0) {
          const wr = d.with_win_rate;
          html += `<td style="background:${heatColor(wr)};color:#000;font-weight:800"
            onmouseenter="showTooltip(event,'${p1} + ${p2}<br>${d.with_games} games, ${pct(wr)} WR')"
            onmouseleave="hideTooltip()">${pct(wr)}</td>`;
        } else {
          html += '<td style="background:#1a1a2e;color:#444">-</td>';
        }
      }
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  container.innerHTML = html;

  // Best & worst
  const ds = document.getElementById('duoSection');
  let bHtml = '<div><h3>Best Duos</h3>';
  DATA.duo_chemistry.best_duos.forEach(d => {
    bHtml += `<div class="duo-row"><span class="duo-names">${d.player1} + ${d.player2}</span>
      <span class="duo-stats wr-great">${d.games}g &nbsp; ${pct(d.win_rate)}</span></div>`;
  });
  bHtml += '</div><div><h3>Worst Duos</h3>';
  DATA.duo_chemistry.worst_duos.forEach(d => {
    bHtml += `<div class="duo-row"><span class="duo-names">${d.player1} + ${d.player2}</span>
      <span class="duo-stats wr-bad">${d.games}g &nbsp; ${pct(d.win_rate)}</span></div>`;
  });
  bHtml += '</div>';
  ds.innerHTML = bHtml;
}

// ===== 4. HERO SYNERGIES =====
function getUniquePlayers() {
  const s = new Set();
  DATA.hero_synergies.forEach(h => { s.add(h.player1); s.add(h.player2); });
  return [...s].sort();
}
let synergyFilter1 = '', synergyFilter2 = '';
function renderSynergyFilters() {
  const f = document.getElementById('synergyFilters');
  const players = getUniquePlayers();
  const opts = '<option value="">All</option>' + players.map(p => `<option value="${p}">${p}</option>`).join('');
  f.innerHTML = `
    <label>Player 1:</label><select class="filter-select" id="synF1">${opts}</select>
    <label>Player 2:</label><select class="filter-select" id="synF2">${opts}</select>
  `;
  document.getElementById('synF1').addEventListener('change', e => { synergyFilter1 = e.target.value; renderSynergyTable(); });
  document.getElementById('synF2').addEventListener('change', e => { synergyFilter2 = e.target.value; renderSynergyTable(); });
}
function renderSynergyTable() {
  let data = [...DATA.hero_synergies];
  if (synergyFilter1) data = data.filter(d => d.player1 === synergyFilter1 || d.player2 === synergyFilter1);
  if (synergyFilter2) data = data.filter(d => d.player1 === synergyFilter2 || d.player2 === synergyFilter2);

  const col = synergySort.col;
  data.sort((a, b) => {
    let va = a[col], vb = b[col];
    if (typeof va === 'string') { va = va.toLowerCase(); vb = vb.toLowerCase(); }
    if (va < vb) return synergySort.asc ? -1 : 1;
    if (va > vb) return synergySort.asc ? 1 : -1;
    return 0;
  });

  const tbody = document.getElementById('synergyBody');
  tbody.innerHTML = data.map(d => `<tr>
    <td>${d.player1}</td><td>${d.hero1}</td>
    <td>${d.player2}</td><td>${d.hero2}</td>
    <td style="font-family:monospace">${d.games}</td>
    <td style="font-family:monospace">${d.wins}</td>
    <td class="${wrClass(d.win_rate)}" style="font-family:monospace;font-weight:700">${pct(d.win_rate)}</td>
  </tr>`).join('');

  // Update sort arrows
  document.querySelectorAll('#synergyTable th').forEach(th => {
    const arrow = th.querySelector('.sort-arrow');
    if (th.dataset.col === synergySort.col) {
      arrow.textContent = synergySort.asc ? '▲' : '▼';
    } else {
      arrow.textContent = '';
    }
  });
}
document.getElementById('synergyTable').querySelector('thead').addEventListener('click', e => {
  const th = e.target.closest('th');
  if (!th || !th.dataset.col) return;
  if (synergySort.col === th.dataset.col) synergySort.asc = !synergySort.asc;
  else { synergySort.col = th.dataset.col; synergySort.asc = false; }
  renderSynergyTable();
});

// ===== 5. DREAM TEAM =====
function renderDreamTeam() {
  const ml = DATA.ml;
  const m = ml.win_predictor.metrics;

  // Metrics
  document.getElementById('mlMetrics').innerHTML = `
    <div class="ml-metric-card"><div class="metric-val">${pct(m.accuracy)}</div><div class="metric-label">Accuracy</div></div>
    <div class="ml-metric-card"><div class="metric-val">${pct(m.win_rate_baseline)}</div><div class="metric-label">Baseline WR</div></div>
    <div class="ml-metric-card"><div class="metric-val">${m.n_samples.toLocaleString()}</div><div class="metric-label">Samples</div></div>
    <div class="ml-metric-card"><div class="metric-val">${m.n_features}</div><div class="metric-label">Features</div></div>
    <div class="ml-metric-card"><div class="metric-val">${m.cv_folds}</div><div class="metric-label">CV Folds</div></div>
    <div class="ml-metric-card"><div class="metric-val">&plusmn;${pct(m.std)}</div><div class="metric-label">Std Dev</div></div>
  `;

  // Feature importances horizontal bar chart
  const fi = ml.win_predictor.feature_importances;
  const entries = Object.entries(fi).sort((a,b) => b[1] - a[1]);
  const maxVal = entries[0][1];
  const barH = 28, barGap = 4, labelW = 160, chartW = 700, valW = 60;
  const svgH = entries.length * (barH + barGap) + 10;

  let svg = `<svg width="100%" viewBox="0 0 ${labelW + chartW + valW + 10} ${svgH}" style="max-width:900px">`;
  entries.forEach(([name, val], i) => {
    const y = i * (barH + barGap) + 5;
    const w = (val / maxVal) * chartW;
    svg += `<text x="${labelW - 6}" y="${y + barH/2 + 4}" text-anchor="end" fill="#ccc" font-size="12">${name}</text>`;
    svg += `<rect x="${labelW}" y="${y}" width="${w}" height="${barH}" rx="3" fill="#d4a64e"/>`;
    svg += `<text x="${labelW + w + 6}" y="${y + barH/2 + 4}" fill="#aaa" font-size="11" font-family="monospace">${(val*100).toFixed(1)}%</text>`;
  });
  svg += '</svg>';
  document.getElementById('featureChart').innerHTML = svg;

  // Hero recommendations
  const recGrid = document.getElementById('recGrid');
  recGrid.innerHTML = '';
  for (const [player, heroes] of Object.entries(ml.hero_recommendations)) {
    const card = document.createElement('div');
    card.className = 'card rec-card';
    card.innerHTML = `<div class="rec-player">${player}</div>` +
      heroes.slice(0, 8).map(h => `
        <div class="rec-hero-row">
          <span class="rec-hero-name">${h.hero_name}</span>
          <span class="rec-hero-games">${h.games}g</span>
          <span class="rec-hero-wr ${wrClass(h.win_rate)}">${pct(h.win_rate)}</span>
        </div>
      `).join('');
    recGrid.appendChild(card);
  }
}

// ===== 6. TRENDS =====
function renderTrends() {
  const container = document.getElementById('trendsChart');
  const legend = document.getElementById('trendsLegend');

  // Collect all months
  const allMonths = new Set();
  DATA.performance_trends.forEach(p => {
    p.months.forEach(m => allMonths.add(m.year_month));
  });
  const months = [...allMonths].sort();

  // Only show last 36 months for readability if there are many
  const displayMonths = months.length > 48 ? months.slice(-48) : months;

  // Init visibility
  if (Object.keys(trendsVisible).length === 0) {
    DATA.performance_trends.forEach((p, i) => {
      trendsVisible[p.player] = true;
    });
  }

  // Legend
  legend.innerHTML = '';
  DATA.performance_trends.forEach((p, i) => {
    const item = document.createElement('div');
    item.className = 'legend-item' + (trendsVisible[p.player] ? '' : ' hidden');
    item.innerHTML = `<div class="legend-swatch" style="background:${PLAYER_COLORS[i]}"></div><span>${p.player}</span>`;
    item.addEventListener('click', () => {
      trendsVisible[p.player] = !trendsVisible[p.player];
      renderTrends();
    });
    legend.appendChild(item);
  });

  // SVG chart
  const W = 1100, H = 400, padL = 50, padR = 20, padT = 20, padB = 80;
  const cW = W - padL - padR, cH = H - padT - padB;

  let svg = `<svg width="100%" viewBox="0 0 ${W} ${H}">`;

  // Grid lines + Y axis
  for (let wr = 0.3; wr <= 0.8; wr += 0.1) {
    const y = padT + cH - ((wr - 0.2) / 0.7) * cH;
    svg += `<line x1="${padL}" y1="${y}" x2="${W-padR}" y2="${y}" stroke="#333" stroke-width="0.5"/>`;
    svg += `<text x="${padL-6}" y="${y+4}" text-anchor="end" fill="#888" font-size="10">${(wr*100).toFixed(0)}%</text>`;
  }

  // 50% reference line
  const y50 = padT + cH - ((0.5 - 0.2) / 0.7) * cH;
  svg += `<line x1="${padL}" y1="${y50}" x2="${W-padR}" y2="${y50}" stroke="#d4a64e" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>`;

  // X axis labels (every 6 months)
  displayMonths.forEach((m, i) => {
    const x = padL + (i / (displayMonths.length - 1)) * cW;
    if (i % 6 === 0 || i === displayMonths.length - 1) {
      svg += `<text x="${x}" y="${H - padB + 20}" text-anchor="middle" fill="#888" font-size="9" transform="rotate(-45,${x},${H-padB+20})">${m}</text>`;
    }
  });

  // Lines per player
  DATA.performance_trends.forEach((p, pi) => {
    if (!trendsVisible[p.player]) return;
    const monthMap = {};
    p.months.forEach(m => { monthMap[m.year_month] = m; });

    // Build path with 3-month rolling average for smoothness
    const pts = [];
    displayMonths.forEach((m, i) => {
      const d = monthMap[m];
      if (d && d.games >= 3) {
        const x = padL + (i / (displayMonths.length - 1)) * cW;
        const y = padT + cH - ((d.win_rate - 0.2) / 0.7) * cH;
        pts.push({ x, y, wr: d.win_rate, games: d.games, month: m });
      }
    });

    if (pts.length < 2) return;
    let path = `M${pts[0].x},${pts[0].y}`;
    for (let i = 1; i < pts.length; i++) {
      path += ` L${pts[i].x},${pts[i].y}`;
    }
    svg += `<path d="${path}" fill="none" stroke="${PLAYER_COLORS[pi]}" stroke-width="2" opacity="0.8"/>`;

    // Dots
    pts.forEach(pt => {
      svg += `<circle cx="${pt.x}" cy="${pt.y}" r="3" fill="${PLAYER_COLORS[pi]}" opacity="0.9">
        <title>${p.player} | ${pt.month} | ${(pt.wr*100).toFixed(1)}% (${pt.games}g)</title></circle>`;
    });
  });

  svg += '</svg>';
  container.innerHTML = svg;
}

// ===== 7. TIME ANALYSIS =====
function renderTimeAnalysis() {
  const tp = DATA.time_patterns[currentTier];
  if (!tp) return;

  // Hour chart
  {
    const data = tp.by_hour;
    const W = 1100, H = 320, padL = 50, padR = 20, padT = 20, padB = 50;
    const cW = W - padL - padR, cH = H - padT - padB;
    const barW = cW / 24 - 2;
    const maxGames = Math.max(...data.map(d => d.games));

    let svg = `<svg width="100%" viewBox="0 0 ${W} ${H}">`;
    // Y gridlines
    for (let wr = 0.35; wr <= 0.65; wr += 0.05) {
      const y = padT + cH - ((wr - 0.3) / 0.4) * cH;
      svg += `<line x1="${padL}" y1="${y}" x2="${W-padR}" y2="${y}" stroke="#333" stroke-width="0.5"/>`;
      svg += `<text x="${padL-6}" y="${y+4}" text-anchor="end" fill="#888" font-size="10">${(wr*100).toFixed(0)}%</text>`;
    }
    // 50% line
    const y50 = padT + cH - ((0.5 - 0.3) / 0.4) * cH;
    svg += `<line x1="${padL}" y1="${y50}" x2="${W-padR}" y2="${y50}" stroke="#d4a64e" stroke-width="1" stroke-dasharray="4,4" opacity="0.5"/>`;

    data.forEach((d, i) => {
      const x = padL + (i / 24) * cW + 1;
      const wr = d.win_rate;
      const barH = ((wr - 0.3) / 0.4) * cH;
      const y = padT + cH - barH;
      svg += `<rect x="${x}" y="${y}" width="${barW}" height="${barH}" rx="2" fill="${wrColor(wr)}" opacity="0.85">
        <title>${d.hour}:00 | ${(wr*100).toFixed(1)}% WR | ${d.games} games</title></rect>`;
      svg += `<text x="${x + barW/2}" y="${H - padB + 16}" text-anchor="middle" fill="#888" font-size="9">${d.hour}</text>`;
    });
    svg += '</svg>';
    document.getElementById('hourChart').innerHTML = svg;
  }

  // Day chart
  {
    const data = tp.by_day_of_week;
    const W = 1100, H = 300, padL = 90, padR = 20, padT = 20, padB = 20;
    const cW = W - padL - padR, cH = H - padT - padB;
    const barH = cH / 7 - 4;

    let svg = `<svg width="100%" viewBox="0 0 ${W} ${H}">`;
    data.forEach((d, i) => {
      const y = padT + (i / 7) * cH + 2;
      const wr = d.win_rate;
      const barW = ((wr - 0.3) / 0.4) * cW;
      svg += `<text x="${padL - 8}" y="${y + barH/2 + 4}" text-anchor="end" fill="#ccc" font-size="12">${d.day_of_week}</text>`;
      svg += `<rect x="${padL}" y="${y}" width="${barW}" height="${barH}" rx="3" fill="${wrColor(wr)}" opacity="0.85">
        <title>${d.day_of_week} | ${(wr*100).toFixed(1)}% WR | ${d.games} games</title></rect>`;
      svg += `<text x="${padL + barW + 8}" y="${y + barH/2 + 4}" fill="#aaa" font-size="11" font-family="monospace">${(wr*100).toFixed(1)}% (${d.games}g)</text>`;
    });
    svg += '</svg>';
    document.getElementById('dayChart').innerHTML = svg;
  }
}

// ===== 8. HEAD TO HEAD =====
function renderH2HSelectors() {
  const sel = document.getElementById('h2hSelectors');
  const names = DATA.player_cards.map(p => p.name);
  const opts = names.map(n => `<option value="${n}">${n}</option>`).join('');
  sel.innerHTML = `
    <label>Player 1</label>
    <select class="filter-select" id="h2hP1">${opts}</select>
    <span class="h2h-vs">VS</span>
    <label>Player 2</label>
    <select class="filter-select" id="h2hP2">${names.map((n,i) => `<option value="${n}" ${i===1?'selected':''}>${n}</option>`).join('')}</select>
  `;
  document.getElementById('h2hP1').addEventListener('change', renderH2H);
  document.getElementById('h2hP2').addEventListener('change', renderH2H);
}

function renderH2H() {
  const p1Name = document.getElementById('h2hP1').value;
  const p2Name = document.getElementById('h2hP2').value;
  const cont = document.getElementById('h2hContent');

  if (p1Name === p2Name) {
    cont.innerHTML = '<p style="color:#888;text-align:center;padding:40px;">Select two different players.</p>';
    return;
  }

  const p1 = DATA.player_cards.find(p => p.name === p1Name);
  const p2 = DATA.player_cards.find(p => p.name === p2Name);
  if (!p1 || !p2) return;

  const t1 = p1.tiers[currentTier];
  const t2 = p2.tiers[currentTier];

  function compRow(label, v1, v2, higherBetter, fmt) {
    const f = fmt || (v => v);
    const w1 = higherBetter ? v1 > v2 : v1 < v2;
    const w2 = higherBetter ? v2 > v1 : v2 < v1;
    return `<div class="h2h-row">
      <div class="h2h-val left ${w1?'winner':'loser'}">${f(v1)}</div>
      <div class="h2h-label">${label}</div>
      <div class="h2h-val right ${w2?'winner':'loser'}">${f(v2)}</div>
    </div>`;
  }

  // Role profiles
  function roleBar(player) {
    const rp = DATA.role_profiles[player];
    if (!rp || !rp.role_weights) return '';
    const colors = { Carry:'#e6194b', Support:'#3cb44b', Nuker:'#f58231', Disabler:'#4363d8', Initiator:'#911eb4', Durable:'#42d4f4', Escape:'#f032e6', Pusher:'#bfef45' };
    let html = '<div class="role-bar-container">';
    const entries = Object.entries(rp.role_weights).sort((a,b) => b[1] - a[1]);
    entries.forEach(([role, weight]) => {
      html += `<div class="role-bar-row">
        <span class="role-bar-label">${role}</span>
        <div class="role-bar-track"><div class="role-bar-fill" style="width:${weight}%;background:${colors[role]||'#d4a64e'}"></div></div>
      </div>`;
    });
    html += '</div>';
    return html;
  }

  let html = `
    <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:0;max-width:900px;margin:0 auto;">
      <div class="h2h-player">
        <img class="h2h-avatar" src="${p1.avatar}" alt="${p1.name}" onerror="this.style.display='none'">
        <div class="h2h-name">${p1.name}</div>
        <div style="color:#d4a64e;font-size:0.8rem">${medalName(p1.rank_tier)}</div>
      </div>
      <div class="h2h-stats-col" style="padding-top:30px;">
        ${compRow('Games', t1.total_games, t2.total_games, true, v => v)}
        ${compRow('Win Rate', t1.win_rate, t2.win_rate, true, pct)}
        ${compRow('Avg Kills', t1.avg_kills, t2.avg_kills, true, v => dec(v,1))}
        ${compRow('Avg Deaths', t1.avg_deaths, t2.avg_deaths, false, v => dec(v,1))}
        ${compRow('Avg Assists', t1.avg_assists, t2.avg_assists, true, v => dec(v,1))}
      </div>
      <div class="h2h-player">
        <img class="h2h-avatar" src="${p2.avatar}" alt="${p2.name}" onerror="this.style.display='none'">
        <div class="h2h-name">${p2.name}</div>
        <div style="color:#d4a64e;font-size:0.8rem">${medalName(p2.rank_tier)}</div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:24px;max-width:900px;margin-left:auto;margin-right:auto;">
      <div>
        <h3 style="color:#d4a64e;margin-bottom:8px;font-size:0.95rem;">Top Heroes &mdash; ${p1.name}</h3>
        ${(t1.top_heroes||[]).slice(0,5).map(h => `
          <div class="hero-row"><span class="hero-name">${h.hero_name}</span>
          <span class="hero-stats ${wrClass(h.win_rate)}">${h.games}g ${pct(h.win_rate)}</span></div>
        `).join('')}
        <h3 style="color:#d4a64e;margin:16px 0 8px;font-size:0.95rem;">Role Profile</h3>
        ${roleBar(p1.name)}
      </div>
      <div>
        <h3 style="color:#d4a64e;margin-bottom:8px;font-size:0.95rem;">Top Heroes &mdash; ${p2.name}</h3>
        ${(t2.top_heroes||[]).slice(0,5).map(h => `
          <div class="hero-row"><span class="hero-name">${h.hero_name}</span>
          <span class="hero-stats ${wrClass(h.win_rate)}">${h.games}g ${pct(h.win_rate)}</span></div>
        `).join('')}
        <h3 style="color:#d4a64e;margin:16px 0 8px;font-size:0.95rem;">Role Profile</h3>
        ${roleBar(p2.name)}
      </div>
    </div>
  `;
  cont.innerHTML = html;
}

// ===== 9. WORD CLOUD =====
function renderWCSelector() {
  const sel = document.getElementById('wcSelector');
  const players = Object.keys(DATA.wordclouds);
  sel.innerHTML = `<label>Player:</label><select class="filter-select" id="wcPlayer">${players.map(p => `<option value="${p}">${p}</option>`).join('')}</select>`;
  document.getElementById('wcPlayer').addEventListener('change', renderWordCloud);
}

function renderWordCloud() {
  const player = document.getElementById('wcPlayer').value;
  const words = DATA.wordclouds[player];
  if (!words) return;
  const area = document.getElementById('wcArea');
  const maxCount = Math.max(...words.map(w => w.count));
  const minCount = Math.min(...words.map(w => w.count));

  const wcColors = ['#d4a64e','#f0c674','#e6194b','#3cb44b','#4363d8','#f58231','#911eb4','#42d4f4','#f032e6','#bfef45','#fabed4','#469990','#aaffc3','#ffe119','#e88'];

  area.innerHTML = words.map((w, i) => {
    const t = maxCount === minCount ? 1 : (w.count - minCount) / (maxCount - minCount);
    const size = 14 + t * 52;
    const color = wcColors[i % wcColors.length];
    const rotation = (Math.random() * 20 - 10).toFixed(0);
    return `<span class="wc-word" style="font-size:${size}px;color:${color};font-weight:${t > 0.5 ? 800 : 500};transform:rotate(${rotation}deg)" title="${w.word}: ${w.count} times">${w.word}</span>`;
  }).join('');
}

// ===== INIT =====
renderOverview();
renderAwards();
renderDuo();
renderSynergyFilters();
renderSynergyTable();
renderDreamTeam();
renderTrends();
renderTimeAnalysis();
renderH2HSelectors();
renderH2H();
renderWCSelector();
renderWordCloud();
</script>
</body>
</html>'''

# Build final HTML by embedding data
output = HTML_TEMPLATE.replace('%%DATA_PLACEHOLDER%%', raw_json)

out_path = os.path.join(os.path.dirname(__file__), 'dota-analytics.html')
with open(out_path, 'w') as f:
    f.write(output)

print(f"Dashboard written to {out_path}")
print(f"File size: {len(output):,} bytes")
