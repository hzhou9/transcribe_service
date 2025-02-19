#!/bin/bash

# Check if byobu is installed
if ! command -v byobu &> /dev/null; then
    echo "byobu is not installed. Please install it and try again."
    exit 1
fi

# Function to create a new window and run a command
create_window() {
    local window_name=$1
    local command=$2
    local window_index=$(byobu list-windows | grep "$window_name" | awk -F: '{print $1}')
    byobu send-keys -t "$window_index" "$command" C-m
}

# Create a new byobu session named 'voicechat2' or attach to it if it already exists
byobu new-session -d -s proj_transcribe

# FastAPI server (with Mamba activation)
create_window "worker" "mamba activate proj_transcribe && uvicorn worker-server:app --host 0.0.0.0 --port 8000"
echo "create_window worker"
