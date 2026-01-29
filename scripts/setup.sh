#!/bin/bash
set -e

echo "Setting up Prism Medical Text-to-Video Agent..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3.11 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
pip install -r requirements.txt
cd ..

# Create necessary directories
echo "Creating data directories..."
mkdir -p ./data
mkdir -p ./static/vedios
mkdir -p ./static/audio
mkdir -p ./static/metadata
mkdir -p /var/lib/prism/static/vedios
mkdir -p /var/lib/prism/static/audio
mkdir -p /var/lib/prism/static/metadata

# Set STATIC_ROOT environment variable
export STATIC_ROOT=/var/lib/prism/static

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure your API keys"
echo "2. Run './scripts/deploy.sh' to start the services"
