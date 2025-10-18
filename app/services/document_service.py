"""
Servicio para procesamiento de documentos PDF
"""
import requests
from pathlib import Path
from typing import Optional, Dict
import logging
import hashlib
import tempfile
import PyPDF2
import pdfplumber
from app.services.storage_service import StorageService
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentService:
    """Servicio para descargar y procesar documentos PDF"""
    
    def __init__(self):
        self.storage = StorageService()
        self.temp_dir = Path(tempfile.gettempdir()) / "liticia_docs"
        self.temp_dir.mkdir(exist_ok=True)
    
    def download_document(self, url: str, filename: Optional[str] = None) -> Optional[Path]:
        """
        Descarga un documento desde una URL
        
        Args:
            url: URL del documento
            filename: Nombre del archivo (si None, se genera automáticamente)
            
        Returns:
            Ruta del archivo descargado o None si falla
        """
        try:
            # Generar nombre de archivo si no se proporciona
            if filename is None:
                url_hash = hashlib.md5(url.encode()).hexdigest()
                filename = f"{url_hash}.pdf"
            
            file_path = self.temp_dir / filename
            
            # Descargar archivo
            logger.info(f"Descargando documento: {url}")
            
            response = requests.get(
                url,
                timeout=settings.SCRAPING_TIMEOUT_SECONDS,
                headers={
                    'User-Agent': settings.SCRAPING_USER_AGENT
                },
                stream=True
            )
            response.raise_for_status()
            
            # Verificar tamaño
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > settings.MAX_DOCUMENT_SIZE_MB:
                    logger.warning(f"Documento demasiado grande: {size_mb:.2f} MB")
                    return None
            
            # Guardar archivo
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Documento descargado: {file_path}")
            
            return file_path
        
        except Exception as e:
            logger.error(f"Error descargando documento: {e}")
            return None
    
    def extract_text_pypdf2(self, pdf_path: Path) -> str:
        """
        Extrae texto de un PDF usando PyPDF2
        
        Args:
            pdf_path: Ruta del archivo PDF
            
        Returns:
            Texto extraído
        """
        try:
            text = ""
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n\n"
            
            return text.strip()
        
        except Exception as e:
            logger.error(f"Error extrayendo texto con PyPDF2: {e}")
            return ""
    
    def extract_text_pdfplumber(self, pdf_path: Path) -> str:
        """
        Extrae texto de un PDF usando pdfplumber (mejor calidad)
        
        Args:
            pdf_path: Ruta del archivo PDF
            
        Returns:
            Texto extraído
        """
        try:
            text = ""
            
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            
            return text.strip()
        
        except Exception as e:
            logger.error(f"Error extrayendo texto con pdfplumber: {e}")
            return ""
    
    def extract_text(self, pdf_path: Path, method: str = 'pdfplumber') -> str:
        """
        Extrae texto de un PDF usando el método especificado
        
        Args:
            pdf_path: Ruta del archivo PDF
            method: Método de extracción ('pdfplumber' o 'pypdf2')
            
        Returns:
            Texto extraído
        """
        if method == 'pdfplumber':
            text = self.extract_text_pdfplumber(pdf_path)
            # Si falla, intentar con PyPDF2
            if not text:
                logger.warning("pdfplumber falló, intentando con PyPDF2")
                text = self.extract_text_pypdf2(pdf_path)
        else:
            text = self.extract_text_pypdf2(pdf_path)
        
        return text
    
    def get_pdf_metadata(self, pdf_path: Path) -> Dict:
        """
        Extrae metadatos de un PDF
        
        Args:
            pdf_path: Ruta del archivo PDF
            
        Returns:
            Diccionario con metadatos
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                metadata = {
                    'num_pages': len(pdf_reader.pages),
                    'author': pdf_reader.metadata.get('/Author', '') if pdf_reader.metadata else '',
                    'creator': pdf_reader.metadata.get('/Creator', '') if pdf_reader.metadata else '',
                    'producer': pdf_reader.metadata.get('/Producer', '') if pdf_reader.metadata else '',
                    'subject': pdf_reader.metadata.get('/Subject', '') if pdf_reader.metadata else '',
                    'title': pdf_reader.metadata.get('/Title', '') if pdf_reader.metadata else '',
                    'creation_date': pdf_reader.metadata.get('/CreationDate', '') if pdf_reader.metadata else '',
                }
                
                return metadata
        
        except Exception as e:
            logger.error(f"Error extrayendo metadatos: {e}")
            return {}
    
    def process_document(self, url: str, licitacion_id: int) -> Optional[Dict]:
        """
        Procesa un documento completo: descarga, extrae texto y sube a Spaces
        
        Args:
            url: URL del documento
            licitacion_id: ID de la licitación asociada
            
        Returns:
            Diccionario con información del documento procesado o None si falla
        """
        try:
            # Generar nombre de archivo único
            url_hash = hashlib.md5(url.encode()).hexdigest()
            filename = f"licitacion_{licitacion_id}_{url_hash}.pdf"
            
            # Descargar documento
            pdf_path = self.download_document(url, filename)
            if not pdf_path:
                return None
            
            # Extraer texto
            logger.info(f"Extrayendo texto de: {pdf_path}")
            texto = self.extract_text(pdf_path)
            
            if not texto:
                logger.warning(f"No se pudo extraer texto de: {pdf_path}")
            
            # Extraer metadatos
            metadata = self.get_pdf_metadata(pdf_path)
            
            # Subir a Spaces
            logger.info(f"Subiendo documento a Spaces: {filename}")
            object_name = f"documentos/{licitacion_id}/{filename}"
            spaces_url = self.storage.upload_file(
                str(pdf_path),
                object_name=object_name,
                content_type='application/pdf',
                public=False
            )
            
            if not spaces_url:
                logger.error(f"Error subiendo documento a Spaces")
                return None
            
            # Limpiar archivo temporal
            pdf_path.unlink()
            
            result = {
                'filename': filename,
                'url_original': url,
                'url_spaces': spaces_url,
                'texto': texto,
                'num_caracteres': len(texto),
                'num_paginas': metadata.get('num_pages', 0),
                'metadata': metadata,
            }
            
            logger.info(f"Documento procesado: {filename} ({len(texto)} caracteres, {metadata.get('num_pages', 0)} páginas)")
            
            return result
        
        except Exception as e:
            logger.error(f"Error procesando documento: {e}")
            return None
    
    def cleanup_temp_files(self, older_than_hours: int = 24):
        """
        Limpia archivos temporales antiguos
        
        Args:
            older_than_hours: Eliminar archivos más antiguos que N horas
        """
        import time
        
        try:
            now = time.time()
            cutoff = now - (older_than_hours * 3600)
            
            deleted = 0
            for file_path in self.temp_dir.glob('*.pdf'):
                if file_path.stat().st_mtime < cutoff:
                    file_path.unlink()
                    deleted += 1
            
            logger.info(f"Limpieza de archivos temporales: {deleted} archivos eliminados")
        
        except Exception as e:
            logger.error(f"Error limpiando archivos temporales: {e}")

