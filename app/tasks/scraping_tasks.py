"""
Tareas de Celery para scraping de licitaciones
"""
from celery import Task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.scrapers.placsp_scraper_v2 import PLACSPScraperV2
from app.models.licitacion import Licitacion
from app.services.licitacion_service import LicitacionService
from app.services.pdf_service import PDFService
from app.services.ai_service import AIService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def _procesar_licitacion_con_ia(licitacion: Licitacion, documentos: list, db):
    """
    Procesa los PDFs de una licitación y la analiza con IA
    
    Args:
        licitacion: Objeto Licitacion recién creado
        documentos: Lista de documentos extraídos del feed
        db: Sesión de base de datos
    """
    if not documentos:
        logger.debug(f"No hay documentos para procesar en {licitacion.expediente}")
        return
    
    try:
        # 1. Extraer texto de los PDFs (solo pliegos técnicos y administrativos)
        pdf_service = PDFService()
        docs_texto = pdf_service.procesar_documentos_licitacion(
            documentos,
            max_docs=2  # Procesar máximo 2 documentos (pliego técnico + administrativo)
        )
        
        # 2. Analizar con IA usando el texto extraído
        ai_service = AIService()
        
        # Usar el pliego técnico si está disponible, sino el administrativo
        texto_pliego = docs_texto.get('pliego_tecnico') or docs_texto.get('pliego_administrativo')
        
        if texto_pliego:
            logger.info(f"Analizando licitación {licitacion.expediente} con {len(texto_pliego)} caracteres de PDF")
            
            analisis = ai_service.analizar_licitacion_completa(
                titulo=licitacion.titulo or '',
                descripcion=licitacion.resumen or '',
                texto_pliego=texto_pliego
            )
            
            if analisis:
                # Actualizar licitación con resultados del análisis
                import json
                
                if analisis.get('titulo_adaptado'):
                    licitacion.titulo_adaptado = analisis['titulo_adaptado']
                
                if analisis.get('stack_tecnologico'):
                    licitacion.stack_tecnologico = json.dumps(analisis['stack_tecnologico'])
                
                if analisis.get('conceptos_tic'):
                    licitacion.conceptos_tic = json.dumps(analisis['conceptos_tic'])
                
                if analisis.get('resumen_tecnico'):
                    licitacion.resumen_tecnico = json.dumps(analisis['resumen_tecnico'])
                
                licitacion.analizado_ia = True
                licitacion.fecha_analisis_ia = datetime.now()
                
                db.flush()
                
                logger.info(f"✓ Licitación {licitacion.expediente} analizada con IA usando contenido de PDF")
            else:
                logger.warning(f"No se pudo completar el análisis de IA para {licitacion.expediente}")
        else:
            logger.debug(f"No se pudo extraer texto de PDFs para {licitacion.expediente}")
    
    except Exception as e:
        logger.error(f"Error en procesamiento con IA de {licitacion.expediente}: {e}")
        # No lanzar excepción para no interrumpir el scraping


class DatabaseTask(Task):
    """Tarea base que gestiona la sesión de base de datos"""
    _db = None

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()


@celery_app.task(base=DatabaseTask, bind=True, name="app.tasks.scraping_tasks.scrape_placsp_recent")
def scrape_placsp_recent(self, days: int = 1):
    """
    Scrape licitaciones recientes de PLACSP de los últimos N días
    
    Args:
        days: Número de días hacia atrás para scrapear
    """
    logger.info(f"Iniciando scraping de PLACSP de los últimos {days} días")
    
    db = SessionLocal()
    self._db = db
    
    try:
        scraper = PLACSPScraperV2()
        licitacion_service = LicitacionService(db)
        
        # Scrape licitaciones recientes
        licitaciones = scraper.scrape_recent(days=days, filtrar_tic=True)
        
        # Guardar en base de datos
        nuevas = 0
        actualizadas = 0
        
        for lic_data in licitaciones:
            try:
                # Verificar si ya existe
                existing = licitacion_service.get_by_id_licitacion(lic_data.get('id_licitacion'))
                
                if existing:
                    # Actualizar si hay cambios
                    updated = licitacion_service.update(existing.id, lic_data)
                    if updated:
                        actualizadas += 1
                        logger.debug(f"Actualizada licitación: {lic_data.get('expediente')}")
                else:
                    # Crear nueva licitación
                    nueva_lic = licitacion_service.create(lic_data)
                    nuevas += 1
                    logger.debug(f"Nueva licitación: {lic_data.get('expediente')}")
                    
                    # Procesar PDFs y analizar con IA si es nueva
                    try:
                        _procesar_licitacion_con_ia(nueva_lic, lic_data.get('documentos', []), db)
                    except Exception as e:
                        logger.error(f"Error procesando PDFs/IA para {lic_data.get('expediente')}: {e}")
            
            except Exception as e:
                logger.error(f"Error procesando licitación {lic_data.get('expediente')}: {e}")
                continue
        
        db.commit()
        
        result = {
            'total_scraped': len(licitaciones),
            'nuevas': nuevas,
            'actualizadas': actualizadas,
            'days': days,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Scraping completado: {nuevas} nuevas, {actualizadas} actualizadas de {len(licitaciones)} totales")
        
        return result
    
    except Exception as e:
        logger.error(f"Error en scraping de PLACSP: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()


@celery_app.task(base=DatabaseTask, bind=True, name="app.tasks.scraping_tasks.scrape_placsp_full")
def scrape_placsp_full(self, max_pages: int = 100):
    """
    Scrape completo de PLACSP (todas las páginas hasta max_pages)
    
    Args:
        max_pages: Número máximo de páginas a scrapear
    """
    logger.info(f"Iniciando scraping completo de PLACSP (max {max_pages} páginas)")
    
    db = SessionLocal()
    self._db = db
    
    try:
        scraper = PLACSPScraperV2()
        licitacion_service = LicitacionService(db)
        
        nuevas = 0
        actualizadas = 0
        total = 0
        
        # Scrape todas las páginas
        for lic_data in scraper.scrape_all(max_pages=max_pages, filtrar_tic=True):
            total += 1
            
            try:
                # Verificar si ya existe
                existing = licitacion_service.get_by_id_licitacion(lic_data.get('id_licitacion'))
                
                if existing:
                    # Actualizar
                    updated = licitacion_service.update(existing.id, lic_data)
                    if updated:
                        actualizadas += 1
                else:
                    # Crear nueva licitación
                    nueva_lic = licitacion_service.create(lic_data)
                    nuevas += 1
                    
                    # Procesar PDFs y analizar con IA si es nueva
                    try:
                        _procesar_licitacion_con_ia(nueva_lic, lic_data.get('documentos', []), db)
                    except Exception as e:
                        logger.error(f"Error procesando PDFs/IA para {lic_data.get('expediente')}: {e}")
                
                # Commit cada 50 licitaciones
                if total % 50 == 0:
                    db.commit()
                    logger.info(f"Progreso: {total} licitaciones procesadas ({nuevas} nuevas, {actualizadas} actualizadas)")
            
            except Exception as e:
                logger.error(f"Error procesando licitación {lic_data.get('expediente')}: {e}")
                continue
        
        db.commit()
        
        result = {
            'total_scraped': total,
            'nuevas': nuevas,
            'actualizadas': actualizadas,
            'max_pages': max_pages,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Scraping completo finalizado: {nuevas} nuevas, {actualizadas} actualizadas de {total} totales")
        
        return result
    
    except Exception as e:
        logger.error(f"Error en scraping completo de PLACSP: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()


@celery_app.task(base=DatabaseTask, bind=True, name="app.tasks.scraping_tasks.cleanup_old_licitaciones")
def cleanup_old_licitaciones(self, days: int = 365):
    """
    Limpia licitaciones antiguas de la base de datos
    
    Args:
        days: Número de días de antigüedad para considerar una licitación como antigua
    """
    logger.info(f"Iniciando limpieza de licitaciones con más de {days} días")
    
    db = SessionLocal()
    self._db = db
    
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Contar licitaciones a eliminar
        count = db.query(Licitacion).filter(
            Licitacion.fecha_actualizacion < cutoff_date,
            Licitacion.estado.in_(['CERRADA', 'ANULADA', 'DESISTIDA'])
        ).count()
        
        # Eliminar
        deleted = db.query(Licitacion).filter(
            Licitacion.fecha_actualizacion < cutoff_date,
            Licitacion.estado.in_(['CERRADA', 'ANULADA', 'DESISTIDA'])
        ).delete()
        
        db.commit()
        
        result = {
            'deleted': deleted,
            'days': days,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Limpieza completada: {deleted} licitaciones eliminadas")
        
        return result
    
    except Exception as e:
        logger.error(f"Error en limpieza de licitaciones: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()


@celery_app.task(name="app.tasks.scraping_tasks.test_task")
def test_task():
    """Tarea de prueba para verificar que Celery funciona"""
    logger.info("Ejecutando tarea de prueba")
    return {
        'status': 'success',
        'message': 'Celery está funcionando correctamente',
        'timestamp': datetime.now().isoformat()
    }

