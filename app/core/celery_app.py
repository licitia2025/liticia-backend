"""
Configuración de Celery para Liticia
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Crear instancia de Celery
celery_app = Celery(
    "liticia",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.scraping_tasks",
        "app.tasks.processing_tasks",
        "app.tasks.ai_tasks",
    ]
)

# Configuración de Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Madrid",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutos
    task_soft_time_limit=25 * 60,  # 25 minutos
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Configuración de Beat (tareas programadas)
# FASE 1: VALIDACIÓN - Scraping cada 3 horas para optimizar costes
celery_app.conf.beat_schedule = {
    # Scraping cada 3 horas (optimización de costes Fase 1)
    'scrape-placsp-every-3-hours': {
        'task': 'app.tasks.scraping_tasks.scrape_placsp_recent',
        'schedule': crontab(
            minute='0',
            hour='*/3'  # Cada 3 horas: 00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00
        ),
        'kwargs': {'days': 1}
    },
    
    # Scraping completo semanal (Domingos a las 3:00 AM)
    'scrape-placsp-full-weekly': {
        'task': 'app.tasks.scraping_tasks.scrape_placsp_full',
        'schedule': crontab(
            hour='3',
            minute='0',
            day_of_week='0'  # Domingo
        ),
        'kwargs': {'max_pages': 100}
    },
    
    # Procesamiento de documentos pendientes (cada hora)
    'process-pending-documents': {
        'task': 'app.tasks.processing_tasks.process_pending_documents',
        'schedule': crontab(minute='15'),
        'kwargs': {'limit': 10}
    },
    
    # Análisis con IA de licitaciones pendientes (cada 6 horas - Fase 1 optimización)
    'analyze-pending-licitaciones': {
        'task': 'app.tasks.ai_tasks.analyze_pending_licitaciones',
        'schedule': crontab(minute='30', hour='*/6'),  # Cada 6 horas en lugar de 2
        'kwargs': {'limit': 10}  # Reducido de 20 a 10 por ejecución
    },
    
    # Limpieza de licitaciones antiguas (diario a las 4:00 AM)
    'cleanup-old-licitaciones': {
        'task': 'app.tasks.scraping_tasks.cleanup_old_licitaciones',
        'schedule': crontab(hour='4', minute='0'),
        'kwargs': {'days': 365}
    },
}

# Configuración de rutas de tareas
celery_app.conf.task_routes = {
    'app.tasks.scraping_tasks.*': {'queue': 'scraping'},
    'app.tasks.processing_tasks.*': {'queue': 'processing'},
    'app.tasks.ai_tasks.*': {'queue': 'ai'},
}

# Configuración de prioridades
celery_app.conf.task_default_priority = 5
celery_app.conf.task_queue_max_priority = 10

