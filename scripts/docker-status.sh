#!/bin/bash
# IREE Docker Status and Management Wrapper Script
# Easy-to-use wrapper for Docker image management and status checking

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Function to show usage
show_usage() {
    echo -e "${BLUE}IREE Docker Status and Management Wrapper${NC}"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  status [target]                     Show Docker images and system status"
    echo "  build [target]                      Build Docker images"
    echo "  pull [target]                       Pull Docker images from registry"
    echo "  clean [target]                      Remove Docker images"
    echo "  help                                Show this help message"
    echo ""
    echo "Targets:"
    echo "  cuda, cpu, vulkan, metal, all       [default: all]"
    echo ""
    echo "Examples:"
    echo "  $0 status                           # Show status for all targets"
    echo "  $0 status cuda                      # Show status for CUDA target only"
    echo "  $0 build cuda                       # Build CUDA Docker image"
    echo "  $0 build all                        # Build all Docker images"
    echo "  $0 pull                             # Pull all available images"
    echo "  $0 clean cuda                       # Remove CUDA Docker image"
    echo ""
}

# Function to check if uv is available
check_uv() {
    command -v uv >/dev/null 2>&1
}

# Function to run CLI command
run_cli() {
    local cmd="$1"
    shift
    
    cd "$PROJECT_ROOT"
    
    if check_uv; then
        uv run iree-docker-compile "$cmd" "$@"
    else
        if [ -f ".venv/bin/activate" ]; then
            source .venv/bin/activate
        fi
        python -m iree_docker_integration.cli "$cmd" "$@"
    fi
}

# Function to validate target
validate_target() {
    local target="$1"
    case "$target" in
        cuda|cpu|vulkan|metal|all|"")
            return 0
            ;;
        *)
            echo -e "${RED}Error: Invalid target: $target${NC}"
            echo "Available targets: cuda, cpu, vulkan, metal, all"
            return 1
            ;;
    esac
}

# Function to get target list
get_targets() {
    local target="$1"
    if [ "$target" = "all" ] || [ -z "$target" ]; then
        echo "cuda cpu vulkan metal"
    else
        echo "$target"
    fi
}

# Function to build Docker images
build_images() {
    local target="$1"
    local targets
    targets=$(get_targets "$target")
    
    echo -e "${BLUE}Building Docker images for: $targets${NC}"
    
    for tgt in $targets; do
        echo -e "${BLUE}Building $tgt image...${NC}"
        
        dockerfile_path="$PROJECT_ROOT/docker/$tgt"
        if [ ! -d "$dockerfile_path" ]; then
            echo -e "${YELLOW}Warning: Dockerfile directory not found for $tgt: $dockerfile_path${NC}"
            continue
        fi
        
        if [ ! -f "$dockerfile_path/Dockerfile" ]; then
            echo -e "${YELLOW}Warning: Dockerfile not found for $tgt: $dockerfile_path/Dockerfile${NC}"
            continue
        fi
        
        image_name="iree-compiler:$tgt-latest"
        
        echo "Building $image_name from $dockerfile_path..."
        if docker build -t "$image_name" -f "$dockerfile_path/Dockerfile" "$PROJECT_ROOT"; then
            echo -e "${GREEN}✓ Successfully built $image_name${NC}"
        else
            echo -e "${RED}✗ Failed to build $image_name${NC}"
        fi
    done
}

# Function to pull Docker images
pull_images() {
    local target="$1"
    local targets
    targets=$(get_targets "$target")
    
    echo -e "${BLUE}Pulling Docker images for: $targets${NC}"
    
    for tgt in $targets; do
        image_name="iree-compiler:$tgt-latest"
        
        echo -e "${BLUE}Pulling $image_name...${NC}"
        if docker pull "$image_name" 2>/dev/null; then
            echo -e "${GREEN}✓ Successfully pulled $image_name${NC}"
        else
            echo -e "${YELLOW}⚠ Could not pull $image_name (may not exist in registry)${NC}"
        fi
    done
}

# Function to clean Docker images
clean_images() {
    local target="$1"
    local targets
    targets=$(get_targets "$target")
    
    echo -e "${BLUE}Cleaning Docker images for: $targets${NC}"
    
    for tgt in $targets; do
        image_name="iree-compiler:$tgt-latest"
        
        echo -e "${BLUE}Removing $image_name...${NC}"
        if docker rmi "$image_name" 2>/dev/null; then
            echo -e "${GREEN}✓ Successfully removed $image_name${NC}"
        else
            echo -e "${YELLOW}⚠ Image $image_name not found or could not be removed${NC}"
        fi
    done
}

# Check Docker availability
check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        echo "Please install Docker and try again."
        exit 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running or not accessible${NC}"
        echo "Please start Docker and ensure you have proper permissions."
        exit 1
    fi
}

# Parse command-line arguments
COMMAND="${1:-status}"
TARGET="$2"

case "$COMMAND" in
    status)
        if ! validate_target "$TARGET"; then
            exit 1
        fi
        
        echo -e "${BLUE}Checking Docker status...${NC}"
        
        CLI_ARGS=()
        if [ -n "$TARGET" ] && [ "$TARGET" != "all" ]; then
            CLI_ARGS+=(--target "$TARGET")
        fi
        
        run_cli status "${CLI_ARGS[@]}"
        ;;
        
    build)
        check_docker
        
        if ! validate_target "$TARGET"; then
            exit 1
        fi
        
        build_images "$TARGET"
        ;;
        
    pull)
        check_docker
        
        if ! validate_target "$TARGET"; then
            exit 1
        fi
        
        pull_images "$TARGET"
        ;;
        
    clean)
        check_docker
        
        if ! validate_target "$TARGET"; then
            exit 1
        fi
        
        echo -e "${YELLOW}Warning: This will remove Docker images. Continue? [y/N]${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            clean_images "$TARGET"
        else
            echo "Cancelled."
        fi
        ;;
        
    help|--help|-h)
        show_usage
        ;;
        
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac