# Мультимодельный воркфлоу на двух подписках (Claude Max + ChatGPT Pro)

Состояние на 05.09.2026. Основа — [delegate-kit](https://github.com/tomastaker/delegate-kit) (навык из ТГ-комментария),
сверху — sasha-mode (`.claude/skills/orchestrate`, `.claude/skills/cross-review`, `tools/delegate-kit/`).

## Схема

```
телефон (Claude app) ──Remote Control──► Claude Code на Маке = оркестратор (Fable)
                                              ├─ нативно: dk-planner (fable max), dk-implementer UI (opus), dk-reviewer (opus xhigh), dk-ux-reviewer
                                              └─ codex exec (подписка ChatGPT Pro): implementer / reviewer / verifier на gpt-6-astra
                                          worktree на писателя · frozen diff · ревью другой семьёй · fix → re-review · JSON-отчёт
```

Облачные сессии claude.ai/code Codex не видят: там работает нативный фолбэк с пометкой «одно семейство».
Поэтому основной режим с телефона — Remote Control к Маку, не облако.

## Установка на Маке (один раз)

```bash
git clone https://github.com/alexautorental/panamera-studio ~/dev/panamera-studio   # или git pull
git -C ~/dev/panamera-studio checkout claude/multi-model-orchestration-review-pzkt08
bash ~/dev/panamera-studio/tools/delegate-kit/install-sasha.sh
```

Скрипт: ставит delegate-kit, симлинки, нативные роли и safety-gate, кладёт `~/.delegate-kit/config.json`
с моделями ниже, добавляет `dk-ux-reviewer`, строку-триггер в `~/.claude/CLAUDE.md`, проверяет `codex exec` на
`gpt-6-astra` и откатывает на `gpt-5.6-sol`, если Astra ещё не раскатана на твой логин.

Сессия с телефона: на Маке `cd <repo> && claude`, затем `/remote-control` (или `remoteControlAtStartup` в settings).

## Модели и усилие (sasha-mode)

| Роль | Claude | Codex | Почему |
|---|---|---|---|
| planner / review-lead / verifier | `fable` **max** | `gpt-6-astra` xhigh | одна read-only итерация, ошибка здесь дороже всего |
| implementer (логика, бэкенд, скрипты) | — | `gpt-6-astra` high | сильнейшая OpenAI-модель под код на 05.09 |
| implementer (UI, визуал) | `opus` high | — | `--kind ui`; ревью тогда делает Codex |
| reviewer | `opus` xhigh | `gpt-6-astra` xhigh | всегда другая семья, чем автор |
| researcher | `opus` high | `gpt-5.6-sol` high | дешёвые модели только в изолированной механике с полной автопроверкой |
| оркестратор | Fable (модель чата) | — | план и слияние ревью — у самой сильной |

Источники: `gpt-6-astra` — модель в списке learn.chatgpt.com/docs/models; Codex CLI v0.153.1 (03.09.2026);
усилия Codex low/medium/high/xhigh/max/ultra (`ultra` = субагенты, воркерам не давать); Claude `--effort` low/medium/high/xhigh/max.
Доступность Astra по подписке Pro раскатывается «в течение дней» — потому инсталлер пингует и откатывает.

## Что улучшено относительно стокового delegate-kit

| # | Пункт | Стоковый delegate-kit | sasha-mode | Зачем |
|---|---|---|---|---|
| 1 | Модели | `gpt-5.6-sol`, `fable/opus high`, `sonnet medium` | таблица выше через `config.json`, без правки кода | Astra вышла 03.09; таблица в коде устарела за 2 дня |
| 2 | Ревью плана другой семьёй | нет | после PLAN план уходит Astra read-only, один вызов | ошибка декомпозиции дороже любой ошибки в коде |
| 3 | UX-слот | только `--kind ui` для писателя | `dk-ux-reviewer` (Opus) на любом UI-диффе, параллельно с A | mobile-first, Android 390px, светлая тема |
| 4 | Панель | предлагается, ждёт «да» | «да» заранее по порогам; `led` — спросить | автономия; порог тот же |
| 5 | Вопросы не про код | вне скилла | shape VERDICT: черновик → критика другой семьёй → синтез | замена «триаде» одним синтезом |
| 6 | Отчёт | JSON воркеров | таблица по-русски, статусы, URL в конце | 80 % чтения с телефона |
| 7 | Память | — | Letta read/sync в протоколе | межчатовая память |
| 8 | Облако | фолбэк «одно семейство» молча | явный раздел + пакет `tools/review_packet.py` для дочитки на Маке | честная маркировка |

Оставлено как есть и это правильно: worktree + lock на писателя, frozen diff, ревьюеры вслепую, merge по смыслу,
спор решает команда, а не мнение, `blocked` вместо догадок, ledger, safety-gate, глубина делегирования 1.

## Что проверено, что нет (обновлено 05.09 после прогона на Маке)

| Проверка | Статус |
|---|---|
| delegate-kit: `tests/{caps,route,gate,inspect}.sh` | ✅ прошли (node 22, jq 1.7) |
| `config.sasha.json` читается `agent-run preset/route` | ✅ и в облаке, и на Маке: reviewer A → `codex gpt-6-astra xhigh`, `independent: true` |
| Codex CLI на Маке, вход по ChatGPT Pro | ✅ codex-cli 0.153.1, «Logged in using ChatGPT» |
| `gpt-6-astra` под логином Саши | ✅ есть в `~/.codex/models_cache.json` (плюс sol/terra/luna, gpt-5.5) |
| Флаги `claude -p`, включая `--disallowedTools` | ✅ есть на Маке (claude 2.1.251) |
| `codex exec` флаги | ✅ по доке learn.chatgpt.com |
| `install-sasha.sh` из сессии Claude в auto-режиме | ⛔ классификатор разрешений блокирует (скрипт ставит PreToolUse-hook в `~/.claude/settings.json`). Запускать руками в терминале Мака |
| Живой вызов GPT-воркера с Мака | ❌ два прогона по 20 мин: codex не достучался до `chatgpt.com` через туннель (utun1, fake-IP). `api.openai.com`/`auth.openai.com`/`github.com` живы. Лог: `install-log-2026-09-05.md` |

### Канал chatgpt.com с Мака — что попробовать первым
1. Открывается ли `https://chatgpt.com` в браузере на Маке. Если да — CLI просто не идёт через системный прокси:
   `export HTTPS_PROXY=http://127.0.0.1:<mixed-port Karing/Hiddify>` в той же оболочке и повторить
   `codex exec --skip-git-repo-check -s read-only -m gpt-6-astra 'Reply: OK'`.
2. Если и в браузере нет — в правилах VPN-клиента отправить `chatgpt.com`, `*.openai.com`, `*.oaistatic.com` через прокси (Вильнюс/Амстердам), не direct: с белорусского IP chatgpt.com отдаёт 403.
3. После оживления канала — повтор дымового теста командой из `install-log-2026-09-05.md`, п. 3.

## Ссылки

- https://github.com/tomastaker/delegate-kit
- https://learn.chatgpt.com/docs/models
- https://learn.chatgpt.com/docs/developer-commands?surface=cli
- https://code.claude.com/docs/en/remote-control.md
- https://code.claude.com/docs/en/sub-agents.md
