# IREE Docker Integration Makefile
# Provides convenient commands for building and using IREE Docker containers

.PHONY: help build-cuda build-cpu build-all clean test

# Default target
help:
	@echo "IREE Docker Integration Commands:"
	@echo "  build-cuda    Build CUDA-enabled IREE compiler image"
	@echo "  build-cpu     Build CPU-only IREE compiler image"
	@echo "  build-all     Build all IREE compiler images"
	@echo "  clean         Remove built images and temporary files"
	@echo "  test          Run basic functionality tests"
	@echo "  help          Show this help message"

# Build CUDA image
build-cuda:
	@echo "Building CUDA IREE compiler image..."
	docker build -t iree-compiler:cuda-latest docker/cuda/

# Build CPU image
build-cpu:
	@echo "Building CPU IREE compiler image..."
	docker build -t iree-compiler:cpu-latest docker/cpu/

# Build all images
build-all: build-cuda build-cpu
	@echo "All IREE compiler images built successfully"

# Clean up
clean:
	@echo "Cleaning up Docker images and temporary files..."
	-docker rmi iree-compiler:cuda-latest iree-compiler:cpu-latest
	-docker system prune -f

# Basic functionality test (will be implemented in later tasks)
test:
	@echo "Running basic functionality tests..."
	@echo "Test implementation pending - will validate Docker images"