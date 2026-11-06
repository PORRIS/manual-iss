#!/usr/bin/env bash
# Regenera la BD, la valida y la copia a Windows para Navicat. Se detiene en el primer error,
# y así nunca queda una copia en Navicat de una BD sin validar.
#
# Uso (desde cualquier carpeta):
#   ./actualizar.sh          # ETL + validaciones + copia a Windows
#   ./actualizar.sh --pdf    # además vuelve a extraer el PDF (solo si cambió el PDF o el extractor)
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

COPIA_WINDOWS="/mnt/c/Users/Porris/Documents/manual_iss.db"

paso() { printf '\n=== %s\n' "$1"; }

if [[ "${1:-}" == "--pdf" ]]; then
    paso "Extracción del PDF"
    uv run extraer_pdf.py
    uv run control_extraccion.py
fi

paso "ETL"
uv run etl.py

paso "Validaciones"
uv run validar.py
uv run validar_completo.py
uv run probar_bd.py
uv run pruebas_cotizar.py
uv run pruebas_auditar.py

paso "Copia para Navicat"
if [[ -d "$(dirname "$COPIA_WINDOWS")" ]]; then
    if cp salida/manual_iss.db "$COPIA_WINDOWS"; then
        echo "copiada a $COPIA_WINDOWS"
    else
        echo "ERROR: no pude copiar a $COPIA_WINDOWS. ¿Navicat la tiene abierta? Ciérrela y repita:"
        echo "  cp salida/manual_iss.db $COPIA_WINDOWS"
        exit 1
    fi
else
    echo "AVISO: no existe $(dirname "$COPIA_WINDOWS"); no se copió la BD"
fi

printf '\nTODO OK\n'
