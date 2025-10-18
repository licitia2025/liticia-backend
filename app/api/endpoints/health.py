"""
Health check endpoint para monitoreo
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Health check endpoint para Render y monitoreo
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "liticia-backend"
    }

