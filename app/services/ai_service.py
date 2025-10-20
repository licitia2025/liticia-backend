"""
Servicio de análisis con IA usando OpenAI (versión con requests directos)
"""
import requests
from app.core.config import settings
from typing import Dict, List, Optional
import logging
import json
import hashlib

logger = logging.getLogger(__name__)


class AIService:
    """Servicio para análisis de licitaciones con IA"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.temperature = settings.OPENAI_TEMPERATURE
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self._cache = {}  # Cache simple en memoria
    
    def _get_cache_key(self, text: str, prompt_type: str) -> str:
        """Genera una clave de caché basada en el hash del texto"""
        content = f"{prompt_type}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _call_openai(self, system_prompt: str, user_prompt: str, cache_key: Optional[str] = None) -> Optional[str]:
        """
        Llama a la API de OpenAI usando requests directamente
        
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
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"Error en API de OpenAI: {response.status_code} - {response.text}")
                return None
            
            result_data = response.json()
            result = result_data['choices'][0]['message']['content']
            
            # Log de uso de tokens
            usage = result_data.get('usage', {})
            logger.info(f"Tokens usados - Input: {usage.get('prompt_tokens', 0)}, Output: {usage.get('completion_tokens', 0)}, Total: {usage.get('total_tokens', 0)}")
            
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
        
        # Generar título adaptado
        titulo_adaptado = self.generar_titulo_adaptado(titulo)
        
        # Identificar stack tecnológico
        stack = self.identificar_stack_tecnologico(titulo, descripcion, texto_pliego)
        
        # Clasificar conceptos
        conceptos = self.clasificar_conceptos_tic(titulo, descripcion)
        
        # Generar resumen técnico
        resumen = self.generar_resumen_tecnico(titulo, descripcion, texto_pliego)
        
        if not stack and not conceptos and not resumen and not titulo_adaptado:
            logger.error("No se pudo completar ningún análisis")
            return None
        
        resultado = {
            'titulo_adaptado': titulo_adaptado,
            'stack_tecnologico': stack or {},
            'conceptos_tic': conceptos or [],
            'resumen_tecnico': resumen or {},
            'analizado_con_pliego': texto_pliego is not None
        }
        
        logger.info(f"Análisis completo finalizado")
        
        return resultado
    
    def generar_titulo_adaptado(self, titulo_original: str) -> Optional[str]:
        """
        Genera un título más natural y conciso a partir del título original
        
        Args:
            titulo_original: Título original de la licitación
            
        Returns:
            Título adaptado o None si falla
        """
        system_prompt = """Eres un experto en redacción que adapta títulos de licitaciones públicas.

Tu tarea es convertir títulos largos y burocráticos en títulos más naturales, concisos y fáciles de leer.

Reglas:
1. Máximo 80 caracteres
2. Eliminar redundancias y jerga burocrática
3. Mantener la información esencial: qué se contrata y para qué
4. Usar lenguaje natural y directo
5. NO incluir códigos, expedientes ni referencias administrativas
6. Responder SOLO con el título adaptado, sin comillas ni explicaciones

Ejemplos:

Original: "Servicio de mantenimiento correctivo y evolutivo del sistema de información de gestión económica y presupuestaria del Ayuntamiento de Madrid para el ejercicio 2025"
Adaptado: "Mantenimiento del sistema de gestión económica del Ayuntamiento de Madrid"

Original: "Contrato de servicios para el desarrollo, implantación y mantenimiento de una plataforma digital de tramitación telemática basada en tecnologías cloud"
Adaptado: "Desarrollo de plataforma digital de tramitación en la nube"

Original: "Suministro e instalación de equipamiento informático y licencias de software para la modernización de la infraestructura TI"
Adaptado: "Equipamiento informático y licencias para modernización TI"""
        
        user_prompt = f"Título original: {titulo_original}"
        
        cache_key = self._get_cache_key(titulo_original, "titulo_adaptado")
        
        response = self._call_openai(system_prompt, user_prompt, cache_key)
        
        if not response:
            return None
        
        # Limpiar la respuesta (eliminar comillas si las hay)
        titulo_adaptado = response.strip().strip('"').strip("'")
        
        # Validar longitud
        if len(titulo_adaptado) > 100:
            logger.warning(f"Título adaptado muy largo ({len(titulo_adaptado)} caracteres), truncando...")
            titulo_adaptado = titulo_adaptado[:97] + "..."
        
        logger.info(f"Título adaptado generado: {titulo_adaptado}")
        
        return titulo_adaptado
    
    def clear_cache(self):
        """Limpia la caché de respuestas"""
        self._cache.clear()
        logger.info("Caché de IA limpiada")

