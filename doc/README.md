# Knowledge Base Directory

This directory contains documentation for AI agents working with the inXeption project infrastructure.

## Core Operational Guides

**Start here for common tasks:**

- **`gemini.md`** - Gemini API usage, billing warnings, free tier strategies
- **`gcloud.md`** - Google Cloud infrastructure, BigQuery billing monitoring system
- **`web_ai.md`** - OpenAI web search methodology for research tasks

## Technical Reference

**Deep technical documentation:**

- **`API.md`** - Anthropic Claude API technical reference (tools, caching, rate limits)
- **`stop_button.md`** - Streamlit stop button implementation technical analysis
- **`bible.md`** - Engineering principles and coding standards

## Sensitive Information

**⚠️ Private documentation (excluded from git):**

- **`.private/gcloud-notes.md`** - Account details, API keys, billing incident case studies
- **`.private/`** directory contains information that should NOT be committed to public repositories

## Quick Reference

**For billing/cost investigations:** Start with `gcloud.md` BigQuery monitoring system
**For API usage issues:** Check `gemini.md` for Gemini, `API.md` for Claude, `web_ai.md` for OpenAI
**For code standards:** Review `bible.md` engineering principles
**For account details:** See `.private/gcloud-notes.md` (sensitive information)

## Adding New Documentation

**Where to put new information:**
- **Gemini API guidance** → `gemini.md`
- **Google Cloud procedures** → `gcloud.md`
- **Account/billing details** → `.private/gcloud-notes.md`
- **Technical deep-dives** → Create new file and update this README
- **Sensitive information** → `.private/` directory (never commit to git)

## Notes

- The knowledge base was systematically updated in August 2025 to remove dangerous misinformation about billing-enabled projects
- BigQuery billing monitoring system is fully operational for programmatic cost analysis
- All content duplication has been resolved to prevent agent confusion
