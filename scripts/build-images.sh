#!/bin/bash
# Build script for IREE Docker images
# Builds Docker images for all IREE compilation targets

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}Building IREE Docker images...${NC}"

# Use the docker-status.sh wrapper for building
if [ $# -eq 0 ]; then
    # Build all images
    "$SCRIPT_DIR/docker-status.sh" build all
else
    # Build specific target
    "$SCRIPT_DIR/docker-status.sh" build "$1"
fi

echo -e "${GREEN}✓ Docker image build process completed${NC}"

# Show final status
echo ""
echo -e "${BLUE}Final image status:${NC}"
"$SCRIPT_DIR/docker-status.sh" status