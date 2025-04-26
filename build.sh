#!/bin/bash
set -e

# Change to script directory to find Dockerfile
cd "$(dirname "$0")"

IMAGE_NAME=""
FLAGS=""
FORCE=false
TAG_NAME=""
USE_GPU=false  # Default to CPU-only version

# Print usage information
function print_usage() {
    echo "Usage: $0 --image NAME [--clean] [--force] [--tag TAG_NAME] [--gpu]"
    echo ""
    echo "Options:"
    echo "  --image NAME    Specify the Docker image name (required)"
    echo "  --clean         Build with --no-cache to ensure a clean build"
    echo "  --force         Force build even if git state is not clean"
    echo "  --tag TAG_NAME  Create a git tag after successful build"
    echo "  --gpu           Build with GPU support (CUDA enabled)"
    echo ""
}

# If no arguments provided, show usage and exit
if [[ $# -eq 0 ]]; then
    print_usage
    exit 1
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --image)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --clean)
            FLAGS="--no-cache"
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --tag)
            TAG_NAME="$2"
            shift 2
            ;;
        --gpu)
            USE_GPU=true
            shift
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Verify required arguments
if [ -z "$IMAGE_NAME" ]; then
    echo "Error: --image NAME is required"
    print_usage
    exit 1
fi

# Check if git state is clean
if [ "$FORCE" = false ]; then
    if [ -n "$(git status --porcelain)" ]; then
        echo "Error: Git state not clean -- either fix that or use \`--force\` flag to override"
        echo "Git status:"
        git status
        exit 1
    fi
fi

# Build container with GPU flag if specified
if [ "$USE_GPU" = true ]; then
    echo "Building GPU-enabled image..."
    docker build ${FLAGS} --build-arg USE_GPU=true -t "$IMAGE_NAME" .
else
    echo "Building CPU-only image (lightweight)..."
    docker build ${FLAGS} --build-arg USE_GPU=false -t "$IMAGE_NAME" .
fi

# Only tag if a tag name is provided
if [ -n "$TAG_NAME" ] && [ "$FORCE" = false ]; then
    # Tag the git commit with the provided tag name
    git tag -a "$TAG_NAME" -m "Docker image ${IMAGE_NAME} built from this commit"
    echo "Tagged commit with: $TAG_NAME"
fi

# Show all docker images and containers
echo "Docker Images:"
docker images

echo "Docker Containers:"
docker ps -a
