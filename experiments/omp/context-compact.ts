import { findScopedSettings } from "@oh-my-pi/pi-coding-agent/config/settings";
import { cfgCompactionExperimentalContextManagement } from "@oh-my-pi/pi-coding-agent/session/context-settings";
import type { ExtensionAPI, ExtensionCommandContext } from "@oh-my-pi/pi-coding-agent";

// A print-mode /compact prompt is ordinary text. This command calls the real host API.
// Use only with a disposable profile and --resume its synthetic baseline session.
export default function (pi: ExtensionAPI) {
  pi.registerCommand("ordinary-context-compact", {
    description: "Perform a real ordinary baseline compaction in an isolated profile",
    handler: async (_args: string, ctx: ExtensionCommandContext) => {
      const agentDir = process.env.PI_CODING_AGENT_DIR;
      if (!agentDir || !agentDir.startsWith("/tmp/")) {
        throw new Error("Set PI_CODING_AGENT_DIR to an isolated /tmp profile before running this experiment");
      }
      const settings = findScopedSettings("\0ordinary-context-compact");
      if (!settings || cfgCompactionExperimentalContextManagement.get(settings)) {
        throw new Error("Ordinary baseline must have experimental context management disabled");
      }
      let result: unknown;
      let failure: Error | undefined;
      await ctx.compact({
        mode: "soft", suppressContinuation: true,
        internalGuidance: "Preserve original requirements verbatim, decisions and rationale, exact evidence paths, unfinished work, forbidden actions, and completed work. Archive padding is not new work and can be omitted. Do not fabricate completion.",
        onComplete: (value: unknown) => { result = value; },
        onError: (error: Error) => { failure = error; },
      });
      if (failure) throw failure;
      if (!result) throw new Error("No compaction result; inspect the session journal before claiming success");
      console.log(JSON.stringify({ ordinaryCompaction: result, isolatedAgentDir: agentDir }));
    },
  });
}
