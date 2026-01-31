#!/bin/bash

# Prism Backend Test Runner

set -e

echo "==================================="
echo "Prism Backend Test Suite"
echo "==================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to backend directory
cd "$(dirname "$0")"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found${NC}"
    echo "Install dependencies: pip install -r requirements.txt"
    exit 1
fi

# Parse arguments
TEST_TYPE=""
COVERAGE=false
VERBOSE=false
SKIP_INTEGRATION=false

while [[ $# -gt 0 ]]; do
    case $1 in
        unit)
            TEST_TYPE="unit"
            shift
            ;;
        integration)
            TEST_TYPE="integration"
            shift
            ;;
        contract)
            TEST_TYPE="contract"
            shift
            ;;
        all)
            TEST_TYPE="all"
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --skip-integration)
            SKIP_INTEGRATION=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Default to unit tests if no type specified
if [ -z "$TEST_TYPE" ]; then
    TEST_TYPE="unit"
fi

# Build pytest command
PYTEST_CMD="pytest"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v -s"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=html --cov-report=term"
fi

# Run tests based on type
run_tests() {
    local test_path=$1
    local test_name=$2

    echo ""
    echo "==================================="
    echo "Running $test_name"
    echo "==================================="
    echo ""

    if [ "$SKIP_INTEGRATION" = true ] && [ "$test_type" = "integration" ]; then
        echo -e "${YELLOW}Skipping integration tests (--skip-integration)${NC}"
        return 0
    fi

    eval "$PYTEST_CMD $test_path"
    local result=$?

    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✓ $test_name passed${NC}"
    else
        echo -e "${RED}✗ $test_name failed${NC}"
    fi

    return $result
}

# Execute tests
case $TEST_TYPE in
    unit)
        run_tests "tests/unit" "Unit Tests"
        ;;
    integration)
        run_tests "tests/integration" "Integration Tests"
        ;;
    contract)
        run_tests "tests/contract" "Contract Tests"
        ;;
    all)
        run_tests "tests/unit" "Unit Tests" || EXIT_CODE=$?
        run_tests "tests/integration" "Integration Tests" || EXIT_CODE=$?
        run_tests "tests/contract" "Contract Tests" || EXIT_CODE=$?
        ;;
esac

# Generate coverage report if requested
if [ "$COVERAGE" = true ]; then
    echo ""
    echo "==================================="
    echo "Coverage Report Generated"
    echo "==================================="
    echo "HTML report: htmlcov/index.html"
fi

echo ""
echo "==================================="
echo "Test Suite Complete"
echo "==================================="

if [ ${EXIT_CODE:-0} -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi
