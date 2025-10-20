#!/usr/bin/env python3
"""
Script para generar títulos adaptados con IA para las licitaciones existentes.
Actualiza el campo titulo_adaptado de todas las licitaciones que no lo tienen.
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.licitacion import Licitacion
from app.services.ai_service import AIService
import time

# Configuración de la base de datos
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Error: DATABASE_URL no está configurada")
    sys.exit(1)

# Crear conexión a la base de datos
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Inicializar servicio de IA
ai_service = AIService()

def generar_titulos_adaptados():
    """Genera títulos adaptados para todas las licitaciones sin titulo_adaptado"""
    
    db = SessionLocal()
    try:
        # Obtener licitaciones sin titulo_adaptado
        licitaciones = db.query(Licitacion).filter(
            (Licitacion.titulo_adaptado == None) | (Licitacion.titulo_adaptado == '')
        ).all()
        
        total = len(licitaciones)
        print(f"📊 Encontradas {total} licitaciones sin título adaptado")
        
        if total == 0:
            print("✅ Todas las licitaciones ya tienen título adaptado")
            return
        
        print(f"\n🤖 Generando títulos adaptados con IA...")
        print(f"⏱️  Tiempo estimado: ~{total * 2} segundos")
        print("-" * 60)
        
        exitosos = 0
        fallidos = 0
        
        for i, licitacion in enumerate(licitaciones, 1):
            try:
                # Generar título adaptado
                titulo_adaptado = ai_service.generar_titulo_adaptado(
                    licitacion.titulo,
                    licitacion.descripcion
                )
                
                # Actualizar en la base de datos
                licitacion.titulo_adaptado = titulo_adaptado
                db.commit()
                
                exitosos += 1
                print(f"✅ [{i}/{total}] ID {licitacion.id}: {titulo_adaptado[:60]}...")
                
                # Pequeña pausa para no saturar la API de OpenAI
                time.sleep(0.5)
                
            except Exception as e:
                fallidos += 1
                print(f"❌ [{i}/{total}] ID {licitacion.id}: Error - {str(e)}")
                db.rollback()
                continue
        
        print("-" * 60)
        print(f"\n📈 Resumen:")
        print(f"  ✅ Exitosos: {exitosos}/{total}")
        print(f"  ❌ Fallidos: {fallidos}/{total}")
        print(f"  💰 Coste estimado: ${exitosos * 0.0001:.4f}")
        
        if exitosos > 0:
            print(f"\n🎉 ¡Títulos adaptados generados exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error general: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 GENERADOR DE TÍTULOS ADAPTADOS CON IA")
    print("=" * 60)
    print()
    
    generar_titulos_adaptados()
    
    print()
    print("=" * 60)
    print("✅ Script finalizado")
    print("=" * 60)

