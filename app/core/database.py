"""
Configuración de base de datos con SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from typing import Generator

# Variables globales para lazy initialization
_engine = None
_SessionLocal = None

# Base para modelos
Base = declarative_base()

def get_engine():
    """Obtener engine de SQLAlchemy (lazy initialization)."""
    global _engine
    if _engine is None:
        # Convertir URL de postgresql:// a postgresql+psycopg:// para psycopg3
        db_url = settings.DATABASE_URL
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        
        _engine = create_engine(
            db_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verificar conexiones antes de usarlas
            echo=False,  # Cambiar a True para debug de queries
        )
    return _engine

def get_session_local():
    """Obtener SessionLocal (lazy initialization)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

# Dependency para obtener sesión de BD
def get_db() -> Generator:
    """
    Dependency que proporciona una sesión de base de datos.
    Se cierra automáticamente al finalizar la request.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

