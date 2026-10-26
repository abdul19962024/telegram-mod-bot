import os
import re
import asyncio
import sys
from telethon import TelegramClient, events, errors, utils
from telethon.sessions import StringSession
from aiohttp import web


# ==============================
# TELEGRAM
# ==============================

API_ID_ENV = "35771930"
API_HASH_ENV = "8ea37e234895cfcd0041464824769797"
STRING_SESSION_ENV = "1BJWap1sBu74MswWx1AFRXfinGDpboqNpfTbbF8yyP7ZtBh2Gc88jiclqwIUnYpVCG3vTLag9tl5TaEp2_sYoLzqssmJPDc_jeuzAeA8Hv0xL_Kzxqw_qUNa7PunnGVNtF2N4tF_moO4WS2vBeP7RIB5aEOnF35czVUkjZ56rRRhi82yXkqesFnNkrNfY8GzNvfBd32818Jay9HHBSkXn6up-4Ps4QvbTOrfrKM3B1YrEfYLxJ8OTZe7jUk6EydjimnCLIJKN6m5TVy4JM6bxvqPWtJqkr2HfWqTtUJjRtfk9BqSD4dZLUZQzoU78GsEsUIm9GWOTtCeXaS2h4kPxrbiXNWzUSfQ="

# For local use, fill these three values. Keep this file private after adding
# a StringSession. Replit environment secrets take precedence when present.
LOCAL_TELEGRAM_API_ID = 35771930
LOCAL_TELEGRAM_API_HASH = "8ea37e234895cfcd0041464824769797"
LOCAL_TELEGRAM_STRING_SESSION = "1BJWap1sBu74MswWx1AFRXfinGDpboqNpfTbbF8yyP7ZtBh2Gc88jiclqwIUnYpVCG3vTLag9tl5TaEp2_sYoLzqssmJPDc_jeuzAeA8Hv0xL_Kzxqw_qUNa7PunnGVNtF2N4tF_moO4WS2vBeP7RIB5aEOnF35czVUkjZ56rRRhi82yXkqesFnNkrNfY8GzNvfBd32818Jay9HHBSkXn6up-4Ps4QvbTOrfrKM3B1YrEfYLxJ8OTZe7jUk6EydjimnCLIJKN6m5TVy4JM6bxvqPWtJqkr2HfWqTtUJjRtfk9BqSD4dZLUZQzoU78GsEsUIm9GWOTtCeXaS2h4kPxrbiXNWzUSfQ="

MONITORED_CHANNEL_IDS = (
    -1003891626305,  # SMART PIPS | النقاط الذكية
    -1002210234381,  # NOVEXA | نوفيكسا
)

CHANNEL_LABELS = {
    -1003891626305: "SMART PIPS | النقاط الذكية",
    -1002210234381: "NOVEXA | نوفيكسا",
}

MONITORED_CHANNEL_USERNAMES = (
    "LuluGoldFX",
    "GoldBlackFx",
)

# يبقى للتوافق مع الكود القديم
FORBIDDEN_LINK_MARKERS = (
    "https://t.me/+",
    "https://t.me/addlist/",
)

# كشف أشمل: بدون https، مع http، joinchat، tg://join ...
FORBIDDEN_LINK_PATTERN = re.compile(
    r"(?<![\w.-])(?:https?://)?(?:www\.)?(?:t|telegram)\.(?:me|dog)/"
    r"(?:\+|joinchat/|addlist/)"
    r"|tg://(?:join|addlist)",
    re.IGNORECASE,
)

# فحص احتياطي كل كم ثانية (يلتقط أي رسالة فاتها التحديث اللحظي)
SWEEP_INTERVAL_SECONDS = 2


def log(*args):
    print(*args, flush=True)


def load_telegram_config(require_session=True):
    # ملاحظة: الأسماء التالية هي أسماء متغيرات البيئة (Replit Secrets)
    api_id_value = (
        os.environ.get("TELEGRAM_API_ID")
        or str(LOCAL_TELEGRAM_API_ID).strip()
    )
    api_hash = (
        os.environ.get("TELEGRAM_API_HASH")
        or LOCAL_TELEGRAM_API_HASH.strip()
    )
    string_session = (
        os.environ.get("TELEGRAM_STRING_SESSION")
        or LOCAL_TELEGRAM_STRING_SESSION.strip()
    )

    if not api_id_value or api_id_value == "0":
        raise RuntimeError(
            "Set LOCAL_TELEGRAM_API_ID at the top of main.py."
        )

    try:
        api_id = int(api_id_value)
    except ValueError as error:
        raise RuntimeError(
            "LOCAL_TELEGRAM_API_ID must be a number."
        ) from error

    if api_id <= 0:
        raise RuntimeError("LOCAL_TELEGRAM_API_ID must be greater than zero.")
    if not api_hash:
        raise RuntimeError(
            "Set LOCAL_TELEGRAM_API_HASH at the top of main.py."
        )
    if require_session and not string_session:
        raise RuntimeError(
            "Set LOCAL_TELEGRAM_STRING_SESSION at the top of main.py."
        )

    return api_id, api_hash, string_session


async def generate_string_session():
    api_id, api_hash, _ = load_telegram_config(require_session=False)
    phone = input("Telegram phone number with country code: ").strip()
    if not phone:
        raise SystemExit("A phone number is required.")

    client = TelegramClient(StringSession(), api_id, api_hash)
    try:
        await client.start(phone=phone)
        print("\nCopy this line into the settings section at the top of main.py:")
        print(f"LOCAL_TELEGRAM_STRING_SESSION = {client.session.save()!r}")
        print("Treat this session like a password; do not share this file.")
    finally:
        await client.disconnect()


# ==============================
# WEB SERVER
# ==============================

async def home(request):
    return web.json_response({"status": "ok"})


async def start_web_server():
    app = web.Application()

    app.router.add_get("/", home)
    app.router.add_get("/api/healthz", home)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    log(f"🌐 Web server running on port {port}")


# ==============================
# DETECTION
# ==============================

def has_forbidden_link_text(value):
    if not value:
        return False
    value = value.lower()
    if any(marker in value for marker in FORBIDDEN_LINK_MARKERS):
        return True
    return bool(FORBIDDEN_LINK_PATTERN.search(value))


def get_violation_reason(message):
    """يرجع سبب المخالفة أو None إذا الرسالة سليمة."""
    if message is None:
        return None

    # 1) ستيكر
    if getattr(message, "sticker", None):
        return "sticker"

    # 2) رابط ظاهر في النص / الكابشن
    if has_forbidden_link_text(message.raw_text):
        return "forbidden Telegram link"

    # 3) رابط مخفي داخل نص (hyperlink)
    for entity in (message.entities or []):
        if has_forbidden_link_text(getattr(entity, "url", None)):
            return "forbidden Telegram link (hidden)"

    # 4) رابط داخل أزرار الرسالة
    markup = getattr(message, "reply_markup", None)
    for row in (getattr(markup, "rows", None) or []):
        for button in (getattr(row, "buttons", None) or []):
            if has_forbidden_link_text(getattr(button, "url", None)):
                return "forbidden Telegram link (button)"

    return None


# ==============================
# DELETION
# ==============================

_handled = {}  # (chat_peer_id, msg_id) -> True  (لتجنب الحذف المكرر)


def _mark_handled(key):
    _handled[key] = True
    if len(_handled) > 5000:
        for old_key in list(_handled)[:2500]:
            _handled.pop(old_key, None)


async def delete_violation(client, entity, message, reason):
    peer_id = utils.get_peer_id(entity) if not isinstance(entity, int) else entity
    key = (peer_id, message.id)
    if key in _handled:
        return
    _mark_handled(key)

    for attempt in range(3):
        try:
            await client.delete_messages(entity, [message.id], revoke=True)
            log(f"🗑️ Deleted message {message.id} from {peer_id} ({reason})")
            return
        except errors.FloodWaitError as error:
            log(f"⏳ FloodWait {error.seconds}s while deleting {message.id}")
            await asyncio.sleep(error.seconds + 1)
        except errors.MessageDeleteForbiddenError:
            log(f"❌ No permission to delete {message.id} in {peer_id}")
            return
        except Exception as error:
            log(f"❌ Could not delete {message.id} in {peer_id}: {error!r}")
            await asyncio.sleep(0.5)


# ==============================
# TELEGRAM MESSAGE HANDLER (لحظي)
# ==============================

def make_message_handler(client):
    async def message_handler(event):
        try:
            message = event.message
            reason = get_violation_reason(message)
            if not reason:
                return

            entity = await event.get_input_chat()
            await delete_violation(client, entity, message, reason)
        except Exception as error:
            log(f"❌ Handler error: {error!r}")

    return message_handler


# ==============================
# FALLBACK SWEEPER (يضمن الحذف حتى لو تأخر التحديث)
# ==============================

async def sweep_loop(client, targets, resolved_ids):
    last_seen = {}

    for entity, peer_id in zip(targets, resolved_ids):
        try:
            latest = await client.get_messages(entity, limit=1)
            last_seen[peer_id] = latest[0].id if latest else 0
        except Exception as error:
            log(f"⚠️ Sweep init failed for {peer_id}: {error!r}")
            last_seen[peer_id] = 0

    log(f"🔁 Fallback sweeper running every {SWEEP_INTERVAL_SECONDS}s")

    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)

        for entity, peer_id in zip(targets, resolved_ids):
            try:
                new_messages = []
                async for msg in client.iter_messages(
                    entity, min_id=last_seen[peer_id], limit=50
                ):
                    new_messages.append(msg)

                if not new_messages:
                    continue

                last_seen[peer_id] = max(m.id for m in new_messages)

                for msg in new_messages:
                    reason = get_violation_reason(msg)
                    if reason:
                        await delete_violation(client, entity, msg, reason)
            except errors.FloodWaitError as error:
                await asyncio.sleep(error.seconds + 1)
            except Exception as error:
                log(f"⚠️ Sweep error for {peer_id}: {error!r}")


# ==============================
# RESOLVE CHANNELS
# ==============================

async def resolve_monitor_targets(client, me):
    numeric_targets = {}
    wanted_ids = set(MONITORED_CHANNEL_IDS)

    async for dialog in client.iter_dialogs():
        if dialog.id in wanted_ids:
            numeric_targets[dialog.id] = dialog.entity
            if len(numeric_targets) == len(wanted_ids):
                break

    missing_ids = wanted_ids - numeric_targets.keys()
    if missing_ids:
        labels = ", ".join(CHANNEL_LABELS[channel_id] for channel_id in missing_ids)
        raise RuntimeError(
            "The connected Telegram account cannot find these channels in its "
            f"dialogs: {labels}. Make sure the account is a member."
        )

    targets = [numeric_targets[channel_id] for channel_id in MONITORED_CHANNEL_IDS]
    target_labels = [CHANNEL_LABELS[channel_id] for channel_id in MONITORED_CHANNEL_IDS]

    for username in MONITORED_CHANNEL_USERNAMES:
        try:
            entity = await client.get_entity(username)
        except errors.RPCError as error:
            raise RuntimeError(
                f"Could not access @{username}. Check the username and make "
                "sure the Telegram account can access that channel."
            ) from error

        if not (
            getattr(entity, "broadcast", False)
            or getattr(entity, "megagroup", False)
        ):
            raise RuntimeError(
                f"@{username} did not resolve to a Telegram channel."
            )

        targets.append(entity)
        target_labels.append(f"@{username}")

    final_targets = []
    resolved_ids = []
    seen = set()

    for label, entity in zip(target_labels, targets):
        if not (
            getattr(entity, "broadcast", False)
            or getattr(entity, "megagroup", False)
        ):
            raise RuntimeError(f"{label} did not resolve to a Telegram channel.")

        try:
            permissions = await client.get_permissions(entity, me)
        except errors.UserNotParticipantError as error:
            raise RuntimeError(
                f"The connected Telegram account is not a member of {label}."
            ) from error
        except errors.RPCError as error:
            raise RuntimeError(
                f"Could not verify message-deletion permission for {label}: {error}"
            ) from error

        if not permissions or not permissions.delete_messages:
            raise RuntimeError(
                f"The connected Telegram account cannot delete messages in {label}."
            )

        peer_id = utils.get_peer_id(entity)
        if peer_id in seen:
            continue  # نفس القناة مذكورة بالـ ID وباليوزرنيم
        seen.add(peer_id)

        final_targets.append(entity)
        resolved_ids.append(peer_id)
        log(f"   ✔ {label} -> {peer_id}")

    return final_targets, resolved_ids


# ==============================
# MAIN
# ==============================

async def main():
    log("=" * 50)
    log("🚀 TELEGRAM CHANNEL MODERATOR")
    log("=" * 50)

    api_id, api_hash, string_session = load_telegram_config()

    await start_web_server()

    client = TelegramClient(
        StringSession(string_session),
        api_id,
        api_hash,
        connection_retries=None,
        retry_delay=1,
        auto_reconnect=True,
        receive_updates=True,
    )
    try:
        await client.start()
    except errors.AuthKeyDuplicatedError as error:
        raise RuntimeError(
            "This Telegram session is active in another process or has been "
            "invalidated by simultaneous use. Generate a new "
            "TELEGRAM_STRING_SESSION and run only one instance."
        ) from error

    me = await client.get_me()
    monitor_targets, resolved_channel_ids = await resolve_monitor_targets(client, me)

    handler = make_message_handler(client)
    # رسائل جديدة + رسائل معدّلة (لو عدّل أحدهم رسالة وأضاف رابط)
    client.add_event_handler(handler, events.NewMessage(chats=monitor_targets))
    client.add_event_handler(handler, events.MessageEdited(chats=monitor_targets))

    username = getattr(me, "username", None) or "without username"
    log(f"✅ Telegram connected: @{username}")

    log(
        "📢 Monitoring channels: "
        f"{', '.join(map(str, resolved_channel_ids))}"
    )
    log("🧹 Deleting forbidden-link messages and stickers (instant)")
    log("🟢 Waiting for messages...")

    sweeper = asyncio.create_task(
        sweep_loop(client, monitor_targets, resolved_channel_ids)
    )
    try:
        await client.run_until_disconnected()
    finally:
        sweeper.cancel()


if __name__ == "__main__":
    if sys.argv[1:] == ["--generate-session"]:
        asyncio.run(generate_string_session())
    elif sys.argv[1:]:
        raise SystemExit(
            "Run with `python main.py` or `python main.py --generate-session`."
        )
    else:
        asyncio.run(main())
