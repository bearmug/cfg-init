import { appendFile, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { findScopedSettings } from "@oh-my-pi/pi-coding-agent/config/settings";
import { cfgRetryFallbackChains } from "@oh-my-pi/pi-coding-agent/session/settings";
import { hasNativeJudge, resolveJudge, type JudgmentUsage } from "@oh-my-pi/pi-coding-agent/judgment";
import type { ExtensionAPI, ExtensionCommandContext } from "@oh-my-pi/pi-coding-agent";
import type { JudgmentState, Questions } from "@oh-my-pi/pi-ai";

interface Fixture {
  id: string;
  state: JudgmentState;
  questions: Questions;
}

interface LocalEndpoint {
  provider: string;
  id: string;
  baseUrl: string;
  contextWindow: number;
  responseModel?: string;
}

// Explicit extension: omp -p /decision-eval --no-session --no-extensions -e ./evaluate.ts
// Inputs are public synthetic fixtures. No production role or fallback is changed.
export default function (pi: ExtensionAPI) {
  const locals: LocalEndpoint[] = JSON.parse(process.env.OMP_EVAL_LOCAL_ENDPOINTS || "[]");
  for (const local of locals) {
    const url = new URL(local.baseUrl);
    if (url.hostname !== "127.0.0.1" && url.hostname !== "localhost") {
      throw new Error("Local evaluation endpoints must bind to loopback");
    }
    pi.registerProvider(local.provider, {
      baseUrl: local.baseUrl,
      api: "typesafe",
      apiKey: "local-evaluation-only",
      models: [{ id: local.id, name: local.id, reasoning: false, input: ["text"],
        contextWindow: local.contextWindow, maxTokens: 4096,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } }],
    });
  }
  pi.registerCommand("decision-eval", {
    description: "Evaluate exact judge selectors on held-out synthetic decisions",
    handler: async (_args: string, ctx: ExtensionCommandContext) => {
      const fixturePath = resolve(process.env.OMP_EVAL_FIXTURES || "fixtures.jsonl");
      const outputPath = resolve(process.env.OMP_EVAL_OUTPUT || "results.jsonl");
      if (fixturePath === outputPath) throw new Error("Output must not overwrite fixtures");
      const fixtures: Fixture[] = (await readFile(fixturePath, "utf8")).trim().split("\n").map((line: string) => JSON.parse(line));
      if (new Set(fixtures.map(row => row.id)).size !== fixtures.length) throw new Error("Duplicate fixture ids");
      const selectors = (process.env.OMP_EVAL_MODELS || "typesafe/jev-latest,openai-codex/gpt-6-luna").split(",");
      const concurrency = Number(process.env.OMP_EVAL_CONCURRENCY || 3);
      const timeoutMs = Number(process.env.OMP_EVAL_TIMEOUT_MS || 30000);
      if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 8 || timeoutMs < 1) {
        throw new Error("Invalid concurrency or timeout");
      }
      const base = findScopedSettings("\0decision-eval");
      if (!base) throw new Error("Host settings unavailable");
      const original = { roles: base.getModelRoles(), fallbacks: cfgRetryFallbackChains.get(base) };
      await writeFile(outputPath, "");
      let writes = Promise.resolve();
      for (const selector of selectors) {
        const settings = await base.cloneForCwd(base.getCwd());
        settings.overrideModelRoles({ ...original.roles, judge: selector });
        cfgRetryFallbackChains.override(settings, { ...original.fallbacks, judge: [] });
        const native = hasNativeJudge(settings, ctx.modelRegistry);
        let next = 0;
        await Promise.all(Array.from({ length: concurrency }, async () => {
          while (next < fixtures.length) {
            const fixture = fixtures[next++];
            const attempts: unknown[] = [];
            const judge = resolveJudge({ settings, registry: ctx.modelRegistry, onUsage: (usage: JudgmentUsage) => attempts.push(usage) });
            const started = performance.now();
            let row;
            try {
              const result = await judge.judge({ state: fixture.state, questions: fixture.questions },
                { signal: AbortSignal.timeout(timeoutMs) });
              const [provider, ...id] = selector.split("/");
              const local = locals.find(endpoint => `${endpoint.provider}/${endpoint.id}` === selector);
              const expectedModel = local?.responseModel ?? id.join("/");
              if (result.provider !== provider || (selector !== "typesafe/jev-latest" && result.model !== expectedModel)) {
                throw new Error(`Unauthorized model substitution: ${result.provider}/${result.model}`);
              }
              row = { id: fixture.id, selector, model: result.model, provider: result.provider, api: result.api,
                native, answers: result.answers, usage: result.usage, attempts,
                elapsedMs: Math.round(performance.now() - started) };
            } catch (error) {
              row = { id: fixture.id, selector, native, error: String(error), attempts,
                elapsedMs: Math.round(performance.now() - started) };
            }
            writes = writes.then(() => appendFile(outputPath, `${JSON.stringify(row)}\n`));
            await writes;
            console.log(JSON.stringify({ id: row.id, selector, elapsedMs: row.elapsedMs, error: row.error }));
          }
        }));
      }
      await writes;
      if (JSON.stringify(base.getModelRoles()) !== JSON.stringify(original.roles) ||
          JSON.stringify(cfgRetryFallbackChains.get(base)) !== JSON.stringify(original.fallbacks)) {
        throw new Error("Production settings changed during evaluation");
      }
      console.log(JSON.stringify({ outputPath, fixtures: fixtures.length, selectors, productionSettingsUnchanged: true }));
    },
  });
}
