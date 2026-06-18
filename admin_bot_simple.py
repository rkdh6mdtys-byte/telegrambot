import asyncio
import logging
import os
from datetime import datetime
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ADMIN_BOT_TOKEN = os.getenv('TELEGRAM_ADMIN_BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '6133417158'))
PORT = int(os.getenv('ADMIN_BOT_PORT', '8081'))

# In-memory storage
applications = {}

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👋 Admin bot started!")

async def cmd_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not applications:
        await update.message.reply_text("📭 No applications yet.")
        return
    
    text = "📋 **ALL APPLICATIONS**\n\n"
    for app_id, app in applications.items():
        text += f"• {app['name']} ({app['phone']})\n"
        text += f"  Service: {app['service']}\n"
        text += f"  Date: {app['date']}\n\n"
    
    await update.message.reply_text(text)

async def handle_application(request: web.Request) -> web.Response:
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
        }
        
        logger.info(f"New application: {app_id} from {data.get('name')}")
        
        # Send to admin
        app = applications[app_id]
        text = f"📋 NEW APPLICATION\n\n"
        text += f"Name: {app['name']}\n"
        text += f"Phone: {app['phone']}\n"
        text += f"Service: {app['service']}\n"
        text += f"Date: {app['date']}\n"
        text += f"Guests: {app['guests']}\n"
        text += f"Package: {app['package']}\n"
        text += f"Price: {app['price']}\n"
        
        await request.app['bot'].send_message(ADMIN_CHAT_ID, text)
        
        return web.json_response({'ok': True, 'app_id': app_id})
    except Exception as e:
        logger.error(f"Error: {e}")
        return web.json_response({'ok': False, 'error': str(e)}, status=500)

async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({'ok': True, 'apps': len(applications)})

async def main():
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('applications', cmd_applications))
    
    # HTTP server
    web_app = web.Application()
    web_app['bot'] = app.bot
    web_app.router.add_post('/webhook/application', handle_application)
    web_app.router.add_get('/health', handle_health)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"HTTP server started on port {PORT}")
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Polling started")
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            await app.updater.stop()
    
    await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
