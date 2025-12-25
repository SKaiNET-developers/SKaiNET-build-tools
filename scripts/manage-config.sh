#!/bin/bash
# IREE Configuration Management Wrapper Script
# Easy-to-use wrapper for configuration validation and generation

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
    echo -e "${BLUE}IREE Configuration Management Wrapper${NC}"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  validate <config.json>              Validate configuration file"
    echo "  normalize <config.json> [output]    Validate and normalize configuration"
    echo "  generate <target> [output]          Generate example configuration"
    echo "  help                                Show this help message"
    echo ""
    echo "Options for validate/normalize:"
    echo "  -v, --verbose                       Enable verbose output"
    echo ""
    echo "Targets for generate:"
    echo "  cuda, cpu, vulkan, metal"
    echo ""
    echo "Examples:"
    echo "  $0 validate config.json                           # Validate configuration"
    echo "  $0 normalize config.json normalized.json          # Normalize and save"
    echo "  $0 generate cuda cuda-example.json                # Generate CUDA config"
    echo "  $0 generate cpu                                   # Generate CPU config to stdout"
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

# Check for minimum arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Command is required${NC}"
    echo ""
    show_usage
    exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
    validate)
        if [ $# -lt 1 ]; then
            echo -e "${RED}Error: Configuration file is required for validate command${NC}"
            exit 1
        fi
        
        CONFIG_FILE="$1"
        shift
        
        if [ ! -f "$CONFIG_FILE" ]; then
            echo -e "${RED}Error: Configuration file does not exist: $CONFIG_FILE${NC}"
            exit 1
        fi
        
        CLI_ARGS=(--config "$CONFIG_FILE")
        
        # Parse additional options
        while [[ $# -gt 0 ]]; do
            case $1 in
                -v|--verbose)
                    CLI_ARGS+=(--verbose)
                    shift
                    ;;
                *)
                    echo -e "${RED}Unknown option for validate: $1${NC}"
                    exit 1
                    ;;
            esac
        done
        
        echo -e "${BLUE}Validating configuration: $CONFIG_FILE${NC}"
        run_cli validate-config "${CLI_ARGS[@]}"
        ;;
        
    normalize)
        if [ $# -lt 1 ]; then
            echo -e "${RED}Error: Configuration file is required for normalize command${NC}"
            exit 1
        fi
        
        CONFIG_FILE="$1"
        OUTPUT_FILE="$2"
        
        if [ ! -f "$CONFIG_FILE" ]; then
            echo -e "${RED}Error: Configuration file does not exist: $CONFIG_FILE${NC}"
            exit 1
        fi
        
        CLI_ARGS=(--config "$CONFIG_FILE" --normalize)
        
        if [ -n "$OUTPUT_FILE" ]; then
            CLI_ARGS+=(--output "$OUTPUT_FILE")
        fi
        
        echo -e "${BLUE}Normalizing configuration: $CONFIG_FILE${NC}"
        run_cli validate-config "${CLI_ARGS[@]}"
        
        if [ -n "$OUTPUT_FILE" ]; then
            echo -e "${GREEN}✓ Normalized configuration saved to: $OUTPUT_FILE${NC}"
        fi
        ;;
        
    generate)
        if [ $# -lt 1 ]; then
            echo -e "${RED}Error: Target is required for generate command${NC}"
            echo "Available targets: cuda, cpu, vulkan, metal"
            exit 1
        fi
        
        TARGET="$1"
        OUTPUT_FILE="$2"
        
        # Validate target
        case "$TARGET" in
            cuda|cpu|vulkan|metal)
                ;;
            *)
                echo -e "${RED}Error: Invalid target: $TARGET${NC}"
                echo "Available targets: cuda, cpu, vulkan, metal"
                exit 1
                ;;
        esac
        
        CLI_ARGS=(--target "$TARGET")
        
        if [ -n "$OUTPUT_FILE" ]; then
            CLI_ARGS+=(--output "$OUTPUT_FILE")
        fi
        
        echo -e "${BLUE}Generating $TARGET configuration${NC}"
        run_cli generate-config "${CLI_ARGS[@]}"
        
        if [ -n "$OUTPUT_FILE" ]; then
            echo -e "${GREEN}✓ Configuration saved to: $OUTPUT_FILE${NC}"
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