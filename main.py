import subprocess
import shutil
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

# Load the hidden environment variables
load_dotenv()

app = FastAPI()

# Authorize your frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pull credentials securely from the .env file
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

Path("uploads").mkdir(exist_ok=True)
Path("hls").mkdir(exist_ok=True)

def process_and_ship(video_id: str, file_path: Path, output_dir: Path):
    try:
        print(f"--- STARTING: Manufacturing {video_id} ---")
        output_dir.mkdir(exist_ok=True)
        m3u8_file = output_dir / "playlist.m3u8"
        
        # 1. Manufacturing (FFmpeg)
        subprocess.run([
            "ffmpeg", "-i", str(file_path), "-profile:v", "baseline", "-level", "3.0",
            "-start_number", "0", "-hls_time", "4", "-hls_list_size", "0", 
            "-f", "hls", "-hls_playlist_type", "vod", str(m3u8_file)
        ], check=True) 
        
        print(f"--- MANUFACTURING COMPLETE: Shipping to Cloud ---")
        
        # 2. Outbound Logistics
        for item in output_dir.iterdir():
            if item.is_file():
                content_type = "application/x-mpegURL" if item.suffix == '.m3u8' else "video/mp2t"
                
                with open(item, "rb") as f:
                    supabase.storage.from_("videos").upload(
                        path=f"hls/{video_id}/{item.name}",
                        file=f.read(),
                        file_options={"content-type": content_type, "upsert": "true"}
                    )
                print(f"Shipped: {item.name}")
                
        print(f"--- SUCCESS: All files in Supabase ---")
        
    except Exception as e:
        print(f"!!! SYSTEM FAILURE: {e} !!!")

@app.post("/upload/")
async def upload_video(file: UploadFile, background_tasks: BackgroundTasks):
    video_id = file.filename.split(".")[0]
    file_location = Path(f"uploads/{file.filename}")
    output_dir = Path(f"hls/{video_id}")
    
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    background_tasks.add_task(process_and_ship, video_id, file_location, output_dir)
    
    # We now send the video_id back to the frontend so it knows what to load
    return {
        "message": "Production started. Chunks will be shipped to Supabase shortly.",
        "video_id": video_id
    }