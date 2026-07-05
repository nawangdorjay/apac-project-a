# Use official lightweight Python image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed for libraries (e.g. Scipy/ReportLab)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from backend directory
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all backend code into the docker container
COPY backend/ .

# Run pre-loaded data generation to bake datasets into the container
RUN python generate_demo_data.py

# Cloud Run / Render expects the container to listen on the PORT env variable (default 8080)
EXPOSE 8080

# Start Uvicorn bound to 0.0.0.0 and port 8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
