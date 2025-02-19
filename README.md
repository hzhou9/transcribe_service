# Audio Transcription with Speaker Detection

A modular system that transcribes audio files while identifying and separating different speakers. The system provides accurate transcriptions with speaker labels, making it perfect for meetings, interviews, or any multi-speaker audio content.

## Features

### Modular Architecture
- **SRT Server**: Handles voice-to-text transcription using Whisper
- **Worker Server**: Manages speaker detection and orchestrates the transcription process
- Independent services that can be scaled or modified separately

### Fully Localized Deployment
- All processing happens on your local machine
- No data sent to external services
- Complete privacy and data control
- Works offline once models are downloaded

## Core Services

### SRT Server (Speech-to-Text)
- Powered by OpenAI's Whisper model
- Supports multiple languages
- Configurable parameters for transcription accuracy
- RESTful API interface
- Optimized for GPU acceleration when available

### Worker Server (Speaker Detection)
- Uses pyannote-audio for speaker diarization
- Segments audio by speaker
- Coordinates with SRT Server for transcription
- Provides timestamped output with speaker labels
- Handles audio preprocessing and segmentation

## Getting Started

[Preparation]
Accept pyannote/segmentation-3.0 user conditions
Accept pyannote/speaker-diarization-3.1 user conditions
Create access token at hf.co/settings/tokens.

# Use byobu to manage multiple sessions
sudo apt install byobu

# install miniforge
wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh

[Environment]
mamba create -y -n proj_transcribe python=3.11
mamba activate proj_transcribe

[Install]
Check out the repo and run:
pip install -r requirements.txt

[Run]
./run.sh

Visit http://localhost:8000 to try the demo.