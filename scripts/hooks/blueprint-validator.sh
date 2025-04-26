#!/bin/bash
# Pre-commit hook to validate blueprint documentation
# Ensures all blueprints have proper indices and markers

# Get the project root directory
PROJ_ROOT="$(git rev-parse --show-toplevel)"
BLUEPRINT_SCRIPT="$PROJ_ROOT/scripts/blueprints.sh"

# Check if the blueprint script exists
if [ ! -f "$BLUEPRINT_SCRIPT" ]; then
    echo "Error: Could not find blueprints.sh at $BLUEPRINT_SCRIPT"
    exit 1
fi

echo "Validating blueprints across the entire project..."

# Run validation on the entire project
"$BLUEPRINT_SCRIPT" --check "$PROJ_ROOT"

if [ $? -ne 0 ]; then
    echo "❌ Blueprint validation failed. Please fix the issues before committing."
    exit 1
else
    echo "✅ Blueprint validation passed for the entire project."
    exit 0
fi
