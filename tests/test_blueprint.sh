#!/bin/bash
# Test script for blueprint extraction using sample files

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJ_ROOT="$SCRIPT_DIR/.."
BLUEPRINT_SCRIPT="$PROJ_ROOT/scripts/blueprints.sh"

# Check if blueprints.sh script exists
if [ ! -f "$BLUEPRINT_SCRIPT" ]; then
    echo "Error: Could not find blueprints.sh at $BLUEPRINT_SCRIPT"
    exit 1
fi

# Create temporary directory for testing
TMP_DIR="/tmp/test_blueprint"
mkdir -p "$TMP_DIR"

# Copy sample files to temporary directory
cp "$SCRIPT_DIR/blueprint_sample.py_" "$TMP_DIR/blueprint_sample.py"
cp "$SCRIPT_DIR/blueprint_sample.md_" "$TMP_DIR/blueprint_sample.md"
cp "$SCRIPT_DIR/blueprint_sample.sh_" "$TMP_DIR/blueprint_sample.sh"
cp "$SCRIPT_DIR/blueprint_sample_faulty.md_" "$TMP_DIR/blueprint_sample_faulty.md"

echo "Running blueprint extraction on test samples..."

# Run blueprint extraction on the temporary directory
"$BLUEPRINT_SCRIPT" "$TMP_DIR"

echo ""
echo "================ Testing --check validation ================"

# Run validation on valid files (should pass)
echo "Running check on valid files (should pass):"
"$BLUEPRINT_SCRIPT" --check "$TMP_DIR/blueprint_sample.py" "$TMP_DIR/blueprint_sample.md" "$TMP_DIR/blueprint_sample.sh"
VALID_EXIT=$?
if [ $VALID_EXIT -eq 0 ]; then
    echo "✅ Valid files check PASSED as expected."
else
    echo "❌ Valid files check FAILED unexpectedly. Exit code: $VALID_EXIT"
fi

# Run validation on faulty file (should fail)
echo ""
echo "Running check on faulty file (should fail - this is expected):"
"$BLUEPRINT_SCRIPT" --check "$TMP_DIR/blueprint_sample_faulty.md"
FAULTY_EXIT=$?
if [ $FAULTY_EXIT -ne 0 ]; then
    echo "✅ Faulty file check FAILED as expected. Exit code: $FAULTY_EXIT"
else
    echo "❌ Faulty file check PASSED unexpectedly."
fi

# Clean up temporary directory
echo ""
echo "Tests completed. Cleaning up temporary directory."
rm -rf "$TMP_DIR"
