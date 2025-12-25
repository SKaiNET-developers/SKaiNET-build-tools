#!/bin/bash
# IREE Compilation Wrapper Script
# Easy-to-use wrapper for common IREE compilation workflows

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

# Default values
TARGET="cuda"
OPTIMIZATION="O3"
FORMAT="vmfb"
VALIDATE=true
BENCHMARK=false
VERBOSE=false
DRY_RUN=false

# Function to show usage
show_usage() {
    echo -e "${BLUE}IREE Compilation Wrapper${NC}"
    echo ""
    echo "Usage: $0 [options] <input.mlir> <output.vmfb>"
    echo ""
    echo "Options:"
    echo "  -t, --target TARGET        Compilation target (cuda, cpu, vulkan, metal) [default: cuda]"
    echo "  -O, --optimization LEVEL   Optimization level (O0, O1, O2, O3) [default: O3]"
    echo "  -f, --format FORMAT        Output format (vmfb, so, dylib) [default: vmfb]"
    echo "  --features FEATURES        Target-specific features (comma-separated)"
    echo "  --no-validate              Disable output validation"
    echo "  --benchmark                Enable performance benchmarking"
    echo "  -v, --verbose              Enable verbose output"
    echo "  -n, --dry-run              Show what would be done without executing"
    echo "  -c, --config FILE          Use configuration file instead of command-line options"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 model.mlir model.vmfb                           # Basic CUDA compilation"
    echo "  $0 -t cpu -O O2 model.mlir model.vmfb             # CPU compilation with O2"
    echo "  $0 --features sm_80,sm_86 model.mlir model.vmfb   # CUDA with specific compute capabilities"
    echo "  $0 --benchmark -v model.mlir model.vmfb           # With benchmarking and verbose output"
    echo "  $0 -c config.json model.mlir model.vmfb           # Using configuration file"
    echo "  $0 --dry-run model.mlir model.vmfb                # Dry run to see what would be executed"
    echo ""
    echo "Target-specific features:"
    echo "  CUDA:   sm_70, sm_75, sm_80, sm_86, sm_89, sm_90"
    echo "  CPU:    avx, avx2, avx512, sse4.1, sse4.2, neon"
    echo "  Vulkan: spirv1.3, spirv1.4, spirv1.5, spirv1.6"
    echo "  Metal:  metal2.4, metal3.0"
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

# Parse command-line arguments
POSITIONAL_ARGS=()
FEATURES=""
CONFIG_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -O|--optimization)
            OPTIMIZATION="$2"
            shift 2
            ;;
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        --features)
            FEATURES="$2"
            shift 2
            ;;
        --no-validate)
            VALIDATE=false
            shift
            ;;
        --benchmark)
            BENCHMARK=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -*)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Restore positional parameters
set -- "${POSITIONAL_ARGS[@]}"

# Check for required arguments
if [ $# -lt 2 ] && [ -z "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Input and output files are required${NC}"
    echo ""
    show_usage
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"

# Validate input file
if [ -n "$INPUT_FILE" ] && [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}Error: Input file does not exist: $INPUT_FILE${NC}"
    exit 1
fi

# Build CLI arguments
CLI_ARGS=()

if [ -n "$CONFIG_FILE" ]; then
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}Error: Configuration file does not exist: $CONFIG_FILE${NC}"
        exit 1
    fi
    CLI_ARGS+=(--config "$CONFIG_FILE")
else
    CLI_ARGS+=(--input "$INPUT_FILE")
    CLI_ARGS+=(--output "$OUTPUT_FILE")
    CLI_ARGS+=(--target "$TARGET")
    CLI_ARGS+=(--optimization "$OPTIMIZATION")
    CLI_ARGS+=(--format "$FORMAT")
    
    if [ -n "$FEATURES" ]; then
        IFS=',' read -ra FEATURE_ARRAY <<< "$FEATURES"
        for feature in "${FEATURE_ARRAY[@]}"; do
            CLI_ARGS+=(--target-features "$feature")
        done
    fi
    
    if [ "$VALIDATE" = false ]; then
        CLI_ARGS+=(--no-validate)
    fi
    
    if [ "$BENCHMARK" = true ]; then
        CLI_ARGS+=(--benchmark)
    fi
fi

if [ "$VERBOSE" = true ]; then
    CLI_ARGS+=(--verbose)
fi

if [ "$DRY_RUN" = true ]; then
    CLI_ARGS+=(--dry-run)
fi

# Show what we're about to do
echo -e "${BLUE}IREE Compilation Wrapper${NC}"
echo "Target: $TARGET"
echo "Input: $INPUT_FILE"
echo "Output: $OUTPUT_FILE"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Dry run mode - showing what would be executed${NC}"
fi

echo ""

# Execute compilation
echo -e "${BLUE}Running compilation...${NC}"
run_cli compile "${CLI_ARGS[@]}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Compilation completed successfully${NC}"
else
    echo -e "${RED}✗ Compilation failed${NC}"
    exit 1
fi