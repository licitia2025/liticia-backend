#!/bin/bash
# Script para iniciar Celery beat (scheduler de tareas programadas)

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Iniciar Celery beat
celery -A app.core.celery_app beat \
    --loglevel=info \
    --scheduler=celery.beat:PersistentScheduler

