#!/bin/bash

# Startup script for Media Manager AI

# Create data directory if it doesn't exist
mkdir -p /data

# Set proper permissions
chmod 755 /data

# Run Streamlit
exec streamlit run media_ui.py \
     --server.port=8501 \
     --server.address=0.0.0.0 \
     --server.headless=true \
     --server.fileWatcherType=none \
     --browser.gatherUsageStats=false
