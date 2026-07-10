"""FastAPI backend for ZipZop Pro AI Editor.

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .video_processor import VideoProcessingError, trim_silence_from_video

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
OUTPUT_DIR = BASE_DIR / "storage" / "outputs"
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("zipzop.backend")

app = FastAPI(
    title="ZipZop Pro AI Editor API",
    description="Open-source SaaS-ready gaming video editor API using FastAPI and MoviePy.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight health check for deployment probes."""
    return {"status": "ok"}


@app.post("/api/videos/process")
async def process_video(file: UploadFile = File(...)) -> JSONResponse:
    """Upload a gaming clip, remove silent sections, and return a download URL."""
    original_name = file.filename or "uploaded-video"
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Use one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
        )

    job_id = uuid.uuid4().hex
    input_path = UPLOAD_DIR / f"{job_id}{extension}"
    output_path = OUTPUT_DIR / f"{job_id}_zipzop.mp4"

    logger.info("Received video upload: filename=%s job_id=%s", original_name, job_id)

    try:
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = trim_silence_from_video(input_path=input_path, output_path=output_path)
        logger.info("Finished processing job_id=%s output=%s", job_id, output_path)

        return JSONResponse(
            {
                "jobId": job_id,
                "downloadUrl": f"/api/videos/download/{job_id}",
                "originalDuration": result.original_duration,
                "processedDuration": result.processed_duration,
                "removedSeconds": result.removed_seconds,
            }
        )
    except VideoProcessingError as exc:
        logger.exception("Video processing failed for job_id=%s: %s", job_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # log exact terminal error before returning safe response
        logger.exception("Unexpected backend failure for job_id=%s", job_id)
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {exc}") from exc
    finally:
        file.file.close()


@app.get("/api/videos/download/{job_id}")
def download_video(job_id: str) -> FileResponse:
    """Download a processed video by job id."""
    if not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job id.")

    output_path = OUTPUT_DIR / f"{job_id}_zipzop.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Processed video not found.")

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename="zipzop-pro-edited.mp4",
    )
