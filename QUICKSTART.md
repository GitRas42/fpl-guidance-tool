# FPL AI Recommender — Quick Start

## Instant Demo (no setup)

1. Open `fpl_optimizer.html` in your browser
2. Browse the 5 tabs: Squad, Transfers, Captain, Rotation, Settings
3. Adjust settings (sliders) to see recommendations update

## Full System Setup (5 minutes)

### Prerequisites
- Python 3.8+
- Node.js 16+

### Step 1: Backend

```bash
pip install -r requirements.txt
python app.py
```

You should see:
```
==================================================
FPL AI Recommendation System
API running at http://localhost:5000
==================================================
```

### Step 2: Frontend

```bash
cd frontend
npm install
npm start
```

React dev server opens at http://localhost:3000.

### Step 3: Use

1. Find your FPL team ID at https://fantasy.premierleague.com (go to "My Team", the number in the URL is your team ID)
2. Enter it in the Team ID field and click "Load Data"
3. Browse tabs for recommendations

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Backend won't start | Check Python version: `python --version` (need 3.8+) |
| Frontend won't start | Run `npm install` in the `frontend/` directory |
| "team_id is required" | Enter your FPL team ID in the input field |
| Data not loading | FPL API may be down during gameweek updates; try again later |
| CORS errors | Make sure backend is running on port 5000 |
