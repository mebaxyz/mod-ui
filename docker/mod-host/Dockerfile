# Build and run mod-host in a container
# Usage: docker build -f docker/mod-host/Dockerfile -t mod-host:local .
# Then run with: docker run --rm -it --device /dev/snd -p 5555:5555 -p 5556:5556 mod-host:local

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install build and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    pkg-config \
    automake \
    autoconf \
    libtool \
    libjack-jackd2-dev \
    libjack-jackd2-0 \
    liblilv-dev \
    lilv-utils \
    libreadline-dev \
    libfftw3-dev \
    libsndfile1-dev \
    jackd2 \
    python3 \
    python3-dev \
    python3-setuptools \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# Copy mod-host sources from the repository into the image
# This expects you to build the image from the repository root so the
# path src/mod_ui/services/mod-host exists in the build context.
COPY src/mod_ui/services/mod-host /src/mod-host

WORKDIR /src/mod-host

# Build
RUN make -j"$(nproc)"

# Expose TCP ports used by mod-host control and feedback sockets
EXPOSE 5555 5556

# Copy entrypoint and make executable
COPY docker/mod-host/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Default entrypoint starts a dummy JACK server and then runs mod-host
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
