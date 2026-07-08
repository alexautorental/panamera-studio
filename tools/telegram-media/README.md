# telegram-media — медиа-инструменты для Telegram-инфраструктуры Саши

Протестированный комплект MCP-инструментов: транскрипция видео и голосовых **любой
длины** (без таймаутов шлюза), покадровый просмотр видео, постоянный **архив кадров**
с подписями и поиском, отправка сообщений с allowlist.

Написан и оттестирован Claude (сессия по сверке денег с Павлом, 08.07.2026).
Тесты: 9/9 компонентов на реальном видео; найденный на тестах баг исправлен.

## Зачем

Старый маршрут `/voice_text` делал всю работу в одном HTTP-вызове и падал на шлюзе
(60 с → HTTP 504) на любом видео длиннее минуты. Здесь каждый вызов короткий:
тяжелая работа уходит в фон, результат забирается отдельным вызовом и кэшируется
на диске (переживает перезапуск сервиса).

## Состав

| Файл | Что это |
|---|---|
| `telegram_media_tools.py` | 7 MCP-инструментов (самодостаточный, кроме `mcp` и `get_client`) |
| `server.py` | автономный MCP-сервер, если не хочется трогать существующий |

## Инструменты

| Инструмент | Назначение |
|---|---|
| `telegram_media_job(account, chat, msg_id, action, nframes)` | запустить фоновую обработку: `transcribe` \| `frames` \| `both`. Мгновенно отдает `job_id` |
| `telegram_job_status(job_id, frame=-1)` | статус/результат; `frame=k` → кадр k как base64-JPEG с таймкодом |
| `telegram_jobs(action)` | `list` — последние задачи; `cleanup` — удалить рабочие файлы старше 72 ч (архив не трогается) |
| `telegram_archive_frame(job_id, frame, label, note)` | сохранить кадр в постоянный архив `/root/tg_archive` (помесячные папки + `index.jsonl`) |
| `telegram_archive_list(query)` | поиск по архиву: подпись/заметка/чат/дата |
| `telegram_archive_get(archive_id)` | достать сохраненный кадр (base64-JPEG) |
| `telegram_send(account, chat, text, reply_to)` | отправка сообщения; только чаты из `SEND_ALLOWLIST`, журнал в `/root/tg_send.log` |

## Развертывание

**Важно: инструменты должны работать там, где лежат файлы Telethon-сессий**
(сейчас — VPS, `/root/live_madeonsun` и т.д.). С другой машины (Мак и пр.) к
аккаунтам не подключиться без копирования сессий — копировать не рекомендуется:
файл сессии = полный доступ к аккаунту.

Зависимости:

```bash
pip install faster-whisper imageio-ffmpeg
# модель Whisper скачается при первом вызове (~460 МБ для small);
# если faster-whisper недоступен, код сам откатится на openai-whisper (уже стоит на VPS)
```

**Вариант А (рекомендуемый): встроить в существующий MCP-сервер Sasha_Infra.**
В `telegram_media_tools.py` два TODO в блоке INTEGRATION: импортировать реальную
фабрику Telethon-клиентов (ту же, что у `telegram_live`) и экземпляр FastMCP.
Перезапустить сервис. Nginx не трогать — долгих вызовов больше нет.

**Вариант Б: отдельный MCP-сервер** (не трогает существующий код):

```bash
export TG_API_ID=... TG_API_HASH=...
claude mcp add telegram-media -- python3 /path/to/tools/telegram-media/server.py
```

## Протокол использования (для любой модели)

1. Найти сообщение: `telegram_live` / `telegram_deepsearch` → `chat_id`, `msg_id`.
2. `telegram_media_job(account, chat_id, msg_id, action="both", nframes=10)` → `job_id`.
3. Подождать 30–90 с → `telegram_job_status(job_id)` → транскрипция с таймкодами.
4. Кадры: `telegram_job_status(job_id, frame=0..N-1)` → декодировать base64 → смотреть.
5. Важные кадры — в архив: `telegram_archive_frame(job_id, k, "плита-опалубка-08.07",
   "видно армирование угла")`. Потом искать: `telegram_archive_list("плита")`.
6. Ответ в чат: `telegram_send(...)` — только чаты из allowlist, каждая отправка
   пишется в журнал.

## Памятка для общей памяти (вставить в Letta/архивную память как есть)

> [TOOLS: telegram-media] На VPS развернуты MCP-инструменты обработки Telegram-медиа:
> telegram_media_job → telegram_job_status (транскрипция любой длины + кадры видео,
> job-модель, без 504), telegram_archive_frame/list/get (постоянный архив кадров,
> /root/tg_archive), telegram_send (отправка, allowlist: Павел 591966536, Дом с
> Павлом −5236779041, Катя 1776323080, чат передач −4990982206; журнал
> /root/tg_send.log). Исходники и инструкция: repo panamera-studio,
> tools/telegram-media/README.md. Протокол: job → подождать 30–90 с → status;
> кадры смотреть по одному (frame=k), важные — в архив с подписью.

## Конфигурация

Все настройки — константы в начале `telegram_media_tools.py`: каталоги, лимит
размера файла (512 МБ), максимум кадров (24), TTL рабочих файлов (72 ч), модель
Whisper (`TG_WHISPER_MODEL`: tiny|base|small|medium), `SEND_ALLOWLIST`.
