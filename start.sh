#!/bin/bash
export TOOL_API_KEY=toolarr-benchmark-key-2026
export SONARR_INSTANCE_1_NAME=sonarr
export SONARR_INSTANCE_1_URL=http://192.168.45.15:8083
export SONARR_INSTANCE_1_API_KEY=7ce61d72c943483ca03864e03f013127
export RADARR_INSTANCE_1_NAME=radarr
export RADARR_INSTANCE_1_URL=http://192.168.45.15:5051
export RADARR_INSTANCE_1_API_KEY=d81da54eab704db0aa2d4e1d66cd697a

cd /home/cory/proj/toolarr
python3 -m uvicorn main:app --host 0.0.0.0 --port 8010
