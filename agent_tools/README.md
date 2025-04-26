# Agent Tools

This directory contains tools and utilities developed by AI agents to enhance their capabilities. These tools are separate from the core inXeption codebase and represent extensions built by the agents themselves.

## Available Tools

### Browser Automation
- **Module**: `browser_automation.py`
- **Documentation**: `doc/browser.md`
- **Purpose**: Provides Selenium-based browser automation with persistent profiles
- **Features**:
  - Firefox automation with DOM-level access and control
  - Uses persistent profiles in `/host/.persist/.firefox/`
  - Shares profiles with desktop Firefox for continuity
  - Helper functions for waiting and interacting with elements

### Web Search
- **Documentation**: `doc/web_ai.md`
- **Purpose**: Instructions for performing web searches

## Usage

To use the browser automation module in your Python code:

```python
import sys
sys.path.append('/host')  # Add host directory to Python path

from agent_tools.browser_automation import get_browser

# Create a browser instance
browser = get_browser()

try:
    # Navigate to a website
    browser.get('https://www.example.com')

    # Interact with the page
    element = browser.find_element('id', 'some-element')
    element.click()

finally:
    # Always close the browser when done
    browser.quit()
```

See the documentation files in the `doc/` directory for detailed information on each tool.
