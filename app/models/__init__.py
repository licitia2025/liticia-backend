"""
Modelos de base de datos.
"""
from app.models.licitacion import (
    Licitacion,
    Organismo,
    Tecnologia,
    ConceptoTIC,
    Documento,
    ResumenIA,
    Adjudicacion,
    ScrapingLog,
    licitaciones_tecnologias,
    licitaciones_conceptos,
)

__all__ = [
    "Licitacion",
    "Organismo",
    "Tecnologia",
    "ConceptoTIC",
    "Documento",
    "ResumenIA",
    "Adjudicacion",
    "ScrapingLog",
    "licitaciones_tecnologias",
    "licitaciones_conceptos",
]

