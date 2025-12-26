# IREE Docker Integration

Docker-based IREE compilation service that compiles StableHLO MLIR to optimized executable bytecode for multiple hardware targets including CUDA, CPU, Vulkan, and Metal.

## Quick Start - CUDA Compilation

### Prerequisites

1. **Docker**: Ensure Docker is installed and running
   ```bash
   docker --version
   docker info
   ```

2. **Python Environment**: Install uv for Python environment management
   ```bash
   # Install uv (if not already installed)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Set up the project environment
   uv sync
   ```

### Step 1: Build the CUDA Docker Image

```bash
# Build the CUDA-enabled IREE compiler image
docker build -t iree-compiler:cuda-latest docker/cuda/
```

This creates a Docker image with:
- NVIDIA CUDA 12.4.1 runtime
- Complete IREE toolchain (iree-compile, iree-run-module, iree-benchmark-module)
- Compilation, validation, and benchmarking scripts

### Step 2: Prepare Your MLIR Model

Create or use an existing StableHLO MLIR file. Example:

```mlir
// input/my_model.mlir
module {
  func.func @main() -> tensor<4xf32> {
    %0 = stablehlo.constant dense<[1.0, 2.0, 3.0, 4.0]> : tensor<4xf32>
    %1 = stablehlo.multiply %0, %0 : tensor<4xf32>
    return %1 : tensor<4xf32>
  }
}
```

### Step 3: Compile to CUDA Executable

#### Option A: Using the CLI Tool (Recommended)

```bash
# Compile MLIR to CUDA executable
uv run iree-docker-compile compile \
  --input input/my_model.mlir \
  --target cuda \
  --output output/my_model.vmfb \
  --arch sm_80 \
  --validate \
  --benchmark
```

#### Option B: Using Configuration File

```bash
# Generate a configuration template
uv run iree-docker-compile generate-config \
  --target cuda \
  --output cuda-config.json

# Edit the configuration as needed, then compile
uv run iree-docker-compile compile --config cuda-config.json
```

### Step 4: Run Your Compiled Model

The compilation produces a `.vmfb` (Virtual Machine FlatBuffer) file that can be executed with the IREE runtime:

```bash
# Run the compiled model (inside Docker container)
docker run --gpus all \
  -v $(pwd)/output:/output \
  iree-compiler:cuda-latest \
  iree-run-module \
  --device=cuda \
  --module=/output/my_model.vmfb \
  --function=main
```

## Complete Example Workflow

Here's a complete example of compiling and running a CUDA application:

```bash
# 1. Set up environment
uv sync

# 2. Build Docker image
docker build -t iree-compiler:cuda-latest docker/cuda/

# 3. Create a simple MLIR model
cat > input/example.mlir << 'EOF'
module {
  func.func @main(%arg0: tensor<1024x1024xf32>) -> tensor<1024x1024xf32> {
    %0 = stablehlo.multiply %arg0, %arg0 : tensor<1024x1024xf32>
    return %0 : tensor<1024x1024xf32>
  }
}
EOF

# 4. Compile to CUDA
uv run iree-docker-compile compile \
  --input input/example.mlir \
  --target cuda \
  --output output/example.vmfb \
  --arch sm_80 \
  --optimize O3 \
  --validate \
  --benchmark

# 5. Check compilation results
ls -la output/
cat output/compilation_result.json
```

## Configuration Options

### CUDA-Specific Options

```json
{
  "input_file": "/input/model.mlir",
  "target": "cuda",
  "optimization_level": "O3",
  "target_features": ["sm_80", "sm_86"],
  "output_format": "vmfb",
  "validation": true,
  "benchmark": true,
  "target_specific": {
    "cuda": {
      "compute_capability": ["sm_80", "sm_86"],
      "max_threads_per_block": 256,
      "use_fast_math": false
    }
  }
}
```

### Supported CUDA Architectures

- `sm_70`: Tesla V100, Titan V
- `sm_75`: RTX 20 series, Tesla T4
- `sm_80`: A100, RTX 30 series
- `sm_86`: RTX 30 series (consumer)
- `sm_89`: RTX 40 series
- `sm_90`: H100

## CLI Commands

### Compilation
```bash
# Basic compilation
uv run iree-docker-compile compile --input input/model.mlir --target cuda

# Advanced compilation with options
uv run iree-docker-compile compile \
  --input input/model.mlir \
  --target cuda \
  --output output/model.vmfb \
  --arch sm_80 \
  --optimize O3 \
  --validate \
  --benchmark \
  --verbose
```

### Configuration Management
```bash
# Generate example config
uv run iree-docker-compile generate-config --target cuda --output config.json

# Validate configuration
uv run iree-docker-compile validate-config --config config.json

# Check system status
uv run iree-docker-compile status
```

## Multi-Target Support

The system supports multiple compilation targets:

```bash
# CPU compilation
uv run iree-docker-compile compile --input input/model.mlir --target cpu

# Vulkan compilation (cross-platform GPU)
uv run iree-docker-compile compile --input input/model.mlir --target vulkan

# Metal compilation (Apple Silicon)
uv run iree-docker-compile compile --input input/model.mlir --target metal
```

## Performance Optimization

### CUDA Optimization Tips

1. **Choose the right architecture**: Use `--arch` matching your GPU
2. **Enable optimizations**: Use `--optimize O3` for maximum performance
3. **Tune thread blocks**: Adjust `max_threads_per_block` in config
4. **Enable fast math**: Set `use_fast_math: true` for approximate math operations

### Benchmarking

```bash
# Enable benchmarking during compilation
uv run iree-docker-compile compile \
  --input input/model.mlir \
  --target cuda \
  --benchmark

# Results will be in output/compilation_result.json
jq '.benchmark_results' output/compilation_result.json
```

## Troubleshooting

### Common Issues

1. **Docker not running**:
   ```bash
   # Start Docker daemon
   sudo systemctl start docker  # Linux
   # or start Docker Desktop on macOS/Windows
   ```

2. **NVIDIA Docker runtime not available**:
   ```bash
   # Install nvidia-docker2
   sudo apt-get install nvidia-docker2
   sudo systemctl restart docker
   ```

3. **Compilation errors**:
   ```bash
   # Check logs with verbose output
   uv run iree-docker-compile compile --input input/model.mlir --target cuda --verbose
   
   # Check compilation logs
   cat output/compilation.log
   ```

4. **GPU not detected**:
   ```bash
   # Test GPU access in Docker
   docker run --gpus all nvidia/cuda:12.3-runtime-ubuntu22.04 nvidia-smi
   ```

### Getting Help

```bash
# CLI help
uv run iree-docker-compile --help
uv run iree-docker-compile compile --help

# Check system status
uv run iree-docker-compile status

# Validate your configuration
uv run iree-docker-compile validate-config --config your-config.json
```

## Development and Testing

### Running Tests

```bash
# Run all tests
uv run python test_checkpoint.py

# Run basic integration tests
uv run python test_basic_integration.py

# Run compilation readiness tests
uv run python test_compilation_readiness.py
```

### Project Structure

```
├── docker/
│   └── cuda/
│       ├── Dockerfile              # CUDA Docker image
│       └── scripts/
│           ├── compile.sh          # Main compilation script
│           ├── validate.sh         # Output validation
│           └── benchmark.sh        # Performance testing
├── iree_docker_integration/
│   ├── cli.py                      # Command-line interface
│   ├── config_validator.py         # Configuration validation
│   ├── docker_manager.py           # Docker orchestration
│   └── file_handler.py             # Secure file handling
├── input/                          # Input MLIR files
├── output/                         # Compiled outputs
└── config/                         # Configuration templates
```

## License

This project is licensed under the terms specified in the LICENSE file.
