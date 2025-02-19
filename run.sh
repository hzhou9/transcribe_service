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
    byobu new-window -n "$window_name"
    byobu send-keys -t "$window_name" "$command" C-m
}

# Create a new byobu session named 'voicechat2' or attach to it if it already exists
byobu new-session -d -s proj_transcribe

# FastAPI server (with Mamba activation)
create_window "worker" "mamba activate proj_transcribe && uvicorn worker-server:app --host 0.0.0.0 --port 8000"
echo "create_window voicechat2"

# SRT server (HF transformers w/ distil-whisper)
create_window "srt" "mamba activate proj_transcribe && uvicorn srt-server:app --host 0.0.0.0 --port 9001"
echo "create_window srt"

#create_window "watchdog" "./watchdog.sh"
#echo "create_window watchdog"

# Attach to the session
byobu attach-session -t proj_transcribe

echo "To attach to the session, use: byobu attach -t proj_transcribe"
echo "To detach from the session, use: Ctrl-a d"
