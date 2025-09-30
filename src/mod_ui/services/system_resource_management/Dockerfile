FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY src/mod_ui/services/system_resource_management/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy common modules
COPY src/mod_ui/common ./src/mod_ui/common/

# Copy service code
COPY src/mod_ui/services/system_resource_management ./src/mod_ui/services/system_resource_management/

# Create necessary directories
RUN mkdir -p /app/data

# Expose port
EXPOSE 8081

# Set Python path
ENV PYTHONPATH=/app

# Run the service
CMD ["python", "-m", "src.mod_ui.services.system_resource_management.main"]