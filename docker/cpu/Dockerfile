# IREE CPU Compiler Docker Image
# Base on Ubuntu for CPU-only IREE compilation
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV IREE_VERSION=20241220.123

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    cmake \
    ninja-build \
    git \
    wget \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install IREE toolchain
RUN pip3 install --upgrade pip && \
    pip3 install iree-compiler iree-runtime

# Create working directories
RUN mkdir -p /usr/local/bin/iree-scripts
RUN mkdir -p /input /output /config

# Copy compilation scripts (will be added in later tasks)
COPY scripts/ /usr/local/bin/iree-scripts/

# Set up volumes
VOLUME ["/input", "/output", "/config"]

# Set working directory
WORKDIR /workspace

# Default entry point (will be implemented in later tasks)
ENTRYPOINT ["/usr/local/bin/iree-scripts/compile.sh"]