#!/usr/bin/env python3
"""chat-sync: автоматический общий журнал чатов Claude Code и Codex.

Сканирует локальные транскрипты обоих ассистентов, рендерит новые/изменённые
сессии в Markdown внутри git-журнала (~/ChatJournal по умолчанию), обновляет
INDEX.md и пушит в приватный репозиторий, если он настроен. Запускается
фоново (launchd/cron) — руками ничего делать не нужно.

Только стандартная библиотека Python 3. Настройки: ~/.chat-sync/config.json.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path.home() / ".chat-sync" / "config.json"

DEFAULTS = {
    "journal_dir": str(Path.home() / "ChatJournal"),
    "remote": "",  # URL ПРИВАТНОГО git-репозитория для синхронизации между маками
    "sources": {
        "claude": [str(Path.home() / ".claude" / "projects")],
        "codex": [
            str(Path.home() / ".codex" / "sessions"),
            str(Path.home() / ".codex" / "archived_sessions"),
        ],
    },
    "max_message_chars": 4000,
}

SKIP_PREFIXES = (
    "<system-reminder", "[SYSTEM NOTIFICATION", "<local-command",
    "<command-name", "<task-notification", "Caveat:", "<command-message",
)


def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            user_cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            for k, v in user_cfg.items():
                cfg[k] = v
        except (json.JSONDecodeError, OSError) as e:
            print(f"warning: cannot read {CONFIG_PATH}: {e}", file=sys.stderr)
    return cfg


def collect_text(content, max_chars):
    """content: строка или список блоков; вернуть только человеческий текст."""
    if isinstance(content, str):
        return content.strip()
    parts = []
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") in ("text", "input_text", "output_text"):
                t = (block.get("text") or "").strip()
                if t:
                    parts.append(t)
    text = "\n\n".join(parts).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n_…сообщение обрезано…_"
    return text


def find_messages(obj, out, max_chars):
    """Рекурсивно ищет словари с role+content (форматы Claude и Codex различаются)."""
    if isinstance(obj, dict):
        role = obj.get("role")
        if role in ("user", "assistant") and "content" in obj:
            text = collect_text(obj["content"], max_chars)
            text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text,
                          flags=re.S).strip()
            if text and not text.startswith(SKIP_PREFIXES):
                out.append((role, text))
            return
        for v in obj.values():
            find_messages(v, out, max_chars)
    elif isinstance(obj, list):
        for v in obj:
            find_messages(v, out, max_chars)


def render_session(src: Path, tool: str, max_chars: int):
    """Вернуть (title, markdown) или None, если человеческих сообщений нет."""
    messages = []
    try:
        with src.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                find_messages(rec, messages, max_chars)
    except OSError as e:
        print(f"warning: cannot read {src}: {e}", file=sys.stderr)
        return None
    # убрать подряд идущие дубликаты
    deduped = []
    for m in messages:
        if not deduped or deduped[-1] != m:
            deduped.append(m)
    if not any(r == "user" for r, _ in deduped):
        return None
    first_user = next(t for r, t in deduped if r == "user")
    title = first_user.splitlines()[0][:80]
    stamp = datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    label = "Claude Code" if tool == "claude" else "Codex"
    lines = [f"# {title}", "",
             f"_Инструмент: **{label}** · файл: `{src.name}` · обновлено: {stamp}_",
             "", "---", ""]
    for role, text in deduped:
        who = "👤 Пользователь" if role == "user" else "🤖 Ассистент"
        lines.append(f"## {who}\n\n{text}\n")
        lines.append("---\n")
    return title, "\n".join(lines)


def rel_out_path(src: Path, tool: str, roots) -> Path:
    """Куда класть md внутри журнала: <tool>/<группа>/<имя>.md"""
    group = "misc"
    for root in roots:
        root = Path(root)
        try:
            rel = src.relative_to(root)
        except ValueError:
            continue
        parts = rel.parts[:-1]
        group = "-".join(parts).strip("-") or "misc"
        break
    group = re.sub(r"[^A-Za-z0-9._-]+", "-", group).strip("-") or "misc"
    return Path(tool) / group / (src.stem + ".md")


def run_git(journal: Path, *args, check=False):
    return subprocess.run(["git", "-C", str(journal), *args],
                          capture_output=True, text=True, check=check)


def ensure_repo(journal: Path, remote: str):
    journal.mkdir(parents=True, exist_ok=True)
    if not (journal / ".git").exists():
        run_git(journal, "init", "-q")
        run_git(journal, "config", "user.name", "chat-sync")
        run_git(journal, "config", "user.email", "chat-sync@local")
    gi = journal / ".gitignore"
    if not gi.exists():
        gi.write_text(".state.json\n", encoding="utf-8")
    if remote:
        r = run_git(journal, "remote", "get-url", "origin")
        if r.returncode != 0:
            run_git(journal, "remote", "add", "origin", remote)
        elif r.stdout.strip() != remote:
            run_git(journal, "remote", "set-url", "origin", remote)


def git_sync(journal: Path, remote: str, changed: int):
    run_git(journal, "add", "-A")
    if run_git(journal, "diff", "--cached", "--quiet").returncode == 0:
        return  # нечего коммитить
    run_git(journal, "commit", "-q", "-m", f"chat-sync: update {changed} session(s)")
    if not remote:
        return
    branch = run_git(journal, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
    run_git(journal, "pull", "--rebase", "-q", "origin", branch)
    for attempt in range(4):
        if run_git(journal, "push", "-q", "-u", "origin", branch).returncode == 0:
            return
        time.sleep(2 ** (attempt + 1))
    print("warning: git push failed; journal is saved locally and will sync later",
          file=sys.stderr)


def main():
    cfg = load_config()
    journal = Path(os.path.expanduser(cfg["journal_dir"]))
    remote = cfg.get("remote", "")
    max_chars = int(cfg.get("max_message_chars", 4000))
    ensure_repo(journal, remote)
    if remote:  # подтянуть свежее с другого мака до рендера
        branch = run_git(journal, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
        run_git(journal, "pull", "--rebase", "-q", "origin", branch)

    state_path = journal / ".state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}

    changed = 0
    for tool, roots in cfg["sources"].items():
        for root in roots:
            root_path = Path(os.path.expanduser(root))
            if not root_path.is_dir():
                continue
            for src in sorted(root_path.rglob("*.jsonl")):
                st = src.stat()
                key = str(src)
                prev = state.get(key)
                sig = [int(st.st_mtime), st.st_size]
                if prev and prev.get("sig") == sig:
                    continue
                rendered = render_session(src, tool, max_chars)
                entry = {"sig": sig, "tool": tool, "mtime": int(st.st_mtime)}
                if rendered:
                    title, md = rendered
                    rel = rel_out_path(src, tool, roots)
                    out = journal / rel
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(md, encoding="utf-8")
                    entry.update({"title": title, "path": str(rel)})
                    changed += 1
                state[key] = entry

    # индекс: свежие сверху
    rows = sorted((e for e in state.values() if e.get("path")),
                  key=lambda e: e["mtime"], reverse=True)
    lines = [
        "# Журнал чатов (Claude Code + Codex)", "",
        "_Обновляется автоматически службой chat-sync. Свежие сверху._", "",
        "| Когда | Инструмент | Чат |", "|---|---|---|",
    ]
    for e in rows:
        when = datetime.fromtimestamp(e["mtime"]).strftime("%Y-%m-%d %H:%M")
        label = "Claude" if e["tool"] == "claude" else "Codex"
        title = e.get("title", "(без названия)").replace("|", "\\|")
        lines.append(f"| {when} | {label} | [{title}]({e['path']}) |")
    (journal / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    git_sync(journal, remote, changed)
    print(f"chat-sync: {changed} session(s) updated, index has {len(rows)} entries")


if __name__ == "__main__":
    main()
