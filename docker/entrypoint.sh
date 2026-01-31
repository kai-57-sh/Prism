#!/bin/sh
set -e

: "${DATA_DIR:=/mnt/workspace/data}"
: "${STATIC_ROOT:=/mnt/workspace/static}"
: "${STATIC_VIDEO_SUBDIR:=vedios}"
: "${STATIC_AUDIO_SUBDIR:=audio}"
: "${STATIC_METADATA_SUBDIR:=metadata}"
: "${REDIS_URL:=redis://localhost:6379/0}"
: "${RQ_QUEUE_NAME:=prism}"

if [ -z "${DATABASE_URL:-}" ]; then
    DATABASE_URL="sqlite:///${DATA_DIR}/jobs.db"
    export DATABASE_URL
fi

mkdir -p \
    "${DATA_DIR}" \
    "${STATIC_ROOT}/${STATIC_VIDEO_SUBDIR}" \
    "${STATIC_ROOT}/${STATIC_AUDIO_SUBDIR}" \
    "${STATIC_ROOT}/${STATIC_METADATA_SUBDIR}"

redis-server --save "" --appendonly no &

sleep 1

cd /app/backend

rq worker --url "${REDIS_URL}" "${RQ_QUEUE_NAME}" &
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --log-level "${LOG_LEVEL:-info}" &

exec nginx -g "daemon off;"
