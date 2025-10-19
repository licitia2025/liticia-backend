"""
Scraper para PLACSP (Plataforma de Contratación del Sector Público)
Utiliza el feed ATOM oficial de datos abiertos
"""
import feedparser
import requests
from typing import List, Dict, Optional, Generator
from datetime import datetime
from lxml import etree
import logging

logger = logging.getLogger(__name__)


class PLACSPScraper:
    """Scraper para licitaciones de PLACSP usando feed ATOM"""
    
    # URL base del feed ATOM
    BASE_FEED_URL = "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom"
    
    # Códigos CPV relacionados con TIC (primeros dígitos)
    CPV_TIC = [
        '48',  # Paquetes de software y sistemas de información
        '72',  # Servicios TI: consultoría, desarrollo, Internet
        '30200',  # Equipo informático
        '32400',  # Redes
        '32420',  # Componentes de red
        '32500',  # Telecomunicaciones
    ]
    
    # Keywords para identificar licitaciones TIC
    KEYWORDS_TIC = [
        'software', 'aplicación', 'aplicacion', 'sistema informático', 'sistema informatico',
        'desarrollo', 'programación', 'programacion',
        'cloud', 'nube',
        'ciberseguridad', 'seguridad informática', 'seguridad informatica',
        'base de datos', 'bbdd', 'bases de datos',
        'inteligencia artificial', ' ia ', 'machine learning', 'aprendizaje automático',
        'devops', 'ci/cd', 'integración continua',
        'erp', 'crm', 'sap', 'oracle',
        'web', 'portal', 'plataforma digital', 'sitio web',
        'infraestructura ti', 'tecnología', 'tecnologia', 'tecnologías', 'tecnologias',
        'migración', 'migracion', 'modernización', 'modernizacion', 'transformación digital',
        'servidor', 'servidores', 'hosting', 'datacenter',
        'virtualización', 'virtualizacion', 'contenedores', 'kubernetes', 'docker',
        'big data', 'analítica', 'analitica', 'business intelligence',
        'blockchain', 'iot', 'internet de las cosas',
        'app móvil', 'app movil', 'aplicación móvil', 'aplicacion movil',
        'api', 'microservicios', 'arquitectura',
        'backup', 'respaldo', 'recuperación', 'recuperacion',
        'firewall', 'antivirus', 'vpn',
        'licencia', 'licencias', 'microsoft', 'adobe', 'autodesk',
    ]
    
    def __init__(self, session: Optional[requests.Session] = None):
        """
        Inicializa el scraper
        
        Args:
            session: Sesión de requests opcional para reutilizar conexiones
        """
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Liticia/1.0 (Scraper de licitaciones TIC; +https://liticia.es)'
        })
        
    def fetch_feed(self, url: str) -> feedparser.FeedParserDict:
        """
        Descarga y parsea un feed ATOM
        
        Args:
            url: URL del feed ATOM
            
        Returns:
            Feed parseado
        """
        logger.info(f"Descargando feed: {url}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        logger.info(f"Feed descargado: {len(feed.entries)} entradas")
        
        return feed
    
    def extract_namespaces(self, entry_content: str) -> Dict[str, str]:
        """Extrae namespaces del contenido XML"""
        return {
            'cac': 'urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2',
            'cac-place-ext': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2',
            'cbc-place-ext': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2',
        }
    
    def parse_entry(self, entry: feedparser.FeedParserDict) -> Dict:
        """
        Parsea una entrada del feed ATOM y extrae todos los datos relevantes
        
        Args:
            entry: Entrada del feed
            
        Returns:
            Diccionario con los datos de la licitación
        """
        # Parsear el contenido XML de la entrada
        content = entry.get('content', [{}])[0].get('value', '')
        if not content:
            content = entry.get('summary', '')
        
        # Datos básicos del feed
        data = {
            'id_licitacion': entry.get('id', ''),
            'link': entry.get('link', ''),
            'titulo': entry.get('title', ''),
            'resumen': entry.get('summary', ''),
            'fecha_actualizacion': entry.get('updated', ''),
        }
        
        # Parsear XML para extraer datos estructurados
        try:
            # Buscar el contenido XML en tags
            for tag in entry.get('tags', []):
                if hasattr(tag, 'term') and 'ContractFolderStatus' in tag.term:
                    content = str(tag)
            
            # Si hay contenido XML, parsearlo
            if '<cac' in str(entry) or '<cbc' in str(entry):
                # Extraer del entry completo
                xml_str = str(entry)
                
                # Extraer expediente
                if 'ContractFolderID' in xml_str:
                    import re
                    match = re.search(r'<cbc:ContractFolderID>([^<]+)</cbc:ContractFolderID>', xml_str)
                    if match:
                        data['expediente'] = match.group(1)
                
                # Extraer estado
                if 'ContractFolderStatusCode' in xml_str:
                    import re
                    match = re.search(r'>([A-Z]+)</cbc-place-ext:ContractFolderStatusCode>', xml_str)
                    if match:
                        data['estado'] = match.group(1)
                
                # Extraer códigos CPV
                import re
                cpv_matches = re.findall(r'<cbc:ItemClassificationCode[^>]*>(\d+)</cbc:ItemClassificationCode>', xml_str)
                if cpv_matches:
                    data['codigos_cpv'] = list(set(cpv_matches))
                
                # Extraer importes
                amount_match = re.search(r'<cbc:TaxExclusiveAmount currencyID="EUR">([^<]+)</cbc:TaxExclusiveAmount>', xml_str)
                if amount_match:
                    try:
                        data['presupuesto_base'] = float(amount_match.group(1))
                    except ValueError:
                        pass
                
                # Extraer órgano de contratación
                org_match = re.search(r'<cbc:Name>([^<]+)</cbc:Name>', xml_str)
                if org_match:
                    data['organo_contratacion'] = org_match.group(1)
                
                # Extraer tipo de contrato
                type_match = re.search(r'<cbc:TypeCode[^>]*>(\d+)</cbc:TypeCode>', xml_str)
                if type_match:
                    type_code = type_match.group(1)
                    tipos = {'1': 'Suministros', '2': 'Servicios', '3': 'Obras', 
                            '7': 'Administrativo especial', '8': 'Privado',
                            '21': 'Concesión de Servicios', '22': 'Concesión de Obras',
                            '40': 'Patrimonial'}
                    data['tipo_contrato'] = tipos.get(type_code, f'Tipo {type_code}')
                
                # Extraer lugar de ejecución
                location_match = re.search(r'<cbc:CountrySubentity>([^<]+)</cbc:CountrySubentity>', xml_str)
                if location_match:
                    data['lugar_ejecucion'] = location_match.group(1)
                
                # Extraer código NUTS
                nuts_match = re.search(r'<cbc:CountrySubentityCode[^>]*>([^<]+)</cbc:CountrySubentityCode>', xml_str)
                if nuts_match:
                    data['codigo_nuts'] = nuts_match.group(1)
                
                # Extraer documentos adjuntos (PDFs)
                documentos = []
                
                # Buscar LegalDocumentReference (Pliego de Cláusulas Administrativas)
                legal_docs = re.findall(
                    r'<cac:LegalDocumentReference>.*?<cbc:ID>([^<]+)</cbc:ID>.*?<cbc:URI>([^<]+)</cbc:URI>.*?</cac:LegalDocumentReference>',
                    xml_str,
                    re.DOTALL
                )
                for nombre, url in legal_docs:
                    # Decodificar entidades HTML
                    url = url.replace('&amp;', '&')
                    documentos.append({
                        'nombre': nombre,
                        'tipo': 'pliego_administrativo',
                        'url': url
                    })
                
                # Buscar TechnicalDocumentReference (Pliego de Prescripciones Técnicas)
                tech_docs = re.findall(
                    r'<cac:TechnicalDocumentReference>.*?<cbc:ID>([^<]+)</cbc:ID>.*?<cbc:URI>([^<]+)</cbc:URI>.*?</cac:TechnicalDocumentReference>',
                    xml_str,
                    re.DOTALL
                )
                for nombre, url in tech_docs:
                    url = url.replace('&amp;', '&')
                    documentos.append({
                        'nombre': nombre,
                        'tipo': 'pliego_tecnico',
                        'url': url
                    })
                
                # Buscar AdditionalDocumentReference (Otros documentos)
                additional_docs = re.findall(
                    r'<cac:AdditionalDocumentReference>.*?<cbc:ID>([^<]+)</cbc:ID>.*?<cbc:URI>([^<]+)</cbc:URI>.*?</cac:AdditionalDocumentReference>',
                    xml_str,
                    re.DOTALL
                )
                for nombre, url in additional_docs:
                    url = url.replace('&amp;', '&')
                    documentos.append({
                        'nombre': nombre,
                        'tipo': 'anexo',
                        'url': url
                    })
                
                if documentos:
                    data['documentos'] = documentos
                    logger.debug(f"Encontrados {len(documentos)} documentos para licitación {data.get('titulo', '')[:50]}")
        
        except Exception as e:
            logger.warning(f"Error parseando XML de entrada: {e}")
        
        return data
    
    def es_licitacion_tic(self, licitacion: Dict) -> bool:
        """
        Determina si una licitación es relevante para el sector TIC
        
        Args:
            licitacion: Diccionario con datos de la licitación
            
        Returns:
            True si es licitación TIC, False en caso contrario
        """
        # Filtro 1: Por código CPV
        codigos_cpv = licitacion.get('codigos_cpv', [])
        for cpv in codigos_cpv:
            for cpv_tic in self.CPV_TIC:
                if cpv.startswith(cpv_tic):
                    logger.debug(f"Licitación TIC por CPV {cpv}: {licitacion.get('titulo', '')[:50]}")
                    return True
        
        # Filtro 2: Por keywords en título
        titulo = licitacion.get('titulo', '').lower()
        for keyword in self.KEYWORDS_TIC:
            if keyword in titulo:
                logger.debug(f"Licitación TIC por keyword '{keyword}' en título: {titulo[:50]}")
                return True
        
        # Filtro 3: Por keywords en resumen
        resumen = licitacion.get('resumen', '').lower()
        for keyword in self.KEYWORDS_TIC:
            if keyword in resumen:
                logger.debug(f"Licitación TIC por keyword '{keyword}' en resumen: {titulo[:50]}")
                return True
        
        return False
    
    def scrape_feed_page(self, url: str, filtrar_tic: bool = True) -> tuple[List[Dict], Optional[str]]:
        """
        Scrape una página del feed ATOM
        
        Args:
            url: URL del feed
            filtrar_tic: Si True, solo devuelve licitaciones TIC
            
        Returns:
            Tupla (lista de licitaciones, URL de siguiente página o None)
        """
        feed = self.fetch_feed(url)
        
        licitaciones = []
        for entry in feed.entries:
            licitacion = self.parse_entry(entry)
            
            # Filtrar por TIC si se solicita
            if filtrar_tic and not self.es_licitacion_tic(licitacion):
                continue
            
            licitaciones.append(licitacion)
        
        # Obtener URL de siguiente página
        next_url = None
        for link in feed.feed.get('links', []):
            if link.get('rel') == 'next':
                next_url = link.get('href')
                break
        
        logger.info(f"Scraped {len(licitaciones)} licitaciones TIC de {len(feed.entries)} totales")
        
        return licitaciones, next_url
    
    def scrape_all(self, max_pages: Optional[int] = None, filtrar_tic: bool = True) -> Generator[Dict, None, None]:
        """
        Scrape todas las páginas del feed siguiendo la paginación
        
        Args:
            max_pages: Número máximo de páginas a scrapear (None = todas)
            filtrar_tic: Si True, solo devuelve licitaciones TIC
            
        Yields:
            Diccionarios con datos de licitaciones
        """
        url = self.BASE_FEED_URL
        page = 0
        
        while url:
            page += 1
            logger.info(f"Scraping página {page}...")
            
            licitaciones, next_url = self.scrape_feed_page(url, filtrar_tic=filtrar_tic)
            
            for licitacion in licitaciones:
                yield licitacion
            
            # Verificar si continuar
            if max_pages and page >= max_pages:
                logger.info(f"Alcanzado límite de {max_pages} páginas")
                break
            
            url = next_url
            
            if not url:
                logger.info("No hay más páginas")
                break
    
    def scrape_recent(self, days: int = 7, filtrar_tic: bool = True) -> List[Dict]:
        """
        Scrape licitaciones recientes de los últimos N días
        
        Args:
            days: Número de días hacia atrás
            filtrar_tic: Si True, solo devuelve licitaciones TIC
            
        Returns:
            Lista de licitaciones
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        licitaciones = []
        
        for licitacion in self.scrape_all(max_pages=50, filtrar_tic=filtrar_tic):
            # Parsear fecha de actualización
            fecha_str = licitacion.get('fecha_actualizacion', '')
            try:
                # Formato: 2025-10-15T17:00:00.008+02:00
                fecha = datetime.fromisoformat(fecha_str.replace('+02:00', ''))
                
                if fecha < cutoff_date:
                    logger.info(f"Alcanzada fecha límite: {fecha}")
                    break
                
                licitaciones.append(licitacion)
            except Exception as e:
                logger.warning(f"Error parseando fecha: {fecha_str} - {e}")
                # Si no podemos parsear la fecha, incluir la licitación por seguridad
                licitaciones.append(licitacion)
        
        logger.info(f"Scraped {len(licitaciones)} licitaciones de los últimos {days} días")
        return licitaciones


def main():
    """Función de prueba"""
    logging.basicConfig(level=logging.INFO)
    
    scraper = PLACSPScraper()
    
    print("=== Scraping últimas 100 licitaciones TIC ===\n")
    
    count = 0
    for licitacion in scraper.scrape_all(max_pages=10, filtrar_tic=True):
        count += 1
        print(f"\n--- Licitación {count} ---")
        print(f"Título: {licitacion.get('titulo', 'N/A')}")
        print(f"Expediente: {licitacion.get('expediente', 'N/A')}")
        print(f"Órgano: {licitacion.get('organo_contratacion', 'N/A')}")
        print(f"Tipo: {licitacion.get('tipo_contrato', 'N/A')}")
        print(f"Presupuesto: {licitacion.get('presupuesto_base', 'N/A')} EUR")
        print(f"CPV: {', '.join(licitacion.get('codigos_cpv', []))}")
        print(f"Link: {licitacion.get('link', 'N/A')}")
        
        if count >= 20:
            break
    
    print(f"\n\nTotal licitaciones TIC encontradas: {count}")


if __name__ == '__main__':
    main()

