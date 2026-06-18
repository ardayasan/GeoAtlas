#!/bin/bash
clear
echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║          GeoAtlas  v1.0          ║"
echo "  ║     Demografik Harita Platformu  ║"
echo "  ╚══════════════════════════════════╝"
echo ""

PROJ="$(cd "$(dirname "$0")" && pwd)"
VENV="$PROJ/venv"
BACKEND="$PROJ/backend"
PORT=8000
URL="http://localhost:$PORT"

# Port temizle
lsof -ti:$PORT | xargs kill -9 2>/dev/null && sleep 0.5

# İlk kurulum
if [ ! -d "$VENV" ]; then
    echo "  📦 İlk kurulum yapılıyor..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -r "$BACKEND/requirements.txt" -q
    echo "  ✓  Hazır."
fi

echo "  🚀 Sunucu başlatılıyor..."
(sleep 2 && open "$URL") &

cd "$BACKEND"
"$VENV/bin/python3" -m uvicorn main:app \
    --host 0.0.0.0 --port $PORT --log-level warning

echo ""
read -p "  Kapatmak için Enter..." _
