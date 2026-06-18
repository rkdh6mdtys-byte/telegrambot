import asyncio
import logging
import os
from datetime import datetime
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ADMIN_BOT_TOKEN = os.getenv('TELEGRAM_ADMIN_BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '6133417158'))
PORT = int(os.getenv('ADMIN_BOT_PORT', '8081'))

# Хранилище заявок в памяти
applications = {}

# Статусы заявок
STATUSES = {
    'new':     ('🆕', 'Новая'),
    'working': ('⏳', 'В работе'),
    'done':    ('✅', 'Завершена'),
}

def status_label(status: str) -> str:
    """Вернуть строку вида «🆕 Новая» для переданного статуса."""
    emoji, name = STATUSES.get(status, STATUSES['new'])
    return f"{emoji} {name}"

def status_keyboard(app_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для смены статуса заявки."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🆕 Новая",    callback_data=f"status_new_{app_id}"),
        InlineKeyboardButton("⏳ В работе", callback_data=f"status_working_{app_id}"),
        InlineKeyboardButton("✅ Завершена", callback_data=f"status_done_{app_id}"),
    ]])

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start"""
    text = (
        "👋 <b>Добро пожаловать в панель администратора ВОЛНЫ!</b>\n\n"
        "Этот бот получает заявки с основного бота.\n\n"
        "<b>Команды:</b>\n"
        "/start — показать эту инструкцию\n"
        "/applications — список всех заявок со статусами\n"
        "/status — фильтр заявок по статусу\n\n"
        "<b>Статусы заявок:</b>\n"
        "🆕 Новая — только что поступила\n"
        "⏳ В работе — менеджер взял в работу\n"
        "✅ Завершена — заявка закрыта\n"
    )
    await update.message.reply_text(text, parse_mode='HTML')

async def cmd_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /applications - список всех заявок"""
    if not applications:
        await update.message.reply_text("📭 Заявок пока нет.", parse_mode='HTML')
        return
    
    text = "<b>📋 ВСЕ ЗАЯВКИ</b>\n\n"
    for app_id, app in sorted(applications.items(), key=lambda x: x[1]['created_at'], reverse=True):
        text += f"<b>#{app_id}</b> {status_label(app.get('status', 'new'))}\n"
        text += f"<b>Имя:</b> {app['name']}\n"
        text += f"<b>Телефон:</b> {app['phone']}\n"
        text += f"<b>Услуга:</b> {app['service']}\n"
        text += f"<b>Дата:</b> {app['date']}\n"
        text += f"<b>Гостей:</b> {app['guests']}\n"
        text += f"<b>Пакет:</b> {app['package']}\n"
        text += f"<b>Цена:</b> {app['price']}\n"
        text += f"<b>Время:</b> {app['created_at']}\n\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /status — список заявок, сгруппированных по статусу."""
    if not applications:
        await update.message.reply_text("📭 Заявок пока нет.", parse_mode='HTML')
        return

    sections = []
    for status_key, (emoji, label) in STATUSES.items():
        apps = [
            (app_id, app)
            for app_id, app in sorted(
                applications.items(),
                key=lambda x: x[1]['created_at'],
                reverse=True,
            )
            if app.get('status', 'new') == status_key
        ]
        if not apps:
            continue
        block = f"<b>{emoji} {label.upper()} ({len(apps)})</b>\n"
        for app_id, app in apps:
            block += (
                f"  <b>#{app_id}</b> — {app['name']}, {app['phone']}\n"
                f"  {app['service']} · {app['date']} · {app['package']}\n"
            )
        sections.append(block)

    text = "<b>📊 ЗАЯВКИ ПО СТАТУСАМ</b>\n\n" + "\n".join(sections)
    await update.message.reply_text(text, parse_mode='HTML')


async def callback_status_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """CallbackQuery: status_<new|working|done>_<app_id>"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_', 2)   # ['status', '<key>', '<app_id>']
    if len(parts) != 3:
        return

    _, new_status, app_id = parts
    if new_status not in STATUSES:
        return
    if app_id not in applications:
        await query.answer("Заявка не найдена.", show_alert=True)
        return

    applications[app_id]['status'] = new_status
    app = applications[app_id]
    logger.info(f"Статус заявки #{app_id} изменён на «{new_status}»")

    # Обновляем сообщение с новым статусом
    text = (
        f"<b>📋 ЗАЯВКА #{app_id}</b>\n\n"
        f"<b>Статус:</b> {status_label(new_status)}\n"
        f"<b>Имя:</b> {app['name']}\n"
        f"<b>Телефон:</b> {app['phone']}\n"
        f"<b>Услуга:</b> {app['service']}\n"
        f"<b>Дата:</b> {app['date']}\n"
        f"<b>Гостей:</b> {app['guests']}\n"
        f"<b>Пакет:</b> {app['package']}\n"
        f"<b>Цена:</b> {app['price']}\n"
        f"<b>Время:</b> {app['created_at']}\n"
    )
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=status_keyboard(app_id),
    )


async def handle_application(request: web.Request) -> web.Response:
    """POST /webhook/application - получить заявку от telegram-bot'а"""
    try:
        data = await request.json()
        app_id = str(len(applications) + 1)
        
        applications[app_id] = {
            'name': data.get('name', '—'),
            'phone': data.get('phone', '—'),
            'service': data.get('service', '—'),
            'date': data.get('date', '—'),
            'guests': data.get('guests', '—'),
            'package': data.get('package', '—'),
            'price': data.get('price', '—'),
            'created_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'status': 'new',
        }
        
        logger.info(f"✅ Новая заявка #{app_id} от {data.get('name')}")
        
        # Отправляем администратору
        app = applications[app_id]
        text = (
            f"<b>📋 НОВАЯ ЗАЯВКА #{app_id}</b>\n\n"
            f"<b>Статус:</b> {status_label(app['status'])}\n"
            f"<b>Имя:</b> {app['name']}\n"
            f"<b>Телефон:</b> {app['phone']}\n"
            f"<b>Услуга:</b> {app['service']}\n"
            f"<b>Дата:</b> {app['date']}\n"
            f"<b>Гостей:</b> {app['guests']}\n"
            f"<b>Пакет:</b> {app['package']}\n"
            f"<b>Цена:</b> {app['price']}\n"
            f"<b>Время:</b> {app['created_at']}\n"
        )
        
        await request.app['bot'].send_message(
            ADMIN_CHAT_ID, text,
            parse_mode='HTML',
            reply_markup=status_keyboard(app_id),
        )
        logger.info(f"✅ Заявка отправлена администратору")
        
        return web.json_response({'ok': True, 'app_id': app_id})
    except Exception as e:
        logger.error(f"❌ Ошибка при получении заявки: {e}")
        return web.json_response({'ok': False, 'error': str(e)}, status=500)

async def handle_health(request: web.Request) -> web.Response:
    """GET /health - проверка здоровья"""
    return web.json_response({'ok': True, 'applications': len(applications)})

async def main():
    """Главная функция"""
    if not ADMIN_BOT_TOKEN:
        raise ValueError("TELEGRAM_ADMIN_BOT_TOKEN не установлен!")
    
    logger.info("🚀 Запуск admin-bot'а...")
    
    # Telegram Application
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('applications', cmd_applications))
    app.add_handler(CommandHandler('status', cmd_status))
    app.add_handler(CallbackQueryHandler(callback_status_change, pattern=r'^status_(new|working|done)_'))
    
    # HTTP сервер для приёма заявок
    web_app = web.Application()
    web_app['bot'] = app.bot
    web_app.router.add_post('/webhook/application', handle_application)
    web_app.router.add_get('/health', handle_health)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"✅ HTTP-сервер запущен на порту {PORT}")
    
    # Запускаем бота
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("✅ Polling запущен. Бот готов к работе.")
        
        # Ждём сигнала завершения
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("⏹ Получен сигнал завершения")
        finally:
            await app.updater.stop()
            await app.stop()
    
    await runner.cleanup()
    logger.info("✅ Admin-bot остановлен")

if __name__ == '__main__':
    asyncio.run(main())
