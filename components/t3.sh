# about: T3 Code: OMP ACP relay (omp-feedback), Sol/Luna delegation helper, worker guards
. "$(dirname -- "$0")/../lib/cfg.sh"

need python3
need omp "run the packages component first"
[ -f "$HOME/.agents/skills/dissatisfaction/feedback.py" ] || die "install the feedback component first (the relay submits prompts to it)"
for file in omp_acp.py t3_policy.py; do
	put ".local/share/cfg-init-feedback/$file"
done
put .omp/agent/extensions/t3-coordinator.ts
put .omp/agent/t3.yml

launcher="$HOME/.local/bin/omp-feedback"
mkdir -p "$HOME/.local/bin"
printf '#!/bin/sh\nexec %q %q "$@"\n' "$(command -v python3)" "$HOME/.local/share/cfg-init-feedback/omp_acp.py" > "$launcher.tmp"
chmod 755 "$launcher.tmp"
mv "$launcher.tmp" "$launcher"
log "T3 > Settings > OMP provider: commandPath $launcher, commandArgs [\"acp\"]"
