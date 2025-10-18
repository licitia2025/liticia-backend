"""
Schemas Pydantic para Licitaciones
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class LicitacionBase(BaseModel):
    """Schema base de Licitación"""
    titulo: Optional[str] = None
    expediente: Optional[str] = None
    estado: Optional[str] = None
    resumen: Optional[str] = None
    organo_contratacion: Optional[str] = None
    tipo_contrato: Optional[str] = None
    presupuesto_base: Optional[float] = None
    lugar_ejecucion: Optional[str] = None


class LicitacionCreate(LicitacionBase):
    """Schema para crear Licitación"""
    id_licitacion: str
    link: Optional[str] = None


class LicitacionUpdate(BaseModel):
    """Schema para actualizar Licitación"""
    titulo: Optional[str] = None
    estado: Optional[str] = None
    resumen: Optional[str] = None
    presupuesto_base: Optional[float] = None


class LicitacionListItem(BaseModel):
    """Schema para item en lista de licitaciones"""
    id: int
    titulo: str
    expediente: Optional[str] = None
    estado: Optional[str] = None
    organo_contratacion: Optional[str] = None
    tipo_contrato: Optional[str] = None
    presupuesto_base: Optional[float] = None
    lugar_ejecucion: Optional[str] = None
    fecha_limite_presentacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    conceptos_tic: Optional[List[str]] = None
    analizado_ia: bool = False
    
    class Config:
        from_attributes = True


class LicitacionDetail(LicitacionListItem):
    """Schema para detalle completo de licitación"""
    id_licitacion: str
    link: Optional[str] = None
    resumen: Optional[str] = None
    nif_organo: Optional[str] = None
    web_organo: Optional[str] = None
    email_organo: Optional[str] = None
    telefono_organo: Optional[str] = None
    ciudad_organo: Optional[str] = None
    codigo_postal_organo: Optional[str] = None
    tipo_contrato_codigo: Optional[str] = None
    codigos_cpv: Optional[List[str]] = None
    valor_estimado: Optional[float] = None
    codigo_nuts: Optional[str] = None
    duracion: Optional[str] = None
    duracion_unidad: Optional[str] = None
    procedimiento_codigo: Optional[str] = None
    financiacion_ue: Optional[str] = None
    hora_limite_presentacion: Optional[str] = None
    resultado_codigo: Optional[str] = None
    fecha_adjudicacion: Optional[datetime] = None
    adjudicatario: Optional[str] = None
    nif_adjudicatario: Optional[str] = None
    importe_adjudicacion: Optional[float] = None
    stack_tecnologico: Optional[Dict] = None
    resumen_tecnico: Optional[Dict] = None
    fecha_analisis_ia: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class LicitacionFilters(BaseModel):
    """Schema para filtros de búsqueda"""
    search: Optional[str] = Field(None, description="Búsqueda en título y descripción")
    estado: Optional[str] = Field(None, description="Estado de la licitación")
    tipo_contrato: Optional[str] = Field(None, description="Tipo de contrato")
    presupuesto_min: Optional[float] = Field(None, description="Presupuesto mínimo")
    presupuesto_max: Optional[float] = Field(None, description="Presupuesto máximo")
    lugar_ejecucion: Optional[str] = Field(None, description="Lugar de ejecución")
    conceptos_tic: Optional[List[str]] = Field(None, description="Conceptos TIC")
    tecnologias: Optional[List[str]] = Field(None, description="Tecnologías específicas")
    fecha_desde: Optional[datetime] = Field(None, description="Fecha desde")
    fecha_hasta: Optional[datetime] = Field(None, description="Fecha hasta")
    solo_analizadas_ia: Optional[bool] = Field(False, description="Solo licitaciones analizadas con IA")


class LicitacionListResponse(BaseModel):
    """Schema para respuesta de lista de licitaciones"""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[LicitacionListItem]


class EstadisticasResponse(BaseModel):
    """Schema para estadísticas de licitaciones"""
    total_licitaciones: int
    total_presupuesto: float
    presupuesto_promedio: float
    licitaciones_por_estado: Dict[str, int]
    licitaciones_por_tipo: Dict[str, int]
    licitaciones_por_concepto: Dict[str, int]
    top_tecnologias: List[Dict[str, int]]
    evolucion_mensual: List[Dict[str, any]]


class TecnologiaResponse(BaseModel):
    """Schema para tecnología"""
    nombre: str
    categoria: str
    count: int


class ConceptoResponse(BaseModel):
    """Schema para concepto TIC"""
    nombre: str
    count: int
    descripcion: Optional[str] = None

