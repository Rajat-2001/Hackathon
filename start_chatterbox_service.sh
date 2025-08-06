#!/bin/bash

# Start ChatterboxTTS Persistent Service
# This script should be run in the chatter_box conda environment

echo "🚀 Starting ChatterboxTTS Persistent Service..."

# Activate the chatter_box conda environment and run the service
exec conda run -n chatter_box python chatterbox_service.py