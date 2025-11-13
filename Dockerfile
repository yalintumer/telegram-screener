"""Production-ready Dockerfile for telegram-screener"""

FROM python:3.13-slim

# Install system dependencies (tesseract for OCR)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY config.example.yaml .
COPY pyproject.toml .

# Create necessary directories
RUN mkdir -p logs shots

# Environment variables (override these at runtime)
ENV TELEGRAM_BOT_TOKEN="" \
    TELEGRAM_CHAT_ID="" \
    LOG_LEVEL="INFO" \
    PYTHONUNBUFFERED=1

# Health check (checks if process is running)
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
    CMD python -m src.main list || exit 1

# Default command (override with docker run)
CMD ["python", "-m", "src.main", "run", "--interval", "3600"]
