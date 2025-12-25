# IREE Docker Integration CLI Usage Guide

This document provides comprehensive usage instructions for the IREE Docker Integration CLI tools and wrapper scripts.

## Overview

The IREE Docker Integration provides multiple ways to interact with the compilation system:

1. **Python CLI** (`iree-docker-compile`) - Full-featured command-line interface
2. **Shell Wrappers** - Easy-to-use scripts for common workflows
3. **Development Helpers** - Scripts for setup and development

## Quick Start

### 1. Set up the environment

```bash
# Set up Python environment and dependencies
./scripts/local-dev.sh setup

# Check Docker status
./scripts/docker-status.sh status
```

### 2. Generate example configuration

```bash
# Generate CUDA configuration
./scripts/manage-config.sh generate cuda cuda-config.json

# Generate CPU configuration  
./scripts/manage-config.sh generate cpu cpu-config.json
```

### 3. Compile a model

```bash
# Simple compilation
./scripts/compile-with-iree.sh model.mlir model.vmfb

# With specific target and features
./scripts/compile-with-iree.sh -t cuda --features sm_80,sm_86 model.mlir model.vmfb

# Using configuration file
./scripts/compile-with-iree.sh -c cuda-config.json model.mlir model.vmfb
```

## Python CLI Reference

The main CLI tool is `iree-docker-compile` with several subcommands:

### Compilation

```bash
# Basic compilation
uv run iree-docker-compile compile --input model.mlir --output model.vmfb

# With options
uv run iree-docker-compile compile \
    --input model.mlir \
    --output model.vmfb \
    --target cuda \
    --optimization O3 \
    --target-features sm_80 \
    --target-features sm_86 \
    --benchmark \
    --verbose

# Using configuration file
uv run iree-docker-compile compile --config config.json

# Dry run (show what would be executed)
uv run iree-docker-compile compile --input model.mlir --output model.vmfb --dry-run
```

### Configuration Management

```bash
# Generate example configuration
uv run iree-docker-compile generate-config --target cuda --output cuda-config.json

# Validate configuration
uv run iree-docker-compile validate-config --config config.json

# Normalize configuration
uv run iree-docker-compile validate-config --config config.json --normalize --output normalized.json
```

### System Status

```bash
# Show overall status
uv run iree-docker-compile status

# Show status for specific target
uv run iree-docker-compile status --target cuda
```

## Shell Wrapper Scripts

### Local Development Helper (`scripts/local-dev.sh`)

```bash
# Set up development environment
./scripts/local-dev.sh setup

# Run compilation test
./scripts/local-dev.sh test

# Check Docker status
./scripts/local-dev.sh status

# Generate example configurations
./scripts/local-dev.sh examples

# Show help
./scripts/local-dev.sh help
```

### Compilation Wrapper (`scripts/compile-with-iree.sh`)

```bash
# Basic usage
./scripts/compile-with-iree.sh [options] <input.mlir> <output.vmfb>

# Options:
#   -t, --target TARGET        Compilation target (cuda, cpu, vulkan, metal)
#   -O, --optimization LEVEL   Optimization level (O0, O1, O2, O3)
#   -f, --format FORMAT        Output format (vmfb, so, dylib)
#   --features FEATURES        Target-specific features (comma-separated)
#   --no-validate              Disable output validation
#   --benchmark                Enable performance benchmarking
#   -v, --verbose              Enable verbose output
#   -n, --dry-run              Show what would be done without executing
#   -c, --config FILE          Use configuration file
#   -h, --help                 Show help message

# Examples:
./scripts/compile-with-iree.sh model.mlir model.vmfb
./scripts/compile-with-iree.sh -t cpu -O O2 model.mlir model.vmfb
./scripts/compile-with-iree.sh --features sm_80,sm_86 model.mlir model.vmfb
./scripts/compile-with-iree.sh --benchmark -v model.mlir model.vmfb
./scripts/compile-with-iree.sh -c config.json model.mlir model.vmfb
./scripts/compile-with-iree.sh --dry-run model.mlir model.vmfb
```

### Configuration Management (`scripts/manage-config.sh`)

```bash
# Validate configuration
./scripts/manage-config.sh validate config.json

# Normalize configuration
./scripts/manage-config.sh normalize config.json normalized.json

# Generate example configuration
./scripts/manage-config.sh generate cuda cuda-config.json
./scripts/manage-config.sh generate cpu  # Output to stdout
```

### Docker Management (`scripts/docker-status.sh`)

```bash
# Show status for all targets
./scripts/docker-status.sh status

# Show status for specific target
./scripts/docker-status.sh status cuda

# Build Docker images
./scripts/docker-status.sh build cuda
./scripts/docker-status.sh build all

# Pull Docker images
./scripts/docker-status.sh pull cuda
./scripts/docker-status.sh pull all

# Clean Docker images
./scripts/docker-status.sh clean cuda
./scripts/docker-status.sh clean all
```

### Build Images (`scripts/build-images.sh`)

```bash
# Build all Docker images
./scripts/build-images.sh

# Build specific target
./scripts/build-images.sh cuda
```

## Configuration File Format

Configuration files use JSON format with the following structure:

```json
{
  "input_file": "/input/model.mlir",
  "output_file": "/output/model.vmfb",
  "target": "cuda",
  "optimization_level": "O3",
  "target_features": ["sm_80", "sm_86"],
  "output_format": "vmfb",
  "validation": true,
  "benchmark": false,
  "verbose": false,
  "target_specific": {
    "cuda": {
      "compute_capability": ["sm_80", "sm_86"],
      "max_threads_per_block": 256,
      "use_fast_math": false
    }
  },
  "metadata": {
    "description": "Example CUDA compilation configuration",
    "version": "1.0"
  }
}
```

## Target-Specific Features

### CUDA
- Features: `sm_70`, `sm_75`, `sm_80`, `sm_86`, `sm_89`, `sm_90`
- Example: `--target-features sm_80 --target-features sm_86`

### CPU
- Features: `avx`, `avx2`, `avx512`, `sse4.1`, `sse4.2`, `neon`
- Example: `--target-features avx2 --target-features fma`

### Vulkan
- Features: `spirv1.3`, `spirv1.4`, `spirv1.5`, `spirv1.6`
- Example: `--target-features spirv1.3`

### Metal
- Features: `metal2.4`, `metal3.0`
- Example: `--target-features metal2.4`

## Environment Setup

### Using uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up project environment
uv venv .venv
uv pip install -e .

# Run CLI
uv run iree-docker-compile --help
```

### Using pip

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Run CLI
python -m iree_docker_integration.cli --help
```

## Troubleshooting

### Docker Issues

```bash
# Check Docker status
./scripts/docker-status.sh status

# Build images if missing
./scripts/build-images.sh

# Check Docker daemon
docker info
```

### Python Environment Issues

```bash
# Reset environment
rm -rf .venv
./scripts/local-dev.sh setup

# Check dependencies
uv run python -c "import docker, jsonschema, click, rich; print('All dependencies available')"
```

### Compilation Issues

```bash
# Use verbose mode
./scripts/compile-with-iree.sh -v model.mlir model.vmfb

# Use dry-run to check configuration
./scripts/compile-with-iree.sh --dry-run model.mlir model.vmfb

# Validate configuration
./scripts/manage-config.sh validate config.json
```

## Integration with Build Systems

### Makefile Integration

```makefile
# Add to your Makefile
compile-model:
	./scripts/compile-with-iree.sh model.mlir model.vmfb

compile-cuda:
	./scripts/compile-with-iree.sh -t cuda --features sm_80 model.mlir model.vmfb

compile-cpu:
	./scripts/compile-with-iree.sh -t cpu --features avx2 model.mlir model.vmfb
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Set up IREE environment
  run: ./scripts/local-dev.sh setup

- name: Build Docker images
  run: ./scripts/build-images.sh

- name: Compile model
  run: ./scripts/compile-with-iree.sh model.mlir model.vmfb
```

## Advanced Usage

### Custom Docker Images

```bash
# Build custom image
docker build -t my-iree-compiler:cuda docker/cuda/

# Use custom image (modify docker_manager.py)
# Or set environment variable
export IREE_CUDA_IMAGE=my-iree-compiler:cuda
```

### Batch Processing

```bash
# Process multiple files
for file in *.mlir; do
    ./scripts/compile-with-iree.sh "$file" "${file%.mlir}.vmfb"
done
```

### Performance Monitoring

```bash
# Enable benchmarking
./scripts/compile-with-iree.sh --benchmark -v model.mlir model.vmfb

# Monitor Docker resource usage
docker stats
```

This CLI system provides a comprehensive, user-friendly interface for IREE Docker compilation with both simple wrapper scripts and full-featured Python CLI tools.