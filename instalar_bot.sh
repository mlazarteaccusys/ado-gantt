#!/bin/bash
# Instalación del robot AST Time Report

echo ""
echo "═══════════════════════════════════"
echo "  Instalando AST Time Report Bot"
echo "═══════════════════════════════════"
echo ""

# Verificar Python
if ! command -v python3 &>/dev/null; then
  echo "✗  Python3 no encontrado. Instalalo desde https://python.org"
  exit 1
fi
echo "✓  Python3: $(python3 --version)"

# Instalar playwright
echo "→  Instalando playwright..."
pip3 install playwright --quiet

# Instalar browser Chromium
echo "→  Instalando Chromium (puede tardar ~1 min)..."
python3 -m playwright install chromium

echo ""
echo "✅  Instalación completa!"
echo ""
echo "Para correr el robot:"
echo "  python3 timereport_bot.py             → 8 horas hoy"
echo "  python3 timereport_bot.py --horas 6   → 6 horas hoy"
echo "  python3 timereport_bot.py --auto       → sin confirmación"
echo ""
