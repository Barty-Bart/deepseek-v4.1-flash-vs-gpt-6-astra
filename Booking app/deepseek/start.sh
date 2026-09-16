#!/usr/bin/env bash
# Start the Northline Barber preview server.
#
#   ./start.sh              # uses PORT from the environment, or 5181
#   PORT=5182 ./start.sh    # a second copy next to the first
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-5181}"
export PORT

VENV_DIR="${NORTHLINE_VENV:-.venv}"
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Creating virtual environment in $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip
  "$VENV_DIR/bin/python" -m pip install --quiet -r requirements.txt
fi

# Same resolution order as northline/config.py, so the hint below matches the
# database the server will actually open.
if [ -n "${NORTHLINE_DB:-}" ]; then
  DB_PATH="$NORTHLINE_DB"
elif [ -n "${NORTHLINE_INSTANCE_DIR:-}" ]; then
  DB_PATH="$NORTHLINE_INSTANCE_DIR/northline.sqlite"
else
  DB_PATH="instance/northline.sqlite"
fi
if [ ! -f "$DB_PATH" ]; then
  cat <<'MSG'
No local database yet. Create it once with the explicit seed command:

    .venv/bin/python -m flask --app northline:create_app seed

Starting with an empty database (the server will still run; the booking page
will show no services until you seed).
MSG
fi

echo "Northline Barber starting on 127.0.0.1:${PORT}"
exec "$VENV_DIR/bin/python" -m northline
