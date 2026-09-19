#!/usr/bin/env bash
# Build and run the bookstore from the umbrella.
#
#   bookstore.sh build    publish the contract, then build backend and web
#   bookstore.sh start    run backend (gRPC :9090) and web (http :8080) until Ctrl-C
#   bookstore.sh up       build, then start
#
# Members are siblings of the umbrella; the script finds them by their names.
# The services run from their boot jars on the Java the build targets (25).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
workspace="$(cd "$here/.." && pwd)"
api="$workspace/bookstore-api"
backend="$workspace/bookstore-backend"
web="$workspace/bookstore-web"
version="0.1.0"
java_major_required=25
grpc_port=9090
http_port=8080
log_dir="$(mktemp -d "${TMPDIR:-/tmp}/bookstore.XXXXXX")"

die() { printf 'bookstore: %s\n' "$*" >&2; exit 1; }

member_present() {
  [ -d "$1" ] || die "member missing: $1 — check the sibling out beside the umbrella"
}

build() {
  for m in "$api" "$backend" "$web"; do member_present "$m"; done
  (cd "$api" && ./gradlew -q publishToMavenLocal)
  (cd "$backend" && ./gradlew -q build)
  (cd "$web" && ./gradlew -q build)
  printf 'bookstore: built api, backend, web\n'
}

# The boot jars target Java 25; prefer the java on PATH, else ask macOS for one.
java_bin() {
  local candidate="${JAVA_HOME:+$JAVA_HOME/bin/java}"
  [ -n "$candidate" ] && [ -x "$candidate" ] || candidate="$(command -v java || true)"
  if [ -n "$candidate" ] && [ "$(java_major "$candidate")" -ge "$java_major_required" ]; then
    printf '%s' "$candidate"; return
  fi
  if [ -x /usr/libexec/java_home ]; then
    candidate="$(/usr/libexec/java_home -v "$java_major_required" 2>/dev/null || true)/bin/java"
    [ -x "$candidate" ] && { printf '%s' "$candidate"; return; }
  fi
  die "no Java $java_major_required found on PATH, in JAVA_HOME, or via java_home"
}

java_major() {
  "$1" -version 2>&1 | awk -F'"' '/version/ { split($2, v, "."); print (v[1] == "1") ? v[2] : v[1]; exit }'
}

wait_for_port() {
  local port="$1" name="$2" tries=60
  until nc -z localhost "$port" 2>/dev/null; do
    tries=$((tries - 1))
    [ "$tries" -gt 0 ] || die "$name did not open port $port; log: $log_dir/$name.log"
    sleep 1
  done
}

start() {
  member_present "$backend"; member_present "$web"
  local java backend_jar web_jar
  java="$(java_bin)"
  backend_jar="$backend/build/libs/bookstore-backend-$version.jar"
  web_jar="$web/build/libs/bookstore-web-$version.jar"
  [ -f "$backend_jar" ] && [ -f "$web_jar" ] || die "boot jars missing — run: bookstore.sh build"

  "$java" -jar "$backend_jar" >"$log_dir/backend.log" 2>&1 &
  local backend_pid=$!
  "$java" -jar "$web_jar" >"$log_dir/web.log" 2>&1 &
  local web_pid=$!
  # shellcheck disable=SC2064  # the pids are fixed now; expand at trap time
  trap "kill $backend_pid $web_pid 2>/dev/null; wait $backend_pid $web_pid 2>/dev/null; printf 'bookstore: stopped\n'" INT TERM EXIT

  wait_for_port "$grpc_port" backend
  wait_for_port "$http_port" web
  printf 'bookstore: backend gRPC on localhost:%s, web on http://localhost:%s/ (logs in %s); Ctrl-C stops both\n' \
    "$grpc_port" "$http_port" "$log_dir"
  wait
}

case "${1:-}" in
  build) build ;;
  start) start ;;
  up) build; start ;;
  *) sed -n '2,8p' "$0" >&2; exit 2 ;;
esac
