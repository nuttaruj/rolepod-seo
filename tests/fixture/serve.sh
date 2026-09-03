#!/usr/bin/env bash
# Copy tests/fixtures/site-a to a scratch dir with __BASE__ substituted and
# serve it with python http.server. Prints the base URL, writes the PID.
#   tests/fixture/serve.sh [port] [scratch-dir]
set -euo pipefail
cd "$(dirname "$0")/../.."
PORT="${1:-0}"
SCRATCH="${2:-tests/fixture/.out}"
if [ "$PORT" = "0" ]; then
  PORT=$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')
fi
BASE="http://127.0.0.1:$PORT"
rm -rf "$SCRATCH/site" && mkdir -p "$SCRATCH/site"
cp -R tests/fixtures/site-a/. "$SCRATCH/site/"
python3 - "$SCRATCH/site" "$BASE" <<'PY'
import os, sys
root, base = sys.argv[1], sys.argv[2]
for dp, _, fns in os.walk(root):
    for fn in fns:
        p = os.path.join(dp, fn)
        try: s = open(p, encoding="utf-8").read()
        except UnicodeDecodeError: continue
        if "__BASE__" in s: open(p, "w", encoding="utf-8").write(s.replace("__BASE__", base))
PY
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SCRATCH/site" >"$SCRATCH/server.log" 2>&1 &
echo $! > "$SCRATCH/server.pid"
for _ in $(seq 1 40); do
  python3 -c "import urllib.request,sys;urllib.request.urlopen('$BASE/robots.txt',timeout=1)" 2>/dev/null && break
  sleep 0.1
done
echo "$BASE"
