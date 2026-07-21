#!/bin/bash
# Wrapper para cron — AST Time Report Bot
# Este script se ejecuta automáticamente cada día hábil a las 18:00

export HOME="/Users/matiaslazarte"
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

LOG_DIR="$HOME/Cloude_1/logs"
LOG_FILE="$LOG_DIR/timereport_$(date +%Y%m%d).log"
SCRIPT="$HOME/Cloude_1/timereport_bot.py"

mkdir -p "$LOG_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> "$LOG_FILE"
echo "$(date '+%d/%m/%Y %H:%M:%S') — Iniciando robot" >> "$LOG_FILE"

/usr/bin/python3 "$SCRIPT" --headless --horas 8 >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date '+%H:%M:%S') — ✅ OK" >> "$LOG_FILE"
else
    echo "$(date '+%H:%M:%S') — ❌ ERROR (código $EXIT_CODE)" >> "$LOG_FILE"
    osascript -e 'display notification "No se pudieron cargar las horas en Time Report. Se reintentará a las 15:00." with title "⚠️ Time Report - ERROR" sound name "Basso"'
fi

# Mantener solo los últimos 30 logs
ls -t "$LOG_DIR"/timereport_*.log 2>/dev/null | tail -n +31 | xargs rm -f

exit $EXIT_CODE
