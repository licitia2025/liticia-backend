"""
Configuración de base de datos con SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Crear engine de SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verificar conexiones antes de usarlas
    echo=False,  # Cambiar a True para debug de queries
)

# Crear SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# Dependency para obtener sesión de BD
def get_db():
    """
    Dependency que proporciona una sesión de base de datos.
    Se cierra automáticamente al finalizar la request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

