# -*- coding: utf-8 -*-
"""
server.py — автономный MCP-сервер «telegram-media».

Запускать ТАМ, ГДЕ ЛЕЖАТ TELETHON-СЕССИИ (сейчас это VPS: /root/live_madeonsun,
/root/live_alexamg, /root/live_imblack). На машине без файлов сессий подключиться
к аккаунтам невозможно — это защита Telegram, а не ограничение кода.

ЗАПУСК:
    export TG_API_ID=...        # те же api_id/api_hash, что у остальной инфраструктуры
    export TG_API_HASH=...
    export TG_SESSION_DIR=/root         # каталог с файлами сессий (по умолчанию /root)
    export TG_SESSION_PREFIX=live_      # префикс имен сессий (по умолчанию live_)
    export TG_WHISPER_MODEL=small       # tiny|base|small|medium (по умолчанию small)
    python3 server.py                   # stdio-транспорт для Claude Code / Claude Desktop

РЕГИСТРАЦИЯ В CLAUDE CODE (на той же машине):
    claude mcp add telegram-media -- python3 /path/to/server.py

Альтернатива этому файлу: встроить telegram_media_tools.py в существующий MCP-сервер
Sasha_Infra — см. README.md, вариант А.
"""

import os

from mcp.server.fastmcp import FastMCP
from telethon import TelegramClient

mcp = FastMCP("telegram-media")

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION_DIR = os.environ.get("TG_SESSION_DIR", "/root")
SESSION_PREFIX = os.environ.get("TG_SESSION_PREFIX", "live_")

_clients: dict = {}


async def get_client(account: str) -> TelegramClient:
    """Ленивая фабрика Telethon-клиентов по файлам сессий."""
    client = _clients.get(account)
    if client is not None and client.is_connected():
        return client
    session_path = os.path.join(SESSION_DIR, f"{SESSION_PREFIX}{account}")
    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError(
            f"сессия {session_path} не авторизована — запустите авторизацию Telethon")
    _clients[account] = client
    return client


# Инструменты написаны так, что ссылаются на глобальные `mcp` и `get_client`, —
# исполняем их в текущем пространстве имен (тот же прием проверен тестами).
_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "telegram_media_tools.py"), encoding="utf-8") as _f:
    exec(compile(_f.read(), "telegram_media_tools.py", "exec"), globals())  # noqa: S102


if __name__ == "__main__":
    mcp.run()
