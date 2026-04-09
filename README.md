# Wardrobe AI

Personalized wardrobe suggestions based on skin tone, weather/lighting, and color theory.

## Architecture

```
├── backend/          # Python FastAPI server
│   ├── app/
│   │   ├── core/         # Config, database
│   │   ├── models/       # SQLAlchemy models (User, WardrobeItem)
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── routers/      # API endpoints
│   │   └── services/     # Business logic
│   │       ├── color_extraction.py      # K-means color extraction from images
│   │       ├── color_recommendation.py  # Skin tone → color palette engine
│   │       ├── outfit_matcher.py        # Delta E color matching
│   │       └── weather.py              # OpenWeatherMap integration
│   └── tests/
├── frontend/         # React web app
│   └── src/
│       ├── pages/        # Onboarding, Wardrobe, Recommendation
│       └── services/     # API client
├── data/             # Color theory reference data
├── ml/               # Notebooks for experiments
├── scripts/          # Utility scripts
└── uploads/          # Uploaded wardrobe images
```

## How It Works

1. **Onboarding** — User selects their skin tone / color season
2. **Wardrobe Upload** — User photographs clothing items; the system extracts dominant colors using k-means clustering with background removal
3. **Recommendation** — The system combines the user's color season + current weather/lighting to recommend a color palette, then matches wardrobe items using Delta E perceptual color distance

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env to add your OpenWeatherMap API key (optional for dev)

# Run the server
uvicorn app.main:app --reload
```

API docs available at http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm start
```

App runs at http://localhost:3000

### Seed Database (optional)

```bash
python scripts/seed_db.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/` | Create user profile |
| GET | `/api/users/{id}` | Get user profile |
| PATCH | `/api/users/{id}` | Update user profile |
| POST | `/api/wardrobe/items` | Upload clothing item (multipart) |
| GET | `/api/wardrobe/items?user_id=` | List wardrobe items |
| DELETE | `/api/wardrobe/items/{id}` | Delete wardrobe item |
| GET | `/api/recommendations/colors?user_id=` | Get recommended colors |
| GET | `/api/recommendations/outfit?user_id=` | Get full outfit recommendation |

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **ML/CV**: scikit-learn (k-means), Pillow, rembg (background removal), colormath
- **Frontend**: React, React Router, Axios
- **Weather**: OpenWeatherMap API
