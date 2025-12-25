# IREE Docker Integration - Project Structure

This document outlines the project structure created for the Docker-based IREE compilation service.

## Directory Structure

```
.
├── cli/                           # Command-line tools
│   └── iree-docker-compile       # Main CLI tool (implementation pending)
├── config/                       # Configuration files
│   └── example-config.json       # Example compilation configuration
├── docker/                       # Docker image definitions
│   ├── cuda/                     # CUDA-enabled IREE compiler
│   │   ├── Dockerfile            # CUDA Docker image definition
│   │   └── scripts/              # CUDA-specific compilation scripts
│   └── cpu/                      # CPU-only IREE compiler
│       ├── Dockerfile            # CPU Docker image definition
│       └── scripts/              # CPU-specific compilation scripts
├── docs/                         # Documentation
│   ├── README.md                 # Main documentation
│   ├── setup.md                  # Setup guide
│   ├── examples.md               # Usage examples
│   ├── troubleshooting.md        # Troubleshooting guide
│   └── api.md                    # API reference
├── examples/                     # Usage examples (to be populated)
├── input/                        # Input directory for StableHLO MLIR files
├── output/                       # Output directory for compiled modules
├── scripts/                      # Build and development scripts
│   ├── build-images.sh           # Docker image build script
│   └── local-dev.sh              # Local development helper
├── .dockerignore                 # Docker build context exclusions
├── docker-compose.yml            # Docker Compose configuration
├── iree-config.yml               # Project configuration
├── Makefile                      # Build automation
└── PROJECT_STRUCTURE.md          # This file
```

## Configuration Files

- **docker-compose.yml**: Orchestrates CUDA and CPU IREE compiler services
- **iree-config.yml**: Central project configuration
- **Makefile**: Provides convenient build commands
- **.dockerignore**: Excludes unnecessary files from Docker build context

## Docker Images

### CUDA Image (`docker/cuda/`)
- Based on `nvidia/cuda:12.3-devel-ubuntu22.04`
- Includes IREE toolchain with CUDA support
- Optimized for NVIDIA GPU compilation

### CPU Image (`docker/cpu/`)
- Based on `ubuntu:22.04`
- CPU-only IREE compilation
- Lighter weight for CPU-only workloads

## Implementation Status

This structure represents the foundation created in Task 1. Key components are:

✅ **Completed**:
- Directory structure
- Base Docker image definitions
- Configuration files
- Documentation structure
- Build automation (Makefile)

🔄 **Pending** (later tasks):
- Compilation scripts implementation
- CLI tool functionality
- Validation and benchmarking
- Integration testing
- Complete documentation

## Next Steps

The next tasks will implement:
1. CUDA Docker image with compilation scripts
2. Validation and benchmarking capabilities
3. Service interface and configuration system
4. CLI wrapper and orchestration tools
5. Build system integration

## Requirements Addressed

This structure addresses the following requirements:
- **1.1**: Docker-based IREE compilation foundation
- **2.1**: Docker container support structure
- **7.3**: Modular integration architecture

The foundation is now ready for implementing the actual compilation functionality in subsequent tasks.