import asyncio
import aiohttp
import io
import json
import os
import re
import soundfile as sf
import tempfile
import time
import traceback
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
from collections import defaultdict
from typing import Dict
from pydub import AudioSegment

from typing import Any, Mapping, Optional, Text


SRT_ENDPOINT = os.getenv("SRT_ENDPOINT", "http://localhost:9001/inference")
KEY_HUGGINGFACE = os.getenv("KEY_HUGGINGFACE", "hf_***")

pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=KEY_HUGGINGFACE)
device = "cuda" if torch.cuda.is_available() else "cpu"
pipeline.to(torch.device(device))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Origins allowed to access your API
    allow_credentials=True,
    allow_methods=["*"],  # HTTP methods allowed
    allow_headers=["*"],  # Headers allowed
)

app.mount("/web", StaticFiles(directory="web"), name="web")

UPLOAD_DIR = "web/audio_upload"
os.makedirs(UPLOAD_DIR, exist_ok=True)

background_tasks: Dict[str, asyncio.Task] = {}
task_results: Dict[str, any] = defaultdict(dict)

class CustomProgressHook(ProgressHook):
    def __init__(self, name):
        self.name = name
        return super().__init__()

    def __call__(
        self,
        step_name: Text,
        step_artifact: Any,
        file: Optional[Mapping] = None,
        total: Optional[int] = None,
        completed: Optional[int] = None,
    ):
        if completed is None:
            completed = total = 1

        progress = (completed / total) * 100
        progress_info = f"{step_name} ({progress:.0f}%)"
        task_results[self.name]["info"] = progress_info
        return super().__call__(step_name, step_artifact, file, total, completed)

    def __enter__(self):
        return super().__enter__()

    def __exit__(self, *args):
        return super().__exit__(*args)

async def transcribe_audio(audio_file_path, lang = None):
    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            # Check if file exists and is readable
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
                
            # Open file in binary read mode
            with open(audio_file_path, 'rb') as f:
                data.add_field('file', f, filename=os.path.basename(audio_file_path))
                data.add_field('temperature', "0.0")
                data.add_field('temperature_inc', "0.2")
                data.add_field('response_format', "json")
                if lang is not None:
                    data.add_field('lang', lang)
                async with session.post(SRT_ENDPOINT, data=data) as response:
                    result = await response.json()
                    print(f"transcribe_audio: {result}")
            return result['text']
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        print(traceback.format_exc())
        raise

async def diarize_audio(audio_file_path, filename):
    try:
        # apply pretrained pipeline (with optional progress hook)
        audio = AudioSegment.from_file(audio_file_path)
        audio = audio.set_frame_rate(16000)
        temp_path = f"{audio_file_path}.temp.wav"
        audio.export(temp_path, format="wav")

        async def run_pipeline():
            with CustomProgressHook(filename) as hook:
                return await asyncio.to_thread(pipeline, temp_path, hook=hook)
                
        diarization = await run_pipeline()
        # get the total duration of the audio file in seconds
        total_duration = max(segment.end for segment in diarization.get_timeline())
        count = 0
        transcribe_data = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            # print(f"start={turn.start:.1f}s stop={turn.end:.1f}s {speaker}")
            if turn.end - turn.start > 0.5:
                count += 1
                percentage = int((turn.start / total_duration) * 100)
                progress_info = f"Transcribing ({percentage}%)"
                task_results[filename]["info"] = progress_info

                # extract the audio segment from turn.start to turn.end in the audio file
                audio_segment = AudioSegment.from_file(temp_path)[turn.start*1000:turn.end*1000]
                # save the audio segment to a new file
                subaudio_file_path = f"{audio_file_path}.{count}.wav"
                audio_segment.export(subaudio_file_path, format="wav")
                print(f"Transcribing {subaudio_file_path} ({turn.start}:{turn.end})")
                text = await transcribe_audio(subaudio_file_path)
                transcribe_data.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker,
                    "text": text,
                    "file": subaudio_file_path
                })
        
        # Sort transcribe_data by end time
        transcribe_data.sort(key=lambda x: x["end"])

        os.remove(temp_path)
        return transcribe_data
    except Exception as e:
        print(f"Diarization error: {str(e)}")
        print(traceback.format_exc())
        raise

@app.get("/")
def read_root():
    return FileResponse("web/test.html")

@app.get("/ping")
def ping():
    return JSONResponse(
        content={},
        media_type="application/json"
    )

@app.get("/task_status/{filename}")
async def get_task_status(filename: str):
    if filename in task_results:
        if task_results[filename]["error"] is not None:
            return {"status": "failed", "error": task_results[filename]["error"]}
        else:
            if task_results[filename]["data"] is not None:
                return {"status": "completed", "data": task_results[filename]["data"]}
            else:
                return {"status": "processing", "info": task_results[filename]["info"]}
    return {"status": "not_found"}

@app.post("/upload_audio")
async def upload_audio(file: UploadFile = File(...)):
    try:
        # 生成唯一的文件名
        timestamp = int(time.time())
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # 保存上传的文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 创建后台任务
        async def process_audio():
            try:
                result = await diarize_audio(file_path, filename)
                task_results[filename]["data"] = result
            except Exception as e:
                errormsg = f"Background task error: {str(e)}"
                task_results[filename]["error"] = errormsg
                print(errormsg)
                raise

        task_results[filename] = {
            "info": "Upload success",
            "error": None,
            "data": None
        }
        task = asyncio.create_task(process_audio())
        background_tasks[filename] = task
        
        return {"filename": filename, "status": "processing", "info": task_results[filename]["info"]}
    except Exception as e:
        print(f"Upload error: {str(e)}")
        print(traceback.format_exc())
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)