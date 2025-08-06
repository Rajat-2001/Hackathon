#!/bin/bash

# Chatterbox TTS Optimization Startup Script
# This script starts the persistent chatterbox server for optimized performance

echo "🚀 Starting Chatterbox TTS Optimization Server..."

# Set environment variables
export CUDA_VISIBLE_DEVICES=0  # Use first GPU
export PYTHONPATH="/var/www/html/zsapiens/hindi_english/pronunciation_analysis:$PYTHONPATH"

# Navigate to the chatterbox directory
cd /var/www/html/zsapiens/hindi_english/pronunciation_analysis/chatterbox

# Activate the chatter_box conda environment and start the server
conda run -n chatter_box python chatterbox_server.py &

# Store the PID for later management
echo $! > /var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/chatterbox_server.pid

echo "✅ Chatterbox server started with PID $(cat /var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/chatterbox_server.pid)"
echo "🌐 Server running on http://localhost:8001"
echo "📊 Health check: curl http://localhost:8001/health"
echo ""
echo "To stop the server, run:"
echo "kill $(cat /var/www/html/zsapiens/hindi_english/pronunciation_analysis/sessions/chatterbox_server.pid)"