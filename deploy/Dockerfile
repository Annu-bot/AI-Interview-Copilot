# Use lightweight official Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENV_MODE=deploy

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and configurations
COPY config/ /app/config/
COPY ai_apps/ /app/ai_apps/
COPY templates/ /app/templates/
COPY static/ /app/static/
COPY runserver.py /app/runserver.py

# Expose port
EXPOSE 8000

# Run FastAPI app via uvicorn
CMD ["python", "runserver.py"]
