"""
Aplicación principal de Liticia API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.config import settings

# Importar routers
from app.api.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de compresión
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Endpoint de salud para monitorización."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME
    }

# Root endpoint
@app.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "message": f"Bienvenido a {settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs"
    }

# Incluir routers de la API
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar la aplicación."""
    print(f"🚀 Iniciando {settings.PROJECT_NAME} API v{settings.VERSION}")
    # Aquí se pueden inicializar conexiones, caché, etc.

@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al cerrar la aplicación."""
    print(f"👋 Cerrando {settings.PROJECT_NAME} API")
    # Aquí se pueden cerrar conexiones, limpiar recursos, etc.

