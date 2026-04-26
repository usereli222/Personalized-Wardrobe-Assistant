# Wardrobe AI — Setup & things to implement

Group handoff doc. Two halves:

1. **Setup** — get the app running on your machine in ~5 minutes.
2. **Things to implement** — the stubs that need real code, with
   step-by-step recipes (not just hints) so you can pick a task and ship.

If you only read one section, read **"Things to implement → pick what to
work on"** below. It tells you what's small, what's load-bearing, and
what depends on what.

---

## Part 1 — Setup (5 minutes)

### Prerequisites

- **Python 3.10+** (tested on 3.12)
- **Node 18+** (tested on 24)
- **A Gemini API key** — required for both try-on AND the auto-categorizer.
  Get one for free at <https://aistudio.google.com/apikey>. Ask Daniel
  for the demo key if you don't have your own yet.

### Clone and switch to the working branch

```bash
git clone https://github.com/usereli222/Personalized-Wardrobe-Assistant.git
cd Personalized-Wardrobe-Assistant
git checkout dx-edits
```

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Add the Gemini key
echo 'GEMINI_API_KEY=YOUR_KEY_HERE' > .env

# Run it
.venv/bin/uvicorn app.main:app --reload --port 8000
```

You should see `Uvicorn running on http://127.0.0.1:8000`. The interactive
API docs are at <http://127.0.0.1:8000/docs>.

### Frontend

In a **new terminal**:

```bash
cd Personalized-Wardrobe-Assistant/frontend
npm install
npm start
```

Auto-opens at <http://localhost:3000>. If port 3000 is busy:
`PORT=3001 npm start` — but if you change the port, also add it to the
CORS allowlist in `backend/app/main.py`.

### First-time demo (no setup data needed)

1. Open the frontend, click the door, then on the login page click
   **"✦ Use demo account"**. That auto-creates a `demo` account and
   drops you into onboarding.
2. **Step 1**: upload a full-body photo of yourself.
3. **Step 2**: upload a `.zip` containing one or more clothing photos
   (one image per item). The backend extracts each entry, sends it to
   Gemini, and stores them with predicted categories.
4. Click **Enter the Mirror** → you're on the wardrobe page.
5. Visit **Outfits** in the nav — auto-paired top/bottom suggestions.
   Click "Try this on" → you're on the try-on page with both pre-selected.
6. Hit **Try It On** → Gemini generates a photorealistic image of you in
   that outfit.

### Troubleshooting

| Symptom | Fix |
|---|---|
| `GEMINI_API_KEY is not configured` on try-on | Edit `backend/.env`, restart uvicorn (the env is read at startup, not on `--reload` of code changes) |
| 401 on every request after a backend restart | The in-memory user store was wiped. Click "Use demo account" again, or sign up. |
| `Login failed: Username already taken` | The demo account survives within one uvicorn run — just click "Step Inside" with `demo` / `demo` instead of "Use demo account". |
| CORS error in the browser console | Your frontend port isn't in the CORS allowlist. Add it to `backend/app/main.py`. |
| Categorizer puts everything as "top/shirt" | Either the Gemini key isn't set OR Gemini returned malformed JSON. Check uvicorn logs. The categorizer has a safe fallback by design. |

---

## Part 2 — Architecture (10-minute read)

### High level

```
[ Browser (React :3000) ] ──HTTP──> [ FastAPI :8000 ] ──> [ Gemini API ]
                                          │
                                          ├─ in-memory dicts (will become real DB)
                                          └─ uploads/ on disk (will become object storage)
```

### Backend layout

```
backend/app/
├── main.py                   FastAPI app, CORS, registers routers
├── core/
│   ├── config.py             Env-driven settings (Gemini key, models, etc.)
│   ├── database.py           SQLAlchemy engine + session factory (already wired,
│   │                         not currently used by routers)
│   ├── auth.py               get_current_user dependency (decodes bearer token)
│   ├── security.py           ⚠ STUB — token + password helpers
│   └── store.py              ⚠ STUB — in-memory dicts for users/items/login history
├── models/                   SQLAlchemy models (used once you switch on the DB)
├── routers/
│   ├── auth.py               POST /signup /login, GET /me /login-history
│   ├── wardrobe.py           CRUD on items, body photo upload, bulk zip upload
│   ├── outfits.py            GET /outfits/suggestions
│   └── tryon.py              POST /tryon/generate (calls Gemini image model)
├── services/
│   ├── categorizer.py        Gemini vision classifier — works, can be improved
│   ├── outfit_suggester.py   ⚠ STUB — color-distance pairing
│   └── color_extraction.py   KMeans on PIL — works
├── migrations/               Alembic — env.py is gitignored, you'll regenerate
└── requirements.txt
```

### Frontend layout

```
frontend/src/
├── App.js                    Routes (some auth-gated via AppShell)
├── components/AppShell.js    Header nav + RequireAuth guard
├── pages/
│   ├── Door.js               3D portal intro (Three.js)
│   ├── Login.js, Signup.js   Auth pages — Login has a demo-account button
│   ├── Onboarding.js         Body photo + zip upload
│   ├── Wardrobe.js           Categorized grid
│   ├── Outfits.js            Suggested combinations
│   └── TryOn.js              Single-viewport try-on UI (no page scroll)
└── services/
    ├── api.js                fetch wrapper, attaches Authorization header
    ├── auth.js               signup/login/logout/me
    ├── wardrobeApi.js        items + body photo + bulk upload
    ├── outfitsApi.js         suggestions
    └── tryon.js              try-on POST (multipart form)
```

### Auth flow today

1. User signs up or logs in via `/api/auth/{signup,login}`.
2. Backend returns `{ token, username }`. Right now `token === username`
   (no signing).
3. Frontend stores `token` in `localStorage`.
4. Every subsequent fetch sends `Authorization: Bearer <token>`.
5. Backend `get_current_user` decodes the token via `decode_token()` in
   `core/security.py` and looks up the user via `core/store.py`.

Once you implement Tasks 1+2 below, the only thing that changes is what
`security.py` does internally — the routers don't touch.

### Data flow today

- **User accounts + login history**: `core/store.py` module-level dicts.
- **Wardrobe items**: same dicts (per-user lists).
- **Uploaded image bytes**: written to `settings.UPLOAD_DIR`
  (`./uploads/` by default), served by FastAPI's `StaticFiles` at
  `/uploads/<filename>`.
- **Body photo path**: stored on the user dict in the in-memory store.

Everything except the on-disk image files dies on uvicorn restart. The
disk images linger but become orphans because the DB references are gone.

---

## Part 3 — Things to implement

### Pick what to work on

| # | Task | Size | Depends on | Why it matters |
|---|---|---|---|---|
| 1 | Real password hashing (bcrypt) | 15 min | — | Stops storing plaintext passwords |
| 2 | Real JWT tokens | 15 min | — | Stops anyone from forging tokens by typing a username |
| 3 | Real database (SQLAlchemy + SQLite) | 2-3 hrs | — | Survives restart; everything else gets easier after this |
| 4 | Persistent login history | 15 min | 3 | Now actually meaningful |
| 5 | Production file storage (S3 etc.) | 1 hr | optional | Required for real deployment |
| 6 | Better categorizer | 30 min – 2 hrs | — | Higher accuracy / works on harder photos |
| 7 | Real outfit suggester | 1-3 hrs | — | Make recommendations actually stylish |
| 8 | Deploy to Render or similar | 1-2 hrs | 3, ideally 5 | Demo it without everyone running it locally |

The big-bang task is **#3** (real DB). After that, #1, #2, #4 are
fast follow-ups. #6 and #7 are independent — anyone can grab them.

A hard rule across all tasks: **don't change the API contracts** in
"Part 4 — API contract" below without telling the team. The frontend
speaks them verbatim.

---

### Task 1 — Real password hashing

**File:** `backend/app/core/security.py`

**Why:** Right now `hash_password("foo")` returns `"plain::foo"`. Anyone
who reads the in-memory store sees passwords. We want a one-way hash
(bcrypt) so a leak doesn't reveal the actual password.

**Steps:**

1. Add to `backend/requirements.txt`:
   ```
   passlib[bcrypt]>=1.7.4
   ```
2. Install:
   ```bash
   cd backend && .venv/bin/pip install -r requirements.txt
   ```
3. Replace the two stub functions in `backend/app/core/security.py`:
   ```python
   from passlib.hash import bcrypt

   def hash_password(plain: str) -> str:
       return bcrypt.hash(plain)

   def verify_password(plain: str, hashed: str) -> bool:
       try:
           return bcrypt.verify(plain, hashed)
       except Exception:
           return False
   ```

**Verify:**

```bash
# Sign up
curl -sX POST http://127.0.0.1:8000/api/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","email":"a@x.com","password":"secret"}'
# → { "token": "...", "username": "alice" }

# Login with the right password works
curl -sX POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"secret"}'
# → 200, returns token

# Login with the wrong password fails
curl -isX POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"wrong"}'
# → 401 Invalid username or password
```

---

### Task 2 — Real JWT tokens

**Files:** `backend/app/core/security.py`, `backend/app/core/config.py`,
`backend/.env`

**Why:** Today the "token" is just the username string. There's no
signature, so a request like `Authorization: Bearer alice` is accepted
even if you never logged in. JWT signs the token with a server-side
secret, so forged tokens fail verification.

**Steps:**

1. Add to `backend/requirements.txt`:
   ```
   python-jose[cryptography]>=3.3.0
   ```
2. Install (`pip install -r requirements.txt`).
3. Add settings in `backend/app/core/config.py`:
   ```python
   class Settings(BaseSettings):
       # ...existing fields...
       JWT_SECRET: str = "change-me-in-production"
       JWT_TTL_DAYS: int = 7
   ```
4. Generate a real secret and add it to `backend/.env`:
   ```bash
   python3 -c 'import secrets; print("JWT_SECRET=" + secrets.token_urlsafe(48))' >> backend/.env
   ```
5. Replace the two stub functions in `backend/app/core/security.py`:
   ```python
   from datetime import datetime, timedelta, timezone
   from jose import jwt, JWTError
   from app.core.config import settings

   def create_token(username: str) -> str:
       payload = {
           "sub": username,
           "exp": datetime.now(timezone.utc) + timedelta(days=settings.JWT_TTL_DAYS),
       }
       return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

   def decode_token(token: str) -> str | None:
       try:
           payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
           return payload.get("sub")
       except JWTError:
           return None
   ```

**Verify:**

```bash
TOKEN=$(curl -sX POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"secret"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
echo $TOKEN
# Should look like: eyJhbGc...

# Real token works
curl -s http://127.0.0.1:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
# → { "username": "alice", ... }

# Forged token fails
curl -is http://127.0.0.1:8000/api/auth/me -H "Authorization: Bearer alice"
# → 401 Invalid token
```

---

### Task 3 — Real database (SQLAlchemy + SQLite)

**This is the big one.** It replaces `app/core/store.py` (in-memory dicts)
with real DB tables. After this, everything persists across restarts and
the rest of the tasks become trivial.

**Recommendation:** use **SQLite**. It's a single file, no docker
required, no separate server. The repo also has a `docker-compose.yml`
for Postgres if you'd rather use that — same SQLAlchemy code works for
both.

**Files you'll touch:**
- `backend/app/core/config.py` — change `DATABASE_URL` default
- `backend/app/core/database.py` — small SQLite tweak
- `backend/app/models/user.py` — add fields, drop firebase
- `backend/app/models/wardrobe.py` — add fields
- `backend/app/models/login_event.py` — **new file**
- `backend/app/main.py` — auto-create tables on startup
- `backend/app/core/store.py` — rewrite to use the DB
- All routers — accept a `db: Session` dependency

**Steps:**

1. **Switch the default DB to SQLite.** In `backend/app/core/config.py`:
   ```python
   DATABASE_URL: str = "sqlite:///./wardrobe.db"
   ```

2. **SQLite tweak in `backend/app/core/database.py`:**
   ```python
   connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
   engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
   ```

3. **Update `backend/app/models/user.py`:**
   - Add `username` column (unique, indexed, NOT NULL)
   - Add `password_hash` column (NOT NULL)
   - Add `body_photo_path` column (nullable)
   - Drop `firebase_uid` (we don't use Firebase anymore)

   ```python
   from sqlalchemy import Column, Integer, String, DateTime, func
   from app.core.database import Base

   class User(Base):
       __tablename__ = "users"
       id = Column(Integer, primary_key=True, index=True)
       username = Column(String, unique=True, nullable=False, index=True)
       email = Column(String, unique=True, nullable=False, index=True)
       password_hash = Column(String, nullable=False)
       body_photo_path = Column(String, nullable=True)
       created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
   ```

4. **Update `backend/app/models/wardrobe.py`:**
   - Add `subcategory` column
   - Add `created_at` column

5. **New file `backend/app/models/login_event.py`:**
   ```python
   from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
   from app.core.database import Base

   class LoginEvent(Base):
       __tablename__ = "login_events"
       id = Column(Integer, primary_key=True)
       user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
       logged_in_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
       ip = Column(String, nullable=True)
       user_agent = Column(String, nullable=True)
   ```

6. **Auto-create tables on startup.** Edit `backend/app/main.py`:
   ```python
   from app.core.database import Base, engine
   from app.models import user, wardrobe, login_event  # registers models with Base

   Base.metadata.create_all(bind=engine)
   ```
   (For dev. Production should use Alembic migrations — see "Going further" below.)

7. **Rewrite `backend/app/core/store.py`** to use the DB. Each function
   now takes a `Session`. Example:
   ```python
   from sqlalchemy.orm import Session
   from app.models.user import User
   from app.models.wardrobe import WardrobeItem
   from app.models.login_event import LoginEvent

   def create_user(db: Session, *, username: str, email: str, password_hash: str) -> User:
       user = User(username=username, email=email, password_hash=password_hash)
       db.add(user)
       db.commit()
       db.refresh(user)
       return user

   def get_user(db: Session, username: str) -> User | None:
       return db.query(User).filter(User.username == username).first()

   def record_login(db: Session, *, user_id: int, ip: str | None, user_agent: str | None) -> None:
       db.add(LoginEvent(user_id=user_id, ip=ip, user_agent=user_agent))
       db.commit()

   def get_login_history(db: Session, user_id: int) -> list[LoginEvent]:
       return (db.query(LoginEvent)
                 .filter(LoginEvent.user_id == user_id)
                 .order_by(LoginEvent.logged_in_at.desc())
                 .all())

   def add_wardrobe_item(db: Session, *, user_id: int, **fields) -> WardrobeItem:
       item = WardrobeItem(user_id=user_id, **fields)
       db.add(item)
       db.commit()
       db.refresh(item)
       return item

   # ...etc for list_wardrobe_items, delete_wardrobe_item, set_body_photo
   ```

8. **Update routers to inject `db`.** Each route handler gains:
   ```python
   from sqlalchemy.orm import Session
   from app.core.database import get_db

   @router.post("/signup")
   def signup(payload, request, db: Session = Depends(get_db)):
       if store.get_user(db, payload.username):
           raise HTTPException(409, "Username already taken")
       user = store.create_user(db, username=..., email=..., password_hash=hash_password(payload.password))
       store.record_login(db, user_id=user.id, ip=..., user_agent=...)
       return TokenOut(token=create_token(user.username), username=user.username)
   ```
   Apply the same pattern to every route currently calling `store.*`.

9. **Update `core/auth.py`** so `get_current_user` accepts a `db` and
   returns the SQLAlchemy `User` object (the routers already use
   `current_user.username` etc., which works on both dicts and ORM
   objects):
   ```python
   def get_current_user(
       creds = Depends(bearer_scheme),
       db: Session = Depends(get_db),
   ) -> User:
       # ...same checks...
       username = decode_token(creds.credentials)
       user = store.get_user(db, username)
       if not user:
           raise HTTPException(401, "User not found")
       return user
   ```
   Update each `current_user["username"]` access in the routers to
   `current_user.username` (Pydantic v2 ORM mode handles serialization
   if you use `model_config = {"from_attributes": True}` in your
   response schemas).

10. **Restart uvicorn.** A `wardrobe.db` file appears in `backend/`. Sign
    up. Stop uvicorn. Start it again. Log in with the same credentials.
    If it works, the DB is persisting.

**Verify:**
```bash
# Sign up
TOKEN=$(curl -sX POST http://127.0.0.1:8000/api/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"username":"persist","email":"p@x.com","password":"pw"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')

# Stop and restart uvicorn

# Log in
curl -sX POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"persist","password":"pw"}'
# → 200 with token (the "persist" user survived the restart)
```

**Pitfalls:**
- If you change a column after the DB exists, SQLite won't auto-migrate.
  Delete `wardrobe.db` and restart, or use Alembic.
- Don't forget to add `from app.models import login_event` (or wherever)
  in `main.py` — Base.metadata.create_all only knows about tables that
  have been imported.
- `pydantic.EmailStr` requires `pydantic[email]` (already in requirements).

**Going further:**
- Switch on Alembic for real migrations. The repo has `alembic.ini` and
  one initial migration. You'll need to recreate `migrations/env.py` (it's
  gitignored) — `alembic init migrations` regenerates it; then edit it to
  point `target_metadata = Base.metadata`.

---

### Task 4 — Persistent login history

If you finished Task 3, this is essentially done — just confirm the
endpoints return DB rows. The route in `backend/app/routers/auth.py`
should look like:

```python
@router.get("/login-history", response_model=list[LoginEventOut])
def login_history(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    events = store.get_login_history(db, current_user.id)
    return [LoginEventOut(logged_in_at=e.logged_in_at.isoformat(), ip=e.ip, user_agent=e.user_agent) for e in events]
```

**Verify:**
```bash
curl -s http://127.0.0.1:8000/api/auth/login-history -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Should show one entry per login (signup counts as a login too)
```

You can also surface this in the UI — add a "Recent logins" section to
the wardrobe page or a `/profile` page. The frontend service is already
there: `fetchLoginHistory()` in `frontend/src/services/auth.js`.

---

### Task 5 — Production file storage

Locally, uploaded images live in `./uploads/`. For a real deploy you have
three options:

**Option A: Local persistent disk** (Render, Fly.io)
- The simplest. Mount a persistent volume at the path `UPLOAD_DIR` points
  to. **No code changes** — `app.mount("/uploads", StaticFiles(...))`
  serves them as before.
- Works fine for a class project at small scale.

**Option B: S3 (or Cloudflare R2 / any S3-compatible)**
- Add `boto3>=1.34` to requirements.
- Replace `_save_upload` and `_ingest_image_bytes` in
  `backend/app/routers/wardrobe.py` to upload to S3 instead of disk:
  ```python
  import boto3
  from botocore.config import Config

  s3 = boto3.client("s3", region_name=settings.AWS_REGION,
                    config=Config(signature_version="s3v4"))

  def _save_upload(image: UploadFile) -> tuple[None, str]:
      ext = Path(image.filename or "").suffix.lower() or ".png"
      filename = f"{uuid.uuid4()}{ext}"
      s3.upload_fileobj(image.file, settings.S3_BUCKET, filename,
                        ExtraArgs={"ContentType": image.content_type or "image/png"})
      return None, filename
  ```
- Change `image_url` to a public S3 URL (or generate a presigned URL).
- Drop `app.mount("/uploads", ...)` from `main.py` — no longer serving
  files locally.
- Add `S3_BUCKET`, `AWS_REGION`, AWS keys to `core/config.py`.

**Option C: Cloudflare Images** — if you want auto-resize/optimization
for free at low volume.

For the class demo, Option A is plenty.

---

### Task 6 — Better categorizer

The current categorizer (`backend/app/services/categorizer.py`) sends
each image to `gemini-2.5-flash` with a strict-JSON classification
prompt. It works on clean product photos but can misfire on:

- People wearing the item (may classify "person in shirt" as outerwear)
- Multi-item shots
- Accessories (jewelry, hats) get bucketed inconsistently

**Quick wins** (15 min, no new deps):
- Improve the prompt with few-shot examples or a confidence requirement.
- Have it also extract `name` and a short `description` you can store.
- Add a structured output schema if you switch to a model that supports
  it.

Example better prompt (drop into `_PROMPT` in `categorizer.py`):
```
You are classifying a single clothing item from a product photo.
Reply with strict JSON only, no code fences:
{"category": "<top|bottom|outerwear|shoes|accessory>",
 "subcategory": "<one short noun: shirt, sweater, jeans, jacket, sneakers, etc.>",
 "color": "<dominant color in plain English>",
 "name": "<3-5 word descriptive name>"}

Notes:
- "top" includes shirts, t-shirts, sweaters, blouses, hoodies.
- "bottom" includes pants, jeans, shorts, skirts.
- "outerwear" includes jackets, coats, blazers.
- "shoes" includes any footwear.
- "accessory" includes hats, bags, belts, jewelry, scarves.
- If the photo shows a person wearing the item, classify the most prominent garment.
```

Update the function to also return `name` and `color`, and update the
upload route to store them.

**Medium effort** — swap to FashionCLIP. The repo already has FashionCLIP
embeddings wired up under `wardrobe/embeddings.py`. Sketch:

```python
from wardrobe.embeddings import get_image_embedding, get_text_embeddings
import numpy as np

PROMPTS = {
    "top": "a photo of a shirt or top",
    "bottom": "a photo of pants or a skirt",
    "outerwear": "a photo of a jacket or coat",
    "shoes": "a photo of shoes",
    "accessory": "a photo of an accessory like a hat or bag",
}

_text_embs = None
def _get_text_embs():
    global _text_embs
    if _text_embs is None:
        _text_embs = get_text_embeddings(list(PROMPTS.values()))
    return _text_embs

def categorize_item(image):
    img_emb = get_image_embedding(image)
    sims = img_emb @ _get_text_embs().T
    cat = list(PROMPTS.keys())[int(np.argmax(sims))]
    return {"category": cat, "subcategory": cat}
```

Pros: no Gemini dependency, faster, free. Cons: needs torch + the
FashionCLIP weights downloaded (slow first run).

---

### Task 7 — Real outfit suggester

Today's suggester (`backend/app/services/outfit_suggester.py`) does a
top × bottom cross product and ranks by HSL color distance. Looks
plausible but isn't actually stylish.

**Option A: Gemini stylist** (1 hour, no new deps):

```python
import json
from google import genai
from app.core.config import settings

def suggest_outfits(items, limit=8):
    if not settings.GEMINI_API_KEY or len(items) < 2:
        return _fallback_color_pairing(items, limit)

    items_summary = [
        {"id": i["id"], "category": i["category"],
         "subcategory": i.get("subcategory"),
         "name": i.get("name")}
        for i in items
    ]
    prompt = (
        f"Here is a wardrobe: {json.dumps(items_summary)}.\n"
        f"Suggest {limit} stylish outfits. Each outfit must include exactly "
        f"one top and one bottom from the list above. Reply with strict JSON "
        f"only (no prose, no code fences) of the form: "
        f'[{{"top_id": "...", "bottom_id": "...", "rationale": "..."}}]'
    )
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_VISION_MODEL,
        contents=[prompt],
    )
    text = "".join(p.text for c in response.candidates for p in c.content.parts if p.text)
    # ...parse JSON, handle code-fence wrapping (see categorizer.py for a robust parser)
    parsed = json.loads(_strip_fences(text))
    by_id = {i["id"]: i for i in items}
    return [
        {"top": by_id[p["top_id"]], "bottom": by_id[p["bottom_id"]],
         "rationale": p.get("rationale"), "score": 1.0}
        for p in parsed
        if p["top_id"] in by_id and p["bottom_id"] in by_id
    ]
```

You can extend the response shape with a `rationale` field — the
frontend ignores unknown fields, so it won't break, but you can also
update `frontend/src/pages/Outfits.js` to display it.

**Option B: FAISS over a stylish-outfit corpus** (3+ hours):

The repo already has `wardrobe/faiss_index.py` and Polyvore data under
`data/`. Workflow:
1. Pre-compute FashionCLIP embeddings of top/bottom pairs from the
   corpus, store in a FAISS index.
2. At suggestion time, embed each user item, find nearest-neighbor
   reference outfits, then pick combinations from the user's wardrobe
   that best match those reference styles.

More involved but gives genuinely good recommendations.

---

### Task 8 — Deploy

Render is the path of least resistance:

1. Push to GitHub — already done (the `dx-edits` branch is up).
2. Render dashboard → New → **Web Service** → connect this repo, branch
   `dx-edits` (or whatever you merge to).
3. **Build command:**
   ```
   cd backend && pip install -r requirements.txt
   ```
4. **Start command:**
   ```
   cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
5. **Env vars:** `GEMINI_API_KEY`, `JWT_SECRET`, `DATABASE_URL` (point
   at SQLite path under the persistent disk, e.g.
   `sqlite:////opt/render/project/data/wardrobe.db`).
6. **Persistent disk:** add a 1GB disk mounted at `/opt/render/project/data`.
   Update `UPLOAD_DIR` to point inside that mount.
7. **Frontend** → Vercel: import the repo, set root directory to
   `frontend`, set env var `REACT_APP_API_URL=https://your-render-url/api`.
8. Add the Vercel URL to the CORS allowlist in
   `backend/app/main.py`.

Render's free web service spins down after 15 min of inactivity (cold
start ~30s on next request). Fine for a class demo.

---

## Part 4 — API contract (don't break without telling the team)

```
POST /api/auth/signup            {username, email, password} → {token, username}
POST /api/auth/login             {username, password}        → {token, username}
GET  /api/auth/me                (auth)                       → {username, email, created_at, has_body_photo}
GET  /api/auth/login-history     (auth)                       → [{logged_in_at, ip, user_agent}]

POST /api/wardrobe/items         (auth, multipart: image, [name], [category])
                                                              → {id, category, subcategory, image_url, dominant_colors, ...}
POST /api/wardrobe/items/bulk    (auth, multipart: archive=<zip>)
                                                              → {created: [item], skipped: [filename]}
GET  /api/wardrobe/items         (auth)                       → [item]
DELETE /api/wardrobe/items/{id}  (auth)                       → {detail}
POST /api/wardrobe/body-photo    (auth, multipart: image)     → {body_photo_url}
GET  /api/wardrobe/body-photo    (auth)                       → {body_photo_url}

GET  /api/outfits/suggestions    (auth)                       → [{top: item, bottom: item, score: float}]

POST /api/tryon/generate         (multipart: body_photo, top, bottom, [extra_instructions])
                                                              → image/png bytes
```

All authed endpoints expect `Authorization: Bearer <token>`.

You **can** add fields to a response (frontend ignores unknown keys).
You **can't** remove or rename existing fields without updating the
frontend.

---

## Part 5 — Common pitfalls (read before debugging)

- **In-memory store resets on every uvicorn restart.** Sign back up. (Fixed by Task 3.)
- **Gemini key required for try-on AND categorizer.** Categorizer falls
  back to "top/shirt" if missing. Try-on returns 500 if missing.
- **`--reload` only watches code, not `.env`.** Restart uvicorn after
  editing `.env`.
- **CORS** allows `:3000` and `:3001` only — add your port to
  `backend/app/main.py`.
- **Image URLs are relative** (`/uploads/<filename>`). The frontend
  resolves them with `fileUrl()` in `services/api.js`.
- **macOS sandbox** blocks the terminal from reading `~/Downloads` and
  `~/Desktop` by default. Either grant Full Disk Access in System
  Settings → Privacy, or move files to a non-protected folder.

---

## Where to ask questions

- Backend stub markers: search for `TODO(mentee):`
- Routes / API behaviour: hit <http://127.0.0.1:8000/docs> for live docs
- Frontend wiring: each `pages/*.js` is small and self-contained — read
  top to bottom.
