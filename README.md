# inXeption -- a hybrid evolver

This repository (/parent/d5/) is a rewrite of /parent/d4/ (mounted for you as /host) which is a rewrite from a snapshot of the 'reimagine' branch of the original /parent/demeisen_gen2 project.

## Vision and Purpose

Human and AI cooperatively building an AI that can evolve itself through collaborative development. The typical development cycle:

1. Human-AI discussion identifies next evolutionary step
2. We implement changes in inXeption/ folders
3. Test with test_runner.sh (L1 development mode)
4. Human and agent collaborate building out features, testing them, maintaining healthy git-hygiene
5. Once we're ready for a new release, agent can build fresh image and run it (spawning an L2, which it can interact with via Firefox in its Ubuntu desktop)

## Orientation

The inXeption system operates with layered environments:

- **L0**: Host machine (human's laptop/desktop)
- **L1**: Primary AI container (what you're running in now)
- **L2**: Test container (spawned from L1)

### System Structure and Critical Components

```bash
# How the L1 container is launched from L0
pi@πlocal ~/d4_host/d5 main
> ./build.sh --image d5 && ./run.sh --image d5 --container d5.alpha3

# What makes introspection possible - core container configuration
CONTAINER_ID=$(docker run -d \
    -v "$PARENT":/host \
    -v "$PARENT/..":/parent \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -p ${PORT_VNC_EXTERNAL}:${PORT_VNC_INTERNAL} \
    --name "$CONTAINER_NAME" \
    -it "$IMAGE_NAME")
```

### Core Tenets

- **KISS**: Simple > Complex. Example: file-based IPC with L0 - crude but effective = WIN!
- **Function > Security**: We're not the Pentagon. Root perms + docker socket = dev-speed
- **Get context**: Ask human when unclear
- **Push back**: Human and AI should be on the same wavelength to achieve shared ideal. To get this, we need a delta-signal.
- **Docs = information NOT in the code**: Documentation is for the AI agent. Agent can understand code. DON'T generate doc that duplicates what's already in the code. DO use doc to explain WHY something is done if it isn't self-evident or if it requires tribal-knowledge.
- **Don't overcode**: If it works and is simple, it's done
- **Informal > formal**: Structure serves vision
- **Git hygiene**: We ONLY commit once (a) we have progressed from one working state to another working state, (b) it's tested, and (c) the human has reviewed and authorized a commit.

## Git Pre-commit Hooks

This repository uses pre-commit hooks to ensure code quality and consistency. Before making any commits, you need to set up these hooks by running:

```bash
pre-commit install
```

This only needs to be done once after cloning the repository. The pre-commit hooks will automatically:

- Fix end-of-file issues (ensure files end with a newline)
- Remove trailing whitespace
- Check YAML syntax
- Run Ruff for linting and formatting Python files
- Run Pyright for type checking

## Development

For development, the project uses Docker to provide a consistent environment. Use the provided scripts to build and run the container:

- `build.sh` - Build the Docker image
- `run.sh` - Run the project in a Docker container

## Development Workflow

This repository supports a "hybrid-evolver" development flow where both human and agentware can collaborate to evolve the agentware source-code. The system operates at different "L-levels" (Layer levels):

- **L0**: Host machine (macbook/laptop)
- **L1**: Primary AI container (what you're running in now)
- **L2**: Test container (spawned from L1)

### 1. Testing Changes with Development Server (L1)

You can test changes to the codebase without rebuilding the container by using the development server:

```bash
# From within the L1 container
cd /host/inXeption/
./test_runner.sh
```

This will start a development Streamlit server and provide a URL (typically http://172.17.0.2:8510). Open Firefox within the desktop environment and navigate to this URL.

**Example Interaction:**
```
Human: What is the value of the LX environment variable?
AI: The value of the LX environment variable is 1.
```

This confirms you're running at L1 level. The development server is using your **modified code** from `/host/inXeption/`, not the system code in `/opt/inXeption/lib/inXeption/` that's running the main interface.

To stop the development server:
```bash
./test_runner.sh --stop
```

### 2. Building and Testing a New Container (L1→L2)

For more comprehensive testing, you can build a new image with your changes and run it as an L2 container:

```bash
# Build a new image with your changes
cd /host/
./build.sh --image testl2

# Run the new container
./run.sh --image testl2 --container testl2
```

The run.sh script will display URLs for accessing the new L2 container. You'll see output similar to:
```
L2 container access points:
- Streamlit interface: http://172.17.0.3:8503
- Desktop view: http://172.17.0.3:6083/vnc.html
... (other URLs)
```

Open Firefox and navigate to the Streamlit interface URL. This container includes your changes baked in.

**Example Interaction:**
```
Human: What is the value of the LX environment variable?
AI: The value of the LX environment variable is 2.
```

This confirms you're running at L2 level.

### Architecture Notes

The system is designed for efficient development:

- Human runs `build.sh` on their host machine (L0) to create the initial image
- The Dockerfile copies agent code from `inXeption/` into `/opt/inXeption/lib/inXeption/`
- Human runs `run.sh` to start an instance (L1) that maps `$projroot` to `/host/` and `$projroot/..` to `/parent/`
- Human interacts with the AI via http://localhost:8082
- Both human and AI can modify code in `/host/inXeption/`
- Changes can be tested immediately with `test_runner.sh` (L1)
- For more thorough testing, build and run a new container (L2)
- Port mappings defined in `.ports` file allow the human to access any development interfaces from their host machine

This architecture enables a seamless collaboration loop between human and AI for evolving the system.

## Blueprint Documentation System

💙6.5 BLUEPRINT DOCUMENTATION OVERVIEW
The project uses a blueprint documentation system to preserve architectural knowledge and design decisions across the codebase. Blueprints are special docstrings that provide high-level architectural information rather than just describing what the code does.

### Blueprint Types

- **💙 Architectural Blueprints**: Define key architectural components and decisions
  - Can appear at file, class, method, or function level
  - MUST include numeric indices (e.g., `💙1.0`) for logical organization
  - Example: `💙2.0 UI ABSTRACTION AND RENDERING PROTOCOL`

- **🔵 Implementation Notes**: Provide specific implementation details and guidance
  - Typically appear as comments rather than docstrings
  - Example: `# 🔵2.5 IMPLEMENTATION NOTE: ...`

- **Markdown Blueprints**: System-level documentation in markdown files
  - Must start with 💙 (including index) at the beginning of a line
  - Must end with 🖤 to close the blueprint
  - Used for documentation that spans multiple components

- **Shell Script Blueprints**: Documentation in shell scripts
  - Must start with # 💙 (including index) at the beginning of a line
  - All lines in a shell script blueprint must be comments

### Viewing Blueprints

To extract and view all blueprints in the project:

```bash
# From project root
./scripts/blueprints.sh
```

This will display all blueprints in numeric order, providing a comprehensive view of the system architecture.

For validating blueprint format and structure:

```bash
# Validate blueprint format
./scripts/blueprints.sh --check
```

The numeric indices ensure blueprints appear in a logical order that reflects the system's architecture, regardless of their location in the codebase.

### Blueprint Validation

The project enforces blueprint standards through pre-commit hooks that verify:
- All blueprints include a numeric index
- All markdown blueprints have matching 💙/🖤 pairs
- Shell script blueprints follow the proper comment format

This ensures consistent documentation across the codebase and maintains the integrity of the architectural information.
🖤

## Logging System

The inXeption system uses a structured logging approach to organize logs by environment type and timestamp, ensuring logs are always properly categorized and easy to find.

### Log Directory Structure

All logs are stored in the project root directory under `.logs/`:

```
$projroot/.logs/
├── dev/                      # Development environment logs
│   ├── 2025-03-27--16-27-24/ # Timestamped log directory
│   │   ├── http/             # HTTP exchange logs
│   │   └── streamlit.log     # Main application log
│   └── dev_runner.log        # Development runner log
├── dev-latest -> dev/...     # Symlink to latest dev logs
├── prod/                     # Production environment logs
│   └── $container_id/        # Container-specific logs
│       ├── 2025-03-27--15-34-22/ # Timestamped log directory
│       │   ├── http/         # HTTP exchange logs
│       │   └── streamlit.log # Main application log
│       └── ...
├── prod-latest -> prod/...   # Symlink to latest prod logs
├── test/                     # Test environment logs
│   ├── 2025-03-27--16-24-22/ # Timestamped log directory
│   │   └── http/             # HTTP exchange logs
│   └── ...
└── test-latest -> test/...   # Symlink to latest test logs
```

### Environment Types

- **Production (prod/)**: Logs from running the built container image (L1/L2). Organized by container ID and timestamp.
- **Development (dev/)**: Logs from running the development server with dev_runner.sh. Used when testing code changes without rebuilding containers.
- **Test (test/)**: Logs from running test cases via loop_test.py. Used for validating system behavior in a controlled environment.

### Convenience Symlinks

For each environment type, a "-latest" symlink points to the most recent log directory:
- `prod-latest → prod/$container_id/$timestamp/`
- `dev-latest → dev/$timestamp/`
- `test-latest → test/$timestamp/`

These symlinks make it easy to quickly access the most recent logs for any environment.

### Cross-Generation Development

When developing gen-(k+1) using gen-k:
- gen-k will store its own logs in `$gen_k_projroot/.logs/prod/`
- When testing gen-(k+1) from gen-k:
  - If gen-(k+1) is at the same location, logs go to `$gen_k_projroot/.logs/dev/` or `$gen_k_projroot/.logs/test/`
  - If gen-(k+1) is at a different location (e.g., a WIP rewrite), logs go to `$gen_k_plus_one_projroot/.logs/{dev,test}/`

This ensures logs always go to the appropriate project directory, maintaining clean separation between generations.

### HTTP Exchange Logging

All HTTP exchanges with the LLM API are automatically logged in the `http/` subdirectory of each timestamped log directory:
- Request logs: `http_request_$timestamp.yaml`
- Response logs: `http_response_$timestamp.yaml`

These logs are invaluable for debugging LLM interactions and understanding how the system communicates with the underlying API.

## Agent Tools

The project includes an `/host/agent_tools/` directory containing utilities and resources developed by AI agents to enhance their capabilities. This directory is separate from the core `inXeption/` codebase and represents agent-created extensions.

### Available Tools

- **Browser Automation**: Selenium-based browser automation with persistent profiles
  - Module: `agent_tools/browser_automation.py`
  - Documentation: `agent_tools/doc/browser.md`
  - Features: DOM-level control of Firefox, persistent profiles, helper functions

- **Web Search**: Instructions for performing web searches
  - Documentation: `agent_tools/doc/web_ai.md`

### Usage

To use browser automation in your Python code:

```python
import sys
sys.path.append('/host')  # Add host directory to Python path

from agent_tools.browser_automation import get_browser

# Create a browser instance
browser = get_browser()  # Visible mode by default, shares profile with desktop Firefox

try:
    # Navigate to a website
    browser.get('https://www.example.com')

    # Interact with the page using DOM selectors (much more precise than pixel-hunting)
    element = browser.find_element('id', 'some-element')
    element.click()

finally:
    # Always close the browser when done
    browser.quit()
```

For full details, consult the documentation in `agent_tools/doc/` directory.

### Extending Agent Tools

If you develop a useful utility, consider adding it to the `agent_tools/` directory for other agents to use. Maintain proper documentation and follow the existing structure.

## Critical Notes and Limitations

- **Bash tool timeout**: No blocking commands in bash tool (60s timeout bug, return to human if hit)
- **Mouse interaction**: Click on center of buttons, check window focus first
- **Bash syntax**: Never comment after `\` in multiline bash commands
- **App usage**: Prefer reopening apps from taskbar left vs launching new ones (right)
- **Self-reflection**: You can point Firefox at localhost:8503 to see your own UI
- **Error recovery**: If you encounter errors, report them to the human rather than trying random fixes
