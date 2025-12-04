# Backend Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
# ffmpeg: for audio processing
# git: for cloning model repos
# build-essential: for compiling python extensions
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Pre-download ViSoBERT-HSD tokenizer files for faster startup
# The ONNX model files are mounted via volume
RUN python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('visolex/visobert-hsd')" || true

# Expose port
EXPOSE 8000

# Environment variables for content moderation
ENV ENABLE_CONTENT_MODERATION=true
ENV MODERATION_CONFIDENCE_THRESHOLD=0.7
ENV MODERATION_ON_FINAL_ONLY=true

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
