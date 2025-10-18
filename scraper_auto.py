#!/usr/bin/env python3.11
"""
Script automático que ejecuta el scraper y analiza con IA las licitaciones nuevas.
Se ejecuta cada 3 horas mediante Cron Job en Render.
"""

import os
import sys
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    Ejecuta el scraper y analiza con IA las licitaciones nuevas.
    """
    try:
        logger.info("=" * 80)
        logger.info("INICIANDO SCRAPER AUTOMÁTICO CON ANÁLISIS DE IA")
        logger.info("=" * 80)
        
        # Importar módulos necesarios
        from app.core.database import get_db
        from app.services.placsp_scraper import PLACSPScraper
        from app.services.ai_service import AIService
        from sqlalchemy.orm import Session
        
        # Obtener sesión de base de datos
        db = next(get_db())
        
        try:
            # 1. Ejecutar scraper
            logger.info("\n📥 PASO 1: Ejecutando scraper de PLACSP...")
            scraper = PLACSPScraper(db)
            
            # Scrapear licitaciones TIC de los últimos 30 días
            nuevas_licitaciones = scraper.scrapear_licitaciones_tic(dias=30)
            
            logger.info(f"✅ Scraper completado: {len(nuevas_licitaciones)} licitaciones nuevas encontradas")
            
            if len(nuevas_licitaciones) == 0:
                logger.info("ℹ️  No hay licitaciones nuevas para analizar")
                return
            
            # 2. Analizar con IA las licitaciones nuevas
            logger.info(f"\n🤖 PASO 2: Analizando {len(nuevas_licitaciones)} licitaciones con IA...")
            
            ai_service = AIService()
            analizadas = 0
            errores = 0
            
            for i, licitacion in enumerate(nuevas_licitaciones, 1):
                try:
                    logger.info(f"Analizando licitación {i}/{len(nuevas_licitaciones)}: {licitacion.titulo[:50]}...")
                    
                    # Analizar con IA
                    resultado = ai_service.analizar_licitacion_completo(
                        titulo=licitacion.titulo,
                        descripcion=licitacion.descripcion or "",
                        presupuesto=licitacion.presupuesto_base_sin_impuestos
                    )
                    
                    # Actualizar licitación con resultados de IA
                    licitacion.conceptos_tic = resultado.get("conceptos_tic", [])
                    licitacion.stack_tecnologico = resultado.get("stack_tecnologico", {})
                    licitacion.resumen_tecnico = resultado.get("resumen_tecnico", {})
                    licitacion.analizado_ia = True
                    
                    db.commit()
                    analizadas += 1
                    
                    logger.info(f"  ✅ Analizada correctamente ({len(resultado.get('conceptos_tic', []))} conceptos TIC)")
                    
                except Exception as e:
                    logger.error(f"  ❌ Error al analizar: {str(e)}")
                    errores += 1
                    db.rollback()
                    continue
            
            logger.info("\n" + "=" * 80)
            logger.info(f"✅ PROCESO COMPLETADO")
            logger.info(f"   - Licitaciones nuevas: {len(nuevas_licitaciones)}")
            logger.info(f"   - Analizadas con IA: {analizadas}")
            logger.info(f"   - Errores: {errores}")
            logger.info("=" * 80)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ ERROR FATAL: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

