import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { randomUUID } from "node:crypto";

// Scoring happens outside the agent process. ACP ingress is handled by omp_acp.py.
export default function dissatisfaction(pi: ExtensionAPI) {
	const engine = join(homedir(), ".agents/skills/dissatisfaction/feedback.py");
	let config: Record<string, string> = {};
	try {
		config = pi.zod.record(pi.zod.string(), pi.zod.string()).parse(
			JSON.parse(readFileSync(join(homedir(), ".config/cfg-init-feedback/config.json"), "utf8")));
	} catch (error: unknown) {
		if (!(error instanceof Error && "code" in error && error.code === "ENOENT"))
			console.error("feedback config:", String(error));
	}
	const env = { ...config, ...process.env };
	const run = (args: string[], input?: unknown): Promise<string> => {
		const { promise, resolve, reject } = Promise.withResolvers<string>();
		const child = spawn(env.FEEDBACK_PYTHON || "python3", [engine, ...args], { env, stdio: ["pipe", "pipe", "pipe"] });
		let output = "", errors = "";
		child.stdout.on("data", chunk => { output = (output + chunk).slice(-64000); });
		child.stderr.on("data", chunk => { errors = (errors + chunk).slice(-2000); });
		child.on("error", reject);
		child.on("close", code => code === 0 ? resolve(output) : reject(new Error(errors || `feedback exited ${code}`)));
		child.stdin.end(input === undefined ? undefined : JSON.stringify(input));
		return promise;
	};
	pi.on("input", (event, ctx) => {
		if (env.FEEDBACK_DISABLED === "1" || event.source === "extension" || process.env.FEEDBACK_ACP === "1") return;
		const prompt = event.text.length > 8000 ? event.text.slice(0, 2000) + event.text.slice(-6000) : event.text;
		if (event.text.length > 8000) console.error("feedback scoring first 2000 and last 6000 characters of long prompt");
		void run(["submit"], { event_id: randomUUID(), session_id: ctx.sessionManager.getSessionId(),
			prompt, cwd: ctx.cwd }).catch(error => console.error("feedback enqueue:", String(error)));
	});
	pi.registerCommand("feedback", {
		description: "Show feedback queue, or /feedback resolve EVENT_ID ANSWER (approve to implement in a worktree)",
		handler: async (args, ctx) => {
			const match = args.match(/^resolve\s+(\S+)\s+([\s\S]+)$/);
			try {
				const output = await run(match ? ["resolve", match[1], match[2]] : ["status"]);
				pi.sendMessage({ customType: "dissatisfaction", content: output, display: true }, { triggerTurn: false });
			} catch (error: unknown) { ctx.ui.notify(String(error), "error"); }
		}
	});
}
