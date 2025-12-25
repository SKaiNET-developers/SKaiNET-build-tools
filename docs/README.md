# IREE Docker Integration

A standalone Docker-based IREE compilation service that takes StableHLO MLIR as input and produces optimized backend-specific executables.

## Overview

This project provides Docker containers with the complete IREE toolchain for compiling StableHLO MLIR to executable bytecode across multiple hardware targets including CPU, CUDA, Vulkan, and Metal.

## Quick Start

*Documentation will be expanded in later implementation tasks*

### Prerequisites

- Docker Engine 20.10+
- NVIDIA Docker runtime (for CUDA support)
- Docker Compose (optional)

### Basic Usage

```bash
# Build IREE compiler images
make build-all

# Compile StableHLO MLIR (implementation pending)
./cli/iree-docker-compile --input model.mlir --target cuda --output model.vmfb
```

## Architecture

The system consists of:

- **Docker Images**: Pre-built containers with IREE toolchain
- **Compilation Scripts**: Entry points for IREE compilation
- **CLI Tools**: User-friendly command-line interface
- **Build Integration**: Gradle tasks for build system integration

## Directory Structure

```
.
├── docker/                 # Docker image definitions
│   ├── cuda/              # CUDA-enabled IREE compiler
│   └── cpu/               # CPU-only IREE compiler
├── cli/                   # Command-line tools
├── scripts/               # Build and development scripts
├── docs/                  # Documentation
└── examples/              # Usage examples (to be added)
```

## Documentation

- [Setup Guide](setup.md) *(coming soon)*
- [Usage Examples](examples.md) *(coming soon)*
- [API Reference](api.md) *(coming soon)*
- [Troubleshooting](troubleshooting.md) *(coming soon)*

## Contributing

*Contributing guidelines will be added in later tasks*

## License

See [LICENSE](../LICENSE) file for details.