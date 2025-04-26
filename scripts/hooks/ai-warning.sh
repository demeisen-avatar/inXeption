#!/usr/bin/env bash

# This script is used for pre-commit hooks to warn AIs about making unauthorized changes
# It will always display a warning message when the pre-commit hooks are run


# Display a prominent warning message to AIs
cat <<'EOF'
⚠️ ⚠️ ⚠️ WARNING to AI-Assistant ⚠️ ⚠️ ⚠️

DO NOT MAKE CODE CHANGES.

If any auto-changes have been made, this is ok -- you may proceed with the commit (you may need to restage auto-changed files). If so, execute `git status` after the commit is done to make sure it has completed successfully.

However if ANY further code-change is required you MUST RETURN CONTROL TO THE HUMAN OPERATOR.

⚠️ ⚠️ ⚠️ END OF WARNING ⚠️ ⚠️ ⚠️
EOF

# The script always returns success to avoid affecting the actual commit status
exit 0
