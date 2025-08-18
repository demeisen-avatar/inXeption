# inXeption — A Hybrid Evolver

Crafted by π, released 28 April 2025

A framework for human-AI collaborative software development with recursive self-improvement capabilities.

🙏 A big thankyou to [Naptha AI](https://naptha.ai/) for sponsoring this work. They provided funding and an Anthropic API key. Without this, this project would likely not exist! 👋 Mark & Richard, you are appreciated! 🚀

## Vision

**inXeption** is a (human + AI) Hybrid Evolver, allowing:
1. human + gen[k] build gen[k+1],
2. human + inXeption build arbitrary software.
(1) is the driver, (2) is the consequence. Most people will want (2). However this doc is focused on (1).

### Guiding principles
- Design so that Human and AI each play to their strengths and cover the weakness of the other.
- AI can {see / modify / run} itself and evolve to a next stable-point.
- Incremental transference of autonomy -- address pain points as they arise naturally.


## Overview

- L0 (Level 0) user (human, on hostbox) executes `build.sh` which builds the Docker image, baking a copy of the `gen[k]` code into the image.
- L0 user executes `run.sh` which runs a container from the image, mapping `$projroot/../` and the docker socket.
- L0 user points a browser-tab to the given url to interact with agent.
- The inXeption agent (AI, a.k.a. L1 user) is root-user of its own ubuntu docker container, where it can execute arbitrary code.
- Human + AI (L0 + L1) collaborate to build out a new feature. L1 can test.
- Since the gen[k] code is baked into the image, code-changes do not affect the L1's performance.
- L1 can also execute `build.sh` and `run.sh` to spin up an L2 user and interact with it, playing the part of the human.
- Once tested, L0 can ctrl+c the running run.sh and re-run run.sh on the new image.
- This allows the human and `gen[k]` agent to perform a complete deployment cycle to `gen[k+1]`.


## Notes
- You'll need an Anthropic API key
- If you want it to do AI web-searches you'll also need an OpenAI API key
- You'll need a brain configured to support Western Scientific Method / Critical Thinking; i.e. you'll need your wits about you.


## Using inXeption for arbitrary software development

Most humans will only want this.

```bash
$ cd /path/to/parent_dir/
$ git clone project_I_want_to_work_on
$ git clone inXeption
$ cd inXeption/
$ ./build.sh --image foo
$ ./run.sh --image foo --container cfoo  # <-- spins up ubuntu container with access to parent_dir/
# Now point your browser at http://localhost:8082 and interact with the agent and/or the ubuntu container's desktop
```


## Workflow -- Using inXeption to evolve inXeption

I'll present a window into what working with inXeption looks like for me. YMMV.

- Run, as above.

- You as the human pilot need to identify a point of weakness/improvement. If you just ask the agent, it will end up bloating and tangling itself. There's a reason I'm working on a HYBRID evolver and not a SELF evolver. The LLM core isn't (yet) capable to support self-evolution. More on that later...

- Get the agent to dump out tests/README.md and run an appropriate loop test (or create and run a new one) -- using Test-Driven-Development is key to this kind of work.

- If it's a bugfix, work with the agent to identify the root cause. Your human dev-fu is critical here, as the LLM is weak here. It is prone to misdiagnosing, jumping to wrong conclusions and treating a HYPOTHESIS as a FACT.

- Work with the agent to construct a solution path. Challenge it on its thought process and decisions. Remember, today's LLMs lack the discipline of a software engineer -- you'll have to provide that rigour yourself.

- Once you're happy, get it to implement, and review the implementation. I often keep VSCode open, pointed at the $projroot/, so I can review.

- Once you're happy, get it to create a feature branch, commit its implementation, then go about trying to get it to work.

- Having that commit is SUPER important, since the agent's idea of "fixing code" involves charging around like a bull in a china shop.

- If it's a mid-to-large task, you'll probably want to get the agent to write a handoff doc into /tmp/ and spin up a fresh browser-tab and work with a fresh agent to get it working. Yes -- you can have multiple tabs open. Each tab represents a separate independent agent. Sometimes for a major task I get through several subagents over several days.

- The agent has its loop-test to iterate over (TDD wins!) to get the test to pass. Keep an eye on it and make sure it's not buckling the project-code to make the test pass.

- If it needs to look stuff up from the internet, add an OpenAI API key to your .env and tell it to inspect doc/web_ai.md. Now it will be able to use OpenAI's web-ai capability and pull stuff off the internet. Super-useful for obscure stuff.

- Once it's gotten a solution, get another commit in NOW before it fucks it all up. Then challenge it to consider an OPTIMAL solution.

- Once you've got something decent committed, either try it out yourself or get the agent to do it.

  - Expand your browser tab's vnc Virtual Desktop, open the (kitty) terminal, and do `cd /host/inXeption` then `./dev_runner.sh` (don't let the agent use its bash-tool to do it since that tool nukes its bash process at the end of the interaction).

  - Either spin up Firefox in the Virtual Desktop and point it at localhost:8510, or point a browser tab on your hostbox at localhost:8509, and you can now interact with the agent running on the modified code.

- Once everything's looking healthy, you might want to `build.sh` a fresh docker image, `run.sh` it, point your browser at the url given, and play with the agent. You can do this from within the virtual-desktop (or you can get the agent to do it). This way the (old-code) (running) agent is still there to assist if you bump into issues.

- Once you're happy, get the agent to squash-merge the feature branch to main, terminate the running `run.sh` on your hostbox and do `build.sh` and `run.sh` again.

- You've now successfully hybrid-evolved from state [k] to state [k+1]. If you are a skilled pilot, you're converging towards an ideal information-space. 🚀


## Development path

I led AutoGPT for its first couple of months in 2022, leaving the project to focus on my own research.

In October 2024 I cloned Anthropic's [computer-use-demo](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo) and tweaked it, getting it to the point where I could apply this basic workflow. I've since performed over a hundred cycles to build inXeption into what it is today.

- I rewrote the AI tools (bash, edit, computer) and added a python tool
- I removed the API header that specifies the Anthropic tools and supplied the tool-schemas locally -- this gives me the flexibility to evolve the tools
- I monkey-patched streamlit to hook the "stop" button and decoupled the agent-loop from the UI
- I rewrote the agent-loop
- I hand-coded the API interface, removing a dep on Anthropic's Python API
- I decided to use an abstract "UI-element" structure as "single source of truth" for conversation, thus decoupling from Streamlit
- I used multiline YAML everywhere instead of JSON (never looked back from that one)
- I redesigned the Docker container, providing a pretty kitty terminal, setting the agent as root-user of its own container, providing a --gpu flag so it runs on a GPU-enabled box.
- I provided a `build.sh` and `run.sh` for building and running the container. `run.sh` maps the `$projroot/` and `$projroot/../` folders. Plus I pass the Docker socket thru. The result is that the agent can introspect its own codebase and access its own Docker runtime.
- I created a loop-test chassis in `tests/` for TDD. This is "AI-age TDD" where rather than tests checking for fixed conditions, the agent will run the test and compare the (verbose) output against an (english-prose) expectation (see `tests/loop_tests.yaml`). This is the future of (my) TDD.
- I created an `agent_tools/` folder -- currently it only has two things in it: a `web_ai.md` doc (agent reads it then can perform internet AI searches) and a browser-automation tooling (so it can control its firefox directly from Python, rather than fumbling around with injecting mouse/keyboard events and taking screenshots). I've found the former to be super-useful in certain tasks, haven't really played with the latter, but it's there!


## Notes on intelligence...

There's a fundamental question in the air in AI circles: Are our current architectures (backprop -> LLM) capable to extend to human/superhuman capability? Or are we "doing it wrong"?

Most awkward examples I can find:

1. One-shot learning. A playful child touching a hot-coal instantly learns never to do that thing again. It doesn't need 10k synthetic training examples or a sleep cycle. If your lottery ticket wins, or you're diagnosed with terminal cancer, you rebalance your entire reality-model upon a single piece of information.

2. Catastrophic forgetting. If you move from the UK to the USA you learn to drive on the other side of the road. When you return to the UK you "flip back" to left-hand-drive mode. There's minimal interference.

3. ARC-AGI -- a smart 8-year-old can solve an ARC grid-puzzle that will confound a SotA LLM that beats university graduates in their chosen domain. Why this disparity? There's something our brains are doing (dynamic {de/re}composition / reconceptualization / concept-formation) that LLMs are NOT and likely CANNOT.

We can fudge (1) with "In-Context Learning". But it's a fudge. (2) is awkward. We can play with LoRA adaptors etc. And we can surely improve (3) by training an LLM to operate optimally in the context of an agent-system (difference between an undisciplined mind and a disciplined mind; Western Scientific Method, etc.) just as brain tissue learns to adapt to serve the organism's architecture.

AFAICS backprop + Transformer gives us Artificial INTELLECT (whereby we may model a static distribution) but not Artificial INTELLIGENCE (ability to adapt to thrive in a changing environment). And we may need a radically new foundation to bridge the gap. Nobody wants to hear it, right? Sunk costs, "but we're nearly there -- it looks like a duck and quacks like a duck", etc.

BUT... regardless, we CAN design a tooling that leverages what we've GOT to push us towards where we WANT to get to.

Optimal solution path is likely THROUGH our current trajectory rather than tangential.

So, that's what I'm working on.


## Quick Start

NOTE: I've only tested inXeption on macOS and ubuntu (Windows people, YMMV)

### Prerequisites

- **Docker**: Docker Desktop for macOS/Windows or Docker Engine for Linux
   ```bash
   brew install --cask docker  # macOS
   ```

- **pulseaudio** (if you want sounds)
   ```bash
   brew install --cask pulseaudio  # macOS
   ```

- **API Keys**: An Anthropic API key, optionally an OpenAI API key (if you want the agent to do web-ai searches)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/demeisen/inXeption.git
   cd inXeption
   ```

2. **Configure environment**
   ```bash
   cp .env.template .env
   # Edit .env to add your ANTHROPIC_API_KEY

   cp .ports.template .ports
   # Default ports are fine for most users
   ```

3. **Build the Docker image**
   ```bash
   ./build.sh --image inxeption
   ```

4. **Run the container**
   ```bash
   ./run.sh --image inxeption --container inxeption
   ```

5. **Access the interface**

   Once running, the script will output URLs for different interfaces:
   ```
   - Combined interface: http://localhost:8082 <-- (BOTH) -- use this one!
   - Streamlit interface: http://localhost:8502  <-- agent-dialog only
   - Desktop view: http://localhost:6082/vnc.html  <-- Ubuntu Desktop only
   ```

   Open your browser and navigate to the combined interface URL.

   Try asking the agent to calculate sqrt(42) or take a screenshot or do `tree /host`. etc.


## Blueprint Documentation System

This is experimental. The idea here is blueprint-driven-development. Specify the goal+constraints and the AI can interpolate the code, using AI-TDD to ensure it works. I think this is where s/w dev is heading.

```bash
./scripts/blueprints.sh
```

This pulls out all "blueprint-marked" comments from all .sh .py .md files. I've put in these comments to give a basic overview/tut of the system. Probably could do with some work.


## Agent Tools

The `/host/agent_tools/` directory contains utilities that enhance the AI's capabilities:

- **Browser Automation**: Control Firefox programmatically using DOM selectors
  ```python
  from agent_tools.browser_automation import get_browser
  browser = get_browser()
  ```

- **Web Search**: Access web search capabilities for retrieving information
  (See documentation in `agent_tools/doc/web_ai.md`)


## Persistence

Each time you `run.sh`, you get a fresh container. The mapped `.persist/` folder maintains state across container restarts:

- Firefox profiles persist (bookmarks, history, cookies)
- Other tools can store persistent data here as needed

This enables continuity in development sessions, even when containers are rebuilt.


### Logging System

All system activity is logged in `.logs/` with a structured organization:

- **dev/**: Development server logs
- **prod/**: Production container logs
- **test/**: Test execution logs

Each environment maintains symlinks to the most recent logs, facilitating debugging.


## Contributing

inXeption uses git pre-commit hooks, to cope with some of the more egregious AI-code fails (e.g. wanton whitespace). Set them up with:

```bash
pre-commit install
```


## Learn More

The best way to learn more about inXeption is to interact with it. Once you have the system running, ask the AI assistant to explain its architecture, capabilities, or any specific components you're interested in.

For a deep dive into the architecture, run `./scripts/blueprints.sh`.

Another good starting point is to get the agent to `tree /host/` (which is mapped from L0's $projroot), dump out `build.sh` and `run.sh` and take it from there.

Another good starting point is to get the agent to dump out `tests/README.md`, run the first loop-test, and explain what's going on.
