# ==============================================================================
# GTA6 Viral Shorts Studio - Unified Single-Container Dockerfile (Railway Ready)
# Optimized for Railway $5 Free Trial: fast build, low RAM, bold fonts for FFmpeg
# ==============================================================================

# Stage 1: Build static Next.js 15 + Remotion 4 Player UI
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
ENV NEXT_PUBLIC_BACKEND_URL=""
RUN npm run build

# Stage 2: Lean Python 3.11 + FFmpeg + Fonts + Node (for yt-dlp JS runtime)
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WHISPER_MODEL_SIZE=tiny \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE_TYPE=int8 \
    OUTPUT_FPS=30 \
    ENABLE_REMOTION_RENDER=false \
    LIVE_BUFFER_SECONDS=90 \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    fonts-dejavu-core \
    fontconfig \
    libsndfile1 \
    libglib2.0-0 \
    curl \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --prefer-binary -r /app/backend/requirements.txt && \
    python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"

COPY backend/ /app/backend/
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

WORKDIR /app/backend
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
