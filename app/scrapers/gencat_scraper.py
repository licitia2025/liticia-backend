"""
Scraper para la Plataforma de Contratación Pública de Cataluña (Gencat)
Utiliza SODA API (Socrata Open Data API)
"""
import requests
from datetime import datetime, timedelta
from typing import Generator, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GencatScraper:
    """
    Scraper para licitaciones de la Generalitat de Catalunya
    
    Fuente: Plataforma de Serveis de Contractació Pública (PSCP)
    API: SODA (Socrata Open Data API)
    Dataset: ybgg-dgi6 (1.45M registros)
    """
    
    BASE_URL = "https://analisi.transparenciacatalunya.cat/resource/ybgg-dgi6.json"
    
    # Códigos CPV relacionados con TIC
    CPV_TIC = [
        "48000000-8",  # Paquetes de software y sistemas de información
        "48100000-9",  # Paquetes de software de la industria específica
        "48200000-0",  # Paquetes de software de red, Internet e intranet
        "48300000-1",  # Paquetes de software de documentación
        "48400000-2",  # Paquetes de software de transacciones comerciales
        "48500000-3",  # Paquetes de software de comunicación y multimedia
        "48600000-4",  # Paquetes de software de bases de datos y operativos
        "48700000-5",  # Paquetes de software de utilidades y aplicaciones
        "48800000-6",  # Sistemas de información
        "48900000-7",  # Paquetes de software de correo electrónico y mensajería
        "72000000-5",  # Servicios de tecnología de la información: consultoría, desarrollo de software, Internet y apoyo
        "72100000-6",  # Servicios de consultoría en equipo y programas de informática
        "72200000-7",  # Servicios de programación de software y de consultoría
        "72300000-8",  # Servicios de datos
        "72400000-4",  # Servicios de Internet
        "72500000-0",  # Servicios informáticos
        "72600000-1",  # Servicios de apoyo informático y de consultoría
    ]
    
    # Keywords TIC en catalán
    KEYWORDS_TIC = [
        "programari", "software", "aplicació", "aplicación",
        "sistema informàtic", "sistema informático",
        "desenvolupament", "desarrollo",
        "base de dades", "base de datos",
        "tecnologia", "tecnología",
        "informàtica", "informática",
        "digital", "web", "app", "cloud",
        "ciberseguretat", "ciberseguridad",
        "intel·ligència artificial", "inteligencia artificial",
        "big data", "analítica", "analytics"
    ]
    
    def __init__(self):
        """Inicializa el scraper"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Liticia/1.0 (licitaciones TIC)',
            'Accept': 'application/json'
        })
    
    def _build_query_params(
        self,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        filtrar_tic: bool = True
    ) -> Dict[str, Any]:
        """
        Construye los parámetros de consulta para la API SODA
        
        Args:
            fecha_desde: Fecha desde la que buscar
            fecha_hasta: Fecha hasta la que buscar
            limit: Número máximo de resultados por página
            offset: Offset para paginación
            filtrar_tic: Si True, filtra solo licitaciones TIC
        
        Returns:
            Diccionario con parámetros de consulta
        """
        params = {
            "$limit": limit,
            "$offset": offset,
            "$order": "data_publicacio_anunci DESC"
        }
        
        # Construir condiciones WHERE
        where_conditions = []
        
        # Filtro de fechas
        if fecha_desde:
            fecha_str = fecha_desde.strftime("%Y-%m-%dT00:00:00.000")
            where_conditions.append(f"data_publicacio_anunci >= '{fecha_str}'")
        
        if fecha_hasta:
            fecha_str = fecha_hasta.strftime("%Y-%m-%dT23:59:59.999")
            where_conditions.append(f"data_publicacio_anunci <= '{fecha_str}'")
        
        # Filtro TIC por CPV
        if filtrar_tic and self.CPV_TIC:
            # En SODA API, usamos OR para múltiples condiciones de CPV
            cpv_conditions = " OR ".join([f"codi_cpv = '{cpv}'" for cpv in self.CPV_TIC])
            where_conditions.append(f"({cpv_conditions})")
        
        # Combinar condiciones
        if where_conditions:
            params["$where"] = " AND ".join(where_conditions)
        
        return params
    
    def _es_licitacion_tic(self, licitacion: Dict[str, Any]) -> bool:
        """
        Verifica si una licitación es relacionada con TIC
        
        Args:
            licitacion: Datos de la licitación
        
        Returns:
            True si es licitación TIC, False en caso contrario
        """
        # Verificar CPV
        cpv = licitacion.get('codi_cpv', '')
        if any(cpv.startswith(tic_cpv[:2]) for tic_cpv in self.CPV_TIC):
            return True
        
        # Verificar keywords en título y descripción
        titulo = (licitacion.get('denominacio', '') or '').lower()
        descripcion = (licitacion.get('objecte_contracte', '') or '').lower()
        texto_completo = f"{titulo} {descripcion}"
        
        return any(keyword.lower() in texto_completo for keyword in self.KEYWORDS_TIC)
    
    def _mapear_a_modelo_liticia(self, licitacion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapea los campos de Gencat al modelo de datos de Liticia
        
        Args:
            licitacion: Datos de la licitación de Gencat
        
        Returns:
            Diccionario con datos mapeados al modelo Liticia
        """
        expediente = licitacion.get('codi_expedient', '')
        
        # Construir ID único
        id_licitacion = f"GENCAT-{expediente}"
        
        # Mapear campos
        return {
            'id_licitacion': id_licitacion,
            'fuente': 'GENCAT',
            'expediente': expediente,
            'titulo': licitacion.get('denominacio', ''),
            'resumen': licitacion.get('objecte_contracte', ''),
            'organo_contratacion': licitacion.get('nom_organ', ''),
            'tipo_contrato': licitacion.get('tipus_contracte', ''),
            'procedimiento': licitacion.get('procediment', ''),
            'presupuesto_base': self._parse_float(licitacion.get('pressupost_licitacio_sense')),
            'valor_estimado': self._parse_float(licitacion.get('valor_estimat_contracte')),
            'fecha_publicacion': self._parse_datetime(licitacion.get('data_publicacio_anunci')),
            'fecha_limite': self._parse_datetime(licitacion.get('termini_presentacio_ofertes')),
            'cpv': licitacion.get('codi_cpv', ''),
            'lugar_ejecucion': licitacion.get('lloc_execucio', ''),
            'url': licitacion.get('enllac_publicacio', {}).get('url', ''),
            'estado': self._mapear_estado(licitacion.get('fase_publicacio', '')),
            'ambito': licitacion.get('nom_ambit', ''),
            'nuts': licitacion.get('codi_nuts', ''),
            'duracion_contrato': licitacion.get('durada_contracte', ''),
            'documentos': []  # Los documentos se procesarán por separado si es necesario
        }
    
    def _mapear_estado(self, fase: str) -> str:
        """Mapea la fase de Gencat al estado de Liticia"""
        fase_lower = fase.lower()
        
        if 'licitaci' in fase_lower or 'anunci' in fase_lower:
            return 'Publicada'
        elif 'adjudicaci' in fase_lower:
            return 'Adjudicada'
        elif 'formalitzaci' in fase_lower:
            return 'Formalizada'
        elif 'anulaci' in fase_lower:
            return 'Anulada'
        else:
            return 'Publicada'
    
    def _parse_float(self, value: Any) -> Optional[float]:
        """Convierte un valor a float de forma segura"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Convierte un string ISO a datetime de forma segura"""
        if not value:
            return None
        try:
            # Formato: "2023-07-18T14:00:00.000"
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    def scrape_all(
        self,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        max_results: int = 1000,
        filtrar_tic: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Scrapea licitaciones de Gencat
        
        Args:
            fecha_desde: Fecha desde la que buscar (por defecto: hace 30 días)
            fecha_hasta: Fecha hasta la que buscar (por defecto: hoy)
            max_results: Número máximo de resultados a devolver
            filtrar_tic: Si True, filtra solo licitaciones TIC
        
        Yields:
            Diccionarios con datos de licitaciones
        """
        # Valores por defecto de fechas
        if fecha_desde is None:
            fecha_desde = datetime.now() - timedelta(days=30)
        
        if fecha_hasta is None:
            fecha_hasta = datetime.now()
        
        logger.info(f"Scraping Gencat desde {fecha_desde.date()} hasta {fecha_hasta.date()}")
        logger.info(f"Filtrar TIC: {filtrar_tic}")
        
        offset = 0
        limit = 100
        total_procesadas = 0
        total_tic = 0
        
        while total_procesadas < max_results:
            # Construir parámetros de consulta
            params = self._build_query_params(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                limit=limit,
                offset=offset,
                filtrar_tic=filtrar_tic
            )
            
            try:
                # Hacer petición a la API
                response = self.session.get(self.BASE_URL, params=params, timeout=30)
                response.raise_for_status()
                
                licitaciones = response.json()
                
                # Si no hay más resultados, terminar
                if not licitaciones:
                    logger.info(f"No hay más resultados. Total procesadas: {total_procesadas}")
                    break
                
                logger.debug(f"Obtenidas {len(licitaciones)} licitaciones (offset: {offset})")
                
                # Procesar cada licitación
                for licitacion in licitaciones:
                    # Verificar si es TIC (doble filtro para mayor precisión)
                    if filtrar_tic and not self._es_licitacion_tic(licitacion):
                        continue
                    
                    # Mapear a modelo Liticia
                    licitacion_mapeada = self._mapear_a_modelo_liticia(licitacion)
                    
                    total_tic += 1
                    total_procesadas += 1
                    
                    yield licitacion_mapeada
                    
                    if total_procesadas >= max_results:
                        break
                
                # Incrementar offset para siguiente página
                offset += limit
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error en petición a API Gencat: {e}")
                break
            except Exception as e:
                logger.error(f"Error procesando licitaciones Gencat: {e}")
                break
        
        logger.info(f"Scraping completado. Total licitaciones TIC: {total_tic}")
    
    def scrape_hot(self) -> Generator[Dict[str, Any], None, None]:
        """Scrapea licitaciones de las últimas 24 horas"""
        fecha_desde = datetime.now() - timedelta(hours=24)
        return self.scrape_all(fecha_desde=fecha_desde, max_results=100)
    
    def scrape_warm(self) -> Generator[Dict[str, Any], None, None]:
        """Scrapea licitaciones de los últimos 7 días"""
        fecha_desde = datetime.now() - timedelta(days=7)
        return self.scrape_all(fecha_desde=fecha_desde, max_results=500)
    
    def scrape_cold(self) -> Generator[Dict[str, Any], None, None]:
        """Scrapea licitaciones de los últimos 30 días"""
        fecha_desde = datetime.now() - timedelta(days=30)
        return self.scrape_all(fecha_desde=fecha_desde, max_results=1000)

