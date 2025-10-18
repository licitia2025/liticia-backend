#!/bin/bash
# Script para iniciar Celery worker

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Iniciar Celery worker con 3 colas
celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=scraping,processing,ai \
    --hostname=worker@%h

