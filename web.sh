#!/usr/bin/env bash
# Interfaz web de consulta (solo lectura sobre salida/manual_iss.db).
# Uso: ./web.sh [puerto]    -> abra http://localhost:8000 en el navegador de Windows
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PUERTO="${1:-8000}"
echo "Manual ISS 2001 en http://localhost:$PUERTO   (Ctrl+C para detener)"
exec uv run uvicorn web.app:app --host 127.0.0.1 --port "$PUERTO"
