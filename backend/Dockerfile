# ============================================================================
# Multi-stage Dockerfile for Backend
# ============================================================================

# Stage 1: Base image with system dependencies
FROM python:3.12-slim AS base
WORKDIR /app

# Install only essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set pip configuration for faster installs
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300


# ============================================================================
# Stage 2: Backend Image Builder
# ============================================================================
FROM base AS backend-builder

# Copy requirements first for better caching
COPY requirements.txt ./

# Install CPU-only PyTorch first (smaller than GPU version)
# Using latest stable CPU version (2.1.0 not available, using 2.2.0+cpu)
RUN pip install --no-cache-dir torch==2.2.0+cpu --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# ============================================================================
# Stage 3: Backend Runtime 
# ============================================================================
FROM base AS backend-image

# Copy installed packages from builder
COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin


# Copy application code (excluding .dockerignore patterns)
COPY celery_app.py ./
COPY app/ ./app/



# Clean up any Python cache files that might have been copied
RUN find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true && \
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Create non-root user for Celery worker (security best practice)
# Use -m to create home directory and ensure user is in system files
RUN groupadd -r -g 1000 celeryuser && \
    useradd -r -m -u 1000 -g celeryuser -d /home/celeryuser celeryuser

# Create log directory (will be mounted as volume in docker-compose)
RUN mkdir -p /var/log/app && chmod 755 /var/log/app && \
    chown -R celeryuser:celeryuser /var/log/app

# Set ownership of app directory
RUN chown -R celeryuser:celeryuser /app

# Copy HuggingFace models to user's home directory (accessible by user 1000)
COPY huggingface/ /home/celeryuser/.cache/huggingface/
RUN chown -R celeryuser:celeryuser /home/celeryuser/.cache

# Set Python path and HuggingFace offline mode
ENV PYTHONPATH=/app \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HOME=/home/celeryuser/.cache/huggingface \
    HF_HUB_CACHE=/home/celeryuser/.cache/huggingface/hub

# Default command: Run FastAPI with uvicorn (production mode)
# Use multiple workers for production (set UVICORN_WORKERS env var to override)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers ${UVICORN_WORKERS:-4} --log-level info --access-log"]

# ============================================================================
# Stage 4: Flower (Monitoring UI)
# ============================================================================
FROM base AS flower-image

# Install only Flower dependencies
RUN pip install --no-cache-dir \
    celery==5.3.4 \
    redis==5.0.1 \
    flower==2.0.1

# Command to run Flower
CMD ["celery", "flower"]
