#!/bin/sh
# Inject the backend API URL into the built SPA at container start so the api
# client can reach the backend directly. If BACKEND_API_URL is unset/empty the
# SPA stays same-origin and nginx proxies /api and /uploads to the backend.
set -e

API_URL="${BACKEND_API_URL:-}"
INDEX=/usr/share/nginx/html/index.html

if [ -n "$API_URL" ] && [ -f "$INDEX" ]; then
  # Insert a global that the api client reads at runtime.
  sed -i "s|</head>|<script>window.__BACKEND_API_URL__='${API_URL%/}';</script></head>|" "$INDEX"
fi

exec "$@"