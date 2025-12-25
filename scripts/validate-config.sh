#!/bin/bash

# IREE Configuration Validation Wrapper Script
# Provides easy-to-use interface for configuration validation and generation
# Requirements: 3.3, 8.2, 8.3, 8.4, 8.5

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VALIDATOR_SCRIPT="$SCRIPT_DIR/validate-config.py"

# Default paths
DEFAULT_SCHEMA="$PROJECT_ROOT/config/schema/compile-config-schema.json"
DEFAULT_CONFIG_DIR="$PROJECT_ROOT/config"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check dependencies
check_dependencies() {
    if ! command -v python3 &> /dev/null; then
        log_error "python3 is required but not installed"
        exit 1
    fi
    
    if ! python3 -c "import jsonschema" 2>/dev/null; then
        log_error "jsonschema Python package is required"
        log_info "Install with: pip3 install jsonschema"
        exit 1
    fi
    
    if [[ ! -f "$VALIDATOR_SCRIPT" ]]; then
        log_error "Validator script not found: $VALIDATOR_SCRIPT"
        exit 1
    fi
    
    if [[ ! -f "$DEFAULT_SCHEMA" ]]; then
        log_error "Default schema not found: $DEFAULT_SCHEMA"
        exit 1
    fi
}

# Show usage information
show_usage() {
    cat << EOF
IREE Configuration Validation Tool

Usage: $(basename "$0") [COMMAND] [OPTIONS] [FILE]

Commands:
    validate [FILE]              Validate configuration file
    normalize [FILE]             Validate and normalize configuration
    generate [TARGET]            Generate example configuration
    list-targets                 List available compilation targets
    help                         Show this help message

Options:
    -o, --output FILE           Output file for normalized/generated config
    -s, --schema FILE           Custom schema file path
    -v, --verbose               Verbose output
    -q, --quiet                 Quiet mode (errors only)

Targets:
    cuda                        NVIDIA CUDA GPU target
    cpu                         CPU target (x86-64, ARM64)
    vulkan                      Vulkan GPU target
    metal                       Apple Metal GPU target

Examples:
    $(basename "$0") validate config.json
    $(basename "$0") normalize config.json -o normalized.json
    $(basename "$0") generate cuda -o cuda-config.json
    $(basename "$0") validate /path/to/config.json --verbose

Configuration Files:
    Default configurations are stored in: $DEFAULT_CONFIG_DIR
    Schema definition: $DEFAULT_SCHEMA

EOF
}

# List available targets
list_targets() {
    cat << EOF
Available IREE Compilation Targets:

cuda        NVIDIA CUDA GPU
            - Supports compute capabilities (sm_XX)
            - Hardware-accelerated inference
            - Best for NVIDIA GPU deployments

cpu         CPU (x86-64, ARM64)
            - Cross-platform compatibility
            - Vector instruction support (AVX, NEON)
            - Good for CPU-only deployments

vulkan      Vulkan GPU
            - Cross-platform GPU acceleration
            - SPIR-V shader compilation
            - Works on multiple GPU vendors

metal       Apple Metal GPU
            - Apple Silicon optimization
            - iOS/macOS deployment
            - Native Apple GPU acceleration

EOF
}

# Validate configuration file
validate_config() {
    local config_file="$1"
    local schema_file="${2:-$DEFAULT_SCHEMA}"
    local verbose="${3:-false}"
    
    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi
    
    log_info "Validating configuration: $(basename "$config_file")"
    
    local cmd_args=("$config_file" "--schema" "$schema_file")
    if [[ "$verbose" == "true" ]]; then
        cmd_args+=("--verbose")
    fi
    
    if python3 "$VALIDATOR_SCRIPT" "${cmd_args[@]}"; then
        log_success "Configuration is valid"
        return 0
    else
        log_error "Configuration validation failed"
        return 1
    fi
}

# Normalize configuration file
normalize_config() {
    local config_file="$1"
    local output_file="$2"
    local schema_file="${3:-$DEFAULT_SCHEMA}"
    local verbose="${4:-false}"
    
    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi
    
    log_info "Normalizing configuration: $(basename "$config_file")"
    
    local cmd_args=("$config_file" "--normalize" "--schema" "$schema_file")
    if [[ -n "$output_file" ]]; then
        cmd_args+=("--output" "$output_file")
    fi
    if [[ "$verbose" == "true" ]]; then
        cmd_args+=("--verbose")
    fi
    
    if python3 "$VALIDATOR_SCRIPT" "${cmd_args[@]}"; then
        if [[ -n "$output_file" ]]; then
            log_success "Normalized configuration written to: $output_file"
        else
            log_success "Configuration normalized successfully"
        fi
        return 0
    else
        log_error "Configuration normalization failed"
        return 1
    fi
}

# Generate example configuration
generate_config() {
    local target="$1"
    local output_file="$2"
    local schema_file="${3:-$DEFAULT_SCHEMA}"
    
    log_info "Generating example $target configuration"
    
    local cmd_args=("--generate-example" "$target" "--schema" "$schema_file")
    if [[ -n "$output_file" ]]; then
        cmd_args+=("--output" "$output_file")
    fi
    
    if python3 "$VALIDATOR_SCRIPT" "${cmd_args[@]}"; then
        if [[ -n "$output_file" ]]; then
            log_success "Example $target configuration written to: $output_file"
        else
            log_success "Example $target configuration generated"
        fi
        return 0
    else
        log_error "Failed to generate example configuration"
        return 1
    fi
}

# Main execution
main() {
    local command=""
    local config_file=""
    local output_file=""
    local schema_file="$DEFAULT_SCHEMA"
    local verbose="false"
    local quiet="false"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            validate|normalize|generate|list-targets|help)
                command="$1"
                shift
                ;;
            -o|--output)
                output_file="$2"
                shift 2
                ;;
            -s|--schema)
                schema_file="$2"
                shift 2
                ;;
            -v|--verbose)
                verbose="true"
                shift
                ;;
            -q|--quiet)
                quiet="true"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                if [[ -z "$config_file" && "$command" != "generate" && "$command" != "list-targets" ]]; then
                    config_file="$1"
                elif [[ "$command" == "generate" && -z "$config_file" ]]; then
                    config_file="$1"  # This is actually the target for generate command
                else
                    log_error "Unexpected argument: $1"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Set quiet mode
    if [[ "$quiet" == "true" ]]; then
        exec 1>/dev/null
    fi
    
    # Check dependencies
    check_dependencies
    
    # Execute command
    case "$command" in
        validate)
            if [[ -z "$config_file" ]]; then
                log_error "Configuration file required for validate command"
                show_usage
                exit 1
            fi
            validate_config "$config_file" "$schema_file" "$verbose"
            ;;
        normalize)
            if [[ -z "$config_file" ]]; then
                log_error "Configuration file required for normalize command"
                show_usage
                exit 1
            fi
            normalize_config "$config_file" "$output_file" "$schema_file" "$verbose"
            ;;
        generate)
            if [[ -z "$config_file" ]]; then
                log_error "Target required for generate command"
                log_info "Available targets: cuda, cpu, vulkan, metal"
                exit 1
            fi
            case "$config_file" in
                cuda|cpu|vulkan|metal)
                    generate_config "$config_file" "$output_file" "$schema_file"
                    ;;
                *)
                    log_error "Invalid target: $config_file"
                    log_info "Available targets: cuda, cpu, vulkan, metal"
                    exit 1
                    ;;
            esac
            ;;
        list-targets)
            list_targets
            ;;
        help|"")
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"