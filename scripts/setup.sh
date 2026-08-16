#!/bin/bash
# Setup script cho AI20K project

set -e

echo "=== AI20K Project Setup ==="

# Check Python version
python3 -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'"
echo "Python version OK"

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create development environment config if not exists
if [ ! -f .env.development ]; then
    cp .env.development.example .env.development
    echo "Created .env.development — please edit local development values if needed"
fi

# Create data directories
mkdir -p data/chroma

echo "Setup complete! Run: uvicorn src.main:app --reload"
