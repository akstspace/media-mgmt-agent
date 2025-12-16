#!/bin/bash

docker build -t media-manager-ai .

docker volume create media-data

docker stop media-manager-ai 2>/dev/null || true
docker rm media-manager-ai 2>/dev/null || true

# Run the container with volume attached
docker run -d \
    --name media-manager-ai \
    --network host \
    -v media-data:/data \
    -e TZ=UTC \
    -e DATA_DIR=/data \
    --restart unless-stopped \
    --health-cmd "curl -f http://localhost:8501/_stcore/health || exit 1" \
    --health-interval 30s \
    --health-timeout 10s \
    --health-retries 3 \
    --health-start-period 40s \
    media-manager-ai

echo "Container started successfully!"
