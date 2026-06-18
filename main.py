import asyncio
import logging
import os
import re
import signal
import uuid
from datetime import datetime

import aiohttp
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Состояния ConversationHandler ───────────────────────────────────────────
(
    CHOOSING_SERVICE,
    ENTERING_NAME,
    ENTERING_GUESTS,
    CONFIRMING_PACKAGE,
    CHOOSING_PACKAGE_MANUAL,
    ENTERING_DATE,
    ENTERING_PHONE,
) = range(7)

# ID администратора
ADMIN_ID = 6133417158

# URL вебхука admin-бота для передачи заявок
ADMIN_BOT_WEBHOOK_URL = os.getenv(
    'ADMIN_BOT_WEBHOOK_URL',
    'https://admin-bot-production-xxx.railway.app/webhook/application',
)

# Конфигурация HTTP-сервера (для приёма заявок с формы)
HTTP_PORT = int(os.getenv('PORT', '8080'))
HTTP_HOST = os.getenv('HOST', '0.0.0.0')

# ─── Пакеты услуг ─────────────────────────────────────────────────────────────
PACKAGES = {
    'basic': {
        'name': 'Базовый',
        'emoji': '🥂',
        'barmen': 1,
        'guests_label': 'до 30 человек',
        'guests_max': 30,
        'cocktails': 100,
        'extras': [],
        'price': '65 000 ₽',
        'price_int': 65000,
    },
    'standard': {
        'name': 'Стандарт',
        'emoji': '🍸',
        'barmen': 1,
        'guests_label': 'до 100 человек',
        'guests_max': 100,
        'cocktails': 200,
        'extras': [],
        'price': '100 000 ₽',
        'price_int': 100000,
    },
    'premium': {
        'name': 'Премиум',
        'emoji': '✨',
        'barmen': 2,
        'guests_label': '100+ человек',
        'guests_max': 9999,
        'cocktails': '200+',
        'extras': ['4 авторские настойки по 1 л', '6 л фирменного лимонада'],
        'price': '125 000 ₽',
        'price_int': 125000,
    },
}

def suggest_package(guests: int) -> str:
    """Подобрать пакет по количеству гостей."""
    if guests <= 30:
        return 'basic'
    elif guests <= 100:
        return 'standard'
    else:
        return 'premium'

def package_detail_text(key: str) -> str:
    """Полное описание пакета."""
    p = PACKAGES[key]
    lines = [
        f"{p['emoji']} <b>Пакет «{p['name']}»</b>",
        "",
        f"👥 Гостей: {p['guests_label']}",
        f"🧑‍🍳 Барменов: {p['barmen']}",
        f"🍹 Коктейлей: {p['cocktails']}",
    ]
    for extra in p['extras']:
        lines.append(f"➕ {extra}")
    lines += ["", f"💰 Стоимость: <b>{p['price']}</b>"]
    return "\n".join(lines)

# ─── Валидация ────────────────────────────────────────────────────────────────

def validate_phone(phone: str) -> bool:
    """Проверяет, что телефон содержит ровно 11 цифр."""
    digits = re.sub(r'\D', '', phone)
    return len(digits) == 11

def validate_date(date_str: str) -> bool:
    """
    Проверяет формат ДД.ММ.202Х и корректность даты.
    Принимает годы 2020–2029.
    """
    if not re.fullmatch(r'\d{2}\.\d{2}\.202\d', date_str):
        return False
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
        return True
    except ValueError:
        return False

# ─── Отзывы ───────────────────────────────────────────────────────────────────
REVIEWS = [
    {
        'name': 'Александр М.',
        'text': 'Отличный сервис! Бармены профессионалы, коктейли вкусные. Свадьба прошла на 5+. Рекомендую!',
        'rating': '⭐⭐⭐⭐⭐',
    },
    {
        'name': 'Елена К.',
        'text': 'Корпоратив был супер! Безалкогольные коктейли тоже порадовали. Спасибо!',
        'rating': '⭐⭐⭐⭐',
    },
    {
        'name': 'Иван П.',
        'text': 'Профессионалы своего дела. Мероприятие организовано идеально. Гости в восторге от коктейлей.',
        'rating': '⭐⭐⭐⭐⭐',
    },
    {
        'name': 'Мария Л.',
        'text': 'Хороший сервис, качество на высоте. Бармены сами предлагали коктейли — очень удобно!',
        'rating': '⭐⭐⭐⭐',
    },
    {
        'name': 'Дмитрий В.',
        'text': 'Заказывали на день рождения. Бармены креативные, коктейли необычные. Все гости спрашивали рецепты!',
        'rating': '⭐⭐⭐⭐⭐',
    },
    {
        'name': 'Ольга С.',
        'text': 'Всё прошло отлично, бармены работали без остановки весь вечер. Гости были в восторге.',
        'rating': '⭐⭐⭐⭐⭐',
    },
]

# ─── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Стартовое сообщение."""
    welcome_text = (
        "🌊 <b>ВОЛНЫ</b>\n"
        "<b>Коктейльный сервис и вино</b>\n\n"
        "🍸 Авторские коктейли\n"
        "🍷 Винные дегустации\n"
        "🎲 Винное казино\n"
        "📍 Владивосток\n\n"
        "Нажмите кнопку ниже, чтобы начать."
    )
    keyboard = [[InlineKeyboardButton("Открыть меню", callback_data='menu')]]
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

# ─── Главное меню ─────────────────────────────────────────────────────────────
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("🎯 Услуги",           callback_data='services'),
            InlineKeyboardButton("🍹 Коктейльная карта", callback_data='cocktails'),
        ],
        [
            InlineKeyboardButton("🎉 Винные мероприятия", callback_data='wine_events'),
            InlineKeyboardButton("💰 Стоимость",          callback_data='pricing'),
        ],
        [
            InlineKeyboardButton("🛎 Сервис",      callback_data='service_info'),
            InlineKeyboardButton("➕ Доп. услуги", callback_data='extra_services'),
        ],
        [
            InlineKeyboardButton("📸 Наши работы", callback_data='portfolio'),
            InlineKeyboardButton("⭐ Отзывы",      callback_data='reviews'),
        ],
        [InlineKeyboardButton("🖼️ Презентация",    callback_data='presentation')],
        [InlineKeyboardButton("📝 Оставить заявку", callback_data='application')],
    ]
    await query.edit_message_text(
        "Выберите раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

def _main_menu_button() -> list:
    return [[InlineKeyboardButton("🏠 Главное меню", callback_data='menu')]]

# ─── Услуги (вход в ConversationHandler) ─────────────────────────────────────
async def services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Раздел услуг — выбор типа мероприятия."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("💒 Свадьба",              callback_data='service_wedding'),
            InlineKeyboardButton("🏢 Корпоративы",          callback_data='service_corporate'),
        ],
        [
            InlineKeyboardButton("🎂 Частные мероприятия",  callback_data='service_private'),
            InlineKeyboardButton("☕ Кофе-брейки",           callback_data='service_coffee'),
        ],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='menu')],
    ]
    await query.edit_message_text(
        "🎯 <b>УСЛУГИ</b>\n\nВыберите тип мероприятия:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return CHOOSING_SERVICE

async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбран тип услуги → запрашиваем имя."""
    query = update.callback_query
    await query.answer()

    service_map = {
        'service_wedding':   '💒 Свадьба',
        'service_corporate': '🏢 Корпоратив',
        'service_private':   '🎂 Частное мероприятие',
        'service_coffee':    '☕ Кофе-брейк',
    }
    context.user_data['service'] = service_map.get(query.data, 'Мероприятие')

    await query.edit_message_text(
        f"Вы выбрали: <b>{context.user_data['service']}</b>\n\n"
        "Как вас зовут?",
        parse_mode=ParseMode.HTML,
    )
    return ENTERING_NAME

async def entering_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод имени → запрашиваем количество гостей."""
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("Сколько гостей будет на мероприятии?")
    return ENTERING_GUESTS

async def entering_guests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод количества гостей → предлагаем пакет."""
    try:
        guests = int(update.message.text.strip())
        if guests <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число гостей.")
        return ENTERING_GUESTS

    context.user_data['guests'] = guests
    suggested_key = suggest_package(guests)
    context.user_data['suggested_package'] = suggested_key
    p = PACKAGES[suggested_key]

    text = (
        f"На основе <b>{guests} гостей</b> мы рекомендуем:\n\n"
        + package_detail_text(suggested_key)
        + "\n\nПодходит этот пакет?"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, подходит",    callback_data=f'confirm_package_{suggested_key}'),
            InlineKeyboardButton("🔄 Выбрать другой", callback_data='change_package'),
        ],
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return CONFIRMING_PACKAGE

async def confirm_package(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пользователь подтвердил предложенный пакет → запрашиваем дату."""
    query = update.callback_query
    await query.answer()

    package_key = query.data.replace('confirm_package_', '')
    context.user_data['package_key'] = package_key

    await query.edit_message_text(
        f"Отлично! Пакет <b>«{PACKAGES[package_key]['name']}»</b> выбран.\n\n"
        "На какую дату планируется мероприятие? (формат: ДД.ММ.ГГГГ)",
        parse_mode=ParseMode.HTML,
    )
    return ENTERING_DATE

async def change_package(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пользователь хочет выбрать пакет вручную."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("🥂 Базовый",  callback_data='manual_package_basic'),
            InlineKeyboardButton("🍸 Стандарт", callback_data='manual_package_standard'),
            InlineKeyboardButton("✨ Премиум",  callback_data='manual_package_premium'),
        ],
    ]
    await query.edit_message_text(
        "Выберите пакет:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_PACKAGE_MANUAL

async def manual_package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ручной выбор пакета → показываем описание и просим подтвердить."""
    query = update.callback_query
    await query.answer()

    package_key = query.data.replace('manual_package_', '')
    context.user_data['package_key'] = package_key

    text = (
        package_detail_text(package_key)
        + "\n\nПодтвердите выбор этого пакета:"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f'confirm_package_{package_key}'),
            InlineKeyboardButton("🔄 Выбрать другой", callback_data='change_package'),
        ],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return CONFIRMING_PACKAGE

async def entering_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод даты → запрашиваем телефон."""
    date_str = update.message.text.strip()
    if not validate_date(date_str):
        await update.message.reply_text(
            "⚠️ Неверный формат даты.\n\n"
            "Пожалуйста, введите дату в формате <b>ДД.ММ.202Х</b>\n"
            "Пример: <b>15.08.2025</b>",
            parse_mode=ParseMode.HTML,
        )
        return ENTERING_DATE
    context.user_data['date'] = date_str
    await update.message.reply_text("Ваш номер телефона для связи?")
    return ENTERING_PHONE

async def entering_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод телефона → отправляем заявку."""
    phone_str = update.message.text.strip()
    if not validate_phone(phone_str):
        await update.message.reply_text(
            "⚠️ Телефон должен содержать ровно 11 цифр.\n\n"
            "Пожалуйста, введите номер ещё раз.\n"
            "Пример: <b>89241234567</b> или <b>+7 924 123-45-67</b>",
            parse_mode=ParseMode.HTML,
        )
        return ENTERING_PHONE
    context.user_data['phone'] = phone_str

    # Сохраняем username пользователя Telegram
    tg_user = update.effective_user
    username = tg_user.username if tg_user and tg_user.username else None

    package_key = context.user_data.get('package_key', 'basic')
    package = PACKAGES[package_key]

    username_display = f"@{username}" if username else "—"

    # Заявка для администратора
    admin_text = (
        "<b>📋 НОВАЯ ЗАЯВКА</b>\n\n"
        f"<b>Услуга:</b> {context.user_data.get('service', '—')}\n"
        f"<b>Имя:</b> {context.user_data.get('name', '—')}\n"
        f"<b>Username:</b> {username_display}\n"
        f"<b>Телефон:</b> {context.user_data.get('phone', '—')}\n"
        f"<b>Гостей:</b> {context.user_data.get('guests', '—')}\n"
        f"<b>Дата:</b> {context.user_data.get('date', '—')}\n\n"
        f"<b>Пакет:</b> {package['name']}\n"
        f"<b>Цена:</b> {package['price']}\n"
        f"<b>Барменов:</b> {package['barmen']}\n"
        f"<b>Коктейлей:</b> {package['cocktails']}\n\n"
        f"<b>Время заявки:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке заявки администратору: {e}")

    # Отправляем заявку в admin-бот через webhook
    webhook_payload = {
        'service':  context.user_data.get('service', '—'),
        'name':     context.user_data.get('name',    '—'),
        'username': username or '',
        'phone':    context.user_data.get('phone',   '—'),
        'guests':   context.user_data.get('guests',  '—'),
        'date':     context.user_data.get('date',    '—'),
        'package':  package['name'],
        'price':    package['price'],
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ADMIN_BOT_WEBHOOK_URL,
                json=webhook_payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    logger.info("Заявка успешно отправлена в admin-бот (статус %s)", resp.status)
                else:
                    logger.warning("Admin-бот вернул неожиданный статус %s", resp.status)
    except Exception as e:
        logger.error("Ошибка при отправке заявки в admin-бот: %s", e)

    # Подтверждение пользователю
    confirm_text = (
        "✅ <b>Спасибо за заявку!</b>\n\n"
        f"<b>Услуга:</b> {context.user_data.get('service', '—')}\n"
        f"<b>Имя:</b> {context.user_data.get('name', '—')}\n"
        f"<b>Телефон:</b> {context.user_data.get('phone', '—')}\n"
        f"<b>Гостей:</b> {context.user_data.get('guests', '—')}\n"
        f"<b>Дата:</b> {context.user_data.get('date', '—')}\n"
        f"<b>Пакет:</b> {package['name']}\n"
        f"<b>Цена:</b> {package['price']}\n\n"
        "Менеджер свяжется с вами в ближайшее время! 🌊"
    )
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data='menu')]]
    await update.message.reply_text(
        confirm_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END

# ─── Прямая заявка из меню (без выбора услуги) ────────────────────────────────
async def application_direct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Заявка напрямую из главного меню — пропускаем выбор услуги."""
    query = update.callback_query
    await query.answer()

    context.user_data['service'] = '📝 Заявка из меню'
    await query.edit_message_text(
        "📝 <b>ОСТАВИТЬ ЗАЯВКУ</b>\n\nКак вас зовут?",
        parse_mode=ParseMode.HTML,
    )
    return ENTERING_NAME

# ─── Коктейльная карта ────────────────────────────────────────────────────────
async def cocktails(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню коктейльной карты."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("🍹 Коктейли",        callback_data='cocktails_alcoholic'),
            InlineKeyboardButton("🥤 Безалкогольные",  callback_data='cocktails_nonalcoholic'),
        ],
        [InlineKeyboardButton("🎭 Презентация",        callback_data='cocktails_presentation')],
        [InlineKeyboardButton("🏠 Главное меню",       callback_data='menu')],
    ]
    await query.edit_message_text(
        "🍹 <b>КОКТЕЙЛЬНАЯ КАРТА</b>\n\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

async def cocktails_alcoholic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Список алкогольных коктейлей."""
    query = update.callback_query
    await query.answer()

    text = (
        "🍹 <b>КОКТЕЙЛИ (20+)</b>\n\n"
        "• Маргарита\n"
        "• Мохито\n"
        "• Дайкири\n"
        "• Космополитен\n"
        "• Негрони\n"
        "• Апероль Шприц\n"
        "• Гимлет\n"
        "• Олд Фэшн\n"
        "• Манхэттен\n"
        "• Мартини\n"
        "• Пина Колада\n"
        "• Кайпиринья\n"
        "• Кровавая Мэри\n"
        "• Виски Сауэр\n"
        "• Сазерак\n"
        "• Сайдкар\n"
        "• Корпс Ревайвер\n"
        "• Вьё Карре\n"
        "• Клевер Клаб\n"
        "• Авиация\n"
    )
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад к карте", callback_data='cocktails')],
        [InlineKeyboardButton("🏠 Главное меню",  callback_data='menu')],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

async def cocktails_nonalcoholic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Список безалкогольных коктейлей."""
    query = update.callback_query
    await query.answer()

    text = (
        "🥤 <b>БЕЗАЛКОГОЛЬНЫЕ КОКТЕЙЛИ</b>\n\n"
        "<i>Все напитки с префиксом «Virgin» — полноценные коктейли без алкоголя, "
        "сохраняющие вкус и подачу оригинала.</i>\n\n"
        "• Virgin Негрони\n"
        "• Virgin Дайкири\n"
        "• Virgin Нью-Йорк Сауэр\n"
        "• Virgin Виски Сауэр\n"
        "• Virgin Мохито\n"
        "• Virgin Апероль Шприц\n"
        "• Virgin Гимлет\n"
    )
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад к карте", callback_data='cocktails')],
        [InlineKeyboardButton("🏠 Главное меню",  callback_data='menu')],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

async def cocktails_presentation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Презентация коктейльного сервиса."""
    query = update.callback_query
    await query.answer()

    text = (
        "🎭 <b>ПРЕЗЕНТАЦИЯ</b>\n\n"
        "Каждый коктейль — это маленький спектакль. Наши бармены работают "
        "с открытой барной стойкой: гости видят весь процесс приготовления, "
        "от выбора ингредиентов до финального украшения.\n\n"
        "Мы используем только свежие соки, натуральные сиропы и качественный "
        "алкоголь. Никаких готовых миксов — только живой вкус.\n\n"
        "📍 Стойка устанавливается в любом месте площадки.\n"
        "⏱ Время приготовления одного коктейля — 1–2 минуты.\n"
        "🎨 Каждый напиток оформляется индивидуально."
    )
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад к карте", callback_data='cocktails')],
        [InlineKeyboardButton("📝 Оставить заявку", callback_data='application')],
        [InlineKeyboardButton("🏠 Главное меню",    callback_data='menu')],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

# ─── Винные мероприятия ───────────────────────────────────────────────────────
async def wine_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню винных мероприятий."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("🍷 Дегустация",  callback_data='wine_tasting'),
            InlineKeyboardButton("🎲 Винное казино", callback_data='wine_casino'),
        ],
        [InlineKeyboardButton("🍽 Винный пейринг", callback_data='wine_pairing')],
        [InlineKeyboardButton("🏠 Главное меню",   callback_data='menu')],
    ]
    await query.edit_message_text(
        "🍷 <b>ВИННЫЕ МЕРОПРИЯТИЯ</b>\n\nВыберите формат:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

async def wine_tasting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Винная дегустация."""
    query = update.callback_query
    await query.answer()

    text = (
        "🍷 <b>ВИННАЯ ДЕГУСТАЦИЯ</b>\n\n"
        "Профессиональная дегустация под руководством сомелье. "
        "Вы узнаете историю вина, научитесь определять сорта и регионы, "
        "откроете для себя новые вкусы.\n\n"
        "👥 Группа: 8–12 человек\n"
        "💰 Стоимость: <b>4 000 ₽ с человека</b>\n"
        "⏱ Продолжительность: ~2 часа\n\n"
        "<i>В стоимость включены дегустационные образцы, закуски и авторский гид по винам.</i>"
    )
    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку",    callback_data='application')],
        [InlineKeyboardButton("⬅️ Назад к мероприятиям", callback_data='wine_events')],
        [InlineKeyboardButton("🏠 Главное меню",        callback_data='menu')],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

async def wine_casino(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Винное казино."""
    query = update.callback_query
    await query.answer()

    text = (
        "🎲 <b>ВИННОЕ КАЗИНО</b>\n\n"
        "Интерактивная игра с дегустацией редких вин. Гости угадывают "
        "сорт, регион и год урожая — победитель получает приз. "
        "Идеально для корпоративов и вечеринок.\n\n"
        "💰 Стоимость: <b>30 000 ₽</b> (фиксированная цена)\n"
        "👥 Количество участников: без ограничений\n"
        "⏱ Продолжительность: ~1,5 часа\n\n"
        "<i>В стоимость включены все вина, реквизит и ведущий.</i>"
    )
    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку",    callback_data='application')],
        [InlineKeyboardButton("⬅️ Назад к мероприятиям", callback_data='wine_events')],
        [InlineKeyboardButton("🏠 Главное меню",        callback_data='menu')],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

async def wine_pairing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Винный пейринг."""
    query = update.callback_query
    await query.answer()

    text = (
        "🍽 <b>ВИННЫЙ ПЕЙРИНГ</b>\n\n"
        "Искусство сочетания вина и еды. Наш сомелье подберёт вина "
        "к каждому блюду вашего меню, объяснит логику сочетаний и "
        "сделает ужин незабываемым.\n\n"
        "✅ Подходит для: свадебных ужинов, корпоративных банкетов, "
        "частных вечеринок\n\n"
        "💬 Стоимость рассчитывается индивидуально — зависит от меню "
        "и количества гостей. Оставьте заявку, и мы свяжемся с вами."
    )
    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку",    callback_data='application')],
        [InlineKeyboardButton("⬅️ Назад к мероприятиям", callback_data='wine_events')],
        [InlineKeyboardButton("🏠 Главное меню",        callback_data='menu')],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

# ─── Стоимость ────────────────────────────────────────────────────────────────
async def pricing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Раздел стоимости — выбор пакета."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("🥂 Базовый",  callback_data='pricing_basic'),
            InlineKeyboardButton("🍸 Стандарт", callback_data='pricing_standard'),
            InlineKeyboardButton("✨ Премиум",  callback_data='pricing_premium'),
        ],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='menu')],
    ]
    await query.edit_message_text(
        "💰 <b>СТОИМОСТЬ УСЛУГ</b>\n\nВыберите пакет для подробного описания:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

async def pricing_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Детали конкретного пакета."""
    query = update.callback_query
    await query.answer()

    package_key = query.data.replace('pricing_', '')
    text = package_detail_text(package_key) + "\n\n<i>Точная стоимость рассчитывается индивидуально.</i>"

    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку",  callback_data='application')],
        [InlineKeyboardButton("⬅️ Назад к ценам",   callback_data='pricing')],
        [InlineKeyboardButton("🏠 Главное меню",     callback_data='menu')],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

# ─── Сервис ───────────────────────────────────────────────────────────────────
async def service_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Раздел «Сервис» — философия работы барменов."""
    query = update.callback_query
    await query.answer()

    text = (
        "🛎 <b>СЕРВИС</b>\n\n"
        "Наши бармены — это не просто люди за стойкой. Это специалисты "
        "по коктейлям, которые сопровождают ваше мероприятие от первого "
        "до последнего гостя.\n\n"
        "<b>Как это работает:</b>\n"
        "Бармен не ждёт, пока к нему подойдут. Он сам выходит к гостям, "
        "знакомится с предпочтениями и предлагает подходящий коктейль — "
        "алкогольный или безалкогольный. Гостям не нужно ничего просить: "
        "всё происходит само собой.\n\n"
        "<b>Что входит в сервис:</b>\n"
        "• Установка и оформление барной стойки\n"
        "• Полное обслуживание в течение всего мероприятия\n"
        "• Индивидуальный подход к каждому гостю\n"
        "• Авторские рекомендации по коктейлям\n"
        "• Уборка рабочего места после окончания\n\n"
        "<i>Мы работаем так, чтобы вы и ваши гости ни о чём не думали — "
        "только наслаждались вечером.</i>"
    )
    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку", callback_data='application')],
        [InlineKeyboardButton("🏠 Главное меню",    callback_data='menu')],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

# ─── Дополнительные услуги ────────────────────────────────────────────────────
async def extra_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Раздел дополнительных услуг."""
    query = update.callback_query
    await query.answer()

    text = (
        "➕ <b>ДОПОЛНИТЕЛЬНЫЕ УСЛУГИ</b>\n\n"

        "🧊 <b>Ледяные скульптуры</b>\n"
        "Фигурный лёд, вырезанный вручную: сердца, якоря, инициалы, "
        "логотипы. Эффектный декор для барной стойки и фотозоны.\n"
        "<i>Стоимость — по запросу.</i>\n\n"

        "🎀 <b>Декоративная бумага</b>\n"
        "Фирменная упаковка для бутылок и подарочных наборов. "
        "Подходит для корпоративных сувениров и свадебных подарков.\n"
        "<i>Стоимость — по запросу.</i>\n\n"

        "🔷 <b>Фигурный лёд</b>\n"
        "Кубики, сферы, ромбы и нестандартные формы. Медленно тает, "
        "не разбавляет коктейль — только вкус и эстетика.\n"
        "<i>Стоимость — по запросу.</i>\n\n"

        "🍶 <b>Авторский сет</b>\n"
        "Набор из 4–6 авторских настоек на выбор: ягодные, пряные, "
        "цитрусовые. Готовятся специально под ваше мероприятие.\n"
        "<i>Стоимость — по запросу.</i>"
    )
    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку", callback_data='application')],
        [InlineKeyboardButton("🏠 Главное меню",    callback_data='menu')],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

# ─── Портфолио ────────────────────────────────────────────────────────────────
async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Наши работы."""
    query = update.callback_query
    await query.answer()

    text = (
        "📸 <b>НАШИ РАБОТЫ</b>\n\n"
        "Мы организовали более 150 мероприятий:\n"
        "• 45 свадеб\n"
        "• 60 корпоративных событий\n"
        "• 35 частных мероприятий\n"
        "• 15 винных дегустаций\n\n"
        "Все наши клиенты остались довольны качеством сервиса!\n\n"
        "Посмотрите отзывы наших клиентов ⭐"
    )
    keyboard = [
        [InlineKeyboardButton("⭐ Отзывы",       callback_data='reviews')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='menu')],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

# ─── Отзывы ───────────────────────────────────────────────────────────────────
async def reviews(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отзывы клиентов."""
    query = update.callback_query
    await query.answer()

    reviews_text = "⭐ <b>ОТЗЫВЫ КЛИЕНТОВ</b>\n\n"
    for review in REVIEWS:
        reviews_text += f"<b>{review['name']}</b> {review['rating']}\n"
        reviews_text += f"<i>{review['text']}</i>\n\n"

    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data='menu')]]
    await query.edit_message_text(
        reviews_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

# ─── Презентация ─────────────────────────────────────────────────────────────
PRESENTATION_PATH = os.path.join(os.path.dirname(__file__), 'presentations', 'presentation.pdf')

async def presentation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет файл презентации пользователю."""
    query = update.callback_query
    await query.answer()

    if not os.path.isfile(PRESENTATION_PATH):
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data='menu')]]
        await query.edit_message_text(
            "⚠️ Презентация временно недоступна. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data='menu')]]
    await query.edit_message_text(
        "🖼️ <b>ПРЕЗЕНТАЦИЯ</b>\n\nОтправляю файл…",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    with open(PRESENTATION_PATH, 'rb') as f:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=f,
            filename='presentation.pdf',
            caption="🖼️ <b>Презентация ВОЛНЫ</b>",
            parse_mode=ParseMode.HTML,
        )

# ─── Отмена ───────────────────────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога."""
    await update.message.reply_text(
        "Операция отменена. Введите /start для начала."
    )
    return ConversationHandler.END

# ─── Неизвестные сообщения ────────────────────────────────────────────────────
async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ на любое текстовое сообщение, не обработанное другими хендлерами."""
    await update.message.reply_text(
        "Я не понимаю эту команду 😕\n\nНажми /start чтобы начать заново"
    )


# ─── HTTP-обработчики (для приёма заявок с формы) ────────────────────────────

async def handle_application_webhook(request: web.Request) -> web.Response:
    """
    POST /webhook/application
    Принимает JSON с данными заявки от веб-формы и пересылает в admin-бот.

    Ожидаемый формат тела запроса (все поля опциональны):
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
    logger.info(
        "Новая заявка %s от %s (%s) — пересылаем в admin-бот",
        app_id[:8].upper(),
        data.get('name', '—'),
        data.get('phone', '—'),
    )

    # Пересылаем заявку в admin-бот
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ADMIN_BOT_WEBHOOK_URL,
                json=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    logger.info("Заявка успешно переслана в admin-бот (статус %s)", resp.status)
                else:
                    logger.warning("Admin-бот вернул неожиданный статус %s", resp.status)
                return web.json_response({'ok': True, 'app_id': app_id}, status=resp.status)
    except Exception as e:
        logger.error("Ошибка при пересылке заявки в admin-бот: %s", e)
        return web.json_response({'ok': False, 'error': str(e)}, status=500)


async def handle_health(request: web.Request) -> web.Response:
    """GET /health — проверка работоспособности сервиса."""
    return web.json_response({
        'ok':        True,
        'timestamp': datetime.now().isoformat(),
    })


# ─── Запуск ───────────────────────────────────────────────────────────────────

async def run_bot() -> None:
    """Инициализация и запуск бота в режиме polling + HTTP-сервер для заявок."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен!")

    # ── Telegram Application (polling mode) ──────────────────────────────────
    application = (
        Application.builder()
        .token(token)
        .build()
    )

    # ConversationHandler для заявок
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(services,           pattern='^services$'),
            CallbackQueryHandler(application_direct, pattern='^application$'),
        ],
        states={

            CHOOSING_SERVICE: [
                CallbackQueryHandler(service_selected, pattern='^service_'),
            ],
            ENTERING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, entering_name),
            ],
            ENTERING_GUESTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, entering_guests),
            ],
            CONFIRMING_PACKAGE: [
                CallbackQueryHandler(confirm_package,  pattern='^confirm_package_'),
                CallbackQueryHandler(change_package,   pattern='^change_package$'),
            ],
            CHOOSING_PACKAGE_MANUAL: [
                CallbackQueryHandler(manual_package_selected, pattern='^manual_package_'),
            ],
            ENTERING_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, entering_date),
            ],
            ENTERING_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, entering_phone),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(menu, pattern='^menu$'))
    application.add_handler(conv_handler)

    # Информационные разделы (вне диалога)
    application.add_handler(CallbackQueryHandler(cocktails,              pattern='^cocktails$'))
    application.add_handler(CallbackQueryHandler(cocktails_alcoholic,    pattern='^cocktails_alcoholic$'))
    application.add_handler(CallbackQueryHandler(cocktails_nonalcoholic, pattern='^cocktails_nonalcoholic$'))
    application.add_handler(CallbackQueryHandler(cocktails_presentation, pattern='^cocktails_presentation$'))
    application.add_handler(CallbackQueryHandler(wine_events,            pattern='^wine_events$'))
    application.add_handler(CallbackQueryHandler(wine_tasting,           pattern='^wine_tasting$'))
    application.add_handler(CallbackQueryHandler(wine_casino,            pattern='^wine_casino$'))
    application.add_handler(CallbackQueryHandler(wine_pairing,           pattern='^wine_pairing$'))
    application.add_handler(CallbackQueryHandler(pricing,                pattern='^pricing$'))
    application.add_handler(CallbackQueryHandler(pricing_detail,         pattern='^pricing_(basic|standard|premium)$'))
    application.add_handler(CallbackQueryHandler(service_info,           pattern='^service_info$'))
    application.add_handler(CallbackQueryHandler(extra_services,         pattern='^extra_services$'))
    application.add_handler(CallbackQueryHandler(portfolio,              pattern='^portfolio$'))
    application.add_handler(CallbackQueryHandler(reviews,                pattern='^reviews$'))
    application.add_handler(CallbackQueryHandler(presentation,           pattern='^presentation$'))

    # Catch-all: должен быть последним — отвечает на любые необработанные текстовые сообщения
    application.add_handler(MessageHandler(filters.TEXT, unknown_message))

    # ── Shutdown event ────────────────────────────────────────────────────────
    shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_event.set)
        except NotImplementedError:
            # Windows не поддерживает add_signal_handler
            pass

    # ── Запускаем всё внутри async with application: ─────────────────────────
    # Контекстный менеджер вызывает initialize() и shutdown() автоматически,
    # поэтому event loop остаётся свободным для обработки HTTP-запросов.
    async with application:
        await application.start()
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook сброшен, запускаем polling.")

        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        logger.info("Polling запущен. Бот принимает обновления.")

        # ── aiohttp Web Application (для приёма заявок с формы) ──────────────
        web_app = web.Application()

        web_app.router.add_post('/webhook/application', handle_application_webhook)
        web_app.router.add_get('/health',               handle_health)

        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, HTTP_HOST, HTTP_PORT)
        await site.start()
        logger.info("HTTP-сервер запущен на http://%s:%s", HTTP_HOST, HTTP_PORT)

        # Ждём сигнала завершения — event loop свободен для HTTP-запросов
        await shutdown_event.wait()

        logger.info("Остановка бота…")
        await application.updater.stop()
        await application.stop()

    await runner.cleanup()
    logger.info("Бот остановлен.")


def main() -> None:
    """Точка входа: запускает event loop с run_bot()."""
    asyncio.run(run_bot())


if __name__ == '__main__':
    main()
