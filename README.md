# FPL AI Recommendation System

A full-stack Fantasy Premier League recommendation system that suggests optimal transfers, captain picks, and rotation strategies using the official FPL API.

## Architecture

```
Browser  -->  React Frontend (UI)
                   |  HTTP
              Flask Backend (Orchestration)
                   |  Function calls
              Algorithm Module (Pure logic)
                   |  Function calls
              Data Fetcher (I/O)
                   |  HTTP
              FPL API (Official)
```

## Project Structure

```
FPL app/
├── data_fetcher.py        # FPL API data fetching + caching
├── algorithm.py           # Recommendation algorithms (stateless)
├── app.py                 # Flask REST API
├── requirements.txt       # Python dependencies
├── fpl_optimizer.html     # Standalone HTML prototype (no server needed)
└── frontend/
    ├── package.json
    ├── public/index.html
    └── src/
        ├── index.js
        ├── App.jsx        # Main React component
        ├── App.css        # Styles (dark theme)
        └── components/
            └── index.jsx  # Tab components
```

## Quick Start

### Option 1: HTML Prototype (instant, no setup)

Open `fpl_optimizer.html` in your browser. Uses demo data, no server required.

### Option 2: Full System

**Terminal 1 — Backend:**
```bash
pip install -r requirements.txt
python app.py
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm start
```

The backend runs at `http://localhost:5000`, frontend at `http://localhost:3000`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/settings` | GET/POST | Read/update settings |
| `/api/squad?team_id=X` | GET | Current squad with projections |
| `/api/player/<id>/stats?team_id=X` | GET | Player details |
| `/api/fixtures?team_id=X` | GET | Upcoming fixtures |
| `/api/recommendations?team_id=X` | GET | Transfer recommendations |
| `/api/captains?team_id=X` | GET | Captain picks |
| `/api/rotation?team_id=X` | GET | Rotation strategy |

## Algorithm

**Projected Points Formula:**
```
projected = (form * 0.6) + (form * (1 + fixture_adj) * 0.4)
```

- **Form (60%)** — Points per game from FPL API
- **Fixture Difficulty (40%)** — Scaled by opponent difficulty (1-5): `adj = (3 - difficulty) * 0.1`
- **Status adjustments** — Unavailable x0.5, Doubtful x0.7, Injured/Suspended x0.0

**Transfer Logic:**
1. Rank squad by projected points (weakest first)
2. Find best replacement at same position within budget
3. Apply -4 pt penalty for transfers beyond 2 free
4. Only recommend if net gain > 0

**Rotation:** Greedy formation selection (1 GK, 4 DEF, 5 MID, 1 FWD) per gameweek, captain = highest projected in XI.

## Features

- 5 tabs: Squad, Transfers, Captain, Rotation, Settings
- Dark theme UI with responsive design
- Configurable lookahead period (1-10 GWs) and max transfers (1-5)
- 5-minute data caching with JSON fallback
- Standalone HTML prototype with demo data

## Tech Stack

- **Backend:** Python 3.8+, Flask, Requests
- **Frontend:** React 18, Tailwind CSS
- **Data:** Official FPL API (https://fantasy.premierleague.com/api/)
