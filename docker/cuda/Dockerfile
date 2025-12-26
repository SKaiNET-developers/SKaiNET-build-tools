# CUDA-enabled IREE Compiler Docker Image
# Base on nvidia/cuda:12.4.1-devel-ubuntu22.04 (verified available image)
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV IREE_VERSION=20241220.123
ENV CUDA_VERSION=12.4.1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    cmake \
    ninja-build \
    git \
    wget \
    curl \
    jq \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Upgrade pip and install Python dependencies
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install IREE toolchain components
# Install iree-compile, iree-run-module, and iree-benchmark-module
RUN python3 -m pip install \
    iree-compiler \
    iree-runtime \
    iree-tools-tf \
    iree-tools-tflite \
    numpy

# Verify IREE installation
RUN iree-compile --version && \
    iree-run-module --help && \
    iree-benchmark-module --help

# Create directories for volumes
RUN mkdir -p /input /output /config /scripts

# Copy compilation scripts (will be created in next subtask)
COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

# Set working directory
WORKDIR /workspace

# Create volume mount points
VOLUME ["/input", "/output", "/config"]

# Set default entry point to compilation script
ENTRYPOINT ["/scripts/compile.sh"]