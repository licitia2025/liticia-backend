"""
Tareas de Celery para análisis con IA
"""
from celery import Task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.licitacion import Licitacion
from app.services.ai_service import AIService
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Tarea base que gestiona la sesión de base de datos"""
    _db = None

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()


@celery_app.task(base=DatabaseTask, bind=True, name="app.tasks.ai_tasks.analyze_pending_licitaciones")
def analyze_pending_licitaciones(self, limit: int = 20):
    """
    Analiza licitaciones pendientes con IA
    FASE 1: Solo analiza licitaciones con presupuesto >€50,000 para optimizar costes
    
    Args:
        limit: Número máximo de licitaciones a analizar
    """
    from app.core.config import settings
    
    logger.info(f"Iniciando análisis con IA de licitaciones pendientes (límite: {limit})")
    logger.info(f"FASE 1: Solo analizando licitaciones con presupuesto >€{settings.MIN_BUDGET_FOR_AI_ANALYSIS:,}")
    
    db = SessionLocal()
    self._db = db
    
    try:
        # Obtener licitaciones sin analizar Y con presupuesto suficiente (Fase 1 optimización)
        licitaciones = db.query(Licitacion).filter(
            Licitacion.analizado_ia == False,
            Licitacion.presupuesto_base >= settings.MIN_BUDGET_FOR_AI_ANALYSIS  # Solo >€50k
        ).limit(limit).all()
        
        # Contar las que se saltan por presupuesto bajo
        skipped_low_budget = db.query(Licitacion).filter(
            Licitacion.analizado_ia == False,
            Licitacion.presupuesto_base < settings.MIN_BUDGET_FOR_AI_ANALYSIS
        ).count()
        
        if skipped_low_budget > 0:
            logger.info(f"Saltando {skipped_low_budget} licitaciones con presupuesto <€{settings.MIN_BUDGET_FOR_AI_ANALYSIS:,}")
        
        analizadas = 0
        errores = 0
        
        ai_service = AIService()
        
        for lic in licitaciones:
            try:
                # Obtener texto del pliego si existe
                texto_pliego = None
                if lic.documentos:
                    # Buscar documento principal (pliego técnico)
                    for doc in lic.documentos:
                        if doc.procesado and doc.texto_extraido:
                            texto_pliego = doc.texto_extraido
                            break
                
                # Analizar con IA
                resultado = ai_service.analizar_licitacion_completa(
                    titulo=lic.titulo or '',
                    descripcion=lic.resumen or '',
                    texto_pliego=texto_pliego
                )
                
                if resultado:
                    # Guardar resultados del análisis
                    lic.stack_tecnologico = json.dumps(resultado['stack_tecnologico'])
                    lic.conceptos_tic = json.dumps(resultado['conceptos_tic'])
                    lic.resumen_tecnico = json.dumps(resultado['resumen_tecnico'])
                    lic.analizado_ia = True
                    lic.fecha_analisis_ia = datetime.now()
                    analizadas += 1
                    
                    logger.debug(f"Licitación analizada: {lic.expediente}")
                else:
                    logger.error(f"Error analizando licitación {lic.id}")
                    errores += 1
            
            except Exception as e:
                logger.error(f"Error analizando licitación {lic.id}: {e}")
                errores += 1
                continue
        
        db.commit()
        
        result = {
            'analizadas': analizadas,
            'errores': errores,
            'total': len(licitaciones),
            'skipped_low_budget': skipped_low_budget,
            'min_budget_threshold': settings.MIN_BUDGET_FOR_AI_ANALYSIS,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Análisis completado: {analizadas} analizadas, {errores} errores")
        
        return result
    
    except Exception as e:
        logger.error(f"Error en análisis con IA: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()

