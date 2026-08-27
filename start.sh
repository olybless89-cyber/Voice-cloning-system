#!/bin/sh
# Single-container entrypoint: start the FastAPI backend, then serve the SPA
# with nginx (which proxies /api and /uploads to the local backend).
set -e

# Serve from the SPA via nginx on the port Railway provides if set.
NGINX_PORT="${PORT:-80}"

# Substitute the listen port into the nginx config.
sed "s/\${NGINX_PORT}/$NGINX_PORT/g" /etc/nginx/conf.d/default.conf.template \
    > /etc/nginx/conf.d/default.conf

# Start the backend on an internal port that MUST differ from $PORT, because
# $PORT is the public port nginx listens on. If the default backend port
# collides with $PORT, bump it out of the way so the two processes don't fight
# over the same socket (Railway commonly sets PORT=8000).
BACKEND_PORT="${BACKEND_PORT:-8000}"
if [ "$BACKEND_PORT" = "$NGINX_PORT" ]; then
  BACKEND_PORT="8010"
fi
echo "[start] backend on :$BACKEND_PORT, nginx on :$NGINX_PORT"

# Substitute the proxy target port into the nginx config.
sed -i "s/\${BACKEND_PORT}/$BACKEND_PORT/g" /etc/nginx/conf.d/default.conf

uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --workers 1 &
BACKEND_PID=$!

nginx -g 'daemon off;' &
NGINX_PID=$!

# Bounce if either process exits.
wait "$BACKEND_PID" || kill "$NGINX_PID" 2>/dev/null
wait "$NGINX_PID"