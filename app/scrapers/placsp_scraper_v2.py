"""
Scraper mejorado para PLACSP (Plataforma de Contratación del Sector Público)
Utiliza lxml para parsear correctamente el XML del feed ATOM
"""
import requests
from typing import List, Dict, Optional, Generator
from datetime import datetime, timedelta
from lxml import etree
import logging

logger = logging.getLogger(__name__)


class PLACSPScraperV2:
    """Scraper mejorado para licitaciones de PLACSP usando feed ATOM"""
    
    # URL base del feed ATOM
    BASE_FEED_URL = "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom"
    
    # Namespaces del XML
    NAMESPACES = {
        'atom': 'http://www.w3.org/2005/Atom',
        'cac': 'urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2',
        'cbc': 'urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2',
        'cac-place-ext': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2',
        'cbc-place-ext': 'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2',
    }
    
    # Códigos CPV relacionados con TIC
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
        """Inicializa el scraper"""
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Liticia/1.0 (Scraper de licitaciones TIC; +https://liticia.es)'
        })
        
    def fetch_feed_xml(self, url: str) -> etree._Element:
        """Descarga y parsea un feed ATOM como XML"""
        logger.info(f"Descargando feed: {url}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        root = etree.fromstring(response.content)
        logger.info(f"Feed descargado correctamente")
        
        return root
    
    def parse_entry(self, entry: etree._Element) -> Dict:
        """Parsea una entrada del feed ATOM"""
        ns = self.NAMESPACES
        
        data = {
            'id_licitacion': self._get_text(entry, 'atom:id', ns),
            'link': self._get_attr(entry, 'atom:link', 'href', ns),
            'titulo': self._get_text(entry, 'atom:title', ns),
            'resumen': self._get_text(entry, 'atom:summary', ns),
            'fecha_actualizacion': self._get_text(entry, 'atom:updated', ns),
        }
        
        # Buscar ContractFolderStatus
        cfs = entry.find('.//cac-place-ext:ContractFolderStatus', ns)
        if cfs is not None:
            # Expediente
            data['expediente'] = self._get_text(cfs, './/cbc:ContractFolderID', ns)
            
            # Estado
            data['estado'] = self._get_text(cfs, './/cbc-place-ext:ContractFolderStatusCode', ns)
            
            # Órgano de contratación
            party = cfs.find('.//cac-place-ext:LocatedContractingParty//cac:Party', ns)
            if party is not None:
                data['organo_contratacion'] = self._get_text(party, './/cac:PartyName/cbc:Name', ns)
                data['nif_organo'] = self._get_text(party, './/cac:PartyIdentification/cbc:ID[@schemeName="NIF"]', ns)
                data['web_organo'] = self._get_text(party, './/cbc:WebsiteURI', ns)
                data['email_organo'] = self._get_text(party, './/cac:Contact/cbc:ElectronicMail', ns)
                data['telefono_organo'] = self._get_text(party, './/cac:Contact/cbc:Telephone', ns)
                
                # Ubicación del órgano
                address = party.find('.//cac:PostalAddress', ns)
                if address is not None:
                    data['ciudad_organo'] = self._get_text(address, './/cbc:CityName', ns)
                    data['codigo_postal_organo'] = self._get_text(address, './/cbc:PostalZone', ns)
            
            # Proyecto de contratación
            project = cfs.find('.//cac:ProcurementProject', ns)
            if project is not None:
                # Tipo de contrato
                type_code = self._get_text(project, './/cbc:TypeCode', ns)
                tipos = {'1': 'Suministros', '2': 'Servicios', '3': 'Obras', 
                        '7': 'Administrativo especial', '8': 'Privado',
                        '21': 'Concesión de Servicios', '22': 'Concesión de Obras',
                        '40': 'Patrimonial'}
                data['tipo_contrato'] = tipos.get(type_code, f'Tipo {type_code}')
                data['tipo_contrato_codigo'] = type_code
                
                # Códigos CPV
                cpv_elements = project.findall('.//cac:RequiredCommodityClassification/cbc:ItemClassificationCode', ns)
                data['codigos_cpv'] = [elem.text for elem in cpv_elements if elem.text]
                
                # Importes
                budget = project.find('.//cac:BudgetAmount', ns)
                if budget is not None:
                    presupuesto = self._get_text(budget, './/cbc:TaxExclusiveAmount', ns)
                    if presupuesto:
                        try:
                            data['presupuesto_base'] = float(presupuesto)
                        except ValueError:
                            pass
                    
                    valor_estimado = self._get_text(budget, './/cbc:EstimatedOverallContractAmount', ns)
                    if valor_estimado:
                        try:
                            data['valor_estimado'] = float(valor_estimado)
                        except ValueError:
                            pass
                
                # Lugar de ejecución
                location = project.find('.//cac:RealizedLocation', ns)
                if location is not None:
                    data['lugar_ejecucion'] = self._get_text(location, './/cbc:CountrySubentity', ns)
                    data['codigo_nuts'] = self._get_text(location, './/cbc:CountrySubentityCode', ns)
                
                # Duración
                duration = self._get_text(project, './/cac:PlannedPeriod/cbc:DurationMeasure', ns)
                duration_unit = self._get_attr(project, './/cac:PlannedPeriod/cbc:DurationMeasure', 'unitCode', ns)
                if duration:
                    data['duracion'] = duration
                    data['duracion_unidad'] = duration_unit
            
            # Términos de licitación
            terms = cfs.find('.//cac:TenderingTerms', ns)
            if terms is not None:
                # Procedimiento
                proc_code = self._get_text(terms, './/cbc:ProcedureCode', ns)
                data['procedimiento_codigo'] = proc_code
                
                # Financiación UE
                funding = self._get_text(terms, './/cbc:FundingProgramCode', ns)
                data['financiacion_ue'] = funding if funding and funding != 'NO-EU' else None
                
                # Fecha límite de presentación
                deadline = self._get_text(terms, './/cac:TenderSubmissionDeadlinePeriod/cbc:EndDate', ns)
                if deadline:
                    data['fecha_limite_presentacion'] = deadline
                
                deadline_time = self._get_text(terms, './/cac:TenderSubmissionDeadlinePeriod/cbc:EndTime', ns)
                if deadline_time:
                    data['hora_limite_presentacion'] = deadline_time
            
            # Resultado de adjudicación (si existe)
            tender_result = cfs.find('.//cac:TenderResult', ns)
            if tender_result is not None:
                result_code = self._get_text(tender_result, './/cbc:ResultCode', ns)
                data['resultado_codigo'] = result_code
                
                award_date = self._get_text(tender_result, './/cbc:AwardDate', ns)
                if award_date:
                    data['fecha_adjudicacion'] = award_date
                
                # Adjudicatario
                winner = tender_result.find('.//cac:WinningParty', ns)
                if winner is not None:
                    data['adjudicatario'] = self._get_text(winner, './/cac:PartyName/cbc:Name', ns)
                    data['nif_adjudicatario'] = self._get_text(winner, './/cac:PartyIdentification/cbc:ID', ns)
                
                # Importe de adjudicación
                award_amount = self._get_text(tender_result, './/cbc:AwardedTenderedAmount', ns)
                if award_amount:
                    try:
                        data['importe_adjudicacion'] = float(award_amount)
                    except ValueError:
                        pass
            
            # DOCUMENTOS PDF
            documentos = []
            
            # 1. Pliego de Cláusulas Administrativas (LegalDocumentReference)
            legal_docs = cfs.findall('.//cac:LegalDocumentReference', ns)
            for legal_doc in legal_docs:
                nombre = self._get_text(legal_doc, './/cbc:ID', ns)
                url = self._get_text(legal_doc, './/cbc:URI', ns)
                
                if url:
                    documentos.append({
                        'nombre': nombre if nombre else 'Pliego de Cláusulas Administrativas',
                        'tipo': 'pliego_administrativo',
                        'url': url
                    })
            
            # 2. Pliego de Prescripciones Técnicas (TechnicalDocumentReference)
            tech_docs = cfs.findall('.//cac:TechnicalDocumentReference', ns)
            for tech_doc in tech_docs:
                nombre = self._get_text(tech_doc, './/cbc:ID', ns)
                url = self._get_text(tech_doc, './/cbc:URI', ns)
                
                if url:
                    documentos.append({
                        'nombre': nombre if nombre else 'Pliego de Prescripciones Técnicas',
                        'tipo': 'pliego_tecnico',
                        'url': url
                    })
            
            # 3. Documentos Generales (GeneralDocument)
            general_docs = cfs.findall('.//cac-place-ext:GeneralDocument//cac-place-ext:GeneralDocumentDocumentReference', ns)
            for gen_doc in general_docs:
                nombre = self._get_text(gen_doc, './/cbc:ID', ns)
                url = self._get_text(gen_doc, './/cbc:URI', ns)
                tipo_code = self._get_text(gen_doc, './/cbc:DocumentTypeCode', ns)
                
                if url:
                    # Determinar tipo según código
                    tipo_doc = 'anexo'
                    if tipo_code:
                        if tipo_code == '1':
                            tipo_doc = 'pliego_tecnico'
                        elif tipo_code == '2':
                            tipo_doc = 'pliego_administrativo'
                    
                    documentos.append({
                        'nombre': nombre if nombre else 'Documento Anexo',
                        'tipo': tipo_doc,
                        'url': url
                    })
            
            if documentos:
                data['documentos'] = documentos
                logger.info(f"Encontrados {len(documentos)} documentos para: {data.get('titulo', '')[:50]}")
        
        return data
    
    def _get_text(self, element: etree._Element, xpath: str, namespaces: Dict) -> Optional[str]:
        """Obtiene el texto de un elemento usando XPath"""
        try:
            elem = element.find(xpath, namespaces)
            return elem.text.strip() if elem is not None and elem.text else None
        except Exception:
            return None
    
    def _get_attr(self, element: etree._Element, xpath: str, attr: str, namespaces: Dict) -> Optional[str]:
        """Obtiene un atributo de un elemento usando XPath"""
        try:
            elem = element.find(xpath, namespaces)
            return elem.get(attr) if elem is not None else None
        except Exception:
            return None
    
    def es_licitacion_tic(self, licitacion: Dict) -> bool:
        """Determina si una licitación es relevante para el sector TIC"""
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
                logger.debug(f"Licitación TIC por keyword '{keyword}' en título")
                return True
        
        # Filtro 3: Por keywords en resumen
        resumen = licitacion.get('resumen', '').lower()
        for keyword in self.KEYWORDS_TIC:
            if keyword in resumen:
                logger.debug(f"Licitación TIC por keyword '{keyword}' en resumen")
                return True
        
        return False
    
    def scrape_feed_page(self, url: str, filtrar_tic: bool = True) -> tuple[List[Dict], Optional[str]]:
        """Scrape una página del feed ATOM"""
        root = self.fetch_feed_xml(url)
        ns = self.NAMESPACES
        
        # Obtener todas las entradas
        entries = root.findall('.//atom:entry', ns)
        logger.info(f"Encontradas {len(entries)} entradas en el feed")
        
        licitaciones = []
        for entry in entries:
            licitacion = self.parse_entry(entry)
            
            # Filtrar por TIC si se solicita
            if filtrar_tic and not self.es_licitacion_tic(licitacion):
                continue
            
            licitaciones.append(licitacion)
        
        # Obtener URL de siguiente página
        next_url = None
        next_link = root.find('.//atom:link[@rel="next"]', ns)
        if next_link is not None:
            next_url = next_link.get('href')
        
        logger.info(f"Scraped {len(licitaciones)} licitaciones TIC de {len(entries)} totales")
        
        return licitaciones, next_url
    
    def scrape_all(self, max_pages: Optional[int] = None, filtrar_tic: bool = True) -> Generator[Dict, None, None]:
        """Scrape todas las páginas del feed siguiendo la paginación"""
        url = self.BASE_FEED_URL
        page = 0
        
        while url:
            page += 1
            logger.info(f"Scraping página {page}...")
            
            try:
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
            
            except Exception as e:
                logger.error(f"Error scraping página {page}: {e}")
                break
    
    def scrape_recent(self, days: int = 7, filtrar_tic: bool = True) -> List[Dict]:
        """Scrape licitaciones recientes de los últimos N días"""
        cutoff_date = datetime.now() - timedelta(days=days)
        licitaciones = []
        
        for licitacion in self.scrape_all(max_pages=50, filtrar_tic=filtrar_tic):
            # Parsear fecha de actualización
            fecha_str = licitacion.get('fecha_actualizacion', '')
            try:
                # Formato: 2025-10-15T17:00:00.008+02:00
                fecha = datetime.fromisoformat(fecha_str.replace('+02:00', '').replace('+01:00', ''))
                
                if fecha < cutoff_date:
                    logger.info(f"Alcanzada fecha límite: {fecha}")
                    break
                
                licitaciones.append(licitacion)
            except Exception as e:
                logger.warning(f"Error parseando fecha: {fecha_str} - {e}")
                licitaciones.append(licitacion)
        
        logger.info(f"Scraped {len(licitaciones)} licitaciones de los últimos {days} días")
        return licitaciones


def main():
    """Función de prueba"""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    
    scraper = PLACSPScraperV2()
    
    print("=== Scraping licitaciones TIC de PLACSP ===\n")
    
    count = 0
    for licitacion in scraper.scrape_all(max_pages=5, filtrar_tic=True):
        count += 1
        print(f"\n{'='*80}")
        print(f"LICITACIÓN {count}")
        print(f"{'='*80}")
        print(f"Título: {licitacion.get('titulo', 'N/A')}")
        print(f"Expediente: {licitacion.get('expediente', 'N/A')}")
        print(f"Estado: {licitacion.get('estado', 'N/A')}")
        print(f"Órgano: {licitacion.get('organo_contratacion', 'N/A')}")
        print(f"Tipo: {licitacion.get('tipo_contrato', 'N/A')}")
        print(f"Presupuesto: {licitacion.get('presupuesto_base', 'N/A')} EUR")
        print(f"CPV: {', '.join(licitacion.get('codigos_cpv', []))}")
        print(f"Lugar: {licitacion.get('lugar_ejecucion', 'N/A')}")
        print(f"Fecha límite: {licitacion.get('fecha_limite_presentacion', 'N/A')}")
        
        if licitacion.get('adjudicatario'):
            print(f"Adjudicatario: {licitacion.get('adjudicatario', 'N/A')}")
            print(f"Importe adjudicación: {licitacion.get('importe_adjudicacion', 'N/A')} EUR")
        
        print(f"Link: {licitacion.get('link', 'N/A')}")
        
        if count >= 10:
            break
    
    print(f"\n\n{'='*80}")
    print(f"Total licitaciones TIC encontradas: {count}")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()

