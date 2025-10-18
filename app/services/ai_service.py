"""
Servicio de análisis con IA usando OpenAI
"""
from openai import OpenAI
from app.core.config import settings
from typing import Dict, List, Optional
import logging
import json
import hashlib

logger = logging.getLogger(__name__)


class AIService:
    """Servicio para análisis de licitaciones con IA"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.temperature = settings.OPENAI_TEMPERATURE
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self._cache = {}  # Cache simple en memoria
    
    def _get_cache_key(self, text: str, prompt_type: str) -> str:
        """Genera una clave de caché basada en el hash del texto"""
        content = f"{prompt_type}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _call_openai(self, system_prompt: str, user_prompt: str, cache_key: Optional[str] = None) -> Optional[str]:
        """
        Llama a la API de OpenAI
        
        Args:
            system_prompt: Prompt del sistema
            user_prompt: Prompt del usuario
            cache_key: Clave de caché opcional
            
        Returns:
            Respuesta de la IA o None si falla
        """
        # Verificar caché
        if cache_key and cache_key in self._cache:
            logger.debug(f"Usando respuesta cacheada para {cache_key}")
            return self._cache[cache_key]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            result = response.choices[0].message.content
            
            # Guardar en caché
            if cache_key:
                self._cache[cache_key] = result
            
            return result
        
        except Exception as e:
            logger.error(f"Error llamando a OpenAI: {e}")
            return None
    
    def identificar_stack_tecnologico(self, titulo: str, descripcion: str, texto_pliego: Optional[str] = None) -> Optional[Dict]:
        """
        Identifica el stack tecnológico de una licitación
        
        Args:
            titulo: Título de la licitación
            descripcion: Descripción breve
            texto_pliego: Texto completo del pliego técnico (opcional)
            
        Returns:
            Diccionario con stack tecnológico identificado
        """
        system_prompt = """Eres un experto en tecnología que analiza licitaciones públicas de TIC.
Tu tarea es identificar el stack tecnológico mencionado en la licitación.

Debes extraer y categorizar las tecnologías en estas categorías:
- lenguajes_programacion: Python, Java, JavaScript, C#, PHP, etc.
- frameworks: React, Angular, Vue, Django, Spring, .NET, etc.
- bases_datos: PostgreSQL, MySQL, MongoDB, Oracle, SQL Server, etc.
- cloud: AWS, Azure, Google Cloud, DigitalOcean, etc.
- devops: Docker, Kubernetes, Jenkins, GitLab CI, Terraform, etc.
- otros: Cualquier otra tecnología relevante

Responde SOLO con un JSON válido con esta estructura:
{
  "lenguajes_programacion": ["Python", "JavaScript"],
  "frameworks": ["Django", "React"],
  "bases_datos": ["PostgreSQL"],
  "cloud": ["AWS"],
  "devops": ["Docker", "Kubernetes"],
  "otros": ["Elasticsearch", "Redis"]
}

Si no encuentras tecnologías en alguna categoría, devuelve un array vacío [].
NO incluyas explicaciones, SOLO el JSON."""

        # Construir texto a analizar
        texto_analizar = f"Título: {titulo}\n\nDescripción: {descripcion}"
        
        if texto_pliego:
            # Limitar el texto del pliego para no exceder límites de tokens
            texto_pliego_limitado = texto_pliego[:15000]  # ~4000 tokens aprox
            texto_analizar += f"\n\nPliego técnico:\n{texto_pliego_limitado}"
        
        cache_key = self._get_cache_key(texto_analizar, "stack")
        
        response = self._call_openai(system_prompt, texto_analizar, cache_key)
        
        if not response:
            return None
        
        try:
            # Parsear JSON
            stack = json.loads(response)
            
            logger.info(f"Stack tecnológico identificado: {sum(len(v) for v in stack.values())} tecnologías")
            
            return stack
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta JSON: {e}\nRespuesta: {response}")
            return None
    
    def clasificar_conceptos_tic(self, titulo: str, descripcion: str) -> Optional[List[str]]:
        """
        Clasifica una licitación en conceptos TIC
        
        Args:
            titulo: Título de la licitación
            descripcion: Descripción breve
            
        Returns:
            Lista de conceptos TIC identificados
        """
        system_prompt = """Eres un experto en tecnología que clasifica licitaciones públicas de TIC.
Tu tarea es identificar los conceptos TIC principales de la licitación.

Conceptos disponibles:
- Ciberseguridad
- Inteligencia Artificial / Machine Learning
- Cloud Computing
- Big Data / Analítica
- DevOps / CI/CD
- Desarrollo Web
- Desarrollo Móvil
- ERP / CRM
- Infraestructura TI
- Redes y Telecomunicaciones
- Virtualización
- Bases de Datos
- Business Intelligence
- IoT (Internet de las Cosas)
- Blockchain
- Transformación Digital
- Migración / Modernización
- Soporte y Mantenimiento
- Consultoría TI
- Formación TIC

Responde SOLO con un JSON válido con esta estructura:
{
  "conceptos": ["Ciberseguridad", "Cloud Computing", "DevOps / CI/CD"]
}

Selecciona entre 1 y 5 conceptos que mejor describan la licitación.
NO incluyas explicaciones, SOLO el JSON."""

        texto_analizar = f"Título: {titulo}\n\nDescripción: {descripcion}"
        
        cache_key = self._get_cache_key(texto_analizar, "conceptos")
        
        response = self._call_openai(system_prompt, texto_analizar, cache_key)
        
        if not response:
            return None
        
        try:
            # Parsear JSON
            result = json.loads(response)
            conceptos = result.get('conceptos', [])
            
            logger.info(f"Conceptos TIC identificados: {len(conceptos)}")
            
            return conceptos
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta JSON: {e}\nRespuesta: {response}")
            return None
    
    def generar_resumen_tecnico(self, titulo: str, descripcion: str, texto_pliego: Optional[str] = None) -> Optional[Dict]:
        """
        Genera un resumen técnico de la licitación
        
        Args:
            titulo: Título de la licitación
            descripcion: Descripción breve
            texto_pliego: Texto completo del pliego técnico (opcional)
            
        Returns:
            Diccionario con resumen técnico
        """
        system_prompt = """Eres un experto en tecnología que analiza licitaciones públicas de TIC.
Tu tarea es generar un resumen técnico claro y conciso de la licitación.

El resumen debe incluir:
- objetivo: Qué se quiere conseguir con esta licitación (1-2 frases)
- requisitos_clave: Lista de 3-5 requisitos técnicos principales
- complejidad: "Baja", "Media" o "Alta"
- duracion_estimada: Duración estimada del proyecto (ej: "6 meses", "1 año")
- presupuesto_tipo: "Pequeño" (<50k), "Mediano" (50k-200k) o "Grande" (>200k)

Responde SOLO con un JSON válido con esta estructura:
{
  "objetivo": "Implementar un sistema de gestión documental basado en cloud",
  "requisitos_clave": [
    "Integración con sistemas existentes",
    "Alta disponibilidad y escalabilidad",
    "Cumplimiento RGPD"
  ],
  "complejidad": "Media",
  "duracion_estimada": "8 meses",
  "presupuesto_tipo": "Mediano"
}

NO incluyas explicaciones, SOLO el JSON."""

        # Construir texto a analizar
        texto_analizar = f"Título: {titulo}\n\nDescripción: {descripcion}"
        
        if texto_pliego:
            # Limitar el texto del pliego
            texto_pliego_limitado = texto_pliego[:15000]
            texto_analizar += f"\n\nPliego técnico:\n{texto_pliego_limitado}"
        
        cache_key = self._get_cache_key(texto_analizar, "resumen")
        
        response = self._call_openai(system_prompt, texto_analizar, cache_key)
        
        if not response:
            return None
        
        try:
            # Parsear JSON
            resumen = json.loads(response)
            
            logger.info(f"Resumen técnico generado: {resumen.get('complejidad')} complejidad")
            
            return resumen
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta JSON: {e}\nRespuesta: {response}")
            return None
    
    def analizar_licitacion_completa(
        self,
        titulo: str,
        descripcion: str,
        texto_pliego: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Realiza un análisis completo de una licitación
        
        Args:
            titulo: Título de la licitación
            descripcion: Descripción breve
            texto_pliego: Texto completo del pliego técnico (opcional)
            
        Returns:
            Diccionario con análisis completo
        """
        logger.info(f"Iniciando análisis completo de licitación: {titulo[:50]}...")
        
        # Identificar stack tecnológico
        stack = self.identificar_stack_tecnologico(titulo, descripcion, texto_pliego)
        
        # Clasificar conceptos
        conceptos = self.clasificar_conceptos_tic(titulo, descripcion)
        
        # Generar resumen técnico
        resumen = self.generar_resumen_tecnico(titulo, descripcion, texto_pliego)
        
        if not stack and not conceptos and not resumen:
            logger.error("No se pudo completar ningún análisis")
            return None
        
        resultado = {
            'stack_tecnologico': stack or {},
            'conceptos_tic': conceptos or [],
            'resumen_tecnico': resumen or {},
            'analizado_con_pliego': texto_pliego is not None
        }
        
        logger.info(f"Análisis completo finalizado")
        
        return resultado
    
    def clear_cache(self):
        """Limpia la caché de respuestas"""
        self._cache.clear()
        logger.info("Caché de IA limpiada")

