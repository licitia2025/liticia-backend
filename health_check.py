#!/usr/bin/env python3
"""
Script de health check y monitoreo automático para Liticia
Verifica el estado de los servicios y reporta errores
"""

import requests
import sys
from datetime import datetime

def check_backend_health():
    """Verifica que el backend API esté respondiendo"""
    try:
        response = requests.get("https://liticia-backend-api.onrender.com/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ Backend API: OK ({response.status_code})")
            return True
        else:
            print(f"❌ Backend API: ERROR ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Backend API: ERROR - {str(e)}")
        return False

def check_licitaciones_count():
    """Verifica que haya licitaciones en la base de datos"""
    try:
        response = requests.get("https://liticia-backend-api.onrender.com/api/v1/licitaciones?limit=1", timeout=10)
        if response.status_code == 200:
            data = response.json()
            count = len(data)
            print(f"✅ Licitaciones disponibles: {count}")
            return True
        else:
            print(f"❌ Error al obtener licitaciones: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error al verificar licitaciones: {str(e)}")
        return False

def check_frontend():
    """Verifica que el frontend esté accesible"""
    try:
        response = requests.get("https://liticia-frontend.onrender.com", timeout=10)
        if response.status_code == 200:
            print(f"✅ Frontend: OK ({response.status_code})")
            return True
        else:
            print(f"❌ Frontend: ERROR ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Frontend: ERROR - {str(e)}")
        return False

def main():
    print("=" * 80)
    print(f"LITICIA HEALTH CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = []
    results.append(check_backend_health())
    results.append(check_licitaciones_count())
    results.append(check_frontend())
    
    print("=" * 80)
    if all(results):
        print("✅ TODOS LOS SERVICIOS FUNCIONANDO CORRECTAMENTE")
        sys.exit(0)
    else:
        print("❌ ALGUNOS SERVICIOS TIENEN PROBLEMAS")
        sys.exit(1)

if __name__ == "__main__":
    main()

