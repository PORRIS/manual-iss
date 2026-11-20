#!/usr/bin/env bash
# Manual Tarifario SOAT 2026 (UVB): extrae el PDF, construye la BD nueva, la valida, la prueba,
# exporta el Excel y copia la BD a Windows para Navicat. Se detiene en el primer error.
#
# Uso (desde cualquier carpeta): soat2026/actualizar.sh
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."

COPIA_WINDOWS="/mnt/c/Users/Porris/Documents/manual_soat_2026.db"
paso() { printf '\n=== %s\n' "$1"; }

paso "Extracción del PDF";  uv run soat2026/extraer.py
paso "ETL y validaciones";  uv run soat2026/etl.py
paso "Pruebas";             uv run soat2026/pruebas.py && uv run soat2026/pruebas_cotizar.py
paso "Excel";               uv run soat2026/exportar_excel.py

paso "Copia para Navicat"
if [[ -d "$(dirname "$COPIA_WINDOWS")" ]]; then
    cp soat2026/salida/manual_soat_2026.db "$COPIA_WINDOWS" && echo "copiada a $COPIA_WINDOWS" || {
        echo "ERROR: no pude copiar a $COPIA_WINDOWS. ¿Navicat la tiene abierta? Ciérrela y repita."; exit 1; }
else
    echo "AVISO: no existe $(dirname "$COPIA_WINDOWS"); no se copió la BD"
fi
printf '\nTODO OK\n'
