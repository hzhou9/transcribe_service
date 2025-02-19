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
    # Send the command to the new window
    byobu send-keys -t "$window_index" "$command" C-m
}

# Create a new byobu session named 'voicechat2' or attach to it if it already exists
byobu new-session -d -s proj_transcribe

# SRT server (HF transformers w/ distil-whisper)
create_window "srt" "mamba activate proj_transcribe && uvicorn srt-server:app --host 0.0.0.0 --port 9001"
echo "create_window srt"
