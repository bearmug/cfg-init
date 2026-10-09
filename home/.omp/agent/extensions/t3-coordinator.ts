import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { execFileSync } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";

// Scoped to this factory/session; native child sessions receive fresh state.
export default function coordinator(pi: ExtensionAPI) {
	if (!process.env.T3_ACP_MCP_NODE) return;
	let worker = true;
	let verified = false;
	const helper = join(homedir(), ".local/share/cfg-init-feedback/t3_policy.py");
	pi.on("before_agent_start", event => {
		try {
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
			: "T3 coordinator: delegate through ~/.local/share/cfg-init-feedback/t3_policy.py delegate with assignment JSON on stdin. Default OMP Sol6.1 auto; economy Luna only deliberately. All child questions return here. No native task/eval spawning in T3.";
		return { systemPrompt: [...event.systemPrompt, rule] };
	});
	pi.on("before_subagent_spawn", () => ({ block: true,
		reason: "T3 uses app-owned coordinator delegation, not hidden native descendants. Return to coordinator." }));
	pi.on("tool_call", event => {
		const path = typeof event.input.path === "string" ? event.input.path : "";
		const name = event.toolName;
		const operation = path.startsWith("xd://") ? path.slice(5) : name;
		const matches = (tool: string) => operation === tool || operation.endsWith("_" + tool);
		if (matches("delegate_task") || name === "task") return { block: true,
			reason: "Use the coordinator's caller-bound t3_policy.py delegate helper; worker delegation is forbidden." };
		if (worker || !verified) {
			if (name === "ask" || matches("request_secret") || matches("create_threads") ||
				matches("t3_thread_launch") || matches("t3_thread_fork") || matches("schedule_task") ||
				matches("run_scheduled_task_now") || matches("t3_thread_send") ||
				matches("t3_pending_request_respond")) return { block: true,
				reason: "Child interaction/spawning disabled. Report BLOCKED to coordinator; never approve on its behalf." };
		}
	});
}
