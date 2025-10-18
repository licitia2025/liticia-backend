"""
Tareas de Celery para procesamiento de documentos
"""
from celery import Task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.licitacion import Licitacion
from app.models.documento import Documento
from app.services.document_service import DocumentService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Tarea base que gestiona la sesión de base de datos"""
    _db = None

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()


@celery_app.task(base=DatabaseTask, bind=True, name="app.tasks.processing_tasks.process_pending_documents")
def process_pending_documents(self, limit: int = 10):
    """
    Procesa documentos pendientes (descarga y extracción de texto)
    
    Args:
        limit: Número máximo de documentos a procesar
    """
    logger.info(f"Iniciando procesamiento de documentos pendientes (límite: {limit})")
    
    db = SessionLocal()
    self._db = db
    
    try:
        # Obtener documentos pendientes
        documentos = db.query(Documento).filter(
            Documento.procesado == False
        ).limit(limit).all()
        
        procesados = 0
        errores = 0
        
        document_service = DocumentService()
        
        for doc in documentos:
            try:
                # Procesar documento
                result = document_service.process_document(doc.url, doc.licitacion_id)
                
                if result:
                    # Actualizar documento con información procesada
                    doc.url_spaces = result['url_spaces']
                    doc.texto_extraido = result['texto']
                    doc.num_paginas = result['num_paginas']
                    doc.procesado = True
                    doc.fecha_procesamiento = datetime.now()
                    procesados += 1
                    
                    logger.debug(f"Documento procesado: {doc.nombre}")
                else:
                    logger.error(f"Error procesando documento {doc.id}")
                    errores += 1
            
            except Exception as e:
                logger.error(f"Error procesando documento {doc.id}: {e}")
                errores += 1
                continue
        
        db.commit()
        
        result = {
            'procesados': procesados,
            'errores': errores,
            'total': len(documentos),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Procesamiento completado: {procesados} procesados, {errores} errores")
        
        return result
    
    except Exception as e:
        logger.error(f"Error en procesamiento de documentos: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()

