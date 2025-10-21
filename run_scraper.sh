#!/bin/bash
# Script de inicio para cron jobs de Liticia
# Garantiza que las dependencias estén instaladas antes de ejecutar el scraper

set -e  # Exit on error

echo "=========================================="
echo "LITICIA - Iniciando Cron Job"
echo "Fecha: $(date)"
echo "=========================================="

# Verificar que estamos en el directorio correcto
echo "Directorio actual: $(pwd)"
echo "Contenido del directorio:"
ls -la

# Verificar que requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo "❌ ERROR: requirements.txt no encontrado"
    exit 1
fi

echo ""
echo "📦 Instalando dependencias..."
echo "------------------------------------------"

# Instalar dependencias
python3.11 -m pip install --no-cache-dir -r requirements.txt

echo ""
echo "✅ Dependencias instaladas correctamente"
echo ""
echo "🚀 Ejecutando scraper automático..."
echo "=========================================="
echo ""

# Ejecutar el scraper
python3.11 scraper_auto.py

echo ""
echo "=========================================="
echo "✅ Cron Job completado"
echo "Fecha: $(date)"
echo "=========================================="

