#!/bin/sh
# Novel2Script-AI container startup script
# Launches Uvicorn (backend) and Nginx (frontend + reverse proxy);
# if either process exits, the container exits

set -eu

# Start the backend (loopback only, exposed via the Nginx reverse proxy)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 &
BACKEND_PID=$!

stopping=0

stop_children() {
    kill -TERM "$BACKEND_PID" 2>/dev/null || true
    if [ -n "${NGINX_PID:-}" ]; then
        nginx -s quit 2>/dev/null || true
    fi
}

handle_signal() {
    stopping=1
    stop_children
}
trap handle_signal TERM INT

# Run Nginx in the background; the main loop monitors both processes
nginx -g 'daemon off;' &
NGINX_PID=$!

# Monitor both services. A signal handled by the script is an intentional stop;
# any other child exit is reported and returned as a failure to the orchestrator.
while :; do
    if [ "$stopping" -eq 1 ]; then
        break
    fi

    backend_alive=1
    nginx_alive=1
    kill -0 "$BACKEND_PID" 2>/dev/null || backend_alive=0
    kill -0 "$NGINX_PID" 2>/dev/null || nginx_alive=0

    if [ "$backend_alive" -eq 1 ] && [ "$nginx_alive" -eq 1 ]; then
        sleep 2
        continue
    fi

    if [ "$stopping" -eq 1 ]; then
        break
    fi

    if [ "$backend_alive" -eq 0 ]; then
        printf '%s\n' '[START] Backend process exited unexpectedly' >&2
    fi
    if [ "$nginx_alive" -eq 0 ]; then
        printf '%s\n' '[START] Nginx process exited unexpectedly' >&2
    fi

    stop_children

    backend_status=0
    nginx_status=0
    if wait "$BACKEND_PID"; then :; else backend_status=$?; fi
    if wait "$NGINX_PID"; then :; else nginx_status=$?; fi

    printf '%s\n' "[START] Backend exit code: $backend_status" >&2
    printf '%s\n' "[START] Nginx exit code: $nginx_status" >&2

    # Preserve a useful non-zero status even if a child exited cleanly.
    exit_code=$backend_status
    if [ "$backend_alive" -eq 1 ]; then
        exit_code=$nginx_status
    fi
    if [ "$exit_code" -eq 0 ]; then
        exit_code=1
    fi
    exit "$exit_code"
done

# Intentional container shutdown: allow both children to finish cleanly.
wait "$BACKEND_PID" 2>/dev/null || true
wait "$NGINX_PID" 2>/dev/null || true
exit 0
