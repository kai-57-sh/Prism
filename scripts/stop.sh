#!/bin/bash
set -e

echo "Stopping Prism Medical Text-to-Video Agent..."

cd docker
docker-compose down

echo "Services stopped."
