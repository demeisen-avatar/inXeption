#!/bin/bash
# File: scripts/hooks/convert_quotes.sh
# This script handles the triple-quote conversion workflow to maintain consistent quote styles
# while avoiding circular dependencies with ruff formatter.

# Process each file passed as an argument
for file in "$@"; do
  if [[ $file == *.py ]]; then
    # 1. First convert ''' to """ (to prepare for ruff)
    sed -i "s/'''/\"\"\"/g" "$file"

    # 2. Run ruff format on the file
    ruff format "$file"

    # 3. Convert """ back to ''' (after ruff is done)
    sed -i "s/\"\"\"/'''/g" "$file"
  fi
done

# Return success
exit 0
