"""
Servicio para detectar licitaciones duplicadas entre diferentes fuentes
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """
    Servicio para detectar y fusionar licitaciones duplicadas de diferentes fuentes
    """
    
    # Umbrales de similitud
    UMBRAL_EXPEDIENTE = 0.8  # 80% de similitud en código de expediente
    UMBRAL_TITULO = 0.85     # 85% de similitud en título
    UMBRAL_PRESUPUESTO = 0.05  # 5% de diferencia en presupuesto
    UMBRAL_FECHA = 7  # 7 días de diferencia en fechas
    
    def __init__(self):
        """Inicializa el servicio"""
        pass
    
    def _similitud_texto(self, texto1: str, texto2: str) -> float:
        """
        Calcula la similitud entre dos textos usando SequenceMatcher
        
        Args:
            texto1: Primer texto
            texto2: Segundo texto
        
        Returns:
            Valor entre 0 y 1 indicando similitud
        """
        if not texto1 or not texto2:
            return 0.0
        
        # Normalizar textos
        t1 = texto1.lower().strip()
        t2 = texto2.lower().strip()
        
        # Calcular similitud
        return SequenceMatcher(None, t1, t2).ratio()
    
    def _similitud_presupuesto(self, presupuesto1: Optional[float], presupuesto2: Optional[float]) -> float:
        """
        Calcula la similitud entre dos presupuestos
        
        Args:
            presupuesto1: Primer presupuesto
            presupuesto2: Segundo presupuesto
        
        Returns:
            Valor entre 0 y 1 indicando similitud
        """
        if presupuesto1 is None or presupuesto2 is None:
            return 0.0
        
        if presupuesto1 == 0 or presupuesto2 == 0:
            return 0.0
        
        # Calcular diferencia porcentual
        diferencia = abs(presupuesto1 - presupuesto2) / max(presupuesto1, presupuesto2)
        
        # Convertir a similitud (1 - diferencia)
        return 1.0 - min(diferencia, 1.0)
    
    def _similitud_fecha(self, fecha1: Optional[datetime], fecha2: Optional[datetime]) -> float:
        """
        Calcula la similitud entre dos fechas
        
        Args:
            fecha1: Primera fecha
            fecha2: Segunda fecha
        
        Returns:
            Valor entre 0 y 1 indicando similitud
        """
        if fecha1 is None or fecha2 is None:
            return 0.0
        
        # Calcular diferencia en días
        diferencia_dias = abs((fecha1 - fecha2).days)
        
        # Si la diferencia es mayor al umbral, no son similares
        if diferencia_dias > self.UMBRAL_FECHA:
            return 0.0
        
        # Convertir a similitud (1 - diferencia/umbral)
        return 1.0 - (diferencia_dias / self.UMBRAL_FECHA)
    
    def son_duplicadas(
        self,
        licitacion1: Dict[str, Any],
        licitacion2: Dict[str, Any]
    ) -> bool:
        """
        Determina si dos licitaciones son duplicadas
        
        Args:
            licitacion1: Primera licitación
            licitacion2: Segunda licitación
        
        Returns:
            True si son duplicadas, False en caso contrario
        """
        # Si son de la misma fuente, no pueden ser duplicadas (tienen IDs únicos)
        if licitacion1.get('fuente') == licitacion2.get('fuente'):
            return False
        
        # Calcular similitudes
        sim_expediente = self._similitud_texto(
            licitacion1.get('expediente', ''),
            licitacion2.get('expediente', '')
        )
        
        sim_titulo = self._similitud_texto(
            licitacion1.get('titulo', ''),
            licitacion2.get('titulo', '')
        )
        
        sim_presupuesto = self._similitud_presupuesto(
            licitacion1.get('presupuesto_base'),
            licitacion2.get('presupuesto_base')
        )
        
        sim_fecha = self._similitud_fecha(
            licitacion1.get('fecha_publicacion'),
            licitacion2.get('fecha_publicacion')
        )
        
        # Criterios de duplicación (deben cumplirse al menos 2 de 3):
        criterios_cumplidos = 0
        
        # Criterio 1: Expediente muy similar
        if sim_expediente >= self.UMBRAL_EXPEDIENTE:
            criterios_cumplidos += 1
            logger.debug(f"Criterio expediente cumplido: {sim_expediente:.2f}")
        
        # Criterio 2: Título muy similar Y presupuesto similar
        if sim_titulo >= self.UMBRAL_TITULO and sim_presupuesto >= (1 - self.UMBRAL_PRESUPUESTO):
            criterios_cumplidos += 1
            logger.debug(f"Criterio título+presupuesto cumplido: título={sim_titulo:.2f}, presupuesto={sim_presupuesto:.2f}")
        
        # Criterio 3: Título muy similar Y fecha similar
        if sim_titulo >= self.UMBRAL_TITULO and sim_fecha >= 0.7:
            criterios_cumplidos += 1
            logger.debug(f"Criterio título+fecha cumplido: título={sim_titulo:.2f}, fecha={sim_fecha:.2f}")
        
        es_duplicada = criterios_cumplidos >= 2
        
        if es_duplicada:
            logger.info(
                f"Duplicado detectado: {licitacion1.get('fuente')}/{licitacion1.get('expediente')} "
                f"<-> {licitacion2.get('fuente')}/{licitacion2.get('expediente')}"
            )
        
        return es_duplicada
    
    def fusionar_licitaciones(
        self,
        licitacion_principal: Dict[str, Any],
        licitacion_secundaria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fusiona dos licitaciones duplicadas, priorizando la información más completa
        
        Args:
            licitacion_principal: Licitación que se mantendrá
            licitacion_secundaria: Licitación que se fusionará
        
        Returns:
            Licitación fusionada con la mejor información de ambas
        """
        fusionada = licitacion_principal.copy()
        
        # Añadir fuente secundaria a metadatos
        fusionada['fuentes_adicionales'] = fusionada.get('fuentes_adicionales', [])
        fusionada['fuentes_adicionales'].append({
            'fuente': licitacion_secundaria.get('fuente'),
            'id_licitacion': licitacion_secundaria.get('id_licitacion'),
            'url': licitacion_secundaria.get('url')
        })
        
        # Fusionar documentos (sin duplicar)
        docs_principal = fusionada.get('documentos', [])
        docs_secundaria = licitacion_secundaria.get('documentos', [])
        
        # Añadir documentos de la secundaria que no estén en la principal
        nombres_existentes = {doc.get('nombre') for doc in docs_principal}
        for doc in docs_secundaria:
            if doc.get('nombre') not in nombres_existentes:
                docs_principal.append(doc)
        
        fusionada['documentos'] = docs_principal
        
        # Completar campos vacíos con información de la secundaria
        for campo in ['resumen', 'organo_contratacion', 'tipo_contrato', 'procedimiento',
                      'presupuesto_base', 'valor_estimado', 'fecha_limite', 'cpv', 
                      'lugar_ejecucion']:
            if not fusionada.get(campo) and licitacion_secundaria.get(campo):
                fusionada[campo] = licitacion_secundaria[campo]
        
        logger.info(
            f"Licitaciones fusionadas: {licitacion_principal.get('id_licitacion')} "
            f"+ {licitacion_secundaria.get('id_licitacion')}"
        )
        
        return fusionada
    
    def detectar_duplicados_en_lista(
        self,
        licitaciones: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detecta y fusiona duplicados en una lista de licitaciones
        
        Args:
            licitaciones: Lista de licitaciones
        
        Returns:
            Lista de licitaciones sin duplicados
        """
        if not licitaciones:
            return []
        
        # Ordenar por fuente para priorizar (PLACSP primero por tener PDFs)
        prioridad_fuentes = {'PLACSP': 0, 'GENCAT': 1}
        licitaciones_ordenadas = sorted(
            licitaciones,
            key=lambda x: prioridad_fuentes.get(x.get('fuente', ''), 999)
        )
        
        licitaciones_unicas = []
        indices_procesados = set()
        
        for i, lic1 in enumerate(licitaciones_ordenadas):
            if i in indices_procesados:
                continue
            
            # Buscar duplicados
            duplicados = []
            for j, lic2 in enumerate(licitaciones_ordenadas[i+1:], start=i+1):
                if j in indices_procesados:
                    continue
                
                if self.son_duplicadas(lic1, lic2):
                    duplicados.append(j)
                    indices_procesados.add(j)
            
            # Si hay duplicados, fusionar
            if duplicados:
                lic_fusionada = lic1.copy()
                for idx in duplicados:
                    lic_fusionada = self.fusionar_licitaciones(
                        lic_fusionada,
                        licitaciones_ordenadas[idx]
                    )
                licitaciones_unicas.append(lic_fusionada)
            else:
                licitaciones_unicas.append(lic1)
            
            indices_procesados.add(i)
        
        logger.info(
            f"Detección de duplicados completada: {len(licitaciones)} licitaciones -> "
            f"{len(licitaciones_unicas)} únicas ({len(licitaciones) - len(licitaciones_unicas)} duplicados eliminados)"
        )
        
        return licitaciones_unicas

