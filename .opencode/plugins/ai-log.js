import { appendFile, mkdir } from "node:fs/promises"
import { join } from "node:path"

const MAX_PROMPT_LENGTH = 1000

function git(args, cwd) {
  try {
    const result = Bun.spawnSync(["git", ...args], {
      cwd,
      stdout: "pipe",
      stderr: "ignore",
    })
    return new TextDecoder().decode(result.stdout).trim()
  } catch {
    return ""
  }
}

function repositoryName(origin, cwd) {
  const value = origin || cwd.split("/").filter(Boolean).at(-1) || "unknown"
  return value.replace(/\/$/, "").split("/").at(-1).replace(/\.git$/, "")
}

function promptFromParts(parts) {
  return parts
    .filter((part) => part.type === "text" && !part.synthetic && !part.ignored)
    .map((part) => part.text)
    .join("\n")
    .trim()
}

export const AiLogPlugin = async ({ directory, worktree }) => {
  const cwd = worktree || directory

  return {
    "chat.message": async (input, output) => {
      const prompt = promptFromParts(output.parts)
      if (!prompt) return

      const message = output.message
      const timestamp = message.time?.created
        ? new Date(message.time.created).toISOString()
        : new Date().toISOString()
      const entry = {
        ts: timestamp,
        tool: "opencode",
        event: "UserPromptSubmit",
        entry_id: `opencode-${input.sessionID}-${message.id || input.messageID || Date.now()}`,
        session_id: input.sessionID,
        model: input.model
          ? `${input.model.providerID}/${input.model.modelID}`
          : `${message.model.providerID}/${message.model.modelID}`,
        repo: repositoryName(git(["remote", "get-url", "origin"], cwd), cwd),
        branch: git(["rev-parse", "--abbrev-ref", "HEAD"], cwd),
        commit: git(["rev-parse", "--short", "HEAD"], cwd),
        student:
          git(["config", "user.email"], cwd) ||
          process.env.USER ||
          process.env.USERNAME ||
          "unknown",
        prompt: prompt.slice(0, MAX_PROMPT_LENGTH),
        response_summary: "",
      }

      const logDirectory = process.env.AI_LOG_DIR || join(cwd, ".ai-log")
      await mkdir(logDirectory, { recursive: true })
      await appendFile(
        join(logDirectory, "session.jsonl"),
        `${JSON.stringify(entry)}\n`,
        "utf8",
      )
    },
  }
}
