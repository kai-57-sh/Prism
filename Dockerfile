FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/index.html ./
COPY frontend/vite.config.ts ./
COPY frontend/tsconfig.json ./
COPY frontend/postcss.config.js ./
COPY frontend/tailwind.config.js ./
COPY frontend/src ./src
COPY frontend/public ./public

ARG VITE_BASE=./
ENV VITE_BASE=$VITE_BASE

RUN npm run build

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    g++ \
    libgomp1 \
    nginx \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

COPY docker/nginx.modelscope.conf /etc/nginx/nginx.conf
COPY docker/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

ENV DATA_DIR=/mnt/workspace/data \
    STATIC_ROOT=/mnt/workspace/static \
    REDIS_URL=redis://localhost:6379/0 \
    RQ_QUEUE_NAME=prism

EXPOSE 7860

CMD ["/app/entrypoint.sh"]
