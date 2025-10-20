"""
Endpoints de administración para tareas de mantenimiento
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.licitacion import Licitacion
from app.services.ai_service import AIService
import time

router = APIRouter()
ai_service = AIService()

@router.post("/generar-titulos-adaptados")
async def generar_titulos_adaptados(db: Session = Depends(get_db)):
    """
    Genera títulos adaptados con IA para todas las licitaciones que no los tienen.
    
    Este endpoint procesa todas las licitaciones sin titulo_adaptado y genera
    títulos más naturales y concisos usando IA.
    """
    
    try:
        # Obtener licitaciones sin titulo_adaptado
        licitaciones = db.query(Licitacion).filter(
            (Licitacion.titulo_adaptado == None) | (Licitacion.titulo_adaptado == '')
        ).all()
        
        total = len(licitaciones)
        
        if total == 0:
            return {
                "message": "Todas las licitaciones ya tienen título adaptado",
                "total": 0,
                "procesadas": 0,
                "exitosas": 0,
                "fallidas": 0
            }
        
        exitosas = 0
        fallidas = 0
        errores = []
        
        for licitacion in licitaciones:
            try:
                # Generar título adaptado
                titulo_adaptado = ai_service.generar_titulo_adaptado(
                    licitacion.titulo,
                    licitacion.resumen
                )
                
                # Actualizar en la base de datos
                licitacion.titulo_adaptado = titulo_adaptado
                db.commit()
                
                exitosas += 1
                
                # Pequeña pausa para no saturar la API de OpenAI
                time.sleep(0.5)
                
            except Exception as e:
                fallidas += 1
                errores.append({
                    "licitacion_id": licitacion.id,
                    "error": str(e)
                })
                db.rollback()
                continue
        
        return {
            "message": f"Proceso completado: {exitosas} títulos generados exitosamente",
            "total": total,
            "procesadas": total,
            "exitosas": exitosas,
            "fallidas": fallidas,
            "coste_estimado_usd": round(exitosas * 0.0001, 4),
            "errores": errores[:10] if errores else []  # Mostrar máximo 10 errores
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar títulos adaptados: {str(e)}"
        )

