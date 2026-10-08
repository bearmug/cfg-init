import type { ExtensionAPI, ExtensionContext } from "@oh-my-pi/pi-coding-agent";
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { randomUUID } from "node:crypto";

type Proposal = {
	event_id: string; session_id: string; approval_id: string;
	state: string; summary: string; question: string;
};

// Screening and approved work run outside the main agent turn. ACP has its own adapter.
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
	const shown = new Set<string>();
	let presentations = Promise.resolve();
	const offer = (proposal: Proposal, ctx: ExtensionContext): Promise<void> => {
		if (!ctx.hasUI || proposal.state !== "needs_approval" ||
			proposal.session_id !== ctx.sessionManager.getSessionId()) return Promise.resolve();
		const key = `${proposal.event_id}:${proposal.approval_id}`;
		if (shown.has(key)) return Promise.resolve();
		shown.add(key);
		presentations = presentations.catch(() => {}).then(async () => {
			pi.sendMessage({ customType: "feedback-proposal", display: true,
				content: `${proposal.summary}\n\nYes: a separate agent works only on this improvement in a Git worktree and returns changes for review. No: decline. Nothing is installed, pushed, or merged.` },
				{ triggerTurn: false });
			const choice = await ctx.ui.select(proposal.question, ["Yes — work on it separately", "No — decline"]);
			if (choice === undefined) { shown.delete(key); return; }
			const decision = choice.startsWith("Yes") ? "yes" : "no";
			await run(["decide", proposal.event_id, decision, "--approval-id", proposal.approval_id]);
			ctx.ui.notify(decision === "yes" ? "Separate improvement agent queued; the main conversation can continue." : "Improvement declined.", "info");
		}).catch(error => { shown.delete(key); ctx.ui.notify(`Feedback approval: ${String(error)}`, "error"); });
		return presentations;
	};
	pi.on("input", (event, ctx) => {
		if (env.FEEDBACK_DISABLED === "1" || event.source === "extension" || process.env.FEEDBACK_ACP === "1") return;
		const prompt = event.text.length > 8000 ? event.text.slice(0, 2000) + event.text.slice(-6000) : event.text;
		if (event.text.length > 8000) console.error("feedback scoring first 2000 and last 6000 characters of long prompt");
		void run(["submit", "--wait"], { event_id: randomUUID(), session_id: ctx.sessionManager.getSessionId(),
			prompt, cwd: ctx.cwd }).then(output => offer(JSON.parse(output), ctx))
			.catch(error => console.error("feedback enqueue:", String(error)));
	});
	pi.registerCommand("feedback", {
		description: "Show feedback and explained Yes/No improvement choices; resolve clarification or review answers",
		handler: async (args, ctx) => {
			const match = args.match(/^resolve\s+(\S+)\s+([\s\S]+)$/);
			try {
				const output = await run(match ? ["resolve", match[1], match[2]] : ["status"]);
				if (match) void run(["worker"]).then(() => run(["status", match[1]]))
					.then(result => offer(JSON.parse(result), ctx))
					.catch(error => ctx.ui.notify(`Feedback follow-up: ${String(error)}`, "error"));
				if (!match) for (const proposal of JSON.parse(output).events ?? []) {
					shown.delete(`${proposal.event_id}:${proposal.approval_id}`);
					await offer(proposal, ctx);
				}
				pi.sendMessage({ customType: "dissatisfaction", content: output, display: true }, { triggerTurn: false });
			} catch (error: unknown) { ctx.ui.notify(String(error), "error"); }
		}
	});
}
