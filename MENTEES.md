# Mentee handoff — Wardrobe AI

The app runs end-to-end today: signup → onboarding → upload clothes → see
outfit suggestions → try-on with Gemini. Wherever a real database or ML
model belongs, the route shape and function signature already exist as a
**stub**. Your job is to swap the stubs for real implementations without
breaking the contracts the frontend relies on.

Every stub is marked with `TODO(mentee):`. Search for that string to find
the exact spots to work on.

---

## How to run it

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Add a .env with the Gemini key for try-on
echo 'GEMINI_API_KEY=...' > .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm start
# (uses port 3000 by default; PORT=3001 npm start if 3000 is taken)
```

API docs at <http://127.0.0.1:8000/docs>.

---

## Architecture

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, registers routers
│   ├── core/
│   │   ├── auth.py              # Bearer-token dependency
│   │   ├── security.py          # ⚠ STUB: token + password helpers
│   │   ├── store.py             # ⚠ STUB: in-memory dicts (replace with DB)
│   │   └── config.py            # env-driven settings (Gemini key, etc.)
│   ├── routers/
│   │   ├── auth.py              # /signup /login /me /login-history
│   │   ├── wardrobe.py          # /wardrobe/items, /wardrobe/body-photo
│   │   ├── outfits.py           # /outfits/suggestions
│   │   └── tryon.py             # /tryon/generate (Gemini, working)
│   └── services/
│       ├── categorizer.py       # ⚠ STUB: clothing-category classifier
│       ├── outfit_suggester.py  # ⚠ STUB: outfit recommender
│       └── color_extraction.py  # working (KMeans on PIL)
└── requirements.txt
```

```
frontend/src/
├── App.js                       # routes
├── components/AppShell.js       # nav + auth guard
├── pages/
│   ├── Door.js                  # intro (3D portal)
│   ├── Signup.js / Login.js     # auth pages
│   ├── Onboarding.js            # body photo + first uploads
│   ├── Wardrobe.js              # categorized grid
│   ├── Outfits.js               # suggestion cards
│   └── TryOn.js                 # single-viewport try-on
└── services/
    ├── api.js                   # fetch wrapper, token storage
    ├── auth.js, wardrobeApi.js, outfitsApi.js, tryon.js
```

---

## What's stubbed and where to plug in

### 1. Auth & user persistence — `backend/app/core/`

**Files:** `security.py`, `store.py`, `routers/auth.py`

Right now:
- "Token" = the username string. No JWT.
- "Hashed password" = `plain::<password>`.
- Users + login history live in dicts in `core/store.py` (lost on restart).

Replace with:
- **Real password hashing**: `passlib[bcrypt]` — swap `hash_password` / `verify_password` in `security.py`.
- **Real JWT**: `python-jose[cryptography]` — swap `create_token` / `decode_token` in `security.py`. Add a `JWT_SECRET` to `core/config.py` (env var).
- **Real DB**: SQLAlchemy models already exist under `app/models/user.py`. Replace the dict reads/writes in `core/store.py` with DB queries (or delete `store.py` entirely and rewrite each router function to use a `Session` dependency).

The router signatures (`POST /api/auth/signup`, etc.) and their JSON shapes are the contract. Don't change them — the frontend already speaks them.

### 2. Wardrobe categorizer — `backend/app/services/categorizer.py`

```python
def categorize_item(image: Image) -> dict[str, str]:
    return {"category": "top", "subcategory": "shirt"}
```

Right now everything is tagged "top/shirt". Categories the frontend
groups by: `top`, `bottom`, `outerwear`, `shoes`, `accessory`.

Two easy replacements:
- **FashionCLIP** — already wired up in `wardrobe/embeddings.py`. Embed
  the image, run cosine similarity against a list of category prompts
  ("a photo of a shirt", "a photo of pants", …), pick the best.
- **Gemini vision** — `gemini-2.5-flash` (or the already-configured
  image model). Send the image with a prompt like:
  > Classify this clothing item. Reply with strict JSON:
  > `{"category": "<top|bottom|outerwear|shoes|accessory>", "subcategory": "<one word>"}`

Keep the return shape the same — the wardrobe router writes both
`category` and `subcategory` straight to the item.

### 3. Outfit suggester — `backend/app/services/outfit_suggester.py`

```python
def suggest_outfits(items: list[dict], limit: int = 12) -> list[dict]
```

Stub does cross-product of tops × bottoms ranked by HSL color distance.
Returns `[{"top": <item>, "bottom": <item>, "score": float}, ...]`.

Two easy replacements:
- **FashionCLIP + FAISS** — `wardrobe/faiss_index.py` already exists.
  Build an index of "stylish outfit" examples (Polyvore, scraped looks,
  whatever you find), then for each user item find nearest matches.
- **Gemini stylist** — send the wardrobe to `gemini-2.5-flash` with a
  prompt like:
  > Here are the user's clothing items: `<json>`. Suggest 8 stylish
  > outfits. Reply JSON: `[{"top_id": "...", "bottom_id": "...",
  > "rationale": "..."}, ...]`.

You can extend the return shape (add `outerwear`, `shoes`, `rationale`)
— the frontend currently shows top + bottom + score, so adding fields
won't break it. If you remove `top`/`bottom`/`score`, you'll need to
update `frontend/src/pages/Outfits.js`.

### 4. Persistent file storage — `backend/app/routers/wardrobe.py`

Uploaded images are written to `settings.UPLOAD_DIR` on disk and served
by FastAPI's `StaticFiles`. For a real deploy you probably want S3 (or
Cloudflare R2, or local persistent volume). Swap the `_save_upload`
helper to upload to your bucket and return a public URL; the rest of the
code uses `image_url` as an opaque string and doesn't care.

### 5. Try-On (already working)

`backend/app/routers/tryon.py` already calls Gemini's image model
(`gemini-2.5-flash-image`). Set `GEMINI_API_KEY` in `backend/.env` and
it works. Nothing to do here unless you want to swap models or tune the
prompt — see `_PROMPT` at the top of the file.

---

## API contract (what NOT to change without telling the frontend)

```
POST /api/auth/signup           {username, email, password}    → {token, username}
POST /api/auth/login            {username, password}           → {token, username}
GET  /api/auth/me               (auth)                          → {username, email, created_at, has_body_photo}
GET  /api/auth/login-history    (auth)                          → [{logged_in_at, ip, user_agent}]

POST /api/wardrobe/items        (auth, multipart: image, [name], [category])
                                                                → {id, category, subcategory, image_url, dominant_colors, ...}
GET  /api/wardrobe/items        (auth)                          → [item]
DELETE /api/wardrobe/items/{id} (auth)                          → {detail}
POST /api/wardrobe/body-photo   (auth, multipart: image)        → {body_photo_url}
GET  /api/wardrobe/body-photo   (auth)                          → {body_photo_url}

GET  /api/outfits/suggestions   (auth)                          → [{top, bottom, score}]

POST /api/tryon/generate        (multipart: body_photo, top, bottom, [extra_instructions])
                                                                → image/png bytes
```

All authed endpoints expect `Authorization: Bearer <token>`.

---

## Suggested order of work

1. **Replace `core/security.py`** with real bcrypt + JWT. (Smallest blast
   radius — only touches token issuance/verification.)
2. **Replace `core/store.py`** with SQLAlchemy. Pick a DB (SQLite is
   easiest; the existing `docker-compose.yml` brings up Postgres if you'd
   rather). The Alembic setup in `backend/migrations/` is partly there —
   you'll need to recreate `env.py` and `script.py.mako` since they're
   gitignored.
3. **Replace `services/categorizer.py`** — get real categories flowing.
4. **Replace `services/outfit_suggester.py`** — actual recommendations.
5. **Move uploads off local disk** if deploying.

---

## Things deliberately left out

- No CSRF protection on auth — fine for a JWT-bearer setup but worth
  knowing.
- No rate limiting.
- Try-on doesn't currently require auth (the frontend has the token but
  the route doesn't check it). Add `Depends(get_current_user)` if you
  care about gating Gemini usage.
- The `data/`, `wardrobe/`, and `scripts/` directories at the repo root
  contain prior work (FashionCLIP embeddings, FAISS index, polyvore
  embedding script) — useful raw material for the categorizer + outfit
  suggester.

Questions? Find the `TODO(mentee):` markers and start there.
