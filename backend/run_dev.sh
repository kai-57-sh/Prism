#!/bin/bash
# Backend Development Startup Script
# This script starts the FastAPI backend with environment variable loading

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Prism Backend (Development Mode)${NC}"
echo ""

# Change to backend directory
cd "$(dirname "$0")"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "${YELLOW}Please create .env file with required API keys:${NC}"
    echo ""
    echo "  DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx"
    echo "  MODELSCOPE_API_KEY=ms-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    echo "  MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1"
    echo "  QWEN_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507"
    echo ""
    echo -e "${YELLOW}See .env.example for complete configuration${NC}"
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

echo -e "${YELLOW}Configuration:${NC}"
echo -e "  Database URL: ${DATABASE_URL:-sqlite:///./data/jobs.db}"
echo -e "  Redis URL: ${REDIS_URL:-redis://localhost:6379/0}"
echo -e "  Log Level: ${LOG_LEVEL:-INFO}"
echo ""
echo -e "${GREEN}Starting Uvicorn server...${NC}"
echo -e "${YELLOW}Backend will run on:${NC} http://localhost:8000"
echo -e "${YELLOW}API Documentation:${NC} http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start Uvicorn with auto-reload
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
