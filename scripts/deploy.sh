#!/bin/bash
set -e

echo "Deploying Prism Medical Text-to-Video Agent..."

# Build and start services
cd docker
docker-compose build
docker-compose up -d

# Show logs
echo "Services started. Showing logs..."
docker-compose logs -f

# To stop services, run: ./scripts/stop.sh
# To view logs separately, run: cd docker && docker-compose logs -f [service_name]
