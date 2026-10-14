# about: optional Bun proxy that fast-fails local model calls (503) on Low Power Mode or saturation
. "$(dirname -- "$0")/../lib/cfg.sh"

need bun "run the packages component first"
put .local/share/model-gate/model-gate-proxy.mjs
put .local/share/model-gate/omp-models.example.yml
log "run under a supervisor: bun ~/.local/share/model-gate/model-gate-proxy.mjs"
log "env: MODEL_GATE_UPSTREAM (default http://127.0.0.1:8080), MODEL_GATE_PORT (8090), MODEL_GATE_LIMIT"
log "OMP provider example: ~/.local/share/model-gate/omp-models.example.yml"
