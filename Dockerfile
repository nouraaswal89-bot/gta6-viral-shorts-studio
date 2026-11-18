# ==============================================================================
# GTA6 Viral Shorts Studio - Unified Single-Container Dockerfile (Railway Ready)
# Optimized for Railway $5 Free Trial: single service, fast builds, low RAM
# ==============================================================================

# Stage 1: Build static Next.js 15 + Remotion 4 Player UI
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
# Empty NEXT_PUBLIC_BACKEND_URL -> uses same-origin Railway HTTPS domain automatically
ENV NEXT_PUBLIC_BACKEND_URL=""
RUN npm run build

# Stage 2: Lightweight Python 3.11 + FFmpeg + Node (for yt-dlp JS runtime)
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WHISPER_MODEL_SIZE=tiny \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE_TYPE=int8 \
    ENABLE_REMOTION_RENDER=false \
    LIVE_BUFFER_SECONDS=90 \
    PORT=8000

# Install FFmpeg, Node.js (for yt-dlp --js-runtimes node), and OpenCV/audio libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r /app/backend/requirements.txt

# Copy backend code & assets
COPY backend/ /app/backend/

# Copy static Next.js build into /app/frontend/out so FastAPI serves UI + API on one URL
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

WORKDIR /app/backend
EXPOSE 8000

# Bind Railway's dynamic $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
