# about: OMP: Jev judge, compaction, TypeScript LSP, delegation policy (merged, not replaced)
. "$(dirname -- "$0")/../lib/cfg.sh"

need omp "run the packages component first"
need bun "run the packages component first"
bun add -g --silent typescript typescript-language-server@6.0.1
agent="$(omp config path)"
cfg omp-settings "$HOME_SRC/.omp/agent/config.yml" "$agent"
cfg lsp-server "$HOME_SRC/.omp/agent/lsp.json" "$agent/lsp.json" typescript-language-server \
	"$(command -v typescript-language-server)"
cfg section "$agent/APPEND_SYSTEM.md" "$HOME_SRC/.omp/agent/APPEND_SYSTEM.md"
for file in "$HOME_SRC"/.omp/agent/agents/*.md; do
	cfg put "$file" "$agent/agents/$(basename "$file")"
done
