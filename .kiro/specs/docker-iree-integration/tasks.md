# Implementation Plan: Docker IREE Integration

## Overview

This implementation plan creates a standalone Docker-based IREE compilation service that takes StableHLO MLIR as input and produces optimized backend-specific executables, with initial focus on CUDA targets.

## Tasks

- [x] 1. Set up project structure and Docker foundation
  - Create directory structure for Docker images and scripts
  - Set up base project configuration files
  - Create initial documentation structure
  - _Requirements: 1.1, 2.1, 7.3_

- [x] 2. Create base CUDA Docker image
  - [x] 2.1 Create Dockerfile for CUDA-enabled IREE compiler
    - Base on nvidia/cuda:12.3-devel-ubuntu22.04
    - Install IREE toolchain (iree-compile, iree-run-module, iree-benchmark-module)
    - Configure CUDA runtime and development tools
    - _Requirements: 2.1, 2.2, 8.1_

  - [ ]* 2.2 Write property test for Docker image build
    - **Property 1: Docker image completeness**
    - **Validates: Requirements 2.1**

  - [x] 2.3 Create compilation entry script (compile.sh)
    - Implement main compilation logic with JSON config parsing
    - Support CUDA target compilation with architecture selection
    - Add error handling and logging
    - _Requirements: 1.1, 2.2, 8.1_

  - [ ]* 2.4 Write unit tests for compilation script
    - Test configuration parsing and validation
    - Test error handling scenarios
    - _Requirements: 1.5, 6.1_

- [x] 3. Implement validation and benchmarking capabilities
  - [x] 3.1 Create validation script (validate.sh)
    - Implement bytecode module validation
    - Verify execution correctness with test inputs
    - _Requirements: 6.4, 9.2_

  - [x] 3.2 Create benchmarking script (benchmark.sh)
    - Implement performance measurement capabilities
    - Support latency and throughput metrics
    - _Requirements: 5.3, 8.1_

  - [ ]* 3.3 Write property tests for validation pipeline
    - **Property 2: Validation consistency**
    - **Validates: Requirements 6.4**

- [x] 4. Create service interface and configuration system
  - [x] 4.1 Set up local Python environment with uv
    - Create pyproject.toml with dependencies (jsonschema, pydantic)
    - Set up uv virtual environment for local validation
    - Create requirements.txt for Docker image Python dependencies
    - _Requirements: 3.3, 8.2_

  - [x] 4.2 Implement JSON configuration schema and validation
    - Define input/output format specifications in JSON schema
    - Create Python validation logic using jsonschema + pydantic
    - Support multiple compilation targets and options (CUDA, CPU, Vulkan, Metal)
    - Run validation locally via uv before Docker compilation
    - _Requirements: 3.3, 8.2, 8.3, 8.4, 8.5_

  - [x] 4.3 Create volume mounting and file handling
    - Implement secure input/output file management
    - Add temporary file cleanup mechanisms
    - Integrate local Python validation with Docker orchestration
    - _Requirements: 10.3, 10.1_

  - [ ]* 4.4 Write unit tests for configuration system
    - Test JSON schema validation with pytest
    - Test file handling edge cases
    - Set up uv-based test runner
    - _Requirements: 6.1, 10.3_

- [-] 5. Checkpoint - Ensure basic Docker compilation works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create CLI wrapper and orchestration tools
  - [x] 6.1 Implement standalone CLI tool with uv
    - Create command-line interface using Python + uv for local execution
    - Integrate local config validation with Docker container management
    - Support simple compilation workflows with pre-validation
    - Add verbose logging and debugging options
    - _Requirements: 5.1, 5.2_

  - [x] 6.2 Create shell script wrappers
    - Implement easy-to-use wrapper scripts that call uv Python tools
    - Support local development workflows with uv environment
    - Bridge between uv Python validation and Docker compilation
    - _Requirements: 2.4, 5.1_

  - [ ]* 6.3 Write integration tests for CLI tools
    - Test end-to-end compilation workflows with uv + Docker
    - Test error handling and user feedback
    - _Requirements: 6.3, 5.5_

- [ ] 7. Add CPU and multi-backend support
  - [ ] 7.1 Create CPU Docker image
    - Create Dockerfile for CPU-optimized IREE compiler
    - Support x86-64 and ARM64 architectures
    - Add CPU-specific optimization flags
    - _Requirements: 2.2, 8.2_

  - [ ] 7.2 Extend configuration system for multi-backend support
    - Update JSON schema to support CPU, Vulkan, and Metal targets
    - Add target-specific validation logic
    - Update CLI to handle multiple backend options
    - _Requirements: 8.2, 8.3, 8.4, 8.5_

  - [ ]* 7.3 Write property tests for multi-backend compilation
    - **Property 3: Multi-backend consistency**
    - **Validates: Requirements 8.2, 8.3, 8.4, 8.5**

- [ ] 8. Add GitHub Actions CI/CD integration
  - [ ] 8.1 Create GitHub Actions workflow files
    - Implement Docker image building and caching
    - Add matrix builds for multiple IREE targets
    - Configure artifact generation and publishing
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ] 8.2 Create CI/CD testing pipeline
    - Implement automated compilation validation
    - Add performance regression testing
    - _Requirements: 4.2, 6.5_

  - [ ]* 8.3 Write unit tests for CI/CD scripts
    - Test workflow configuration and execution
    - Test artifact handling
    - _Requirements: 4.5, 6.5_

- [ ] 9. Implement security and production readiness
  - [ ] 9.1 Add security configurations
    - Implement minimal privilege container execution
    - Add secure file handling and cleanup
    - Configure network security restrictions
    - _Requirements: 10.1, 10.3, 10.4_

  - [ ] 9.2 Create production deployment artifacts
    - Generate optimized bytecode modules
    - Include runtime dependencies and metadata
    - Support version compatibility requirements
    - _Requirements: 9.1, 9.3, 9.5_

  - [ ]* 9.3 Write security validation tests
    - Test container security configurations
    - Test file system isolation and cleanup
    - _Requirements: 10.1, 10.3_

- [ ] 10. Add comprehensive documentation and examples
  - [ ] 10.1 Create user documentation
    - Write setup and installation guides
    - Create usage examples and tutorials
    - Document troubleshooting procedures
    - _Requirements: 5.1, 5.5_

  - [ ] 10.2 Create developer documentation
    - Document architecture and design decisions
    - Create contribution guidelines
    - Add API reference documentation
    - _Requirements: 7.3, 5.5_

- [ ] 11. Final checkpoint - Complete system validation
  - Ensure all tests pass, ask the user if questions arise.
  - Validate end-to-end compilation pipeline
  - Test production deployment scenarios

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Focus on CUDA targets initially, with architecture for future backend expansion
- **Python Environment**: Use uv for local Python environment management and dependency isolation
- **Hybrid Approach**: Python (via uv) for configuration validation locally, Docker for IREE compilation
- **Development Workflow**: Local validation → Docker compilation → Local result processing