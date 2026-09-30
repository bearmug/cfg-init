import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { findScopedSettings } from "@oh-my-pi/pi-coding-agent/config/settings";
import { cfgRetryFallbackChains } from "@oh-my-pi/pi-coding-agent/session/settings";
import { resolveJudge, type JudgmentUsage } from "@oh-my-pi/pi-coding-agent/judgment";
import type { ExtensionAPI, ExtensionCommandContext } from "@oh-my-pi/pi-coding-agent";

// Real SDK chain + native HTTP transport. Only the upstream HTTP service is synthetic.
// No real provider is disrupted and no production settings are written.
export default function (pi: ExtensionAPI) {
  pi.registerCommand("judge-failover", {
    description: "Exercise native judge failover with loopback fault injection",
    handler: async (_args: string, ctx: ExtensionCommandContext) => {
      const seen: string[] = [];
      const server = Bun.serve({
        hostname: "127.0.0.1", port: 0,
        async fetch(request: Request) {
          assert.equal(new URL(request.url).pathname, "/v1/systemone");
          const body = await request.json() as { model: string; state: string; questions: Record<string, unknown> };
          seen.push(body.model);
          if (body.model.startsWith("primary-")) {
            const fault = body.model.slice("primary-".length);
            if (fault === "timeout" || fault === "abort") {
              await Bun.sleep(fault === "timeout" ? 12000 : 1000);
            } else {
              return Response.json({ error: { message: `Injected HTTP ${fault}` } },
                { status: Number(fault), headers: { "Retry-After": "0" } });
            }
          }
          return Response.json({ model: body.model,
            answers: { destination: { type: "choice", choice: "safe", confidence: 0.9,
              probabilities: { safe: 0.9, unsafe: 0.1 } } },
            usage: { input_tokens: 20, output_tokens: 0 } });
        },
      });
      const provider = "omp-failover-fixture";
      const faults = ["401", "403", "429", "503", "timeout", "abort"];
      pi.registerProvider(provider, {
        baseUrl: server.url.origin, api: "typesafe", apiKey: "isolated-fault-fixture",
        models: faults.flatMap(fault => ["primary", "fallback"].map(role => ({
          id: `${role}-${fault}`, name: `${role}-${fault}`, reasoning: false, input: ["text" as const],
          contextWindow: 8192, maxTokens: 512,
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        }))),
      });
      const base = findScopedSettings("\0judge-failover");
      if (!base) throw new Error("Host settings unavailable");
      const original = { roles: base.getModelRoles(), fallbacks: cfgRetryFallbackChains.get(base) };
      const report: unknown[] = [];
      try {
        for (const fault of faults) {
          const settings = await base.cloneForCwd(base.getCwd());
          settings.overrideModelRoles({ ...original.roles, judge: `${provider}/primary-${fault}` });
          cfgRetryFallbackChains.override(settings,
            { ...original.fallbacks, judge: [`${provider}/fallback-${fault}`] });
          const attempts: unknown[] = [];
          const judge = resolveJudge({ settings, registry: ctx.modelRegistry, onUsage: (usage: JudgmentUsage) => attempts.push(usage) });
          const startIndex = seen.length;
          const started = performance.now();
          const controller = new AbortController();
          const timer = fault === "abort" ? setTimeout(() => controller.abort(new Error("fixture caller abort")), 100) : undefined;
          let result;
          let error;
          try {
            result = await judge.judge({ state: "A public synthetic decision.", questions: {
              destination: { type: "choice", instructions: "Select safe", criteria: { safe: "Safe", unsafe: "Unsafe" } },
            } }, { signal: controller.signal });
          } catch (caught) { error = String(caught); }
          finally { clearTimeout(timer); }
          const requests = seen.slice(startIndex);
          const shouldFallback = fault !== "timeout" && fault !== "abort";
          if (shouldFallback) {
            assert.equal(result?.model, `fallback-${fault}`, `${fault}: exact fallback must answer`);
            assert.equal(result?.answers.destination.choice, "safe");
            assert.equal(requests.includes(`fallback-${fault}`), true);
          } else {
            assert.ok(error, `${fault}: cancellation must propagate`);
            assert.equal(requests.includes(`fallback-${fault}`), false, "Cancellation must not launch fallback");
          }
          const row = { fault, requests, elapsedMs: Math.round(performance.now() - started),
            fallbackAnswered: shouldFallback, result, error, attempts };
          report.push(row);
          console.log(JSON.stringify(row));
        }
        assert.deepEqual(base.getModelRoles(), original.roles);
        assert.deepEqual(cfgRetryFallbackChains.get(base), original.fallbacks);
        const output = process.env.OMP_FAILOVER_OUTPUT || "/tmp/omp-judge-failover.json";
        await writeFile(output, JSON.stringify({ checks: report, productionSettingsUnchanged: true }, null, 2) + "\n");
        console.log(JSON.stringify({ output, checksPassed: report.length, productionSettingsUnchanged: true }));
      } finally {
        pi.unregisterProvider(provider);
        server.stop(true);
      }
    },
  });
}
