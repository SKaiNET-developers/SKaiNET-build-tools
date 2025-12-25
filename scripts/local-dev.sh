#!/bin/bash
# Local development helper script
# Provides easy-to-use wrapper scripts for IREE Docker compilation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}IREE Local Development Helper${NC}"
echo "Project root: $PROJECT_ROOT"

# Function to check if uv is available
check_uv() {
    if command -v uv >/dev/null 2>&1; then
        echo -e "${GREEN}✓ uv is available${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ uv is not available, using system Python${NC}"
        return 1
    fi
}

# Function to set up Python environment
setup_python_env() {
    echo -e "${BLUE}Setting up Python environment...${NC}"
    
    cd "$PROJECT_ROOT"
    
    if check_uv; then
        # Use uv for environment management
        if [ ! -d ".venv" ]; then
            echo "Creating uv virtual environment..."
            uv venv .venv
        fi
        
        echo "Installing dependencies with uv..."
        uv pip install -e .
        
        echo -e "${GREEN}✓ Python environment ready with uv${NC}"
        echo "To activate: source .venv/bin/activate"
        echo "To run CLI: uv run iree-docker-compile --help"
    else
        # Fallback to pip
        if [ ! -d ".venv" ]; then
            echo "Creating Python virtual environment..."
            python3 -m venv .venv
        fi
        
        echo "Activating virtual environment..."
        source .venv/bin/activate
        
        echo "Installing dependencies with pip..."
        pip install -e .
        
        echo -e "${GREEN}✓ Python environment ready with pip${NC}"
        echo "To activate: source .venv/bin/activate"
        echo "To run CLI: python -m iree_docker_integration.cli --help"
    fi
}

# Function to run quick compilation test
test_compilation() {
    echo -e "${BLUE}Running compilation test...${NC}"
    
    # Create test input if it doesn't exist
    mkdir -p "$PROJECT_ROOT/input"
    mkdir -p "$PROJECT_ROOT/output"
    
    if [ ! -f "$PROJECT_ROOT/input/test.mlir" ]; then
        echo "Creating test MLIR file..."
        cat > "$PROJECT_ROOT/input/test.mlir" << 'EOF'
// Simple test MLIR file for IREE compilation
module {
  func.func @simple_add(%arg0: tensor<4xf32>, %arg1: tensor<4xf32>) -> tensor<4xf32> {
    %0 = arith.addf %arg0, %arg1 : tensor<4xf32>
    return %0 : tensor<4xf32>
  }
}
EOF
    fi
    
    # Run dry-run compilation test
    echo "Testing CLI with dry-run..."
    if check_uv; then
        uv run iree-docker-compile compile \
            --input "$PROJECT_ROOT/input/test.mlir" \
            --output "$PROJECT_ROOT/output/test.vmfb" \
            --target cuda \
            --dry-run
    else
        cd "$PROJECT_ROOT"
        source .venv/bin/activate
        python -m iree_docker_integration.cli compile \
            --input "$PROJECT_ROOT/input/test.mlir" \
            --output "$PROJECT_ROOT/output/test.vmfb" \
            --target cuda \
            --dry-run
    fi
    
    echo -e "${GREEN}✓ Compilation test completed${NC}"
}

# Function to show Docker status
show_docker_status() {
    echo -e "${BLUE}Checking Docker status...${NC}"
    
    if check_uv; then
        uv run iree-docker-compile status
    else
        cd "$PROJECT_ROOT"
        source .venv/bin/activate
        python -m iree_docker_integration.cli status
    fi
}

# Function to generate example configurations
generate_examples() {
    echo -e "${BLUE}Generating example configurations...${NC}"
    
    mkdir -p "$PROJECT_ROOT/config/examples"
    
    for target in cuda cpu vulkan metal; do
        echo "Generating $target configuration..."
        if check_uv; then
            uv run iree-docker-compile generate-config \
                --target "$target" \
                --output "$PROJECT_ROOT/config/examples/${target}-config.json"
        else
            cd "$PROJECT_ROOT"
            source .venv/bin/activate
            python -m iree_docker_integration.cli generate-config \
                --target "$target" \
                --output "$PROJECT_ROOT/config/examples/${target}-config.json"
        fi
    done
    
    echo -e "${GREEN}✓ Example configurations generated in config/examples/${NC}"
}

# Function to show usage
show_usage() {
    echo -e "${BLUE}IREE Local Development Helper${NC}"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup       Set up Python environment and dependencies"
    echo "  test        Run compilation test with dry-run"
    echo "  status      Show Docker images and system status"
    echo "  examples    Generate example configuration files"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup                    # Set up development environment"
    echo "  $0 test                     # Test compilation workflow"
    echo "  $0 status                   # Check Docker status"
    echo "  $0 examples                 # Generate example configs"
    echo ""
    echo "After setup, you can use the CLI directly:"
    echo "  uv run iree-docker-compile --help"
    echo "  uv run iree-docker-compile compile --input model.mlir --output model.vmfb"
}

# Main command handling
case "${1:-help}" in
    setup)
        setup_python_env
        ;;
    test)
        test_compilation
        ;;
    status)
        show_docker_status
        ;;
    examples)
        generate_examples
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac