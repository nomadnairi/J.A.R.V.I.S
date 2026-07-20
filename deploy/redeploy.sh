#!/usr/bin/env bash
#
# Bulletproof redeploy for the J.A.R.V.I.S. Docker stack.
#
# The #1 reason "my changes aren't live" is a stale image or a container that
# was never recreated. This script pulls the latest code, rebuilds WITHOUT the
# layer cache, force-recreates the containers, and then prints the bot's own
# startup report so you can SEE whether the subscription gate is on and whether
# the command menu was cleared.
#
# Run it from the project directory (the one with docker-compose.yml):
#
#   bash deploy/redeploy.sh
#
set -euo pipefail

cd "$(dirname "$0")/.."
echo "▶ Project: $(pwd)"

# 1. Latest code on the current branch.
echo "▶ Pulling latest code…"
git pull --ff-only

# 2. Make sure the gate is configured. Warn loudly if it isn't.
if [ -f .env ]; then
    if ! grep -qE '^TELEGRAM_REQUIRED_CHANNEL=.+' .env; then
        echo "⚠  TELEGRAM_REQUIRED_CHANNEL is empty in .env — the subscription"
        echo "   gate will stay OFF. Set it (e.g. TELEGRAM_REQUIRED_CHANNEL=@your_channel)"
        echo "   and make the bot an admin of that channel."
    fi
else
    echo "⚠  No .env found. Copy .env.example to .env and fill it in first."
fi

# 3. Rebuild from scratch (no cache) and force new containers.
echo "▶ Rebuilding images with no cache…"
docker compose build --no-cache

echo "▶ Recreating containers…"
docker compose up -d --force-recreate

# 4. Show the truth: the bot logs its version + gate status on startup.
echo "▶ Waiting for the bot to start…"
sleep 5
echo "──────────────────────────────────────────────────────────────"
echo "  Bot startup report (look for 'SUBSCRIPTION GATE' and version):"
echo "──────────────────────────────────────────────────────────────"
docker compose logs --tail=40 bot || docker compose logs --tail=40
echo "──────────────────────────────────────────────────────────────"
echo "✓ Done. If SUBSCRIPTION GATE says OFF, set TELEGRAM_REQUIRED_CHANNEL"
echo "  in .env and re-run this script."
