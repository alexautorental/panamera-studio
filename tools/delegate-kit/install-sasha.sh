#!/usr/bin/env bash
# Install delegate-kit on the Mac with Sasha's overrides.
# Two subscriptions only: Claude Max (claude) + ChatGPT Pro (codex). No API keys.
# Idempotent; re-run after `git pull`. Usage:  bash tools/delegate-kit/install-sasha.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
DK_SRC="${DK_SRC:-$HOME/dev/delegate-kit}"
DK_HOME="${DELEGATE_KIT_HOME:-$HOME/.delegate-kit}"

say()  { printf '\n== %s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1  ($2)"; exit 1; }; }

say "preflight"
need git    "brew install git"
need jq     "brew install jq"
need node   "brew install node"
need claude "npm i -g @anthropic-ai/claude-code"
need codex  "npm i -g @openai/codex"
node -e 'const [M]=process.versions.node.split("."); if(+M<20){console.error("node >= 20 required");process.exit(1)}'
echo "claude: $(claude --version 2>/dev/null | head -1)"
echo "codex:  $(codex --version 2>/dev/null | head -1)"

say "delegate-kit source -> $DK_SRC"
if [ -d "$DK_SRC/.git" ]; then git -C "$DK_SRC" pull --ff-only; else git clone https://github.com/tomastaker/delegate-kit "$DK_SRC"; fi

say "symlinks: ~/.agents/skills, ~/.claude/skills, ~/.codex/skills"
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills" "$HOME/.codex/skills"
ln -sfn "$DK_SRC/skills/delegate-kit" "$HOME/.agents/skills/delegate-kit"
ln -sfn "$HOME/.agents/skills/delegate-kit" "$HOME/.claude/skills/delegate-kit"
ln -sfn "$HOME/.agents/skills/delegate-kit" "$HOME/.codex/skills/delegate-kit"

say "native roles + safety gate (delegate-kit's installer backs up settings and shows the diff)"
bash "$DK_SRC/skills/delegate-kit/hooks/install.sh"

say "Sasha overrides -> $DK_HOME/config.json"
mkdir -p "$DK_HOME"
[ -f "$DK_HOME/config.json" ] && cp "$DK_HOME/config.json" "$DK_HOME/config.json.bak.$(date +%Y%m%d-%H%M%S)"
cp "$HERE/config.sasha.json" "$DK_HOME/config.json"

say "extra role: dk-ux-reviewer (Opus, mobile-first) -> ~/.claude/agents"
mkdir -p "$HOME/.claude/agents"
sed 's/^name: ux-reviewer$/name: dk-ux-reviewer/' "$REPO_ROOT/.claude/agents/ux-reviewer.md" > "$HOME/.claude/agents/dk-ux-reviewer.md"

say "PATH for agent-run / agent-wt"
LINE='export PATH="$HOME/.agents/skills/delegate-kit/scripts:$PATH"'
for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
  if [ -f "$rc" ] && ! grep -qF "$LINE" "$rc"; then printf '\n%s\n' "$LINE" >> "$rc"; fi
done
export PATH="$HOME/.agents/skills/delegate-kit/scripts:$PATH"

say "trigger line in ~/.claude/CLAUDE.md"
TRIG='Before repository work described in prose or spanning several modules, apply delegate-kit with the sasha-mode rules from the orchestrate skill; a DIRECT verdict needs no announcement.'
mkdir -p "$HOME/.claude"; touch "$HOME/.claude/CLAUDE.md"
grep -qF "apply delegate-kit" "$HOME/.claude/CLAUDE.md" || printf '\n%s\n' "$TRIG" >> "$HOME/.claude/CLAUDE.md"

say "verify: which models Codex exposes under this login"
if [ -f "$HOME/.codex/models_cache.json" ]; then
  jq -r '.. | .slug? // empty' "$HOME/.codex/models_cache.json" 2>/dev/null | sort -u | sed 's/^/  model: /' || true
else
  echo "  ~/.codex/models_cache.json not found yet (run codex once interactively)"
fi

say "ping gpt-6-astra (read-only, tiny prompt)"
if codex exec --skip-git-repo-check -s read-only -m gpt-6-astra -c 'model_reasoning_effort="low"' \
     'Reply with exactly: ASTRA-OK' 2>/dev/null | grep -q 'ASTRA-OK'; then
  echo "  gpt-6-astra: OK"
else
  echo "  gpt-6-astra: not available under this login/version -> falling back to gpt-5.6-sol in config"
  jq '.roles |= with_entries(.value.codex[0] = "gpt-5.6-sol")' "$DK_HOME/config.json" > "$DK_HOME/config.json.tmp" \
    && mv "$DK_HOME/config.json.tmp" "$DK_HOME/config.json"
  if codex exec --skip-git-repo-check -s read-only -m gpt-5.6-sol -c 'model_reasoning_effort="low"' \
       'Reply with exactly: SOL-OK' 2>/dev/null | grep -q 'SOL-OK'; then
    echo "  gpt-5.6-sol: OK"
  else
    echo "  gpt-5.6-sol: FAILED -> run 'codex login' and re-run this script"
  fi
fi

say "effective role table"
agent-run preset | head -40

say "done. Restart claude/codex sessions."
echo "Phone-driven session on this Mac:  cd <repo> && claude   ->   /remote-control"
