# Install git pre-push hook for AI log submission (Windows PowerShell).
# Run once after cloning: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1

$ErrorActionPreference = 'Stop'

$HookFile = '.git/hooks/pre-push'
$BackupHook = '.git/hooks/pre-push.before-ai-log'

if ((Test-Path $HookFile) -and -not (Select-String -Path $HookFile -Pattern 'AI log pre-push dispatcher' -Quiet)) {
    Copy-Item -Path $HookFile -Destination $BackupHook -Force
}

# Git on Windows runs hooks via Git Bash, so the hook body must be bash.
$HookBody = @'
#!/usr/bin/env bash
# AI log pre-push dispatcher. It preserves the pre-existing hook, then sweeps
# recent Antigravity / Gemini prompts and submits all pending AI logs.
set -e
if [ -x .git/hooks/pre-push.before-ai-log ]; then
  .git/hooks/pre-push.before-ai-log "$@"
fi
bash scripts/_pyrun.sh scripts/log_antigravity.py --auto || true
bash scripts/_pyrun.sh scripts/submit_log.py || true
'@

Set-Content -Path $HookFile -Value $HookBody -Encoding UTF8 -NoNewline
Write-Host "[ai-log] Git pre-push hook installed."

if (-not (Test-Path .ai-log)) { New-Item -ItemType Directory -Path .ai-log | Out-Null }
if (-not (Test-Path .ai-log/.gitkeep)) { New-Item -ItemType File -Path .ai-log/.gitkeep | Out-Null }

Write-Host "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."
