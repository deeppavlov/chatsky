#!/usr/bin/env bash
export SERVER_THREADS_AMOUNT=8
set -m
nohup /bin/bash /usr/bin/run-server.sh &
/bin/bash /app/docker/health_stats.sh http://localhost:8088/health
superset fab create-admin --firstname superset --lastname admin --username $SUPERSET_USERNAME --email admin@admin.com --password $SUPERSET_PASSWORD
superset db upgrade
superset init
fg