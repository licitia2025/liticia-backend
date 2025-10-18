"""
Modelos de base de datos para licitaciones.
"""
from sqlalchemy import Column, Integer, String, Text, DECIMAL, TIMESTAMP, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


# Tabla de asociación licitaciones <-> tecnologías
licitaciones_tecnologias = Table(
    'licitaciones_tecnologias',
    Base.metadata,
    Column('licitacion_id', Integer, ForeignKey('licitaciones.id', ondelete='CASCADE'), primary_key=True),
    Column('tecnologia_id', Integer, ForeignKey('tecnologias.id', ondelete='CASCADE'), primary_key=True),
    Column('confianza', DECIMAL(3, 2), nullable=True)
)

# Tabla de asociación licitaciones <-> conceptos
licitaciones_conceptos = Table(
    'licitaciones_conceptos',
    Base.metadata,
    Column('licitacion_id', Integer, ForeignKey('licitaciones.id', ondelete='CASCADE'), primary_key=True),
    Column('concepto_id', Integer, ForeignKey('conceptos_tic.id', ondelete='CASCADE'), primary_key=True),
    Column('relevancia', String(20), nullable=True),  # principal, secundario
    Column('confianza', DECIMAL(3, 2), nullable=True)
)


class Licitacion(Base):
    """Modelo de Licitación."""
    __tablename__ = 'licitaciones'
    
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(Text, nullable=False)
    descripcion = Column(Text, nullable=True)
    organismo_id = Column(Integer, ForeignKey('organismos.id'), nullable=True)
    presupuesto_base = Column(DECIMAL(12, 2), nullable=True, index=True)
    fecha_publicacion = Column(TIMESTAMP, nullable=True, index=True)
    fecha_vencimiento = Column(TIMESTAMP, nullable=True, index=True)
    tipo_contrato = Column(String(50), nullable=True)
    procedimiento = Column(String(100), nullable=True)
    codigo_cpv = Column(String(20), nullable=True)
    ubicacion_ccaa = Column(String(50), nullable=True, index=True)
    ubicacion_provincia = Column(String(50), nullable=True)
    ubicacion_municipio = Column(String(100), nullable=True)
    estado = Column(String(20), nullable=True, index=True)  # activa, adjudicada, cancelada
    url_fuente = Column(Text, nullable=True)
    fuente = Column(String(100), nullable=True)  # PLACSP, Cataluña, etc.
    hash_contenido = Column(String(64), nullable=True, unique=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    organismo = relationship("Organismo", back_populates="licitaciones")
    tecnologias = relationship("Tecnologia", secondary=licitaciones_tecnologias, back_populates="licitaciones")
    conceptos = relationship("ConceptoTIC", secondary=licitaciones_conceptos, back_populates="licitaciones")
    documentos = relationship("Documento", back_populates="licitacion", cascade="all, delete-orphan")
    resumen_ia = relationship("ResumenIA", back_populates="licitacion", uselist=False, cascade="all, delete-orphan")
    adjudicaciones = relationship("Adjudicacion", back_populates="licitacion", cascade="all, delete-orphan")


class Organismo(Base):
    """Modelo de Organismo licitador."""
    __tablename__ = 'organismos'
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(Text, nullable=False)
    tipo = Column(String(50), nullable=True)  # ministerio, ayuntamiento, universidad, etc.
    ccaa = Column(String(50), nullable=True)
    provincia = Column(String(50), nullable=True)
    url_perfil = Column(Text, nullable=True)
    contacto_email = Column(String(255), nullable=True)
    contacto_telefono = Column(String(50), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relaciones
    licitaciones = relationship("Licitacion", back_populates="organismo")


class Tecnologia(Base):
    """Modelo de Tecnología."""
    __tablename__ = 'tecnologias'
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    categoria = Column(String(50), nullable=True)  # lenguaje, framework, cloud, database, etc.
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relaciones
    licitaciones = relationship("Licitacion", secondary=licitaciones_tecnologias, back_populates="tecnologias")


class ConceptoTIC(Base):
    """Modelo de Concepto TIC."""
    __tablename__ = 'conceptos_tic'
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relaciones
    licitaciones = relationship("Licitacion", secondary=licitaciones_conceptos, back_populates="conceptos")


class Documento(Base):
    """Modelo de Documento asociado a licitación."""
    __tablename__ = 'documentos'
    
    id = Column(Integer, primary_key=True, index=True)
    licitacion_id = Column(Integer, ForeignKey('licitaciones.id', ondelete='CASCADE'), nullable=False, index=True)
    tipo = Column(String(50), nullable=True)  # pliego_tecnico, pliego_administrativo, anexo, etc.
    nombre_archivo = Column(String(255), nullable=True)
    url_descarga = Column(Text, nullable=True)
    ruta_local = Column(Text, nullable=True)
    tamano_bytes = Column(Integer, nullable=True)
    hash_archivo = Column(String(64), nullable=True)
    texto_extraido = Column(Text, nullable=True)
    procesado = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relaciones
    licitacion = relationship("Licitacion", back_populates="documentos")


class ResumenIA(Base):
    """Modelo de Resumen generado por IA."""
    __tablename__ = 'resumenes_ia'
    
    id = Column(Integer, primary_key=True, index=True)
    licitacion_id = Column(Integer, ForeignKey('licitaciones.id', ondelete='CASCADE'), nullable=False, unique=True)
    resumen_tecnico = Column(Text, nullable=True)
    requisitos_principales = Column(Text, nullable=True)  # JSON array como texto
    nivel_complejidad = Column(String(20), nullable=True)  # bajo, medio, alto
    modelo_usado = Column(String(50), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relaciones
    licitacion = relationship("Licitacion", back_populates="resumen_ia")


class Adjudicacion(Base):
    """Modelo de Adjudicación (histórico)."""
    __tablename__ = 'adjudicaciones'
    
    id = Column(Integer, primary_key=True, index=True)
    licitacion_id = Column(Integer, ForeignKey('licitaciones.id'), nullable=True)
    empresa_adjudicataria = Column(String(255), nullable=True)
    precio_adjudicacion = Column(DECIMAL(12, 2), nullable=True)
    porcentaje_baja = Column(DECIMAL(5, 2), nullable=True)
    fecha_adjudicacion = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relaciones
    licitacion = relationship("Licitacion", back_populates="adjudicaciones")


class ScrapingLog(Base):
    """Modelo de Log de scraping."""
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    fuente = Column(String(100), nullable=True, index=True)
    url = Column(Text, nullable=True)
    estado = Column(String(20), nullable=True)  # success, error, partial
    licitaciones_nuevas = Column(Integer, default=0)
    licitaciones_actualizadas = Column(Integer, default=0)
    errores = Column(Text, nullable=True)
    tiempo_ejecucion = Column(Integer, nullable=True)  # segundos
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

