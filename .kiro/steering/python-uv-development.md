---
inclusion: manual
---

# Python Development with uv - Steering Guide

## Overview

This project uses **uv** for Python environment management and dependency isolation. This approach provides fast, reliable Python environments while keeping Docker containers focused on IREE compilation.

## Architecture Pattern

```
Local Development:
  uv venv → Python validation/CLI → Docker compilation → Local result processing

Production:
  Same pattern but with CI/CD orchestration
```

## uv Setup and Usage

### Initial Environment Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project virtual environment
uv venv .venv

# Install dependencies from pyproject.toml
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"
```

### Project Structure for uv

```
project/
├── pyproject.toml          # Python dependencies and project config
├── .venv/                  # uv-managed virtual environment
├── scripts/
│   ├── validate-config.py  # Run with: uv run python scripts/validate-config.py
│   └── setup-env.py       # Environment setup utilities
├── cli/
│   └── iree-docker-compile # Main CLI tool
└── tests/
    └── test_*.py          # Run with: uv run pytest
```

### pyproject.toml Template

```toml
[project]
name = "iree-docker-integration"
version = "0.1.0"
description = "Docker-based IREE compilation with local Python validation"
dependencies = [
    "jsonschema>=4.0",
    "pydantic>=2.0", 
    "click>=8.0",
    "pathlib",
    "typing-extensions"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "ruff>=0.1.0",
    "mypy>=1.0"
]

[project.scripts]
iree-docker-compile = "cli.iree_docker_compile:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.black]
line-length = 88
target-version = ['py39']

[tool.ruff]
line-length = 88
target-version = "py39"
```

## Development Workflow

### Daily Development

```bash
# Activate environment and run validation
uv run python scripts/validate-config.py config.json

# Run CLI tool
uv run iree-docker-compile --input model.mlir --target cuda

# Run tests
uv run pytest

# Format code
uv run black .
uv run ruff check --fix .
```

### Adding Dependencies

```bash
# Add runtime dependency
uv add jsonschema

# Add development dependency  
uv add --dev pytest

# Update all dependencies
uv pip install --upgrade-package all
```

## Integration with Docker

### Hybrid Approach Benefits

1. **Fast Local Validation**: uv provides instant Python environment activation
2. **Isolated Compilation**: Docker ensures consistent IREE compilation environment
3. **Development Speed**: No need to rebuild Docker images for Python changes
4. **Dependency Management**: uv handles Python deps, Docker handles IREE toolchain

### Workflow Pattern

```python
# Example CLI integration
def main():
    # 1. Local validation with uv-managed Python
    config = validate_config_locally(config_file)
    
    # 2. Prepare Docker environment
    docker_config = prepare_docker_config(config)
    
    # 3. Run Docker compilation
    result = run_docker_compilation(docker_config)
    
    # 4. Process results locally
    return process_compilation_results(result)
```

## Testing Strategy

### Local Testing with uv

```bash
# Unit tests for validation logic
uv run pytest tests/test_validation.py

# Integration tests (requires Docker)
uv run pytest tests/test_integration.py --docker

# Property-based testing
uv run pytest tests/test_properties.py

# Coverage reporting
uv run pytest --cov=src --cov-report=html
```

### Test Structure

```python
# tests/test_validation.py
import pytest
from src.validation import ConfigValidator

def test_cuda_config_validation():
    validator = ConfigValidator()
    config = {"target": "cuda", "target_features": ["sm_80"]}
    is_valid, errors = validator.validate_config(config)
    assert is_valid
```

## CI/CD Integration

### GitHub Actions with uv

```yaml
# .github/workflows/test.yml
- name: Set up uv
  uses: astral-sh/setup-uv@v1

- name: Install dependencies
  run: uv pip install -e ".[dev]"

- name: Run tests
  run: uv run pytest

- name: Validate configurations
  run: uv run python scripts/validate-config.py config/examples/*.json
```

## Error Handling Patterns

### Local Validation Errors

```python
# Fail fast with clear messages
try:
    config = validate_config(config_file)
except ValidationError as e:
    print(f"❌ Configuration validation failed: {e}")
    print("💡 Run with --generate-example to see valid config format")
    sys.exit(1)
```

### Docker Integration Errors

```python
# Separate local vs Docker errors
try:
    result = run_docker_compilation(config)
except DockerNotAvailableError:
    print("❌ Docker not available. Please install Docker Desktop.")
    sys.exit(1)
except CompilationError as e:
    print(f"❌ IREE compilation failed: {e}")
    print("💡 Check input MLIR file and target configuration")
    sys.exit(1)
```

## Performance Considerations

### uv Advantages

- **Fast environment creation**: ~100ms vs ~10s for conda/virtualenv
- **Dependency resolution**: Faster than pip, more reliable than poetry
- **Disk usage**: Shared dependency cache across projects
- **Reproducible**: Lock files ensure consistent environments

### Best Practices

1. **Use uv run**: Automatically activates environment for single commands
2. **Pin dependencies**: Use exact versions in production
3. **Cache in CI**: Cache uv environments for faster builds
4. **Separate concerns**: Keep Python validation separate from Docker compilation

## Troubleshooting

### Common Issues

```bash
# uv not found
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Environment activation issues
uv venv --force .venv  # Recreate environment

# Dependency conflicts
uv pip install --force-reinstall package_name

# Docker integration issues
docker --version  # Ensure Docker is available
uv run python -c "import docker; print('Docker client OK')"
```

### Debug Mode

```bash
# Verbose uv operations
UV_VERBOSE=1 uv pip install package

# Debug Python validation
uv run python scripts/validate-config.py --verbose config.json

# Debug Docker integration
uv run iree-docker-compile --debug --input model.mlir
```

This steering guide ensures consistent use of uv throughout the project while maintaining the hybrid local-Python + Docker-compilation architecture.