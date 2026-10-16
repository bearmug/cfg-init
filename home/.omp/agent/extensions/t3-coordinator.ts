import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { execFileSync } from "node:child_process";
import { fstatSync, writeSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const FEED = Symbol.for("cfg-init.t3-subagent-feed");
const PROGRESS_FIELDS = ["id", "agent", "status", "description", "lastIntent", "currentTool",
	"currentToolStartMs", "toolCount", "durationMs"] as const;

const record = (value: unknown): Record<string, unknown> =>
	value && typeof value === "object" ? value as Record<string, unknown> : {};

// Relay (omp_acp.py) row feed: OMP stops sending `task` progress over ACP once the parent turn
// ends, but its subagent event bus keeps reporting background agents. Forward that bus to the
// relay's pipe. Claimed once per process (main session loads first); the variable is removed so
// tool subprocesses never inherit a stale descriptor number.
function forwardSubagents(pi: ExtensionAPI) {
	const globals = globalThis as Record<symbol, unknown>;
	const fd = Number(process.env.CFG_INIT_SUBAGENT_FD);
	delete process.env.CFG_INIT_SUBAGENT_FD;
	if (globals[FEED] || !Number.isInteger(fd) || fd < 3) return;
	try {
		if (!fstatSync(fd).isFIFO()) return;
	} catch {
		return;
	}
	globals[FEED] = true;
	const write = (event: Record<string, unknown>) => {
		const bytes = Buffer.from(JSON.stringify(event) + "\n");
		try {
			for (let sent = 0; sent < bytes.length;) sent += writeSync(fd, bytes, sent);
		} catch {
			// Relay gone; rows simply stop updating.
		}
	};
	pi.events.on("task:subagent:progress", (data: unknown) => {
		const payload = record(data), progress = record(payload.progress);
		write({ kind: "progress", parentToolCallId: payload.parentToolCallId,
			progress: Object.fromEntries(PROGRESS_FIELDS.map((field) => [field, progress[field]])) });
	});
	pi.events.on("task:subagent:lifecycle", (data: unknown) => {
		const payload = record(data);
		write({ kind: "lifecycle", parentToolCallId: payload.parentToolCallId, id: payload.id, status: payload.status });
	});
}

// Scoped to this factory/session; native child sessions receive fresh state.
// Native subagents (ctx.agent.kind "sub") share the coordinator's T3 thread, so the
// helper reports them as coordinators; they are always workers. Unknown kind fails closed.
export default function coordinator(pi: ExtensionAPI) {
	if (!process.env.T3_ACP_MCP_NODE) return;
	forwardSubagents(pi);
	let worker = true;
	let verified = false;
	const helper = join(homedir(), ".local/share/cfg-init-feedback/t3_policy.py");
	const restricted = (ctx?: { agent?: { kind?: string } }) => worker || !verified || ctx?.agent?.kind !== "main";
	pi.on("before_agent_start", (event, ctx) => {
		if (ctx?.agent?.kind !== "main") {
			worker = true;
			verified = false;
		} else try {
			const state = JSON.parse(execFileSync(process.env.FEEDBACK_PYTHON || "python3",
				[helper, "context"], { encoding: "utf8", timeout: 65000, maxBuffer: 64000 }));
			worker = state.worker;
			verified = true;
		} catch {
			worker = true;
			verified = false;
		}
		const rule = worker
			? "Bounded T3 worker: no user input/questions/dialogs, no agents/threads/feedback work. Return BLOCKED with missing decisions or permissions to coordinator. Never infer consent."
			: "T3 coordinator: delegate through ~/.local/share/cfg-init-feedback/t3_policy.py delegate with assignment JSON on stdin (visible T3 child task), or native task (runs inside this thread). Pick lane/agent = model tier (easy-luna, easy-haiku, mid-sonnet, high-sol, high-opus; default high-sol), thinking auto. All child questions return here.";
		return { systemPrompt: [...event.systemPrompt, rule] };
	});
	pi.on("before_subagent_spawn", (_event, ctx) => restricted(ctx) ? { block: true,
		reason: "T3 workers cannot spawn native descendants. Return to coordinator." } : undefined);
	pi.on("tool_call", (event, ctx) => {
		const path = typeof event.input.path === "string" ? event.input.path : "";
		const name = event.toolName;
		const operation = path.startsWith("xd://") ? path.slice(5) : name;
		const matches = (tool: string) => operation === tool || operation.endsWith("_" + tool);
		if (matches("delegate_task") || (name === "task" && restricted(ctx))) return { block: true,
			reason: "Use the coordinator's caller-bound t3_policy.py delegate helper; worker delegation is forbidden." };
		if (restricted(ctx)) {
			if (name === "ask" || matches("request_secret") || matches("create_threads") ||
				matches("t3_thread_launch") || matches("t3_thread_fork") || matches("schedule_task") ||
				matches("run_scheduled_task_now") || matches("t3_thread_send") ||
				matches("t3_pending_request_respond")) return { block: true,
				reason: "Child interaction/spawning disabled. Report BLOCKED to coordinator; never approve on its behalf." };
		}
	});
}
