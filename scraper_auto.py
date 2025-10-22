#!/usr/bin/env python3
"""
Script automático que ejecuta el scraper de todas las fuentes y analiza con IA las licitaciones nuevas.
Se ejecuta mediante Cron Jobs en Render.
Actualizado: 2025-10-21 - Agregar directorio local de pip al PYTHONPATH
"""

# ============================================================================
# PASO 1: Instalar dependencias ANTES de importar cualquier módulo externo
# ============================================================================
import subprocess
import sys
import os
import site

print("=" * 80)
print("LITICIA - Verificando e instalando dependencias")
print("=" * 80)

try:
    # Intentar importar sqlalchemy para verificar si las dependencias están instaladas
    import sqlalchemy
    print("✅ Dependencias ya instaladas")
except ImportError:
    print("📦 Instalando dependencias (puede tardar 30-60 segundos)...")
    try:
        # Usar --break-system-packages para evitar error de PEP 668 en Python 3.11+
        # Esto es necesario porque Render usa contenedores efímeros separados para build y ejecución
        subprocess.check_call([
            sys.executable, "-m", "pip", 
            "--break-system-packages",  # Necesario para Python 3.11+ en Render
            "--no-cache-dir", "-q", 
            "-r", "requirements.txt"
        ])
        print("✅ Dependencias instaladas correctamente")
        
        # CRÍTICO: Agregar el directorio de instalación local al sys.path
        # pip install --break-system-packages instala en ~/.local/lib/pythonX.Y/site-packages
        # pero Python no lo busca ahí por defecto
        user_site = site.getusersitepackages()
        if user_site not in sys.path:
            sys.path.insert(0, user_site)
            print(f"✅ Agregado {user_site} al PYTHONPATH")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        sys.exit(1)

print()

# ============================================================================
# PASO 2: Ahora sí, importar módulos y ejecutar el scraper
# ============================================================================
import logging
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """
    Ejecuta el scraper de todas las fuentes y analiza con IA las licitaciones nuevas.
    """
    try:
        logger.info("=" * 80)
        logger.info("INICIANDO SCRAPER AUTOMÁTICO MULTI-FUENTE CON ANÁLISIS DE IA")
        logger.info("=" * 80)
        
        # Importar módulos necesarios
        from app.core.database import get_session_local
        from app.scrapers.placsp_scraper_v2 import PLACSPScraperV2
        from app.scrapers.gencat_scraper import GencatScraper
        from app.services.licitacion_service import LicitacionService
        from app.services.pdf_service import PDFService
        from app.services.ai_service import AIService
        
        # Obtener sesión de base de datos
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        try:
            licitacion_service = LicitacionService(db)
            pdf_service = PDFService()
            ai_service = AIService()
            
            total_nuevas = 0
            total_actualizadas = 0
            
            # ============================================================
            # FUENTE 1: PLACSP (Plataforma de Contratación del Sector Público)
            # ============================================================
            logger.info("\n📥 FUENTE 1: Scraping PLACSP...")
            logger.info("-" * 80)
            
            scraper_placsp = PLACSPScraperV2()
            
            # Scrapear últimos 7 días
            fecha_desde = datetime.now() - timedelta(days=7)
            licitaciones_placsp = list(scraper_placsp.scrape_all(
                max_pages=5,
                filtrar_tic=True
            ))
            
            logger.info(f"✓ PLACSP: {len(licitaciones_placsp)} licitaciones encontradas")
            
            # Procesar licitaciones de PLACSP
            for lic_data_raw in licitaciones_placsp:
                lic_data = lic_data_raw.dict() if hasattr(lic_data_raw, 'dict') else lic_data_raw
                try:
                    existing = licitacion_service.get_by_id_licitacion(lic_data.get("id_licitacion"))
                    
                    if existing:
                        updated = licitacion_service.update(existing.id, lic_data)
                        if updated:
                            total_actualizadas += 1
                    else:
                        nueva_lic = licitacion_service.create(lic_data)
                        total_nuevas += 1
                        
                        # Procesar PDFs y analizar con IA
                        documentos = lic_data.get("documentos", [])
                        if documentos:
                            try:
                                docs_texto = pdf_service.procesar_documentos_licitacion(
                                    documentos,
                                    max_docs=2
                                )
                                
                                texto_pliego = docs_texto.get("pliego_tecnico") or docs_texto.get("pliego_administrativo")
                                
                                if texto_pliego:
                                    logger.info(f"  Analizando con IA: {nueva_lic.expediente}")
                                    
                                    analisis = ai_service.analizar_licitacion_completa(
                                        titulo=nueva_lic.titulo or ''',
                                        descripcion=nueva_lic.resumen or ''',
                                        texto_pliego=texto_pliego
                                    )
                                    
                                    if analisis:
                                        import json
                                        
                                        if analisis.get("titulo_adaptado"):
                                            nueva_lic.titulo_adaptado = analisis["titulo_adaptado"]
                                        
                                        if analisis.get("stack_tecnologico"):
                                            nueva_lic.stack_tecnologico = json.dumps(analisis["stack_tecnologico"])
                                        
                                        if analisis.get("conceptos_tic"):
                                            nueva_lic.conceptos_tic = json.dumps(analisis["conceptos_tic"])
                                        
                                        if analisis.get("resumen_tecnico"):
                                            nueva_lic.resumen_tecnico = json.dumps(analisis["resumen_tecnico"])
                                        
                                        nueva_lic.analizado_ia = True
                                        nueva_lic.fecha_analisis_ia = datetime.now()
                                        
                                        logger.info(f"  ✓ Análisis completado")
                            
                            except Exception as e:
                                logger.error(f"  Error procesando PDFs/IA: {e}")
                
                except Exception as e:
                    logger.error(f"Error procesando licitación PLACSP {lic_data.get('id_licitacion')}: {e}")
                    continue
            
            db.commit()
            logger.info(f"✓ PLACSP procesado: {total_nuevas} nuevas, {total_actualizadas} actualizadas")
            
            # ============================================================
            # FUENTE 2: GENCAT (Generalitat de Catalunya)
            # ============================================================
            logger.info("\n📥 FUENTE 2: Scraping Gencat (Cataluña)...")
            logger.info("-" * 80)
            
            scraper_gencat = GencatScraper()
            
            # Scrapear últimos 7 días
            fecha_desde = datetime.now() - timedelta(days=7)
            licitaciones_gencat = list(scraper_gencat.scrape_all(
                fecha_desde=fecha_desde,
                max_results=500,
                filtrar_tic=True
            ))
            
            logger.info(f"✓ Gencat: {len(licitaciones_gencat)} licitaciones encontradas")
            
            nuevas_gencat = 0
            actualizadas_gencat = 0
            
            # Procesar licitaciones de Gencat
            for lic_data_raw in licitaciones_gencat:
                lic_data = lic_data_raw.dict() if hasattr(lic_data_raw, 'dict') else lic_data_raw
                try:
                    existing = licitacion_service.get_by_id_licitacion(lic_data.get("id_licitacion"))
                    
                    if existing:
                        updated = licitacion_service.update(existing.id, lic_data)
                        if updated:
                            actualizadas_gencat += 1
                            total_actualizadas += 1
                    else:
                        nueva_lic = licitacion_service.create(lic_data)
                        nuevas_gencat += 1
                        total_nuevas += 1
                        
                        # Analizar con IA (sin PDFs por ahora)
                        try:
                            logger.info(f"  Analizando con IA: {nueva_lic.expediente}")
                            
                            analisis = ai_service.analizar_licitacion_completa(
                                titulo=nueva_lic.titulo or ''',
                                descripcion=nueva_lic.resumen or '''
                            )
                            
                            if analisis:
                                import json
                                
                                if analisis.get("titulo_adaptado"):
                                    nueva_lic.titulo_adaptado = analisis["titulo_adaptado"]
                                
                                if analisis.get("stack_tecnologico"):
                                    nueva_lic.stack_tecnologico = json.dumps(analisis["stack_tecnologico"])
                                
                                if analisis.get("conceptos_tic"):
                                    nueva_lic.conceptos_tic = json.dumps(analisis["conceptos_tic"])
                                
                                if analisis.get("resumen_tecnico"):
                                    nueva_lic.resumen_tecnico = json.dumps(analisis["resumen_tecnico"])
                                
                                nueva_lic.analizado_ia = True
                                nueva_lic.fecha_analisis_ia = datetime.now()
                                
                                logger.info(f"  ✓ Análisis completado")
                        
                        except Exception as e:
                            logger.error(f"  Error analizando con IA: {e}")
                
                except Exception as e:
                    logger.error(f"Error procesando licitación Gencat {lic_data.get('id_licitacion')}: {e}")
                    continue
            
            db.commit()
            logger.info(f"✓ Gencat procesado: {nuevas_gencat} nuevas, {actualizadas_gencat} actualizadas")
            
            # ============================================================
            # RESUMEN FINAL
            # ============================================================
            logger.info("\n" + "=" * 80)
            logger.info("✅ PROCESO COMPLETADO")
            logger.info("=" * 80)
            logger.info(f"FUENTES PROCESADAS: 2 (PLACSP, Gencat)")
            logger.info(f"LICITACIONES TOTALES:")
            logger.info(f"  - Nuevas: {total_nuevas}")
            logger.info(f"  - Actualizadas: {total_actualizadas}")
            logger.info(f"  - Total procesadas: {len(licitaciones_placsp) + len(licitaciones_gencat)}")
            logger.info(f"\nDETALLE POR FUENTE:")
            logger.info(f"  PLACSP: {len(licitaciones_placsp)} licitaciones")
            logger.info(f"  Gencat: {len(licitaciones_gencat)} licitaciones")
            logger.info("=" * 80)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ ERROR FATAL: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
    main()

