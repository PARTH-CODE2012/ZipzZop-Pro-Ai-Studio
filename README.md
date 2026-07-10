# ZipzZop-Pro-Ai-Studio
# ZipZop Pro AI Editor

A SaaS-ready, open-source AI gaming video editor starter built with FastAPI, MoviePy, React, Vite, and Tailwind CSS.

## What it does

1. Upload a gameplay video from the React dashboard.
2. Send it to the FastAPI backend.
3. Detect non-silent segments across the full real clip duration.
4. Export an MP4 without hardcoded duration limits.
5. Download the processed result.

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` if your backend is not running on `http://localhost:8000`.

## SaaS path

This repo is structured so you can add accounts, billing, job queues, cloud object storage, and subscription limits later without changing the core upload-process-download workflow.
