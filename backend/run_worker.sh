#!/bin/bash
# Backend RQ worker startup script

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting Prism RQ Worker (Development Mode)${NC}"
echo ""

cd "$(dirname "$0")"

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

set -a
source .env
set +a

queue_name="${RQ_QUEUE_NAME:-prism}"
redis_url="${REDIS_URL:-redis://localhost:6379/0}"

echo -e "${YELLOW}Configuration:${NC}"
echo -e "  Redis URL: ${redis_url}"
echo -e "  Queue: ${queue_name}"
echo ""
echo -e "${GREEN}Starting RQ worker...${NC}"
echo ""

rq worker --url "${redis_url}" "${queue_name}"
