#!/bin/sh
# Single-container entrypoint: start the FastAPI backend, then serve the SPA
# with nginx (which proxies /api and /uploads to the local backend).
set -e

# Serve from the SPA via nginx on the port Railway provides if set.
NGINX_PORT="${PORT:-80}"

# Substitute the listen port into the nginx config.
sed "s/\${NGINX_PORT}/$NGINX_PORT/g" /etc/nginx/conf.d/default.conf.template \
    > /etc/nginx/conf.d/default.conf

# Start the backend (Railway usually sets PORT to the public app port).
BACKEND_PORT="${BACKEND_PORT:-8000}"
echo "[start] backend on :$BACKEND_PORT, nginx on :$NGINX_PORT"
uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --workers 1 &
BACKEND_PID=$!

nginx -g 'daemon off;' &
NGINX_PID=$!

# Bounce if either process exits.
wait "$BACKEND_PID" || kill "$NGINX_PID" 2>/dev/null
wait "$NGINX_PID"