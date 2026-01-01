#!/bin/bash

# Celery Beat health check script
# Simple check if beat process is running

set -e

# Check if celery beat process is running
if pgrep -f "celery.*beat" > /dev/null 2>&1; then
    echo "Celery Beat is running"
    exit 0
else
    echo "Celery Beat is not running"
    exit 1
fi