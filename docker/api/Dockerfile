# FastAPI API Service DockerfileFROM python:3.10-slim



FROM python:3.11-slim# Install system dependencies for building the C++ library

RUN apt-get update && apt-get install -y \

# Install system dependencies    build-essential \

RUN apt-get update && apt-get install -y \    pkg-config \

    build-essential \    libjack-jackd2-dev \

    libjack-jackd2-dev \    liblilv-dev \

    liblilv-dev \    libalsa-ocaml-dev \

    libserd-dev \    && rm -rf /var/lib/apt/lists/*

    libsord-dev \

    libsratom-dev \WORKDIR /app

    lv2-dev \

    pkg-config \COPY services/mod-api/requirements.txt .

    && rm -rf /var/lib/apt/lists/*RUN pip install --no-cache-dir -r requirements.txt



# Set working directoryCOPY mod/ ./mod/

WORKDIR /appCOPY modtools/ ./modtools/



# Copy requirements first for better caching# Copy and build the C++ utilities

COPY requirements.txt .COPY utils/ ./utils/

RUN cd utils && make

# Install Python dependencies

RUN pip install --no-cache-dir -r requirements.txt# Copy the built library to modtools directory

RUN cp utils/libmod_utils.so modtools/

# Copy source code

COPY src/ src/COPY services/mod-api/main.py .

COPY mod/ mod/

COPY modtools/ modtools/# Set library path for the compiled library

COPY utils/ utils/ENV LD_LIBRARY_PATH=/app/utils:$LD_LIBRARY_PATH

COPY html/ html/

COPY default.pedalboard/ default.pedalboard/EXPOSE 8888



# Build C++ utilitiesCMD ["python", "main.py"]
RUN make -C utils

# Create data directory
RUN mkdir -p /data

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/ping || exit 1

# Run the FastAPI application
CMD ["python", "-m", "uvicorn", "src.mod_ui.services.api.main:app", "--host", "0.0.0.0", "--port", "8888"]