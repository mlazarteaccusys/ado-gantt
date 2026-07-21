#!/bin/bash
# Chequeo a las 15:00 — si las horas no se cargaron hoy, las carga ahora.

export HOME="/Users/matiaslazarte"
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

LOG_DIR="$HOME/Cloude_1/logs"
LOG_HOY="$LOG_DIR/timereport_$(date +%Y%m%d).log"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$(date '+%d/%m/%Y %H:%M:%S') — Chequeo 15:00 hs"

# ¿Ya se cargaron exitosamente las horas hoy?
if [ -f "$LOG_HOY" ] && grep -q "✅ OK" "$LOG_HOY"; then
    echo "✅ Las horas ya fueron cargadas hoy. Nada que hacer."
    exit 0
fi

echo "⚠ No se detectó carga exitosa hoy. Ejecutando robot..."
/Users/matiaslazarte/Cloude_1/run_timereport.sh
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    osascript -e 'display notification "No se pudieron cargar las horas en Time Report. Revisá el sistema." with title "⚠️ Time Report - ERROR" sound name "Basso"'
    echo "$(date '+%H:%M:%S') — ❌ Notificación enviada al usuario"
else
    osascript -e 'display notification "Las horas se cargaron correctamente (15:00 hs)." with title "✅ Time Report - OK" sound name "Glass"'
fi
