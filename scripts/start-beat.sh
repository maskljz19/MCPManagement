#!/bin/bash

# Celery Beat startup script
# Ensures proper initialization and cleanup

set -e

echo "Starting Celery Beat..."

# Remove any existing beat schedule file to avoid conflicts
rm -f /app/celerybeat-schedule
rm -f /app/celerybeat.pid

# Wait for dependencies
echo "Waiting for RabbitMQ..."
while ! nc -z $RABBITMQ_HOST $RABBITMQ_PORT; do
  sleep 1
done
echo "RabbitMQ is ready!"

echo "Waiting for Redis..."
while ! nc -z $REDIS_HOST $REDIS_PORT; do
  sleep 1
done
echo "Redis is ready!"

# Start Celery Beat
echo "Starting Celery Beat scheduler..."
exec celery -A app.core.celery_app beat \
    --loglevel=info \
    --pidfile=/app/celerybeat.pid \
    --schedule=/app/celerybeat-schedule