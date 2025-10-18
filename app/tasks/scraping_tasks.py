"""
Tareas de Celery para scraping de licitaciones
"""
from celery import Task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.scrapers.placsp_scraper_v2 import PLACSPScraperV2
from app.models.licitacion import Licitacion
from app.services.licitacion_service import LicitacionService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


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
                    # Crear nueva
                    licitacion_service.create(lic_data)
                    nuevas += 1
                    logger.debug(f"Nueva licitación: {lic_data.get('expediente')}")
            
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
                    # Crear nueva
                    licitacion_service.create(lic_data)
                    nuevas += 1
                
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

