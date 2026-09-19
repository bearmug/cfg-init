# cfg-init
Bootstrap configurations set to speed-up dev setup process.

## Usage
Just run setup scripts for the tooling you need.

## Content
* Tooling
  * **zsh** and **oh-my-zsh** to use as a shell
  * **tmux** as terminal multiplexor
  * **git** as a default version control system
  * **docker-ce** + **docker-compose**
  * **gradle** as a build tool
  * **micro** - tiny console editor with languages support
* Development stacks
  * **JVM** JDK8 + JDK10 + switching toolkit

## Default configurations
### Git defaults
* located inside **.gitconfig** file
* github user configuration
* shortcuts/aliases introduction to reduce useless keyboard typing

### Gradle defaults
* located under **.gradle/** folder
* speed-up build using:
  * daemon to hung around, expecting next call
  * incubating **configure-on-demand** feature
  * turn on incubating **parallel-build** feature

### JDK defaults
* hasJDK8 and JDK11 under the hood
* JDK11 choosen by default
* switch could be done with **update-java-alternatives**

### OMP agent defaults
* located under **home/.omp/agent/**, applied with **cfg-tools-omp.sh**
* tuned for minimum spend: compaction at 280k/200k tokens, token usage +
  cache-miss markers visible, tool-result imaging on
* local **headroom** MCP server for on-demand context compression
  (`uv tool install --python 3.13 "headroom-ai[all]"`, served via stdio)
* trimmed background reviewer (low thinking, 1 note per update)

### Optional local model gate
* `cfg-tools-model-gate.sh` installs a small Bun proxy at `~/.local/share/model-gate/`.
* It is model-agnostic and forwards OpenAI-compatible `/v1` requests to `127.0.0.1:8080` by default.
* Set `MODEL_GATE_UPSTREAM`, `MODEL_GATE_PORT`, and `MODEL_GATE_LIMIT` for another local backend.
* It rejects immediately with HTTP 503 when macOS Low Power Mode is active or the backend is saturated; this lets OMP use its configured fallback without queueing.
* Bonsai 2 is the tested example/default model: subagents use it locally, with GPT-5.6 Luna as spillover.
* Start the installed proxy under a process supervisor (for example OMP `hub`), not as an unmanaged background shell.