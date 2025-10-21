#!/usr/bin/env python3
"""
Script que instala dependencias y ejecuta el scraper.
No requiere dependencias externas, solo la biblioteca estándar de Python.
"""

import subprocess
import sys
import os

def main():
    print("=" * 80)
    print("LITICIA - Instalando dependencias y ejecutando scraper")
    print("=" * 80)
    print()
    
    # Verificar que estamos en el directorio correcto
    print(f"Directorio actual: {os.getcwd()}")
    print()
    
    # Instalar dependencias
    print("📦 Instalando dependencias...")
    print("-" * 80)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", "requirements.txt"],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("✅ Dependencias instaladas correctamente")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias:")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)
    
    print()
    print("🚀 Ejecutando scraper automático...")
    print("=" * 80)
    print()
    
    # Ejecutar el scraper
    try:
        result = subprocess.run(
            [sys.executable, "scraper_auto.py"],
            check=True
        )
        print()
        print("=" * 80)
        print("✅ Scraper completado exitosamente")
        print("=" * 80)
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print()
        print("=" * 80)
        print(f"❌ Error ejecutando scraper (exit code: {e.returncode})")
        print("=" * 80)
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()

