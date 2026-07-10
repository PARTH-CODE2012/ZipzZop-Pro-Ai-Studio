"""FastAPI backend for ZipZop Pro AI Editor.

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .video_processor import VideoProcessingError, trim_silence_from_video

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
OUTPUT_DIR = BASE_DIR / "storage" / "outputs"
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://zipzop-pro-ai-studio.vercel.app",
    "https://zipzzop-pro-ai-studio.vercel.app",
]

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("zipzop.backend")


def _split_env_list(name: str, default: list[str]) -> list[str]:
    raw_value = os.getenv(name, "")
    values = [value.strip().rstrip("/") for value in raw_value.split(",") if value.strip()]
    return values or default


def _cloudinary_is_configured() -> bool:
    return all(
        os.getenv(key)
        for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
    )


def _upload_to_cloudinary(output_path: Path, job_id: str) -> dict[str, Any] | None:
    """Upload processed videos to Cloudinary when credentials are configured."""
    if not _cloudinary_is_configured():
        logger.info("Cloudinary credentials not configured; using local output for job_id=%s", job_id)
        return None

    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    logger.info("Uploading processed video to Cloudinary for job_id=%s", job_id)
    return cloudinary.uploader.upload_large(
        str(output_path),
        resource_type="video",
        folder=os.getenv("CLOUDINARY_FOLDER", "zipzop-pro/processed"),
        public_id=job_id,
        overwrite=True,
    )


app = FastAPI(
    title="ZipZop Pro AI Editor API",
    description="Open-source SaaS-ready gaming video editor API using FastAPI, MoviePy, and Cloudinary.",
    version="0.2.0",
)

allowed_origins = _split_env_list("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=os.getenv("ALLOWED_ORIGIN_REGEX") or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS allowed origins: %s", allowed_origins)


@app.get("/health")
def health() -> dict[str, Any]:
    """Return a lightweight health check for Render/Vercel deployment probes."""
    return {
        "status": "ok",
        "cloudinaryConfigured": _cloudinary_is_configured(),
        "allowedOrigins": allowed_origins,
    }


@app.post("/api/videos/process")
async def process_video(file: UploadFile = File(...)) -> JSONResponse:
    """Upload a gaming clip, remove silent sections, upload to Cloudinary, and return a URL."""
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
        cloudinary_result = _upload_to_cloudinary(output_path, job_id)
        cloudinary_url = cloudinary_result.get("secure_url") if cloudinary_result else None
        download_url = cloudinary_url or f"/api/videos/download/{job_id}"
        logger.info("Finished processing job_id=%s download_url=%s", job_id, download_url)

        return JSONResponse(
            {
                "jobId": job_id,
                "downloadUrl": download_url,
                "cloudinaryUrl": cloudinary_url,
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
    """Download a processed local video by job id when Cloudinary is not configured."""
    if not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job id.")

    output_path = OUTPUT_DIR / f"{job_id}_zipzop.mp4"
    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed video not found locally. If you use Cloudinary, use the cloudinaryUrl returned by /api/videos/process.",
        )

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename="zipzop-pro-edited.mp4",
    )
