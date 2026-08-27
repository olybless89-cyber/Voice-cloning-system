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
| AI / TTS  | ElevenLabs (text-to-speech + voice cloning) with a free **gTTS fallback** when no API key is configured |
| Storage   | Local filesystem (mounted volume on Railway)       |

## AI voice generation (ElevenLabs with free fallback)

The TTS engine works out of the box with **zero configuration** using a local
fallback so you can build and demo the whole flow immediately:

- **With `ELEVENLABS_API_KEY` set** — real neural text-to-speech and multi-speaker voice cloning via ElevenLabs.
- **Without a key** — the platform falls back to the free, no-key **gTTS** service. Voice cloning uploads are validated and stored, and cloned voices reuse the selected reference sample so the product flow works end to end without spending anything.

Set the key later and the platform switches to ElevenLabs automatically.

## Project layout

```
backend/
  app/
    api/routes/     # REST endpoints (auth, voices, tts, history, admin)
    core/           # config, database, security
    models/         # SQLAlchemy models (User, Voice, Generation)
    schemas/        # Pydantic schemas
    services/       # ElevenLabs TTS + voice cloning, audio storage
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
# export ELEVENLABS_API_KEY=...                                                # optional

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

Railway will auto-detect this repo using [`railway.json`](./railway.json) and the
provided [`Dockerfile`](./backend/Dockerfile) / [`frontend/Dockerfile`](./frontend/Dockerfile).

| Service          | Kind     | Notes                                                           |
|------------------|----------|-----------------------------------------------------------------|
| `backend`        | Docker   | ASGI server on `$PORT` (default 8000). Mounts `uploads` volume. |
| `frontend`       | Docker   | Nginx serving the built SPA, proxying `/api` to the backend.    |
| `db`             | Postgres | `DATABASE_URL` from its connection string.                      |

Required environment variables:

- `DATABASE_URL` — Postgres connection string (Railway auto-provides for the `db` service).
- `JWT_SECRET` — any long random string.
- `FRONTEND_URL` — the https URL of your deployed frontend (for CORS).
- `ELEVENLABS_API_KEY` — *optional*, enables real neural TTS + cloning.

Recommended for the backend service: add a **Volume** mounted at `/data/uploads`.
The app reads `UPLOAD_DIR` (default `/data/uploads`) so uploads persist across deploys.

### Nginx proxy note
The frontend container proxies `location /api` and `/uploads` to the backend.
Point `BACKEND_API_URL` at the backend service's public URL so the SPA and nginx
can reach it (defaults to `http://backend:8000`).

## Environment variables

| Variable             | Default                        | Used by     |
|----------------------|--------------------------------|-------------|
| `DATABASE_URL`       | `sqlite:///./voiceclone.db`    | backend     |
| `JWT_SECRET`         | `dev-secret-change-me`         | backend     |
| `ELEVENLABS_API_KEY` | *(empty → gTTS fallback)*      | backend     |
| `UPLOAD_DIR`         | `/data/uploads`                | backend     |
| `FRONTEND_URL`       | `http://localhost:5173`        | backend     |
| `BACKEND_API_URL`    | `http://backend:8000`          | frontend    |

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

---

*Built as an MVP focusing on the core loop: **Choose a Voice → Type Something → Generate Audio**.*