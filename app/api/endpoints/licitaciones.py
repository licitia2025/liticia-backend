"""
Endpoints de la API para Licitaciones
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.licitacion import Licitacion
from app.schemas.licitacion_schema import (
    LicitacionListResponse,
    LicitacionListItem,
    LicitacionDetail,
    LicitacionFilters,
    EstadisticasResponse
)
from typing import List, Optional
import json
import logging
from sqlalchemy import func, or_, and_, extract
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=LicitacionListResponse)
def list_licitaciones(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    search: Optional[str] = Query(None, description="Búsqueda en título y descripción"),
    estado: Optional[str] = Query(None, description="Estado de la licitación"),
    tipo_contrato: Optional[str] = Query(None, description="Tipo de contrato"),
    presupuesto_min: Optional[float] = Query(None, description="Presupuesto mínimo"),
    presupuesto_max: Optional[float] = Query(None, description="Presupuesto máximo"),
    lugar_ejecucion: Optional[str] = Query(None, description="Lugar de ejecución"),
    concepto_tic: Optional[str] = Query(None, description="Concepto TIC"),
    tecnologia: Optional[str] = Query(None, description="Tecnología específica"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha desde"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha hasta"),
    solo_analizadas_ia: bool = Query(False, description="Solo licitaciones analizadas con IA"),
    db: Session = Depends(get_db)
):
    """
    Lista licitaciones con filtros y paginación
    """
    # Construir query base
    query = db.query(Licitacion)
    
    # Aplicar filtros
    if search:
        search_filter = or_(
            Licitacion.titulo.ilike(f"%{search}%"),
            Licitacion.resumen.ilike(f"%{search}%"),
            Licitacion.expediente.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    if estado:
        query = query.filter(Licitacion.estado == estado)
    
    if tipo_contrato:
        query = query.filter(Licitacion.tipo_contrato == tipo_contrato)
    
    if presupuesto_min is not None:
        query = query.filter(Licitacion.presupuesto_base >= presupuesto_min)
    
    if presupuesto_max is not None:
        query = query.filter(Licitacion.presupuesto_base <= presupuesto_max)
    
    if lugar_ejecucion:
        query = query.filter(Licitacion.lugar_ejecucion.ilike(f"%{lugar_ejecucion}%"))
    
    if concepto_tic:
        query = query.filter(Licitacion.conceptos_tic.ilike(f"%{concepto_tic}%"))
    
    if tecnologia:
        query = query.filter(Licitacion.stack_tecnologico.ilike(f"%{tecnologia}%"))
    
    if fecha_desde:
        query = query.filter(Licitacion.fecha_actualizacion >= fecha_desde)
    
    if fecha_hasta:
        query = query.filter(Licitacion.fecha_actualizacion <= fecha_hasta)
    
    if solo_analizadas_ia:
        query = query.filter(Licitacion.analizado_ia == True)
    
    # Contar total
    total = query.count()
    
    # Calcular paginación
    total_pages = (total + page_size - 1) // page_size
    skip = (page - 1) * page_size
    
    # Obtener resultados
    licitaciones = query.order_by(Licitacion.fecha_actualizacion.desc()).offset(skip).limit(page_size).all()
    
    # Convertir a schema
    items = []
    for lic in licitaciones:
        item = LicitacionListItem.model_validate(lic)
        
        # Parsear conceptos TIC si existen
        if lic.conceptos_tic:
            # SQLAlchemy ya devuelve el JSON parseado
            item.conceptos_tic = lic.conceptos_tic if isinstance(lic.conceptos_tic, list) else []
        
        items.append(item)
    
    return LicitacionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items
    )


@router.get("/{licitacion_id}", response_model=LicitacionDetail)
def get_licitacion(
    licitacion_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene el detalle completo de una licitación
    """
    licitacion = db.query(Licitacion).filter(Licitacion.id == licitacion_id).first()
    
    if not licitacion:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")
    
    # Parsear campos antes de la validación de Pydantic
    # Convertir codigos_cpv de string a lista
    if licitacion.codigos_cpv and isinstance(licitacion.codigos_cpv, str):
        try:
            licitacion.codigos_cpv = json.loads(licitacion.codigos_cpv)
        except:
            licitacion.codigos_cpv = []
    
    # Convertir duracion de int a string
    if licitacion.duracion and isinstance(licitacion.duracion, int):
        licitacion.duracion = str(licitacion.duracion)
    
    # Convertir a schema
    detail = LicitacionDetail.model_validate(licitacion)
    
    return detail


@router.get("/stats/general", response_model=EstadisticasResponse)
def get_estadisticas(
    fecha_desde: Optional[datetime] = Query(None, description="Fecha desde"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha hasta"),
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas generales de licitaciones
    """
    # Query base
    query = db.query(Licitacion)
    
    # Aplicar filtros de fecha
    if fecha_desde:
        query = query.filter(Licitacion.fecha_actualizacion >= fecha_desde)
    
    if fecha_hasta:
        query = query.filter(Licitacion.fecha_actualizacion <= fecha_hasta)
    
    # Total de licitaciones
    total_licitaciones = query.count()
    
    # Total y promedio de presupuesto
    presupuesto_stats = query.with_entities(
        func.sum(Licitacion.presupuesto_base),
        func.avg(Licitacion.presupuesto_base)
    ).filter(Licitacion.presupuesto_base.isnot(None)).first()
    
    total_presupuesto = float(presupuesto_stats[0] or 0)
    presupuesto_promedio = float(presupuesto_stats[1] or 0)
    
    # Licitaciones por estado
    licitaciones_por_estado = {}
    estados = query.with_entities(
        Licitacion.estado,
        func.count(Licitacion.id)
    ).filter(Licitacion.estado.isnot(None)).group_by(Licitacion.estado).all()
    
    for estado, count in estados:
        licitaciones_por_estado[estado] = count
    
    # Licitaciones por tipo
    licitaciones_por_tipo = {}
    tipos = query.with_entities(
        Licitacion.tipo_contrato,
        func.count(Licitacion.id)
    ).filter(Licitacion.tipo_contrato.isnot(None)).group_by(Licitacion.tipo_contrato).all()
    
    for tipo, count in tipos:
        licitaciones_por_tipo[tipo] = count
    
    # Licitaciones por concepto (requiere parsear JSON)
    licitaciones_por_concepto = {}
    conceptos_lics = query.filter(Licitacion.conceptos_tic.isnot(None)).all()
    
    for lic in conceptos_lics:
        try:
            # SQLAlchemy ya devuelve el JSON parseado
            conceptos = lic.conceptos_tic if isinstance(lic.conceptos_tic, list) else []
            for concepto in conceptos:
                licitaciones_por_concepto[concepto] = licitaciones_por_concepto.get(concepto, 0) + 1
        except:
            pass
    
    # Top tecnologías
    top_tecnologias = []
    tecnologias_count = {}
    stack_lics = query.filter(Licitacion.stack_tecnologico.isnot(None)).all()
    
    for lic in stack_lics:
        try:
            # SQLAlchemy ya devuelve el JSON parseado
            stack = lic.stack_tecnologico if isinstance(lic.stack_tecnologico, dict) else {}
            for categoria, tecnologias in stack.items():
                for tech in tecnologias:
                    tecnologias_count[tech] = tecnologias_count.get(tech, 0) + 1
        except:
            pass
    
    # Ordenar y tomar top 10
    top_tecnologias = [
        {"nombre": tech, "count": count}
        for tech, count in sorted(tecnologias_count.items(), key=lambda x: x[1], reverse=True)[:10]
    ]
    
    # Evolución mensual (últimos 12 meses)
    evolucion_mensual = []
    for i in range(12, 0, -1):
        mes_inicio = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30*i)
        mes_fin = mes_inicio + timedelta(days=30)
        
        count = db.query(Licitacion).filter(
            and_(
                Licitacion.fecha_actualizacion >= mes_inicio,
                Licitacion.fecha_actualizacion < mes_fin
            )
        ).count()
        
        evolucion_mensual.append({
            "mes": mes_inicio.strftime("%Y-%m"),
            "count": count
        })
    
    return EstadisticasResponse(
        total_licitaciones=total_licitaciones,
        total_presupuesto=total_presupuesto,
        presupuesto_promedio=presupuesto_promedio,
        licitaciones_por_estado=licitaciones_por_estado,
        licitaciones_por_tipo=licitaciones_por_tipo,
        licitaciones_por_concepto=licitaciones_por_concepto,
        top_tecnologias=top_tecnologias,
        evolucion_mensual=evolucion_mensual
    )

