"""
Servicio para gestionar licitaciones
"""
from sqlalchemy.orm import Session
from app.models.licitacion import Licitacion
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class LicitacionService:
    """Servicio para operaciones CRUD de licitaciones"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, licitacion_data: Dict) -> Licitacion:
        """
        Crea una nueva licitación
        
        Args:
            licitacion_data: Diccionario con datos de la licitación
            
        Returns:
            Licitación creada
        """
        # Convertir fechas de string a datetime si es necesario
        if 'fecha_actualizacion' in licitacion_data and isinstance(licitacion_data['fecha_actualizacion'], str):
            try:
                licitacion_data['fecha_actualizacion'] = datetime.fromisoformat(
                    licitacion_data['fecha_actualizacion'].replace('+02:00', '').replace('+01:00', '')
                )
            except Exception as e:
                logger.warning(f"Error parseando fecha_actualizacion: {e}")
                licitacion_data['fecha_actualizacion'] = datetime.now()
        
        if 'fecha_limite_presentacion' in licitacion_data and isinstance(licitacion_data['fecha_limite_presentacion'], str):
            try:
                licitacion_data['fecha_limite_presentacion'] = datetime.fromisoformat(
                    licitacion_data['fecha_limite_presentacion'].replace('+02:00', '').replace('+01:00', '')
                )
            except Exception:
                pass
        
        if 'fecha_adjudicacion' in licitacion_data and isinstance(licitacion_data['fecha_adjudicacion'], str):
            try:
                licitacion_data['fecha_adjudicacion'] = datetime.fromisoformat(
                    licitacion_data['fecha_adjudicacion'].replace('+02:00', '').replace('+01:00', '')
                )
            except Exception:
                pass
        
        # Convertir lista de CPV a string JSON si es necesario
        if 'codigos_cpv' in licitacion_data and isinstance(licitacion_data['codigos_cpv'], list):
            import json
            licitacion_data['codigos_cpv'] = json.dumps(licitacion_data['codigos_cpv'])
        
        # Extraer documentos antes de crear la licitación
        documentos_data = licitacion_data.pop('documentos', [])
        
        licitacion = Licitacion(**licitacion_data)
        self.db.add(licitacion)
        self.db.flush()
        
        # Crear documentos adjuntos si existen
        if documentos_data:
            from app.models.licitacion import Documento
            for doc_data in documentos_data:
                documento = Documento(
                    licitacion_id=licitacion.id,
                    nombre=doc_data.get('nombre'),
                    tipo=doc_data.get('tipo'),
                    url_descarga=doc_data.get('url')
                )
                self.db.add(documento)
            logger.info(f"Guardados {len(documentos_data)} documentos para licitación {licitacion.expediente}")
        
        logger.info(f"Licitación creada: {licitacion.expediente}")
        
        return licitacion
    
    def get_by_id(self, licitacion_id: int) -> Optional[Licitacion]:
        """Obtiene una licitación por su ID"""
        return self.db.query(Licitacion).filter(Licitacion.id == licitacion_id).first()
    
    def get_by_id_licitacion(self, id_licitacion: str) -> Optional[Licitacion]:
        """Obtiene una licitación por su ID de licitación (del feed)"""
        return self.db.query(Licitacion).filter(Licitacion.id_licitacion == id_licitacion).first()
    
    def get_by_expediente(self, expediente: str) -> Optional[Licitacion]:
        """Obtiene una licitación por su número de expediente"""
        return self.db.query(Licitacion).filter(Licitacion.expediente == expediente).first()
    
    def buscar_posibles_duplicados(
        self,
        titulo: str,
        presupuesto: Optional[float],
        fecha_publicacion: Optional[datetime],
        dias_margen: int = 7
    ) -> List[Licitacion]:
        """
        Busca licitaciones que puedan ser duplicadas basándose en similitud
        
        Args:
            titulo: Título de la licitación
            presupuesto: Presupuesto de la licitación
            fecha_publicacion: Fecha de publicación
            dias_margen: Margen de días para buscar licitaciones similares
        
        Returns:
            Lista de licitaciones potencialmente duplicadas
        """
        query = self.db.query(Licitacion)
        
        # Filtrar por fecha (± días_margen)
        if fecha_publicacion:
            fecha_desde = fecha_publicacion - timedelta(days=dias_margen)
            fecha_hasta = fecha_publicacion + timedelta(days=dias_margen)
            query = query.filter(
                Licitacion.fecha_actualizacion >= fecha_desde,
                Licitacion.fecha_actualizacion <= fecha_hasta
            )
        
        # Filtrar por presupuesto similar (±10%)
        if presupuesto and presupuesto > 0:
            presupuesto_min = presupuesto * 0.9
            presupuesto_max = presupuesto * 1.1
            query = query.filter(
                Licitacion.presupuesto_base >= presupuesto_min,
                Licitacion.presupuesto_base <= presupuesto_max
            )
        
        return query.all()
    
    def update(self, licitacion_id: int, licitacion_data: Dict) -> bool:
        """
        Actualiza una licitación existente
        
        Args:
            licitacion_id: ID de la licitación
            licitacion_data: Diccionario con datos actualizados
            
        Returns:
            True si se actualizó, False si no hubo cambios
        """
        licitacion = self.get_by_id(licitacion_id)
        if not licitacion:
            return False
        
        # Verificar si hay cambios reales
        has_changes = False
        
        for key, value in licitacion_data.items():
            if hasattr(licitacion, key):
                current_value = getattr(licitacion, key)
                if current_value != value:
                    setattr(licitacion, key, value)
                    has_changes = True
        
        if has_changes:
            licitacion.updated_at = datetime.now()
            self.db.flush()
            logger.info(f"Licitación actualizada: {licitacion.expediente}")
        
        return has_changes
    
    def delete(self, licitacion_id: int) -> bool:
        """Elimina una licitación"""
        licitacion = self.get_by_id(licitacion_id)
        if not licitacion:
            return False
        
        self.db.delete(licitacion)
        self.db.flush()
        
        logger.info(f"Licitación eliminada: {licitacion.expediente}")
        
        return True
    
    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        estado: Optional[str] = None,
        tipo_contrato: Optional[str] = None,
        presupuesto_min: Optional[float] = None,
        presupuesto_max: Optional[float] = None,
    ) -> List[Licitacion]:
        """
        Lista licitaciones con filtros opcionales
        
        Args:
            skip: Número de registros a saltar
            limit: Número máximo de registros a devolver
            estado: Filtrar por estado
            tipo_contrato: Filtrar por tipo de contrato
            presupuesto_min: Presupuesto mínimo
            presupuesto_max: Presupuesto máximo
            
        Returns:
            Lista de licitaciones
        """
        query = self.db.query(Licitacion)
        
        if estado:
            query = query.filter(Licitacion.estado == estado)
        
        if tipo_contrato:
            query = query.filter(Licitacion.tipo_contrato == tipo_contrato)
        
        if presupuesto_min is not None:
            query = query.filter(Licitacion.presupuesto_base >= presupuesto_min)
        
        if presupuesto_max is not None:
            query = query.filter(Licitacion.presupuesto_base <= presupuesto_max)
        
        return query.order_by(Licitacion.fecha_actualizacion.desc()).offset(skip).limit(limit).all()
    
    def count(
        self,
        estado: Optional[str] = None,
        tipo_contrato: Optional[str] = None,
        presupuesto_min: Optional[float] = None,
        presupuesto_max: Optional[float] = None,
    ) -> int:
        """Cuenta licitaciones con filtros opcionales"""
        query = self.db.query(Licitacion)
        
        if estado:
            query = query.filter(Licitacion.estado == estado)
        
        if tipo_contrato:
            query = query.filter(Licitacion.tipo_contrato == tipo_contrato)
        
        if presupuesto_min is not None:
            query = query.filter(Licitacion.presupuesto_base >= presupuesto_min)
        
        if presupuesto_max is not None:
            query = query.filter(Licitacion.presupuesto_base <= presupuesto_max)
        
        return query.count()

