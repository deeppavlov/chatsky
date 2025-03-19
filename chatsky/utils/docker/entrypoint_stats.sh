#!/usr/bin/env bash
export SERVER_THREADS_AMOUNT=8
set -m
nohup /bin/bash /usr/bin/run-server.sh &
sleep 5
superset fab create-admin --firstname superset --lastname admin --username $SUPERSET_USERNAME --email admin@admin.com --password $SUPERSET_PASSWORD
superset db upgrade
superset init
fg