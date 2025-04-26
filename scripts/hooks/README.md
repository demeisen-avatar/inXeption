# AI Warning Hook

This directory contains a hook that displays a prominent warning message to AI assistants during git pre-commit checks.

## Purpose

When an LLM like Claude is working with code and pre-commit hooks fail, it sometimes tries to fix the issues directly rather than reporting the errors back to the human operator. This can lead to unauthorized or incorrect code changes.

This hook displays a prominent warning message as the final step in the pre-commit process, reminding the AI to:

1. NOT make code changes on its own
2. Report back to the human operator with the full error message
3. Await instructions from the human

## Integration

The hook is integrated into the repository's pre-commit configuration in `.pre-commit-config.yaml` with the lowest priority (-9999) to ensure it runs last, after all other hooks have completed.

## Installation

No special installation is needed - the hook is automatically included when you run:

```bash
pre-commit install
```

## Customization

If you want to modify the warning message, edit the `ai-warning.sh` script in this directory.
