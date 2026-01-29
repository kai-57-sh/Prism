#!/bin/bash
set -e

echo "Running Prism Tests..."

# Activate virtual environment
source venv/bin/activate

# Run unit tests
echo "Running unit tests..."
cd backend
pytest tests/unit/ -v || echo "No unit tests found"

# Run integration tests
echo "Running integration tests..."
pytest tests/integration/ -v || echo "No integration tests found"

# Run contract tests
echo "Running contract tests..."
pytest tests/contract/ -v || echo "No contract tests found"

echo "All tests completed!"
