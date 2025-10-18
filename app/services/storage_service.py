"""
Servicio para almacenamiento de archivos en DigitalOcean Spaces (S3-compatible)
"""
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from typing import Optional, BinaryIO
import logging
import mimetypes
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageService:
    """Servicio para gestionar almacenamiento de archivos en Spaces"""
    
    def __init__(self):
        """Inicializa el cliente de S3"""
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.SPACES_ENDPOINT,
            region_name=settings.SPACES_REGION,
            aws_access_key_id=settings.SPACES_KEY,
            aws_secret_access_key=settings.SPACES_SECRET
        )
        self.bucket = settings.SPACES_BUCKET
    
    def upload_file(
        self,
        file_path: str,
        object_name: Optional[str] = None,
        content_type: Optional[str] = None,
        public: bool = False
    ) -> Optional[str]:
        """
        Sube un archivo a Spaces
        
        Args:
            file_path: Ruta local del archivo
            object_name: Nombre del objeto en Spaces (si None, usa el nombre del archivo)
            content_type: Tipo MIME del archivo (si None, se detecta automáticamente)
            public: Si True, el archivo será públicamente accesible
            
        Returns:
            URL del archivo subido o None si falla
        """
        if object_name is None:
            object_name = Path(file_path).name
        
        if content_type is None:
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
        
        try:
            extra_args = {
                'ContentType': content_type
            }
            
            if public:
                extra_args['ACL'] = 'public-read'
            
            self.s3_client.upload_file(
                file_path,
                self.bucket,
                object_name,
                ExtraArgs=extra_args
            )
            
            # Construir URL
            url = f"{settings.SPACES_ENDPOINT}/{self.bucket}/{object_name}"
            
            logger.info(f"Archivo subido: {object_name}")
            
            return url
        
        except ClientError as e:
            logger.error(f"Error subiendo archivo: {e}")
            return None
    
    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
        public: bool = False
    ) -> Optional[str]:
        """
        Sube un objeto de archivo (file-like object) a Spaces
        
        Args:
            file_obj: Objeto de archivo
            object_name: Nombre del objeto en Spaces
            content_type: Tipo MIME del archivo
            public: Si True, el archivo será públicamente accesible
            
        Returns:
            URL del archivo subido o None si falla
        """
        if content_type is None:
            content_type = 'application/octet-stream'
        
        try:
            extra_args = {
                'ContentType': content_type
            }
            
            if public:
                extra_args['ACL'] = 'public-read'
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket,
                object_name,
                ExtraArgs=extra_args
            )
            
            # Construir URL
            url = f"{settings.SPACES_ENDPOINT}/{self.bucket}/{object_name}"
            
            logger.info(f"Objeto subido: {object_name}")
            
            return url
        
        except ClientError as e:
            logger.error(f"Error subiendo objeto: {e}")
            return None
    
    def download_file(self, object_name: str, file_path: str) -> bool:
        """
        Descarga un archivo de Spaces
        
        Args:
            object_name: Nombre del objeto en Spaces
            file_path: Ruta local donde guardar el archivo
            
        Returns:
            True si se descargó correctamente, False en caso contrario
        """
        try:
            self.s3_client.download_file(
                self.bucket,
                object_name,
                file_path
            )
            
            logger.info(f"Archivo descargado: {object_name}")
            
            return True
        
        except ClientError as e:
            logger.error(f"Error descargando archivo: {e}")
            return False
    
    def delete_file(self, object_name: str) -> bool:
        """
        Elimina un archivo de Spaces
        
        Args:
            object_name: Nombre del objeto en Spaces
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=object_name
            )
            
            logger.info(f"Archivo eliminado: {object_name}")
            
            return True
        
        except ClientError as e:
            logger.error(f"Error eliminando archivo: {e}")
            return False
    
    def file_exists(self, object_name: str) -> bool:
        """
        Verifica si un archivo existe en Spaces
        
        Args:
            object_name: Nombre del objeto en Spaces
            
        Returns:
            True si existe, False en caso contrario
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket,
                Key=object_name
            )
            return True
        
        except ClientError:
            return False
    
    def get_file_url(self, object_name: str, expires_in: int = 3600) -> Optional[str]:
        """
        Genera una URL firmada para acceder a un archivo privado
        
        Args:
            object_name: Nombre del objeto en Spaces
            expires_in: Tiempo de expiración en segundos (default: 1 hora)
            
        Returns:
            URL firmada o None si falla
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': object_name
                },
                ExpiresIn=expires_in
            )
            
            return url
        
        except ClientError as e:
            logger.error(f"Error generando URL firmada: {e}")
            return None
    
    def list_files(self, prefix: str = '') -> list[str]:
        """
        Lista archivos en Spaces con un prefijo dado
        
        Args:
            prefix: Prefijo para filtrar archivos
            
        Returns:
            Lista de nombres de archivos
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            return [obj['Key'] for obj in response['Contents']]
        
        except ClientError as e:
            logger.error(f"Error listando archivos: {e}")
            return []

