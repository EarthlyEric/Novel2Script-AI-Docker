#!/bin/sh
# Novel2Script-AI container startup script
# Launches Uvicorn (backend) and Nginx (frontend + reverse proxy);
# if either process exits, the container exits

set -e

# Start the backend (loopback only, exposed via the Nginx reverse proxy)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 &
BACKEND_PID=$!

shutdown() {
    kill -TERM "$BACKEND_PID" 2>/dev/null || true
    nginx -s quit 2>/dev/null || true
    exit 0
}
trap shutdown TERM INT

# Run Nginx in the background; the main loop monitors both processes
nginx -g 'daemon off;' &
NGINX_PID=$!

# If either process dies, exit the container (restart policy / orchestrator takes over)
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$NGINX_PID" 2>/dev/null; do
    sleep 2
done

# Reached here means a process exited unexpectedly: clean up and exit non-zero
shutdown || true
exit 1
