"""
Router principal de la API
"""
from fastapi import APIRouter
from app.api.endpoints import licitaciones, health, admin

api_router = APIRouter()

# Incluir routers de endpoints
# Health check (sin prefijo para que esté en /health)
api_router.include_router(
    health.router,
    tags=["health"]
)

# Licitaciones
api_router.include_router(
    licitaciones.router,
    prefix="/licitaciones",
    tags=["licitaciones"]
)

# Admin
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"]
)

