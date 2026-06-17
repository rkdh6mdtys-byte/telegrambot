import asyncio
import logging
import os
import json
import signal
import uuid
from datetime import datetime
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes,
)
from telegram.constants import ParseMode

# ─── Логирование ──────────────────────────────────────────────────────────────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Конфигурация ─────────────────────────────────────────────────────────────
ADMIN_BOT_TOKEN  = os.getenv('TELEGRAM_ADMIN_BOT_TOKEN')
ADMIN_CHAT_ID    = int(os.getenv('ADMIN_CHAT_ID', '6133417158'))
WEBHOOK_PORT     = int(os.getenv('ADMIN_BOT_PORT', '8081'))
WEBHOOK_HOST     = os.getenv('ADMIN_BOT_HOST', '0.0.0.0')
WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL', '')

# ─── Статусы заявок ───────────────────────────────────────────────────────────
STATUS_NEW         = 'new'
STATUS_IN_PROGRESS = 'in_progress'
STATUS_DONE        = 'done'

STATUS_LABELS = {
    STATUS_NEW:         '🆕 Новая',
    STATUS_IN_PROGRESS: '⏳ В работе',
    STATUS_DONE:        '✅ Завершена',
}

STATUS_TRANSITIONS = {
    STATUS_NEW:         STATUS_IN_PROGRESS,
    STATUS_IN_PROGRESS: STATUS_DONE,
    STATUS_DONE:        None,
}

# ─── Хранилище заявок (in-memory) ─────────────────────────────────────────────
# Структура: { app_id: { ...data, 'status': str, 'message_id': int|None } }
applications: dict[str, dict] = {}


# ─── Вспомогательные функции ──────────────────────────────────────────────────

def format_application(app: dict) -> str:
    """Форматирует заявку в читаемый текст."""
    status_label = STATUS_LABELS.get(app.get('status', STATUS_NEW), '🆕 Новая')
    lines = [
        f"<b>📋 ЗАЯВКА #{app['id'][:8].upper()}</b>",
        f"<b>Статус:</b> {status_label}",
        "",
        f"<b>Услуга:</b> {app.get('service', '—')}",
        f"<b>Имя:</b> {app.get('name', '—')}",
        f"<b>Телефон:</b> {app.get('phone', '—')}",
        f"<b>Гостей:</b> {app.get('guests', '—')}",
        f"<b>Дата:</b> {app.get('date', '—')}",
    ]
    if app.get('package'):
        lines.append(f"<b>Пакет:</b> {app['package']}")
    if app.get('price'):
        lines.append(f"<b>Цена:</b> {app['price']}")
    lines += [
        "",
        f"<b>Время заявки:</b> {app.get('created_at', '—')}",
    ]
    return "\n".join(lines)


def build_status_keyboard(app_id: str, current_status: str) -> InlineKeyboardMarkup:
    """Строит клавиатуру управления статусом заявки."""
    next_status = STATUS_TRANSITIONS.get(current_status)
    buttons = []

    if next_status:
        next_label = STATUS_LABELS[next_status]
        buttons.append(
            InlineKeyboardButton(
                f"Перевести → {next_label}",
                callback_data=f"status:{app_id}:{next_status}",
            )
        )

    buttons.append(
        InlineKeyboardButton(
            "📋 Все заявки",
            callback_data="list_applications",
        )
    )

    return InlineKeyboardMarkup([buttons])


# ─── Обработчики Telegram ─────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — инструкция для администратора."""
    text = (
        "👋 <b>Добро пожаловать в панель администратора ВОЛНЫ!</b>\n\n"
        "Этот бот получает новые заявки с сайта и из основного бота, "
        "и позволяет управлять их статусами.\n\n"
        "<b>Доступные команды:</b>\n"
        "/start — показать эту инструкцию\n"
        "/applications — список всех заявок с текущими статусами\n\n"
        "<b>Статусы заявок:</b>\n"
        f"{STATUS_LABELS[STATUS_NEW]} — только что поступила\n"
        f"{STATUS_LABELS[STATUS_IN_PROGRESS]} — менеджер взял в работу\n"
        f"{STATUS_LABELS[STATUS_DONE]} — заявка закрыта\n\n"
        "Когда поступает новая заявка, бот автоматически отправит её сюда "
        "с кнопками для смены статуса."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/applications — список всех заявок."""
    if not applications:
        await update.message.reply_text(
            "📭 Заявок пока нет.",
            parse_mode=ParseMode.HTML,
        )
        return

    lines = ["<b>📋 ВСЕ ЗАЯВКИ</b>\n"]
    for app in sorted(applications.values(), key=lambda x: x.get('created_at', ''), reverse=True):
        status_label = STATUS_LABELS.get(app.get('status', STATUS_NEW), '🆕 Новая')
        short_id = app['id'][:8].upper()
        name     = app.get('name', '—')
        service  = app.get('service', '—')
        date     = app.get('date', '—')
        lines.append(
            f"• <b>#{short_id}</b> | {status_label}\n"
            f"  {name} · {service} · {date}"
        )

    text = "\n\n".join(lines)

    # Telegram ограничивает сообщения 4096 символами
    if len(text) > 4096:
        text = text[:4090] + "\n…"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cb_status_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатия кнопки смены статуса."""
    query = update.callback_query
    await query.answer()

    _, app_id, new_status = query.data.split(":", 2)

    if app_id not in applications:
        await query.edit_message_text("⚠️ Заявка не найдена.")
        return

    app = applications[app_id]
    old_status = app.get('status', STATUS_NEW)

    if new_status not in STATUS_LABELS:
        await query.answer("Неизвестный статус.", show_alert=True)
        return

    app['status'] = new_status
    app['updated_at'] = datetime.now().strftime('%d.%m.%Y %H:%M')

    logger.info(
        "Заявка %s: статус изменён %s → %s",
        app_id[:8].upper(),
        STATUS_LABELS[old_status],
        STATUS_LABELS[new_status],
    )

    new_text     = format_application(app)
    new_keyboard = build_status_keyboard(app_id, new_status)

    await query.edit_message_text(
        new_text,
        reply_markup=new_keyboard,
        parse_mode=ParseMode.HTML,
    )


async def cb_list_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки «Все заявки»."""
    query = update.callback_query
    await query.answer()

    if not applications:
        await query.answer("📭 Заявок пока нет.", show_alert=True)
        return

    lines = ["<b>📋 ВСЕ ЗАЯВКИ</b>\n"]
    for app in sorted(applications.values(), key=lambda x: x.get('created_at', ''), reverse=True):
        status_label = STATUS_LABELS.get(app.get('status', STATUS_NEW), '🆕 Новая')
        short_id = app['id'][:8].upper()
        name     = app.get('name', '—')
        service  = app.get('service', '—')
        date     = app.get('date', '—')
        lines.append(
            f"• <b>#{short_id}</b> | {status_label}\n"
            f"  {name} · {service} · {date}"
        )

    text = "\n\n".join(lines)
    if len(text) > 4096:
        text = text[:4090] + "\n…"

    await query.message.reply_text(text, parse_mode=ParseMode.HTML)


# ─── Webhook-обработчик для входящих заявок ───────────────────────────────────

async def handle_application_webhook(request: web.Request) -> web.Response:
    """
    POST /webhook/application
    Принимает JSON с данными заявки, сохраняет и отправляет администратору.

    Ожидаемый формат тела запроса (все поля опциональны, кроме хотя бы одного):
    {
        "service":  "Свадьба",
        "name":     "Иван Иванов",
        "phone":    "+7 999 000 00 00",
        "guests":   50,
        "date":     "15.08.2025",
        "package":  "Стандарт",
        "price":    "100 000 ₽"
    }
    """
    try:
        data = await request.json()
    except Exception:
        logger.warning("Webhook: не удалось разобрать JSON")
        return web.json_response({'ok': False, 'error': 'Invalid JSON'}, status=400)

    app_id = str(uuid.uuid4())
    app = {
        'id':         app_id,
        'status':     STATUS_NEW,
        'created_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
        'updated_at': None,
        'service':    str(data.get('service', '—')),
        'name':       str(data.get('name',    '—')),
        'phone':      str(data.get('phone',   '—')),
        'guests':     str(data.get('guests',  '—')),
        'date':       str(data.get('date',    '—')),
        'package':    str(data.get('package', '')) or None,
        'price':      str(data.get('price',   '')) or None,
    }
    applications[app_id] = app

    logger.info("Новая заявка %s от %s (%s)", app_id[:8].upper(), app['name'], app['phone'])

    # Отправляем заявку администратору
    bot: Bot = request.app['bot']
    text     = format_application(app)
    keyboard = build_status_keyboard(app_id, STATUS_NEW)

    try:
        sent = await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
        app['message_id'] = sent.message_id
    except Exception as e:
        logger.error("Ошибка при отправке заявки администратору: %s", e)
        return web.json_response({'ok': False, 'error': str(e)}, status=500)

    return web.json_response({'ok': True, 'app_id': app_id})


async def handle_telegram_webhook(request: web.Request) -> web.Response:
    """
    POST /webhook/telegram
    Принимает входящие обновления от Telegram и передаёт их в Application.
    """
    try:
        data = await request.json()
    except Exception:
        logger.warning("Telegram webhook: не удалось разобрать JSON")
        return web.json_response({'ok': False, 'error': 'Invalid JSON'}, status=400)

    tg_app = request.app['tg_app']
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return web.json_response({'ok': True})


async def handle_health(request: web.Request) -> web.Response:
    """GET /health — проверка работоспособности сервиса."""
    return web.json_response({
        'ok':               True,
        'applications':     len(applications),
        'timestamp':        datetime.now().isoformat(),
    })


async def run_admin_bot() -> None:
    """Запуск admin-бота вместе с aiohttp-сервером для приёма webhook-заявок."""
    if not ADMIN_BOT_TOKEN:
        raise ValueError(
            "TELEGRAM_ADMIN_BOT_TOKEN не установлен! "
            "Задайте переменную окружения перед запуском."
        )

    # ── Telegram Application ──────────────────────────────────────────────────
    tg_app = Application.builder().token(ADMIN_BOT_TOKEN).build()

    tg_app.add_handler(CommandHandler('start',        cmd_start))
    tg_app.add_handler(CommandHandler('applications', cmd_applications))
    tg_app.add_handler(CallbackQueryHandler(cb_status_update,     pattern=r'^status:'))
    tg_app.add_handler(CallbackQueryHandler(cb_list_applications, pattern=r'^list_applications$'))

    # Инициализируем приложение до запуска web-сервера
    await tg_app.initialize()
    await tg_app.start()
    logger.info("Telegram Application инициализирован.")

    # ── aiohttp Web Application ───────────────────────────────────────────────
    web_app = web.Application()
    web_app['bot']    = tg_app.bot
    web_app['tg_app'] = tg_app

    web_app.router.add_post('/webhook/telegram',     handle_telegram_webhook)
    web_app.router.add_post('/webhook/application',  handle_application_webhook)
    web_app.router.add_get('/health',                handle_health)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, WEBHOOK_HOST, WEBHOOK_PORT)
    await site.start()
    logger.info("HTTP-сервер запущен на http://%s:%s", WEBHOOK_HOST, WEBHOOK_PORT)

    # ── Регистрируем webhook в Telegram ──────────────────────────────────────
    if WEBHOOK_BASE_URL:
        webhook_url = f"{WEBHOOK_BASE_URL.rstrip('/')}/webhook/telegram"
        await tg_app.bot.set_webhook(webhook_url)
        logger.info("Telegram webhook зарегистрирован: %s", webhook_url)
    else:
        logger.warning(
            "WEBHOOK_BASE_URL не задан — webhook не зарегистрирован. "
            "Бот не будет получать обновления от Telegram."
        )

    # ── Shutdown event — сигнализирует о завершении работы ───────────────────
    shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_event.set)
        except NotImplementedError:
            # Windows не поддерживает add_signal_handler
            pass

    # Event loop полностью свободен для обработки HTTP-запросов aiohttp.
    try:
        await shutdown_event.wait()
    finally:
        logger.info("Остановка admin-бота…")
        await tg_app.stop()
        await tg_app.shutdown()
        await runner.cleanup()
        logger.info("Admin-бот остановлен.")


def main() -> None:
    """Точка входа: запускает event loop с run_admin_bot()."""
    asyncio.run(run_admin_bot())


if __name__ == '__main__':
    main()
