FROM python:3.10-slim

# Install system dependencies for building the C++ library
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libjack-jackd2-dev \
    liblilv-dev \
    libalsa-ocaml-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/mod-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mod/ ./mod/
COPY modtools/ ./modtools/

# Copy and build the C++ utilities
COPY utils/ ./utils/
RUN cd utils && make

# Copy the built library to modtools directory
RUN cp utils/libmod_utils.so modtools/

COPY services/mod-api/main.py .

# Set library path for the compiled library
ENV LD_LIBRARY_PATH=/app/utils:$LD_LIBRARY_PATH

EXPOSE 8888

CMD ["python", "main.py"]