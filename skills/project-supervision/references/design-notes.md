# Evidence and context budget

Sampled primary sources checked 2026-10-11; not community consensus.

| Evidence | Design consequence and limit |
|---|---|
| [Superpowers releases](https://github.com/obra/superpowers/blob/main/RELEASE-NOTES.md) | Adaptive what/why interviews, lean plans, fewer repeated check-ins/stalls. Maintainer reproductions, not independent benchmarks. No fixed interview or document ceremony. |
| [Pi creator's account](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/) | Inspectable context/artifact handoffs; opaque delegation concerns. Practitioner opinion; workers remain optional, not universally prohibited. |
| [OpenCode #22236](https://github.com/anomalyco/opencode/issues/22236), [OMP #4570](https://github.com/can1357/oh-my-pi/issues/4570) | Historical fixed duplication report and single-session child-context report with maintainer qualifications. Precise discovery/small briefs, not current-version defect claims. |
| [Anthropic experiment](https://www.anthropic.com/engineering/harness-design-long-running-apps) | Plausible apps had broken interactions; sprint machinery later removed. Keep actual-flow checks, not mandatory evaluator topology. |
| [Task-success/cost study](https://arxiv.org/abs/2602.11988v3), [efficiency study](https://arxiv.org/abs/2601.20404) | Different tasks/outcomes: no general success gain/higher inference cost versus lower runtime/output tokens with comparable completion. Neither establishes a blanket context-file policy. |

Our project failures exposed failed supervision, not just implementation defects.
The baseline/treatment probes in [scenarios](scenarios.md) found no efficacy gain.
Retain the intent/first-use/recovery contract; avoid generic agent instructions,
duplicate records, and permanent additions after every mishap. A real installed
first-use outcome, not these mocked decisions, must validate usefulness.

## Budget

Existing OMP payload: 6,443 bytes (~1,610 tokens), unchanged by this PR. Added global preprompt:
**0 bytes**. Reviewed core: 3,772 bytes (~939 tokens); discovery frontmatter:
166 bytes (~42 tokens), excluding harness wrappers. Estimates use characters/4,
not a vendor tokenizer.
First draft: 8,261 bytes; compared draft: 4,336 bytes. Templates/adapters load only
when needed; scenarios/design evidence are not routine context. Actual wrappers,
injection, and caching depend on the harness. Do not append the package to a
standing system prompt.
