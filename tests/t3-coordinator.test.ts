// Behavioral tests for the T3 coordinator guard. The policy helper is replaced through
// FEEDBACK_PYTHON with a stub that prints the context JSON (or fails) and logs each call.
import { afterAll, beforeEach, describe, expect, test } from "bun:test";
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { chmodSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import coordinator from "../home/.omp/agent/extensions/t3-coordinator.ts";

type Result = { block?: boolean; systemPrompt?: string[] } | undefined;
type Handler = (event: unknown, ctx?: unknown) => Result;
// The extension only calls `on`; a full ExtensionAPI is not constructible outside OMP.
const api = (on: (name: string, handler: Handler) => void) => ({ on }) as unknown as ExtensionAPI;

const dir = mkdtempSync(join(tmpdir(), "t3-coordinator-"));
const calls = join(dir, "calls");
const stub = join(dir, "helper");
writeFileSync(stub, `#!/bin/sh\necho call >> "${calls}"\n[ -n "$STUB_CONTEXT" ] || exit 1\nprintf '%s' "$STUB_CONTEXT"\n`);
chmodSync(stub, 0o755);
afterAll(() => rmSync(dir, { recursive: true, force: true }));

function load(helperWorker: boolean | null, kind?: string) {
	process.env.T3_ACP_MCP_NODE = "bridge";
	process.env.FEEDBACK_PYTHON = stub;
	process.env.STUB_CONTEXT = helperWorker === null ? "" : JSON.stringify({ worker: helperWorker });
	const handlers: Record<string, Handler> = {};
	coordinator(api((name, handler) => { handlers[name] = handler; }));
	const ctx = kind === undefined ? {} : { agent: { kind } };
	const rule = handlers.before_agent_start({ systemPrompt: ["base"] }, ctx)?.systemPrompt?.at(-1) ?? "";
	const tool = (toolName: string, input: Record<string, unknown> = {}) =>
		handlers.tool_call({ toolName, input }, ctx)?.block === true;
	const spawnBlocked = handlers.before_subagent_spawn({ agent: "task" }, ctx)?.block === true;
	return { rule, tool, spawnBlocked };
}

function helperCalls() {
	try { return readFileSync(calls, "utf8").split("\n").filter(Boolean).length; } catch { return 0; }
}

beforeEach(() => rmSync(calls, { force: true }));

describe("t3-coordinator", () => {
	test("verified main coordinator may spawn natively and interact", () => {
		const s = load(false, "main");
		expect(s.rule).toStartWith("T3 coordinator:");
		expect(s.spawnBlocked).toBe(false);
		expect(s.tool("task")).toBe(false);
		expect(s.tool("ask")).toBe(false);
		expect(s.tool("read", { path: "xd://mcp__t3_code_t3_thread_launch" })).toBe(false);
	});

	test("native subagent is a worker even when the helper reports the coordinator thread", () => {
		const s = load(false, "sub");
		expect(helperCalls()).toBe(0);
		expect(s.rule).toStartWith("Bounded T3 worker:");
		expect(s.spawnBlocked).toBe(true);
		for (const name of ["task", "ask"]) expect(s.tool(name)).toBe(true);
		for (const device of ["mcp__t3_code_request_secret", "mcp__t3_code_t3_thread_send", "mcp__t3_code_schedule_task"])
			expect(s.tool("write", { path: `xd://${device}` })).toBe(true);
	});

	test("missing agent kind, helper failure and T3 workers fail closed", () => {
		for (const s of [load(false), load(null, "main"), load(true, "main")]) {
			expect(s.rule).toStartWith("Bounded T3 worker:");
			expect(s.spawnBlocked).toBe(true);
			expect(s.tool("task")).toBe(true);
			expect(s.tool("ask")).toBe(true);
		}
	});

	test("direct delegate_task is blocked even for the coordinator", () => {
		const s = load(false, "main");
		expect(s.tool("write", { path: "xd://mcp__t3_code_delegate_task" })).toBe(true);
		expect(s.tool("mcp__t3_code__delegate_task")).toBe(true);
	});

	test("ordinary tools stay allowed for workers", () => {
		const s = load(true, "main");
		expect(s.tool("bash")).toBe(false);
		expect(s.tool("read", { path: "README.md" })).toBe(false);
	});

	test("outside T3 the extension registers nothing", () => {
		delete process.env.T3_ACP_MCP_NODE;
		const handlers: string[] = [];
		coordinator(api(name => { handlers.push(name); }));
		expect(handlers).toEqual([]);
	});
});
