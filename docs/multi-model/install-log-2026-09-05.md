# Установка delegate-kit + sasha-mode на MacBook — лог 2026-09-05

Исполнитель: Claude (Fable 5), автономная фоновая сессия на MacBook-Pro-Alex.
Цель: поставить delegate-kit с надстройкой sasha-mode и доказать живую связку
Claude ↔ GPT (Codex CLI по подписке ChatGPT Pro).

## Итог одной строкой

Роутинг и скрипты delegate-kit работают, `gpt-6-astra` под логином есть, но живой
вызов GPT не прошёл: канал `chatgpt.com` с Мака в этот вечер был сетево мёртв, и
установка хуков в `~/.claude/settings.json` заблокирована классификатором разрешений —
её надо сделать руками одной командой.

## Шаги

| Шаг | Статус | Ключевой вывод |
|---|---|---|
| 1. Preflight | ✅ | macOS 26.6.2, node v22.23.1, jq 1.7.1, git 2.50.1, claude 2.1.251, codex-cli 0.153.1; `codex login status` → «Logged in using ChatGPT» |
| 2. Репозиторий | ✅ | Клон в `~/dev/panamera-studio`, ветка `claude/multi-model-orchestration-review-pzkt08` (HEAD c51d45a), up to date |
| 3a. Клон delegate-kit | ✅ | `tomastaker/delegate-kit` → `~/dev/delegate-kit` |
| 3b. `install-sasha.sh` | ⛔ | **Не выполнен**: классификатор разрешений Claude Code трижды заблокировал запуск (скрипт правит `~/.claude/settings.json` — PreToolUse-hook на каждый Bash, `CLAUDE.md`, `~/.zshrc`, `~/.codex/config.toml`). Обходить запрет поштучным повторением тех же правок не стал. `/tmp/dk-install.log` поэтому пуст |
| 3c. Конфиг sasha-mode | ✅ | `config.sasha.json` → `~/.delegate-kit/config.json` (файла раньше не было, бэкап не требовался) |
| 4a. `agent-run preset` | ✅ | preset `auto`; роли из sasha-конфига: reviewer `opus xhigh` / `gpt-6-astra xhigh`, planner/verifier/review-lead `fable max` / `gpt-6-astra xhigh` |
| 4b. route reviewer | ✅ | слот A → `codex`, `independent: true`, `gpt-6-astra xhigh`, dispatch external, read-only |
| 4c. route implementer | ✅ | `codex` / `gpt-6-astra high` — фолбэк на `gpt-5.6-sol` не понадобился |
| 4d. Модели Codex | ✅ | `models_cache.json`: codex-auto-review, gpt-5.3-codex-spark, gpt-5.4-mini, gpt-5.5, gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra, **gpt-6-astra**, gpt-reserve |
| 4e. `claude -p` флаги | ✅ | `--allowedTools` и `--disallowedTools` присутствуют |
| 4f. Symlinks/agents | ⛔ | `~/.claude/skills/delegate-kit` и `~/.claude/agents/` не существуют — следствие шага 3b |
| 5. Дымовой тест GPT-ревью | ❌ | Два прогона (`20260905155309-g2fg`, `20260905161349-uhd3`) убиты предохранителем 20 мин: codex-воркер не достучался до `chatgpt.com`. Findings — нет. Дерево репо не тронуто (read-only подтверждён). `~/.delegate-kit/ledger.jsonl` не создан (пишется только по завершённым прогонам) |
| 6. Диагностика канала | ✅ | Туннель utun1 в fake-IP режиме (все домены → 198.20.0.0/24). Системный резолвер не отдаёт именно `chatgpt.com` (timeout), прямой запрос на его fake-IP → 403; `api.openai.com` 401, `auth.openai.com` 403, `github.com` 200 — живы. Минимальный `codex exec -m gpt-6-astra` висел 4+ мин без вывода. VPN не трогал (запрет из CLAUDE.md) |

## Что осталось сделать руками

1. Хуки и роли (одна команда, инсталлер сам делает бэкапы и показывает diff):
   `cd ~/dev/panamera-studio && bash tools/delegate-kit/install-sasha.sh`
   — он же добавит symlinks skills, `dk-*` агентов, PATH в `~/.zshrc` и строку-триггер
   в `~/.claude/CLAUDE.md`.
2. Оживить канал `chatgpt.com` с Мака (правка правил туннеля — за Сашей).
3. Повторить дымовой тест:
   `agent-run run --role reviewer --backend codex --author-backend self --cwd ~/dev/panamera-studio --brief ~/dev/panamera-studio/.scratch/recolor/review-codex.md --timeout 20`

## Полный лог

`/tmp/dk-install.log` пуст — инсталлер не запускался (см. шаг 3b). Ниже фактические
логи preflight и проверок.

```
$ sw_vers; node --version; jq --version; git --version; claude --version; codex --version
ProductName:		macOS
ProductVersion:		26.6.2
BuildVersion:		25G83
v22.23.1
jq-1.7.1-apple
git version 2.50.1 (Apple Git-155)
2.1.251 (Claude Code)
codex-cli 0.153.1

$ codex login status
Logged in using ChatGPT

$ agent-run preset   (сокращено)
preset: auto  (file: /Users/alex/.delegate-kit/config.json)
routes: planner→claude, implementer→codex, researcher→claude
roles:  planner fable max | gpt-6-astra xhigh
        implementer opus high | gpt-6-astra high
        reviewer opus xhigh | gpt-6-astra xhigh
        verifier fable max | gpt-6-astra xhigh
        researcher opus high | gpt-5.6-sol high
        review-lead fable max | gpt-6-astra xhigh

$ agent-run route --role reviewer --parent claude --author-backend claude
reviewers: [{slot: "A", lens: "correctness", backend: "codex", independent: true,
             model: "gpt-6-astra", effort: "xhigh", dispatch: "external"}]

$ agent-run route --role implementer --parent claude
backend: codex, model: gpt-6-astra, effort: high, write: true, dispatch: external

$ jq -r '.. | .slug? // empty' ~/.codex/models_cache.json | sort -u
codex-auto-review
gpt-5.3-codex-spark
gpt-5.4-mini
gpt-5.5
gpt-5.6-luna
gpt-5.6-sol
gpt-5.6-terra
gpt-6-astra
gpt-reserve

$ claude -p --help | grep -i -E 'disallowed|allowedTools'
  --allowedTools, --allowed-tools <tools...>
  --disallowedTools, --disallowed-tools <tools...>

$ agent-run status 20260905161349-uhd3   (второй прогон, сокращено)
{"status": "timeout", "lifecycle": "done", "model": "gpt-6-astra", "effort": "xhigh",
 "started": "2026-09-05T16:13:49Z", "finished": "2026-09-05T16:33:56Z",
 "result": {"status": "failed", "findings": []}}

worker stdout (хвост): {"type":"error","message":"Reconnecting... waiting for network
(Connection failed: error sending request)"}  ×N
worker stderr: http/request failed: error sending request for url
(https://chatgpt.com/backend-api/ps/mcp); failed to refresh available models

$ curl -m 10 https://chatgpt.com          → Resolving timed out
$ curl -m 8  https://api.openai.com/...   → 401 (жив)
$ curl -m 8  https://auth.openai.com      → 403 (жив)
$ curl -m 8  https://github.com           → 200
$ dig @1.1.1.1 chatgpt.com +short         → 198.20.0.11 (fake-IP туннеля)
$ curl --resolve chatgpt.com:443:198.20.0.11 https://chatgpt.com → 403
```
