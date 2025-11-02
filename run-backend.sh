#!/bin/bash
# Start the ML Engineer Agent Backend

cd "$(dirname "$0")/backend"

echo "🚀 Starting ML Engineer Agent Backend..."
echo "📡 API will be available at http://localhost:8000"
echo ""

python api_server.py

