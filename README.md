# VoiceClone AI — Voice Cloning & AI Text-to-Speech Platform

A full-stack web platform that turns text into realistic AI voice audio and lets users clone voices from an audio sample.

## Features

- **Voice Library** — browse, preview and select public voices maintained by admins.
- **Voice Cloning** — upload a ~1 minute audio sample, wait for processing, name the voice, use it.
- **Text to Speech** — pick a voice, type text, generate audio, play it, download it.
- **Generation History** — access, replay and download every past generation.
- **Admin Dashboard** — manage users, add/edit/disable public voices, promote (publish) user-created voices to the public library.

### Voice statuses
`processing` → `private` → `public` | `disabled` | `deleted`

## Tech stack

| Layer     | Choice                                            |
|-----------|---------------------------------------------------|
| Backend   | Python · FastAPI · SQLAlchemy · JWT auth           |
| Database  | PostgreSQL (falls back to SQLite for local dev)    |
| Frontend  | React · TypeScript · Vite                          |
| AI / TTS  | **edge-tts** (free, no-key Microsoft neural voices) by default; optional **ElevenLabs** upgrade for high-quality TTS + true voice cloning |
| Storage   | Local filesystem (mounted volume on Railway)       |

## AI voice generation (voice engine + OpenAI agent)

The production voice engine works **out of the box with no API key**:

- **Default: `edge-tts`** — a free, no-key engine using Microsoft Edge's neural
  voices. TTS works in production immediately, with a voice selected to match
  the voice name (Aurora → en-GB, Nolan → en-US male, Iris → en-AU). `gTTS`
  remains as a final fallback.
- **Optional upgrade: `ELEVENLABS_API_KEY`** — set this to enable ElevenLabs'
  higher-quality neural TTS and **true per-user voice cloning**. Without it,
  clones are stored locally and generated using the free engine (no per-user
  cloning).

An optional **OpenAI agent** (`OPENAI_API_KEY`) powers the **Script Studio** AI
writing assistant built into the Text-to-Speech page: rewrite in a tone,
proofread, translate, and summarise your script before it becomes audio.

## Project layout

```
backend/
  app/
    api/routes/     # REST endpoints (auth, voices, tts, history, admin)
    core/           # config, database, security
    models/         # SQLAlchemy models (User, Voice, Generation)
    schemas/        # Pydantic schemas
    services/       # TTS voice engine (edge-tts/ElevenLabs), audio storage
  uploads/          # uploaded samples + generated audio (volume)
frontend/
  src/
    api/            # API client
    context/        # auth + toasts
    pages/          # dashboard, login, register, admin
    components/     # audio player, voice cards, etc.
```

## Quick start (local)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# DB (optional — SQLite is used automatically if postgres is unreachable)
export DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/voiceclone   # optional
# export ELEVENLABS_API_KEY=...  # optional upgrade (enable true voice cloning)

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the app at http://localhost:5173. The API is proxied to http://localhost:8000.

## Default admin

On first boot the backend seeds a default admin account:

```
email:    admin@voiceclone.app
password: admin123
```

**Change this immediately in production.**

## Deploy to Railway

The repo is a **single all-in-one container**. The root [`Dockerfile`](./Dockerfile)
builds the frontend (Node) and backend (Python) and serves both from one service:
nginx serves the built SPA and proxies `/api` and `/uploads` to the local uvicorn
backend. [`railway.json`](./railway.json) already points Railway at the root
Dockerfile, so **no language auto-detection (Nixpacks) is needed**.

| Service | Kind     | Notes                                                        |
|---------|----------|--------------------------------------------------------------|
| `app`   | Docker   | Single container: nginx (SPA + proxy) + FastAPI backend.     |
| `db`    | Postgres | `DATABASE_URL` from its connection string.                   |

Required environment variables (set on the `app` service):

- `APP_ENV` — `production`. In production the app reports **`degraded`** on
  `/api/health` until `DATABASE_URL` and `JWT_SECRET` are set. TTS works with no
  key via the free edge-tts engine.
- `DATABASE_URL` — Postgres connection string (Railway auto-provides for the `db` service).
- `JWT_SECRET` — any long random string (not the default `dev-secret-change-me`).
- `FRONTEND_URL` — the https URL of your deployed app (for CORS).

Optional:
- `OPENAI_API_KEY` — enables the **Script Studio** AI writing agent (rewrite /
  proofread / translate / summarise your text before it becomes speech).
- `UPLOAD_DIR` — where audio is stored (default `/data/uploads` on the volume).

Recommended: add a **Volume** mounted at `/data/uploads` so uploads persist
across deploys. The app reads `UPLOAD_DIR` (default `/data/uploads`).

### How the container boots
[`start.sh`](./start.sh) starts uvicorn on `$BACKEND_PORT` (default 8000) and
nginx on `$PORT` (Railway's public port, default 80). The SPA talks to `/api`
and `/uploads` on its own origin, which nginx proxies to `localhost:8000` — so
**no `BACKEND_API_URL` or `VITE_API_BASE` is required** for the default setup.

For extra resilience (some Railway configs route the public HTTP port straight
to the backend rather than to nginx's port), the FastAPI app also serves the
built SPA at `/` via a catch-all route with `/api` and `/uploads` taking
precedence. So the UI loads whether Railway hits uvicorn directly or via nginx.

### Postgres + volume (one-time dashboard setup)
The app and database are separate Railway services. `railway.json` covers the app
service's build/healthcheck; the Postgres service and the volume are configured in
the dashboard (Railway does not support creating those via config-as-code):

1. **Create the app service** — New → GitHub repo → pick this repo. It builds from
   the root `Dockerfile` automatically.
2. **Add PostgreSQL** — New → Database → PostgreSQL. Railway provisions it and
   exposes `DATABASE_URL`.
3. **Reference the DB** — on the app service, Variables → add/reference
   `DATABASE_URL = ${{Postgres.DATABASE_URL}}` (use the actual service name shown
   in your canvas, e.g. `Postgres`).
4. **Add a volume** — on the app service, **Volumes** tab → New Volume → mount at
   `/data`. This persists uploaded samples, cloned voices and generated audio
   (`UPLOAD_DIR` defaults to `/data/uploads`).
5. **Add remaining env vars** — on the app service: `APP_ENV=production`,
   `JWT_SECRET` (long, random), `FRONTEND_URL` (your deployed https URL), and
   optionally `ELEVENLABS_API_KEY` for higher-quality TTS/cloning and
   `OPENAI_API_KEY` for Script Studio.

The admin account `admin@voiceclone.app` / `admin123` is seeded on first boot —
**change it immediately in production**.

## Environment variables

| Variable                | Default                        | Used by      |
|-------------------------|--------------------------------|--------------|
| `APP_ENV`               | `production`                   | backend      |
| `APP_NAME`              | `Voxcraft`                     | backend      |
| `DATABASE_URL`          | `sqlite:///./voiceclone.db`    | backend      |
| `JWT_SECRET`            | `dev-secret-change-me` (fail)  | backend      |
| `ELEVENLABS_API_KEY`    | *(empty → free edge-tts)*       | backend      |
| `ELEVENLABS_MODEL`      | `eleven_multilingual_v2`       | backend      |
| `EDGE_VOICE`            | `en-US-AriaNeural`             | backend      |
| `OPENAI_API_KEY`        | *(empty → Script Studio off)*  | backend      |
| `OPENAI_MODEL`          | `gpt-4o-mini`                  | backend      |
| `RATE_LIMIT_MINUTE`     | `20` (TTS gens/min per user)   | backend      |
| `UPLOAD_DIR`            | `/data/uploads`                | backend      |
| `FRONTEND_URL`          | `http://localhost:5173`        | backend      |
| `BACKEND_API_URL`       | *(empty → same-origin proxy)*  | frontend     |

> **Note:** in `APP_ENV=production` the backend reports `status: degraded` on
> `/api/health` (while still passing Railway's healthcheck) only if `DATABASE_URL`
> is SQLite or `JWT_SECRET` is the default. TTS works out of the box via the free
> edge-tts engine (`ELEVENLABS_API_KEY` is optional).

## API overview

```
POST /api/auth/register
POST /api/auth/login             -> access_token + user (role)
GET  /api/voices/library         -> public voices
POST /api/voices/clone           -> upload sample, start a clone voice
GET  /api/voices/mine            -> current user's voices
DELETE /api/voices/{id}          -> delete a user voice
GET  /api/voices/tree            -> voices usable in TTS (public + mine)
POST /api/tts/generate           -> generate audio from text
GET  /api/tts/history            -> my generation history
DELETE /api/tts/{id}             -> delete a generation
# OpenAI agent (Script Studio) — auth required
GET  /api/agent/status           -> {enabled, model, provider}
POST /api/agent/rewrite          -> rewrite text in a tone ({text, option})
POST /api/agent/proofread        -> fix grammar ({text})
POST /api/agent/translate        -> translate ({text, option: language})
POST /api/agent/summarise        -> short voiceover ({text, sentences})
POST /api/agent/describe         -> voice description ({text, option})
# admin
GET  /api/admin/users
POST /api/admin/voices           -> add public voice
PATCH /api/admin/voices/{id}     -> edit / set status (public, disabled)
DELETE /api/admin/voices/{id}
POST /api/admin/voices/{id}/publish   -> promote a user voice to public
```

## Security notes

- Passwords are hashed with bcrypt.
- JWT bearer tokens are required for all voice/TTS/history routes.
- Admin routes are protected by a role check on the token.
- Uploaded audio types are validated (webm, mp3, m4a, opus, ogg, wav, flac).
- In-process rate limiting protects `register`, `login`, `tts/generate` and
  `voices/clone` (HTTP 429 beyond the per-minute cap).
- In `APP_ENV=production` the app **logs a `CONFIG READINESS` warning and reports
  `status: degraded` on `/api/health`** when `DATABASE_URL` is SQLite or the
  `JWT_SECRET` default is used. It still boots so the deploy passes Railway's
  healthcheck. TTS never refuses: the free edge-tts engine generates speech with
  no key, while ElevenLabs (with a key) and gTTS (last resort) are used as needed.
- Change the seeded admin password (`admin@voiceclone.app`) immediately.

---

*Built as an MVP focusing on the core loop: **Choose a Voice → Type Something → Generate Audio**.*