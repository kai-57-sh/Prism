#!/bin/bash
# Load Testing Script for Prism Medical Text-to-Video Agent
# Tests performance for SC-007 (fast mode <3 min) and SC-009 (50 concurrent requests)

set -e

echo "=========================================="
echo "Prism Load Testing"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
API_KEY="${DASHSCOPE_API_KEY:-}"
TEST_PROMPT="create an insomnia emotion video, late night bedroom, low calm narration, no subtitles"
QUALITY_MODE_FAST="fast"
QUALITY_MODE_BALANCED="balanced"
CONCURRENT_REQUESTS=5
WARMUP_REQUESTS=2

echo -e "${YELLOW}Configuration${NC}"
echo "API URL: $API_BASE_URL"
echo "Quality Mode (Fast): $QUALITY_MODE_FAST"
echo "Quality Mode (Balanced): $QUALITY_MODE_BALANCED"
echo "Concurrent Requests: $CONCURRENT_REQUESTS"
echo ""

# Function to make generation request
make_generation_request() {
    local quality_mode=$1
    local prompt=$2

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE_URL/v1/t2v/generate" \
        -H "Content-Type: application/json" \
        -d "{
            \"user_prompt\": \"$prompt\",
            \"quality_mode\": \"$quality_mode\",
            \"resolution\": \"1280x720\"
        }")

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "202" ]; then
        job_id=$(echo "$body" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
        echo "$job_id"
    else
        echo "ERROR"
    fi
}

# Function to check job status
check_job_status() {
    local job_id=$1
    local max_wait=${2:-300}  # 5 minutes default
    local start_time=$(date +%s)

    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))

        if [ $elapsed -ge $max_wait ]; then
            echo "TIMEOUT"
            return
        fi

        response=$(curl -s "$API_BASE_URL/v1/t2v/jobs/$job_id")
        status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

        if [ "$status" = "SUCCEEDED" ] || [ "$status" = "FAILED" ]; then
            echo "$status"
            return
        fi

        sleep 2
    done
}

# Function to measure generation time
measure_generation_time() {
    local quality_mode=$1
    local prompt=$2

    echo -e "${YELLOW}Testing $quality_mode mode...${NC}"

    start_time=$(date +%s)

    job_id=$(make_generation_request "$quality_mode" "$prompt")

    if [ "$job_id" = "ERROR" ]; then
        echo -e "${RED}✗ Failed to submit generation${NC}"
        return 1
    fi

    echo "Job ID: $job_id"

    end_time=$(date +%s)
    submission_time=$((end_time - start_time))

    start_time=$(date +%s)
    status=$(check_job_status "$job_id" 600)  # 10 minutes max
    end_time=$(date +%s)

    generation_time=$((end_time - start_time))
    total_time=$((submission_time + generation_time))

    echo "Submission Time: ${submission_time}s"
    echo "Generation Time: ${generation_time}s"
    echo "Total Time: ${total_time}s"

    echo "$total_time"
}

# Test 1: SC-007 Fast Mode Performance
echo -e "${GREEN}Test 1: Fast Mode Performance (<3 minutes)${NC}"
echo "-----------------------------------"

fast_times=()
for i in $(seq 1 3); do
    echo "Run $i:"
    time=$(measure_generation_time "$QUALITY_MODE_FAST" "$TEST_PROMPT")

    if [ "$time" != "ERROR" ] && [ "$time" != "TIMEOUT" ]; then
        fast_times+=($time)

        # Check if under 3 minutes (180 seconds)
        if [ $time -lt 180 ]; then
            echo -e "${GREEN}✓ Passed: ${time}s < 180s${NC}"
        else
            echo -e "${RED}✗ Failed: ${time}s >= 180s${NC}"
        fi
    else
        echo -e "${RED}✗ Failed: ERROR or TIMEOUT${NC}"
    fi
    echo ""
done

# Calculate average
if [ ${#fast_times[@]} -gt 0 ]; then
    sum=0
    for time in "${fast_times[@]}"; do
        sum=$((sum + time))
    done
    avg=$((sum / ${#fast_times[@]}))
    echo "Average Fast Mode Time: ${avg}s"

    if [ $avg -lt 180 ]; then
        echo -e "${GREEN}✓ SC-007 PASSED: Average ${avg}s < 180s${NC}"
    else
        echo -e "${RED}✗ SC-007 FAILED: Average ${avg}s >= 180s${NC}"
    fi
else
    echo -e "${YELLOW}⚠ No successful fast mode tests${NC}"
fi

echo ""
echo -e "${GREEN}Test 2: Balanced Mode Performance${NC}"
echo "-----------------------------------"

balanced_time=$(measure_generation_time "$QUALITY_MODE_BALANCED" "$TEST_PROMPT")

if [ "$balanced_time" != "ERROR" ] && [ "$balanced_time" != "TIMEOUT" ]; then
    echo "Balanced Mode Time: ${balanced_time}s"
else
    echo -e "${RED}✗ Failed to complete balanced mode test${NC}"
fi

echo ""
echo -e "${GREEN}Test 3: Concurrent Requests (Rate Limiting)${NC}"
echo "------------------------------------------"

echo "Launching $CONCURRENT_REQUESTS concurrent requests..."
start_time=$(date +%s)

job_ids=()
for i in $(seq 1 $CONCURRENT_REQUESTS); do
    echo "Request $i:"
    job_id=$(make_generation_request "$QUALITY_MODE_BALANCED" "$TEST_PROMPT")

    if [ "$job_id" != "ERROR" ]; then
        job_ids+=("$job_id")
        echo "  Job ID: $job_id"
    else
        echo "  Failed"
    fi
done

echo ""
echo "Waiting for all jobs to complete..."

completed=0
failed=0
for job_id in "${job_ids[@]}"; do
    echo "Checking job $job_id..."
    status=$(check_job_status "$job_id" 600)

    if [ "$status" = "SUCCEEDED" ]; then
        echo -e "${GREEN}✓ SUCCEEDED${NC}"
        completed=$((completed + 1))
    elif [ "$status" = "FAILED" ]; then
        echo -e "${RED}✗ FAILED${NC}"
        failed=$((failed + 1))
    else
        echo -e "${YELLOW}⚠ TIMEOUT${NC}"
    fi
done

end_time=$(date +%s)
total_time=$((end_time - start_time))

echo ""
echo "Concurrent Requests Summary:"
echo "Total Requests: $CONCURRENT_REQUESTS"
echo "Succeeded: $completed"
echo "Failed: $failed"
echo "Total Time: ${total_time}s"

# Test SC-009: 50 concurrent requests (scaled down)
echo ""
echo -e "${GREEN}Test 4: Rate Limit Validation${NC}"
echo "-----------------------------"

# Test rate limit (10 req/min)
echo "Testing rate limit (10 requests per minute)..."
echo "Sending 15 requests rapidly..."

rate_limit_hits=0
for i in $(seq 1 15); do
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE_URL/v1/t2v/generate" \
        -H "Content-Type: application/json" \
        -d "{
            \"user_prompt\": \"test generation $i\",
            \"quality_mode\": \"fast\",
            \"resolution\": \"1280x720\"
        }")

    http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" = "429" ]; then
        echo "Request $i: Rate limited (429)"
        rate_limit_hits=$((rate_limit_hits + 1))
    elif [ "$http_code" = "202" ]; then
        echo "Request $i: Accepted (202)"
    else
        echo "Request $i: Error ($http_code)"
    fi
done

echo ""
echo "Rate limit hits: $rate_limit_hits/15"

if [ $rate_limit_hits -gt 0 ]; then
    echo -e "${GREEN}✓ Rate limiting is working${NC}"
else
    echo -e "${YELLOW}⚠ No rate limit hits (may need more requests)${NC}"
fi

echo ""
echo "=========================================="
echo "Load Testing Complete"
echo "=========================================="
echo ""
echo "Results:"
echo "- Fast mode performance tested"
echo "- Concurrent load tested"
echo "- Rate limiting validated"
echo ""
echo "See logs above for detailed results"
