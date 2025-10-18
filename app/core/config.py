"""
Configuración principal de la aplicación Liticia.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación."""
    
    # Información del proyecto
    PROJECT_NAME: str = "Liticia"
    PROJECT_DESCRIPTION: str = "Inteligencia de Licitaciones TIC para la Administración Pública Española"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Base de datos
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300  # 5 minutos por defecto
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # OpenAI (Fase 1: Validación - Optimización de costes)
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"  # 85% más barato: $0.150/1M input, $0.600/1M output
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_TOKENS: int = 4000  # Reducido para ahorrar costes
    
    # Optimización de costes - Análisis selectivo
    MIN_BUDGET_FOR_AI_ANALYSIS: int = 50000  # Solo analizar licitaciones >€50k con IA
    AI_CACHE_TTL_DAYS: int = 30  # Cachear análisis IA por 30 días
    
    # DigitalOcean Spaces (S3-compatible)
    SPACES_ENDPOINT: str
    SPACES_REGION: str = "fra1"
    SPACES_KEY: str
    SPACES_SECRET: str
    SPACES_BUCKET: str = "liticia-docs"
    
    # Seguridad
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Scraping (Fase 1: Validación - Frecuencia reducida)
    SCRAPING_USER_AGENT: str = "Liticia Bot 1.0 (+https://liticia.com/bot)"
    SCRAPING_DELAY_SECONDS: int = 3  # Aumentado para reducir carga
    SCRAPING_CONCURRENT_REQUESTS: int = 1  # Reducido para ahorrar recursos
    SCRAPING_TIMEOUT_SECONDS: int = 30
    SCRAPING_INTERVAL_HOURS: int = 3  # Scraping cada 3 horas en lugar de cada 15-30 min
    
    # Procesamiento de documentos
    MAX_DOCUMENT_SIZE_MB: int = 50
    DOCUMENT_PROCESSING_TIMEOUT_SECONDS: int = 300
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Sentry (opcional)
    SENTRY_DSN: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Instancia global de configuración
settings = Settings()

