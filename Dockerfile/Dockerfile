FROM python:3.9.23-trixie

ENV DEBIAN_FRONTEND=noninteractive
ENV MOD_DEV_ENVIRONMENT=0

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \ 
        cmake \


RUN apt-get update && \
    apt install -y --no-install-recommends \
        libreadline-dev \
        liblilv-dev \
        lilv-utils \
        libfftw3-dev \
        libjack-jackd2-dev


WORKDIR /mod
RUN https://github.com/mod-audio/mod-host mod-host
WORKDIR /mod/mod-host
RUN make
RUN make install


# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        virtualenv \
        python3-pip \
        python3-dev \
        libasound2-dev \
        jackd2 \
        libjack-jackd2-dev \
        liblilv-dev \
        libjpeg-dev \
        zlib1g-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Clone mod-ui repository
RUN git clone https://github.com/moddevices/mod-ui /mod-ui

# Set working directory
WORKDIR /mod-ui

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Compile libmod_utils
RUN make -C utils

# Define default command to run the server
CMD ["python3", "./server.py"]
