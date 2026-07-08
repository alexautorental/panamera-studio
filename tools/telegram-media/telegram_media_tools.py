# -*- coding: utf-8 -*-
"""
telegram_media_tools.py — v2. Профессиональные медиа-инструменты для MCP-сервера Sasha_Infra.

ЧТО УМЕЕТ
  1. telegram_media_job    — фоновая обработка медиа из сообщения (видео/голосовое/кружок/фото):
                             transcribe | frames | both. Мгновенно возвращает job_id.
  2. telegram_job_status   — статус и результаты: текст с таймкодами, кадры base64-JPEG.
  3. telegram_jobs         — список последних задач / очистка старых файлов.
  4. telegram_archive_frame— сохранить нужный кадр в постоянный архив с подписью.
  5. telegram_archive_list — поиск по архиву (подпись/заметка/чат/дата).
  6. telegram_archive_get  — достать сохраненный кадр из архива (base64).
  7. telegram_send         — отправка сообщений (WRITE, allowlist + журнал).

ПОЧЕМУ ТАК: старый /voice_text делал всю работу в одном HTTP-вызове и умирал на шлюзе
(60 с, HTTP 504) на любом видео длиннее минуты. Здесь каждый вызов короткий, тяжелая
работа — в фоне, результаты кэшируются на диске и переживают перезапуск.

УСТАНОВКА (VPS):
    pip install faster-whisper imageio-ffmpeg
    # модель Whisper скачается при первом вызове в ~/.cache/huggingface
    # imageio-ffmpeg содержит статический ffmpeg — системный не обязателен

ПОДКЛЮЧЕНИЕ: заменить два импорта в блоке INTEGRATION ниже и перезапустить сервис.
Nginx не трогать — долгих вызовов больше нет.
"""

import asyncio
import base64
import glob
import json
import os
import re
import shutil
import subprocess
import time
import uuid

# ============================== INTEGRATION ===================================
# TODO(1): фабрика Telethon-клиентов — та же, что у telegram_live/telegram_history
# from sasha_infra.telegram import get_client
# TODO(2): экземпляр FastMCP
# from sasha_infra.server import mcp
# ==============================================================================

# ================================ CONFIG ======================================
JOBS_DIR = "/root/tg_jobs"            # рабочие файлы задач (можно чистить)
ARCHIVE_DIR = "/root/tg_archive"      # постоянный архив кадров (НЕ чистится автоматически)
SEND_LOG = "/root/tg_send.log"
WHISPER_MODEL = os.environ.get("TG_WHISPER_MODEL", "small")  # tiny|base|small|medium
MAX_MEDIA_MB = 512                    # предохранитель от гигантских файлов
MAX_FRAMES = 24
JOB_TTL_HOURS = 72                    # telegram_jobs(action="cleanup") удаляет старше этого
_PROCESS_SEM = asyncio.Semaphore(2)   # не больше 2 тяжелых задач одновременно

ALLOWED_ACCOUNTS = {"madeonsun", "alexamg", "imblack"}
SEND_ALLOWLIST = {
    "-5236779041",   # Дом с Павлом
    "591966536",     # Павел (личка)
    "1776323080",    # Катя
    "-4990982206",   # Семково: передачи денег Павлу
}
# ==============================================================================

os.makedirs(JOBS_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)
_ARCHIVE_INDEX = os.path.join(ARCHIVE_DIR, "index.jsonl")


# ------------------------------- job store -----------------------------------
def _job_file(job_id: str) -> str:
    return os.path.join(JOBS_DIR, f"{job_id}.json")


def _job_write(job_id: str, **fields):
    path = _job_file(job_id)
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    data["job_id"] = job_id
    data.update(fields, updated=round(time.time(), 1))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)  # атомарная запись — статус не побьется при падении


def _job_read(job_id: str) -> dict:
    path = _job_file(job_id)
    if not os.path.exists(path):
        return {"status": "not_found", "job_id": job_id}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return {"status": "error", "error": f"job file unreadable: {exc}"}


# ------------------------------- ffmpeg utils --------------------------------
def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def _media_duration(ffmpeg: str, path: str) -> float:
    """Длительность из stderr ffmpeg (ffprobe в imageio-ffmpeg не входит)."""
    proc = subprocess.run([ffmpeg, "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", proc.stderr)
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def _fmt_ts(sec: float) -> str:
    m, s = divmod(int(round(sec)), 60)
    return f"{m:02d}:{s:02d}"


# ------------------------------ processing -----------------------------------
def _process_transcribe(job_id: str, media_path: str) -> dict:
    ff = _ffmpeg_exe()
    wav = os.path.join(JOBS_DIR, f"{job_id}.wav")
    subprocess.run(
        [ff, "-y", "-i", media_path, "-vn", "-ac", "1", "-ar", "16000", wav],
        check=True, capture_output=True, timeout=1800,
    )
    try:
        try:  # основной путь: faster-whisper (быстрее и экономнее по памяти)
            from faster_whisper import WhisperModel
            model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
            segments, info = model.transcribe(wav, language=None, vad_filter=True)
            segs = [{"t": _fmt_ts(s.start), "start": round(s.start, 1),
                     "text": s.text.strip()} for s in segments]
            return {"text": " ".join(s["text"] for s in segs),
                    "segments": segs,
                    "duration_sec": round(info.duration, 1),
                    "language": info.language,
                    "model": f"faster-whisper/{WHISPER_MODEL}"}
        except ImportError:  # запасной путь: классический openai-whisper (уже стоит на VPS)
            import whisper
            model = whisper.load_model(WHISPER_MODEL)
            res = model.transcribe(wav)
            segs = [{"t": _fmt_ts(s["start"]), "start": round(s["start"], 1),
                     "text": s["text"].strip()} for s in res.get("segments", [])]
            return {"text": res.get("text", "").strip(),
                    "segments": segs,
                    "duration_sec": round(_media_duration(_ffmpeg_exe(), wav), 1),
                    "language": res.get("language", ""),
                    "model": f"openai-whisper/{WHISPER_MODEL}"}
    finally:
        if os.path.exists(wav):
            os.remove(wav)


def _process_frames(job_id: str, media_path: str, nframes: int, is_photo: bool) -> dict:
    ff = _ffmpeg_exe()
    if is_photo:
        dst = os.path.join(JOBS_DIR, f"{job_id}_f00.jpg")
        subprocess.run([ff, "-y", "-i", media_path, "-vf", "scale=1280:-2",
                        "-q:v", "4", dst], check=True, capture_output=True, timeout=300)
        return {"duration_sec": 0, "frames_count": 1, "frame_files": [dst],
                "frame_times": ["00:00"]}
    dur = _media_duration(ff, media_path) or 60.0
    nframes = max(1, min(int(nframes), MAX_FRAMES))
    # кадр из середины каждого из n равных интервалов — стабильно и равномерно
    times = [dur * (i + 0.5) / nframes for i in range(nframes)]
    files, labels = [], []
    for i, t in enumerate(times):
        dst = os.path.join(JOBS_DIR, f"{job_id}_f{i:02d}.jpg")
        subprocess.run([ff, "-y", "-ss", f"{t:.3f}", "-i", media_path,
                        "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "5", dst],
                       check=True, capture_output=True, timeout=300)
        if os.path.exists(dst):
            files.append(dst)
            labels.append(_fmt_ts(t))
    return {"duration_sec": round(dur, 1), "frames_count": len(files),
            "frame_files": files, "frame_times": labels}


async def _run_job(job_id: str, account: str, chat: str, msg_id: int,
                   action: str, nframes: int):
    try:
        client = await get_client(account)  # noqa: F821 — настраивается при установке
        peer = int(chat) if str(chat).lstrip("-").isdigit() else chat
        msg = await client.get_messages(peer, ids=int(msg_id))
        if msg is None or msg.media is None:
            _job_write(job_id, status="error", error="в сообщении нет медиа")
            return
        size = getattr(getattr(msg, "file", None), "size", 0) or 0
        if size > MAX_MEDIA_MB * 1024 * 1024:
            _job_write(job_id, status="error",
                       error=f"файл {size // 1024 // 1024} МБ > лимита {MAX_MEDIA_MB} МБ")
            return
        is_photo = msg.photo is not None
        _job_write(job_id, status="downloading", media_bytes=size,
                   msg_date=str(getattr(msg, "date", "")))
        media_path = await client.download_media(
            msg, file=os.path.join(JOBS_DIR, f"{job_id}_src"))
        if not media_path:
            _job_write(job_id, status="error", error="download_media вернул пусто")
            return
        async with _PROCESS_SEM:  # тяжелая часть — не больше 2 параллельно
            _job_write(job_id, status="processing")
            result = {}
            if action in ("frames", "both"):
                result["frames"] = await asyncio.to_thread(
                    _process_frames, job_id, media_path, nframes, is_photo)
            if action in ("transcribe", "both") and not is_photo:
                result["transcript"] = await asyncio.to_thread(
                    _process_transcribe, job_id, media_path)
        _job_write(job_id, status="done", result=result)
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or b"")[-400:].decode("utf-8", "replace")
        _job_write(job_id, status="error", error=f"ffmpeg failed: {tail}")
    except Exception as exc:  # noqa: BLE001 — статус ошибки должен дойти до клиента
        _job_write(job_id, status="error", error=f"{type(exc).__name__}: {exc}")


# ------------------------------- MCP tools -----------------------------------
@mcp.tool()  # noqa: F821
async def telegram_media_job(account: str, chat: str, msg_id: int,
                             action: str = "both", nframes: int = 8) -> str:
    """Запустить фоновую обработку медиа из Telegram-сообщения. Мгновенно возвращает job_id.

    account: madeonsun | alexamg | imblack
    chat: chat_id или @username
    action: "transcribe" (аудио->текст) | "frames" (видео/фото->кадры) | "both"
    nframes: кадров равномерно по длительности (1..24)

    Результат: telegram_job_status(job_id). Видео 3 мин обрабатывается ~1-3 минуты.
    """
    if account not in ALLOWED_ACCOUNTS:
        return json.dumps({"error": f"неизвестный аккаунт {account}"}, ensure_ascii=False)
    if action not in ("transcribe", "frames", "both"):
        return json.dumps({"error": "action: transcribe | frames | both"}, ensure_ascii=False)
    job_id = uuid.uuid4().hex[:12]
    _job_write(job_id, status="queued", account=account, chat=str(chat),
               msg_id=int(msg_id), action=action, created=round(time.time(), 1))
    asyncio.create_task(_run_job(job_id, account, str(chat), int(msg_id), action, nframes))
    return json.dumps({"job_id": job_id, "status": "queued",
                       "next": "telegram_job_status(job_id) через 20-60 секунд"},
                      ensure_ascii=False)


@mcp.tool()  # noqa: F821
async def telegram_job_status(job_id: str, frame: int = -1) -> str:
    """Статус/результат задачи telegram_media_job.

    frame=-1: статус + результат (текст транскрипции целиком; для кадров - их число и таймкоды).
    frame=0..N-1: вернуть кадр как base64-JPEG (ключ jpeg_base64).
    """
    data = _job_read(job_id)
    if frame < 0:
        slim = dict(data)
        if isinstance(slim.get("result"), dict) and "frames" in slim["result"]:
            fr = dict(slim["result"]["frames"])
            fr.pop("frame_files", None)  # пути сервера клиенту не нужны
            slim["result"] = dict(slim["result"], frames=fr)
        return json.dumps(slim, ensure_ascii=False)
    if data.get("status") != "done":
        return json.dumps({"status": data.get("status"), "error": data.get("error")},
                          ensure_ascii=False)
    files = ((data.get("result") or {}).get("frames") or {}).get("frame_files") or []
    times = ((data.get("result") or {}).get("frames") or {}).get("frame_times") or []
    if frame >= len(files):
        return json.dumps({"error": f"кадра {frame} нет, всего {len(files)}"},
                          ensure_ascii=False)
    with open(files[frame], "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return json.dumps({"frame": frame, "of": len(files),
                       "time": times[frame] if frame < len(times) else "",
                       "jpeg_base64": b64}, ensure_ascii=False)


@mcp.tool()  # noqa: F821
async def telegram_jobs(action: str = "list", limit: int = 15) -> str:
    """Задачи медиа-обработки. action="list" - последние задачи; action="cleanup" -
    удалить рабочие файлы задач старше JOB_TTL_HOURS (архив не трогается)."""
    if action == "cleanup":
        cutoff = time.time() - JOB_TTL_HOURS * 3600
        removed = 0
        for jf in glob.glob(os.path.join(JOBS_DIR, "*.json")):
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    created = json.load(f).get("created", 0)
            except (json.JSONDecodeError, OSError):
                created = 0
            if created < cutoff:
                jid = os.path.basename(jf)[:-5]
                for p in glob.glob(os.path.join(JOBS_DIR, jid + "*")):
                    os.remove(p)
                    removed += 1
        return json.dumps({"removed_files": removed}, ensure_ascii=False)
    jobs = []
    for jf in glob.glob(os.path.join(JOBS_DIR, "*.json")):
        try:
            with open(jf, "r", encoding="utf-8") as f:
                d = json.load(f)
            jobs.append({k: d.get(k) for k in
                         ("job_id", "status", "account", "chat", "msg_id",
                          "action", "created", "error")})
        except (json.JSONDecodeError, OSError):
            continue
    jobs.sort(key=lambda j: j.get("created") or 0, reverse=True)
    return json.dumps(jobs[:max(1, min(limit, 50))], ensure_ascii=False)


# -------------------------------- archive ------------------------------------
@mcp.tool()  # noqa: F821
async def telegram_archive_frame(job_id: str, frame: int, label: str,
                                 note: str = "") -> str:
    """Сохранить кадр задачи в ПОСТОЯННЫЙ архив (/root/tg_archive, автоочистки нет).

    label: короткая подпись латиницей/кириллицей, напр. "плита-опалубка-08.07"
    note: развернутая заметка (что видно, зачем сохранили)
    """
    data = _job_read(job_id)
    files = ((data.get("result") or {}).get("frames") or {}).get("frame_files") or []
    times = ((data.get("result") or {}).get("frames") or {}).get("frame_times") or []
    if not files:
        return json.dumps({"error": "у задачи нет кадров (status/action?)"}, ensure_ascii=False)
    if not 0 <= frame < len(files):
        return json.dumps({"error": f"кадра {frame} нет, всего {len(files)}"}, ensure_ascii=False)
    month_dir = os.path.join(ARCHIVE_DIR, time.strftime("%Y-%m"))
    os.makedirs(month_dir, exist_ok=True)
    safe = re.sub(r"[^\w\-.]+", "_", label, flags=re.U)[:60] or "frame"
    archive_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{safe}_f{frame:02d}"
    dst = os.path.join(month_dir, archive_id + ".jpg")
    shutil.copy2(files[frame], dst)
    entry = {"archive_id": archive_id, "file": dst, "label": label, "note": note,
             "video_time": times[frame] if frame < len(times) else "",
             "job_id": job_id, "frame": frame,
             "account": data.get("account"), "chat": data.get("chat"),
             "msg_id": data.get("msg_id"), "msg_date": data.get("msg_date"),
             "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(_ARCHIVE_INDEX, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return json.dumps({"ok": True, **entry, "file": None}, ensure_ascii=False)


@mcp.tool()  # noqa: F821
async def telegram_archive_list(query: str = "", limit: int = 20) -> str:
    """Поиск по архиву кадров: подстрока в label/note/chat/msg_date/archive_id.
    Пустой query - последние записи."""
    if not os.path.exists(_ARCHIVE_INDEX):
        return json.dumps([], ensure_ascii=False)
    q = query.lower()
    rows = []
    with open(_ARCHIVE_INDEX, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            hay = " ".join(str(e.get(k, "")) for k in
                           ("label", "note", "chat", "msg_date", "archive_id")).lower()
            if not q or q in hay:
                e.pop("file", None)
                rows.append(e)
    return json.dumps(rows[-max(1, min(limit, 100)):][::-1], ensure_ascii=False)


@mcp.tool()  # noqa: F821
async def telegram_archive_get(archive_id: str) -> str:
    """Достать сохраненный кадр из архива как base64-JPEG."""
    matches = glob.glob(os.path.join(ARCHIVE_DIR, "*", archive_id + ".jpg"))
    if not matches:
        return json.dumps({"error": f"нет кадра {archive_id}"}, ensure_ascii=False)
    with open(matches[0], "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return json.dumps({"archive_id": archive_id, "jpeg_base64": b64}, ensure_ascii=False)


# --------------------------------- send --------------------------------------
@mcp.tool()  # noqa: F821
async def telegram_send(account: str, chat: str, text: str, reply_to: int = 0) -> str:
    """Отправить сообщение в Telegram от имени аккаунта. WRITE-операция.
    Разрешены только чаты из SEND_ALLOWLIST; каждая отправка журналируется."""
    if account not in ALLOWED_ACCOUNTS:
        return json.dumps({"error": f"неизвестный аккаунт {account}"}, ensure_ascii=False)
    if str(chat) not in SEND_ALLOWLIST:
        return json.dumps({"error": f"чат {chat} не в allowlist (SEND_ALLOWLIST)"},
                          ensure_ascii=False)
    client = await get_client(account)  # noqa: F821
    peer = int(chat) if str(chat).lstrip("-").isdigit() else chat
    msg = await client.send_message(peer, text, reply_to=reply_to or None)
    with open(SEND_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "account": account, "chat": str(chat),
                            "msg_id": msg.id, "text": text[:200]},
                           ensure_ascii=False) + "\n")
    return json.dumps({"ok": True, "msg_id": msg.id, "chat": str(peer)}, ensure_ascii=False)
