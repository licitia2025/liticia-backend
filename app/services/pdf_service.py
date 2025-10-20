"""
Servicio para descargar y extraer texto de documentos PDF
"""
import requests
import logging
from typing import Optional, Dict
from pypdf import PdfReader
from io import BytesIO
import time

logger = logging.getLogger(__name__)


class PDFService:
    """Servicio para procesar documentos PDF de licitaciones"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Liticia/1.0 (Scraper de licitaciones TIC; +https://liticia.es)'
        })
    
    def descargar_pdf(self, url: str, max_retries: int = 3) -> Optional[bytes]:
        """
        Descarga un PDF desde una URL
        
        Args:
            url: URL del documento PDF
            max_retries: Número máximo de reintentos
            
        Returns:
            Contenido del PDF en bytes o None si falla
        """
        for intento in range(max_retries):
            try:
                logger.info(f"Descargando PDF: {url[:80]}... (intento {intento + 1}/{max_retries})")
                
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # Verificar que es un PDF
                content_type = response.headers.get('Content-Type', '').lower()
                if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                    logger.warning(f"El contenido no parece ser un PDF: {content_type}")
                
                logger.info(f"✓ PDF descargado correctamente ({len(response.content)} bytes)")
                return response.content
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error descargando PDF (intento {intento + 1}/{max_retries}): {e}")
                if intento < max_retries - 1:
                    time.sleep(2 ** intento)  # Backoff exponencial
                continue
        
        logger.error(f"No se pudo descargar el PDF después de {max_retries} intentos: {url}")
        return None
    
    def extraer_texto_pdf(self, pdf_content: bytes, max_pages: Optional[int] = None) -> Optional[str]:
        """
        Extrae el texto de un PDF
        
        Args:
            pdf_content: Contenido del PDF en bytes
            max_pages: Número máximo de páginas a procesar (None = todas)
            
        Returns:
            Texto extraído o None si falla
        """
        try:
            # Crear objeto PDF desde bytes
            pdf_file = BytesIO(pdf_content)
            reader = PdfReader(pdf_file)
            
            num_pages = len(reader.pages)
            logger.info(f"PDF tiene {num_pages} páginas")
            
            # Limitar páginas si se especifica
            pages_to_process = min(num_pages, max_pages) if max_pages else num_pages
            
            # Extraer texto de cada página
            texto_completo = []
            for i in range(pages_to_process):
                try:
                    page = reader.pages[i]
                    texto = page.extract_text()
                    if texto:
                        texto_completo.append(texto)
                except Exception as e:
                    logger.warning(f"Error extrayendo texto de página {i + 1}: {e}")
                    continue
            
            if not texto_completo:
                logger.warning("No se pudo extraer texto del PDF")
                return None
            
            texto_final = "\n\n".join(texto_completo)
            logger.info(f"✓ Texto extraído: {len(texto_final)} caracteres de {pages_to_process} páginas")
            
            return texto_final
            
        except Exception as e:
            logger.error(f"Error procesando PDF: {e}")
            return None
    
    def procesar_documento(self, url: str, max_pages: Optional[int] = 50) -> Dict:
        """
        Descarga un PDF y extrae su texto
        
        Args:
            url: URL del documento PDF
            max_pages: Número máximo de páginas a procesar
            
        Returns:
            Diccionario con información del documento:
            {
                'success': bool,
                'texto': str o None,
                'num_caracteres': int,
                'error': str o None
            }
        """
        resultado = {
            'success': False,
            'texto': None,
            'num_caracteres': 0,
            'error': None
        }
        
        # Descargar PDF
        pdf_content = self.descargar_pdf(url)
        if not pdf_content:
            resultado['error'] = 'No se pudo descargar el PDF'
            return resultado
        
        # Extraer texto
        texto = self.extraer_texto_pdf(pdf_content, max_pages=max_pages)
        if not texto:
            resultado['error'] = 'No se pudo extraer texto del PDF'
            return resultado
        
        resultado['success'] = True
        resultado['texto'] = texto
        resultado['num_caracteres'] = len(texto)
        
        return resultado
    
    def procesar_documentos_licitacion(self, documentos: list, max_docs: int = 3) -> Dict:
        """
        Procesa los documentos de una licitación (pliegos técnicos y administrativos)
        
        Args:
            documentos: Lista de diccionarios con información de documentos
            max_docs: Número máximo de documentos a procesar
            
        Returns:
            Diccionario con textos extraídos:
            {
                'pliego_tecnico': str o None,
                'pliego_administrativo': str o None,
                'anexos': list de str,
                'total_caracteres': int
            }
        """
        resultado = {
            'pliego_tecnico': None,
            'pliego_administrativo': None,
            'anexos': [],
            'total_caracteres': 0
        }
        
        # Priorizar pliegos técnicos y administrativos
        docs_procesados = 0
        
        for doc in documentos:
            if docs_procesados >= max_docs:
                break
            
            tipo = doc.get('tipo', '')
            url = doc.get('url', '')
            
            if not url:
                continue
            
            # Procesar según tipo
            if tipo == 'pliego_tecnico' and not resultado['pliego_tecnico']:
                logger.info(f"Procesando pliego técnico: {doc.get('nombre', 'Sin nombre')}")
                res = self.procesar_documento(url)
                if res['success']:
                    resultado['pliego_tecnico'] = res['texto']
                    resultado['total_caracteres'] += res['num_caracteres']
                    docs_procesados += 1
            
            elif tipo == 'pliego_administrativo' and not resultado['pliego_administrativo']:
                logger.info(f"Procesando pliego administrativo: {doc.get('nombre', 'Sin nombre')}")
                res = self.procesar_documento(url)
                if res['success']:
                    resultado['pliego_administrativo'] = res['texto']
                    resultado['total_caracteres'] += res['num_caracteres']
                    docs_procesados += 1
            
            elif tipo == 'anexo' and docs_procesados < max_docs:
                logger.info(f"Procesando anexo: {doc.get('nombre', 'Sin nombre')}")
                res = self.procesar_documento(url)
                if res['success']:
                    resultado['anexos'].append(res['texto'])
                    resultado['total_caracteres'] += res['num_caracteres']
                    docs_procesados += 1
        
        logger.info(f"Documentos procesados: {docs_procesados}, Total caracteres: {resultado['total_caracteres']}")
        
        return resultado

