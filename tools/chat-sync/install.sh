#!/bin/bash
# chat-sync installer (macOS / Linux).
# Использование:  bash install.sh [URL приватного git-репозитория для журнала]
# Ставит sync.py в ~/.chat-sync, фоновый запуск каждые 10 минут (launchd или cron)
# и добавляет обоим ассистентам (Claude Code, Codex) инструкцию читать журнал.
set -euo pipefail

REMOTE_URL="${1:-}"
BASE_DIR="$HOME/.chat-sync"
JOURNAL_DIR="$HOME/ChatJournal"
RAW_BASE="https://raw.githubusercontent.com/alexautorental/panamera-studio/claude/cloud-code-account-sharing-mp1em2/tools/chat-sync"
MARK_BEGIN="# >>> chat-sync >>>"
MARK_END="# <<< chat-sync <<<"

mkdir -p "$BASE_DIR"

# 1) sync.py: берём локальную копию, если запускаемся из репозитория, иначе качаем
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/sync.py" ]; then
  cp "$SCRIPT_DIR/sync.py" "$BASE_DIR/sync.py"
else
  curl -fsSL "$RAW_BASE/sync.py" -o "$BASE_DIR/sync.py"
fi
chmod +x "$BASE_DIR/sync.py"

# 2) конфиг (не перетираем существующий)
if [ ! -f "$BASE_DIR/config.json" ]; then
  cat > "$BASE_DIR/config.json" <<EOF
{
  "journal_dir": "$JOURNAL_DIR",
  "remote": "$REMOTE_URL"
}
EOF
  echo "config: $BASE_DIR/config.json"
elif [ -n "$REMOTE_URL" ]; then
  python3 - "$BASE_DIR/config.json" "$REMOTE_URL" <<'PY'
import json, sys
path, remote = sys.argv[1], sys.argv[2]
cfg = json.load(open(path))
cfg["remote"] = remote
json.dump(cfg, open(path, "w"), ensure_ascii=False, indent=2)
print("config: remote updated")
PY
fi

# 3) фоновый запуск каждые 10 минут
if command -v launchctl >/dev/null 2>&1; then
  PLIST="$HOME/Library/LaunchAgents/com.chat-sync.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.chat-sync</string>
  <key>ProgramArguments</key>
  <array><string>/usr/bin/python3</string><string>$BASE_DIR/sync.py</string></array>
  <key>StartInterval</key><integer>600</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$BASE_DIR/sync.log</string>
  <key>StandardErrorPath</key><string>$BASE_DIR/sync.log</string>
</dict></plist>
EOF
  launchctl unload "$PLIST" >/dev/null 2>&1 || true
  launchctl load "$PLIST"
  echo "launchd: com.chat-sync загружен (каждые 10 минут)"
else
  CRON_LINE="*/10 * * * * /usr/bin/env python3 $BASE_DIR/sync.py >> $BASE_DIR/sync.log 2>&1"
  ( crontab -l 2>/dev/null | grep -vF "$BASE_DIR/sync.py" ; echo "$CRON_LINE" ) | crontab -
  echo "cron: задание добавлено (каждые 10 минут)"
fi

# 4) инструкция для ассистентов: читать журнал в начале сессии
add_block() {
  local file="$1"
  mkdir -p "$(dirname "$file")"
  touch "$file"
  if ! grep -qF "$MARK_BEGIN" "$file"; then
    cat >> "$file" <<EOF

$MARK_BEGIN
## Общий журнал чатов (chat-sync)
В \`$JOURNAL_DIR/INDEX.md\` лежит автоматически обновляемый журнал всех недавних
локальных чатов и Claude Code, и Codex на этом компьютере (и на других маках
владельца). Если вопрос пользователя может продолжать недавнюю тему или
ссылается на «прошлый разговор» — сначала загляни в INDEX.md и открой
соответствующий файл сессии, чтобы восстановить контекст. Записывать туда
ничего не нужно — журнал ведёт фоновая служба.
$MARK_END
EOF
    echo "instructions: добавлено в $file"
  else
    echo "instructions: уже есть в $file"
  fi
}
add_block "$HOME/.claude/CLAUDE.md"
add_block "$HOME/.codex/AGENTS.md"

# 5) первый прогон
python3 "$BASE_DIR/sync.py" || true

echo
echo "Готово. Журнал: $JOURNAL_DIR (INDEX.md — оглавление)."
if [ -z "$REMOTE_URL" ]; then
  echo "ВНИМАНИЕ: удалённый репозиторий не задан — журнал живёт только на этом маке."
  echo "Чтобы синхронизировать между маками: создайте ПРИВАТНЫЙ репозиторий на GitHub"
  echo "и перезапустите: bash install.sh https://github.com/<вы>/chat-journal.git"
fi
