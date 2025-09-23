# Dockerfile for Standalone System Stats Service
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements-system-stats.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-system-stats.txt

# Copy source code
COPY src/ ./src/

# Set Python path to include the app directory
ENV PYTHONPATH=/app/src:/app

# Create a non-root user with access to system files
RUN groupadd -r modstats && useradd -r -g modstats modstats

# The container will run with privileged access to read system stats
# This is necessary for reading /proc, /sys files

# Set the command to run the service
WORKDIR /app/src
CMD ["python", "-m", "mod_ui.services.system_stats.main"]