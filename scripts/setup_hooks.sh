#!/usr/bin/env bash
# Install git pre-push hook for AI log submission (POSIX / Git Bash).
# Run once after cloning: bash scripts/setup_hooks.sh
set -e

HOOK_FILE=".git/hooks/pre-push"
BACKUP_HOOK=".git/hooks/pre-push.before-ai-log"

# Preserve an existing hook (for example Git LFS). The generated dispatcher
# runs it first, so its exit status continues to protect the push.
if [ -f "$HOOK_FILE" ] && ! grep -q 'AI log pre-push dispatcher' "$HOOK_FILE"; then
  cp "$HOOK_FILE" "$BACKUP_HOOK"
  chmod +x "$BACKUP_HOOK"
fi

cat > "$HOOK_FILE" <<'EOF'
#!/usr/bin/env bash
# AI log pre-push dispatcher. It preserves the pre-existing hook, then sweeps
# recent Antigravity / Gemini prompts and submits all pending AI logs.
# Uses the cross-platform Python launcher so it works whether the user
# has python3, python, or only the `py` launcher (Windows).
set -e

if [ -x .git/hooks/pre-push.before-ai-log ]; then
  .git/hooks/pre-push.before-ai-log "$@"
fi

bash scripts/_pyrun.sh scripts/log_antigravity.py --auto || true
bash scripts/_pyrun.sh scripts/submit_log.py || true
EOF

chmod +x "$HOOK_FILE"
chmod +x scripts/_pyrun.sh 2>/dev/null || true
echo "[ai-log] Git pre-push hook installed."

mkdir -p .ai-log
touch .ai-log/.gitkeep

echo "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."
