import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import os
from datetime import datetime

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CHOOSING_SERVICE, ENTERING_GUESTS, ENTERING_NAME, ENTERING_DATE, ENTERING_PHONE, CHOOSING_PACKAGE = range(6)

# ID администратора (замени на свой Telegram ID)
ADMIN_ID = 6133417158 # Замени на свой ID

# Пакеты услуг
PACKAGES = {
    'standard': {
        'name': '🥂 Стандарт',
        'barmen': 1,
        'guests': 30,
        'cocktails': 100,
        'price': '65 000 ₽',
        'description': (
            '👤 <b>1 профессиональный бармен</b>\n'
            '👥 До <b>30 гостей</b>\n'
            '🍹 <b>100 коктейлей</b>\n'
            '💰 Стоимость: <b>65 000 ₽</b>\n\n'
            'Идеальный выбор для небольших мероприятий — дней рождения, '
            'камерных вечеринок и корпоративов в узком кругу. '
            'Бармен приедет с полным оборудованием и всеми ингредиентами.'
        )
    },
    'business': {
        'name': '💼 Бизнес',
        'barmen': 1,
        'guests': 100,
        'cocktails': 200,
        'price': '100 000 ₽',
        'description': (
            '👤 <b>1 профессиональный бармен</b>\n'
            '👥 До <b>100 гостей</b>\n'
            '🍹 <b>200 коктейлей</b>\n'
            '💰 Стоимость: <b>100 000 ₽</b>\n\n'
            'Оптимальное решение для средних мероприятий — свадеб, '
            'корпоративов и частных праздников. Расширенное меню коктейлей '
            'и профессиональное обслуживание на весь вечер.'
        )
    },
    'premium': {
        'name': '👑 Премиум',
        'barmen': 2,
        'guests': '100+',
        'cocktails': '200+',
        'tinctures': '4 вида настойки по 1 л',
        'lemonade': '6 л фирменного лимонада',
        'price': '125 000 ₽',
        'description': (
            '👥 <b>2 профессиональных бармена</b>\n'
            '🎉 <b>100+ гостей</b>\n'
            '🍹 <b>200+ коктейлей</b>\n'
            '🍶 <b>4 вида авторской настойки по 1 л</b>\n'
            '🍋 <b>6 л фирменного лимонада</b>\n'
            '💰 Стоимость: <b>125 000 ₽</b>\n\n'
            'Максимальный уровень сервиса для масштабных мероприятий. '
            'Два бармена, авторские настойки собственного производства, '
            'фирменный лимонад и расширенное меню — ваши гости запомнят этот вечер навсегда.'
        )
    }
}

# Пакеты кофе-брейков
COFFEE_PACKAGES = {
    'coffee_standard': {
        'name': '☕ Стандарт',
        'description': (
            '☕ <b>Кофе-брейк «Стандарт»</b>\n\n'
            '• Профессиональный бариста\n'
            '• Эспрессо, американо, капучино, латте\n'
            '• До 50 порций\n'
            '• Оборудование и расходники включены\n'
            '• Продолжительность: до 2 часов\n\n'
            '💰 Стоимость рассчитывается индивидуально\n\n'
            '<i>Подходит для деловых встреч, конференций и небольших корпоративных мероприятий.</i>'
        )
    },
    'coffee_premium': {
        'name': '✨ Премиум',
        'description': (
            '✨ <b>Кофе-брейк «Премиум»</b>\n\n'
            '• 2 профессиональных бариста\n'
            '• Полное меню кофейных напитков + авторские позиции\n'
            '• Безлимитное количество порций\n'
            '• Фирменные сиропы и топпинги\n'
            '• Чайная станция в комплекте\n'
            '• Оборудование премиум-класса\n'
            '• Продолжительность: до 4 часов\n\n'
            '💰 Стоимость рассчитывается индивидуально\n\n'
            '<i>Идеально для крупных форумов, выставок и представительских мероприятий.</i>'
        )
    }
}

# Отзывы
REVIEWS = [
    {
        'name': 'Александр М.',
        'text': 'Отличный сервис! Бармены профессионалы, коктейли вкусные. Свадьба прошла на 5+. Рекомендую!',
        'rating': '⭐⭐⭐⭐⭐'
    },
    {
        'name': 'Елена К.',
        'text': 'Корпоратив был супер! Только одно замечание - хотелось бы больше безалкогольных вариантов. Но в целом спасибо!',
        'rating': '⭐⭐⭐⭐'
    },
    {
        'name': 'Иван П.',
        'text': 'Профессионалы своего дела. Мероприятие организовано идеально. Гости в восторге от коктейлей.',
        'rating': '⭐⭐⭐⭐⭐'
    },
    {
        'name': 'Мария Л.',
        'text': 'Хороший сервис, но цены немного высокие. Качество хорошее, но для бюджетного мероприятия дороговато.',
        'rating': '⭐⭐⭐⭐'
    },
    {
        'name': 'Дмитрий В.',
        'text': 'Заказывали на день рождения. Бармены креативные, коктейли необычные. Все гости спрашивали рецепты!',
        'rating': '⭐⭐⭐⭐⭐'
    },
    {
        'name': 'Ольга С.',
        'text': 'Неплохо, но доставка была с опозданием на 15 минут. Сами коктейли отличные, но пунктуальность важна.',
        'rating': '⭐⭐⭐'
    }
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Стартовое сообщение"""
    welcome_text = """🌊 <b>ВОЛНЫ</b>
<b>Коктейльный сервис и вино</b>

🍸 Авторские коктейли
🍷 Винные дегустации
🎲 Винное казино
📍 Владивосток

Нажмите кнопку ниже, чтобы начать."""

    keyboard = [[InlineKeyboardButton("Открыть меню", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню"""
    query = update.callback_query
    await query.answer()
    
    menu_text = "Выберите раздел:"
    
    keyboard = [
        [InlineKeyboardButton("🎯 Услуги", callback_data='services'), InlineKeyboardButton("🍹 Коктейльная карта", callback_data='cocktails')],
        [InlineKeyboardButton("🎉 Винные мероприятия", callback_data='wine_events'), InlineKeyboardButton("💰 Стоимость", callback_data='pricing')],
        [InlineKeyboardButton("📸 Наши работы", callback_data='portfolio'), InlineKeyboardButton("⭐ Отзывы", callback_data='reviews')],
        [InlineKeyboardButton("📝 Оставить заявку", callback_data='application')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(menu_text, reply_markup=reply_markup)

async def services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Раздел услуг"""
    query = update.callback_query
    await query.answer()
    
    services_text = "Выберите тип мероприятия:"
    
    keyboard = [
        [InlineKeyboardButton("💒 Свадьба", callback_data='service_wedding'), InlineKeyboardButton("🏢 Корпоративы", callback_data='service_corporate')],
        [InlineKeyboardButton("🎂 Частные мероприятия", callback_data='service_private'), InlineKeyboardButton("☕ Кофе-брейки", callback_data='service_coffee')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(services_text, reply_markup=reply_markup)
    return CHOOSING_SERVICE

async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбран тип услуги"""
    query = update.callback_query
    await query.answer()

    # Кофе-брейки идут в отдельный поток
    if query.data == 'service_coffee':
        text = "☕ <b>КОФЕ-БРЕЙКИ</b>\n\nВыберите пакет:"
        keyboard = [
            [
                InlineKeyboardButton(COFFEE_PACKAGES['coffee_standard']['name'], callback_data='coffee_pkg_standard'),
                InlineKeyboardButton(COFFEE_PACKAGES['coffee_premium']['name'], callback_data='coffee_pkg_premium'),
            ],
            [InlineKeyboardButton("⬅️ Назад к услугам", callback_data='services')],
            [InlineKeyboardButton("🏠 В главное меню", callback_data='menu')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return CHOOSING_SERVICE

    service_map = {
        'service_wedding': '💒 Свадьба',
        'service_corporate': '🏢 Корпоративы',
        'service_private': '🎂 Частные мероприятия',
    }

    context.user_data['service'] = service_map.get(query.data, 'Услуга')

    await query.edit_message_text(
        f"Вы выбрали: {context.user_data['service']}\n\nСколько гостей будет на мероприятии?"
    )
    return ENTERING_GUESTS

async def entering_guests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод количества гостей"""
    try:
        guests = int(update.message.text)
        context.user_data['guests'] = guests
        
        await update.message.reply_text("Как вас зовут?")
        return ENTERING_NAME
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return ENTERING_GUESTS

async def entering_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод имени"""
    context.user_data['name'] = update.message.text
    
    await update.message.reply_text("На какую дату планируется мероприятие? (формат: ДД.ММ.ГГГГ)")
    return ENTERING_DATE

async def entering_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод даты"""
    context.user_data['date'] = update.message.text
    
    await update.message.reply_text("Ваш номер телефона?")
    return ENTERING_PHONE

async def entering_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод телефона и выбор пакета"""
    context.user_data['phone'] = update.message.text

    packages_text = "🎁 <b>Выберите пакет услуг:</b>\n\nНажмите на пакет, чтобы узнать подробности."

    keyboard = [
        [
            InlineKeyboardButton(PACKAGES['standard']['name'], callback_data='pkg_detail_standard'),
            InlineKeyboardButton(PACKAGES['business']['name'], callback_data='pkg_detail_business'),
        ],
        [InlineKeyboardButton(PACKAGES['premium']['name'], callback_data='pkg_detail_premium')],
        [InlineKeyboardButton("⬅️ В главное меню", callback_data='menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(packages_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return CHOOSING_PACKAGE

async def package_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать детали выбранного пакета с кнопкой подачи заявки"""
    query = update.callback_query
    await query.answer()

    package_key = query.data.replace('pkg_detail_', '')
    package = PACKAGES.get(package_key)

    if not package:
        await query.edit_message_text("Ошибка. Попробуйте снова.")
        return CHOOSING_PACKAGE

    text = f"🎁 <b>Пакет {package['name']}</b>\n\n{package['description']}"

    keyboard = [
        [InlineKeyboardButton("📝 Подать заявку", callback_data=f'package_{package_key}')],
        [InlineKeyboardButton("⬅️ Назад к пакетам", callback_data='back_to_packages')],
        [InlineKeyboardButton("🏠 В главное меню", callback_data='menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return CHOOSING_PACKAGE

async def back_to_packages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Вернуться к выбору пакета"""
    query = update.callback_query
    await query.answer()

    packages_text = "🎁 <b>Выберите пакет услуг:</b>\n\nНажмите на пакет, чтобы узнать подробности."

    keyboard = [
        [
            InlineKeyboardButton(PACKAGES['standard']['name'], callback_data='pkg_detail_standard'),
            InlineKeyboardButton(PACKAGES['business']['name'], callback_data='pkg_detail_business'),
        ],
        [InlineKeyboardButton(PACKAGES['premium']['name'], callback_data='pkg_detail_premium')],
        [InlineKeyboardButton("⬅️ В главное меню", callback_data='menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(packages_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return CHOOSING_PACKAGE

async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пакет выбран — отправить заявку"""
    query = update.callback_query
    await query.answer()

    package_key = query.data.replace('package_', '')
    package = PACKAGES.get(package_key)

    if not package:
        await query.edit_message_text("Ошибка при выборе пакета. Попробуйте снова.")
        return ConversationHandler.END

    context.user_data['package'] = package

    # Формируем заявку
    application_text = f"""
<b>📋 НОВАЯ ЗАЯВКА</b>

<b>Услуга:</b> {context.user_data.get('service', 'N/A')}
<b>Имя:</b> {context.user_data.get('name', 'N/A')}
<b>Телефон:</b> {context.user_data.get('phone', 'N/A')}
<b>Количество гостей:</b> {context.user_data.get('guests', 'N/A')}
<b>Дата мероприятия:</b> {context.user_data.get('date', 'N/A')}

<b>Выбранный пакет:</b> {package['name']}
<b>Цена:</b> {package['price']}
<b>Барменов:</b> {package['barmen']}
<b>Коктейлей:</b> {package['cocktails']}

<b>Время заявки:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""

    # Отправляем заявку администратору
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=application_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке заявки: {e}")

    # Подтверждение пользователю
    confirmation_text = f"""✅ <b>Спасибо за заявку!</b>

Ваши данные:
<b>Услуга:</b> {context.user_data.get('service')}
<b>Имя:</b> {context.user_data.get('name')}
<b>Телефон:</b> {context.user_data.get('phone')}
<b>Гостей:</b> {context.user_data.get('guests')}
<b>Дата:</b> {context.user_data.get('date')}
<b>Пакет:</b> {package['name']}
<b>Цена:</b> {package['price']}

Менеджер свяжется с вами в ближайшее время! 🙌
"""

    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(confirmation_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return ConversationHandler.END

async def cocktails(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню коктейльной карты"""
    query = update.callback_query
    await query.answer()

    text = "🍹 <b>КОКТЕЙЛЬНАЯ КАРТА</b>\n\nВыберите раздел:"

    keyboard = [
        [
            InlineKeyboardButton("🍸 Коктейли", callback_data='cocktails_alcoholic'),
            InlineKeyboardButton("🥤 Безалкогольные", callback_data='cocktails_nonalcoholic'),
        ],
        [InlineKeyboardButton("🎭 Презентация", callback_data='cocktails_presentation')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def cocktails_alcoholic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Раздел коктейлей"""
    query = update.callback_query
    await query.answer()

    text = """🍸 <b>КОКТЕЙЛИ</b>

• Маргарита
• Мохито
• Дайкири
• Космополитен
• Негрони
• Апероль Шприц
• Гимлет
• Олд Фэшн
• Манхэттен
• Мартини
• Пина Колада
• Кайпиринья
• Кровавая Мэри
• Виски Сауэр
• Сазерак
• Сайдкар
• Корпс Ривайвер
• Вью Карре
• Клевер Клаб
• Авиация
• Бетвин зе Шитс
• Французский 75"""

    keyboard = [
        [InlineKeyboardButton("⬅️ К разделам карты", callback_data='cocktails')],
        [InlineKeyboardButton("🏠 В главное меню", callback_data='menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def cocktails_nonalcoholic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Раздел безалкогольных напитков"""
    query = update.callback_query
    await query.answer()

    text = """🥤 <b>БЕЗАЛКОГОЛЬНЫЕ</b>

Все напитки — безалкогольные версии классических коктейлей, приготовленные с тем же вниманием к деталям:

• Негрони
• Апероль Шприц
• Дайкири
• Гимлет
• Мохито
• Нью-Йорк Сауэр
• Виски Сауэр"""

    keyboard = [
        [InlineKeyboardButton("⬅️ К разделам карты", callback_data='cocktails')],
        [InlineKeyboardButton("🏠 В главное меню", callback_data='menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def cocktails_presentation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Раздел презентации"""
    query = update.callback_query
    await query.answer()

    text = """🎭 <b>ПРЕЗЕНТАЦИЯ</b>

Информация о презентации появится совсем скоро.

Следите за обновлениями! 🌊"""

    keyboard = [
        [InlineKeyboardButton("⬅️ К разделам карты", callback_data='cocktails')],
        [InlineKeyboardButton("🏠 В главное меню", callback_data='menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def coffee_package_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Детали пакета кофе-брейка"""
    query = update.callback_query
    await query.answer()

    pkg_key = 'coffee_standard' if query.data == 'coffee_pkg_standard' else 'coffee_premium'
    package = COFFEE_PACKAGES[pkg_key]

    keyboard = [
        [InlineKeyboardButton("📝 Подать заявку", callback_data=f'coffee_apply_{pkg_key}')],
        [InlineKeyboardButton("📞 Связаться с менеджером", url='https://t.me/volny_vl')],
        [InlineKeyboardButton("⬅️ Назад к кофе-брейкам", callback_data='service_coffee')],
        [InlineKeyboardButton("🏠 В главное меню", callback_data='menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(package['description'], reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return CHOOSING_SERVICE

async def coffee_apply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подача заявки на кофе-брейк"""
    query = update.callback_query
    await query.answer()

    pkg_key = query.data.replace('coffee_apply_', '')
    package = COFFEE_PACKAGES.get(pkg_key)

    if not package:
        await query.edit_message_text("Ошибка. Попробуйте снова.")
        return CHOOSING_SERVICE

    context.user_data['service'] = f"☕ Кофе-брейк {package['name']}"
    context.user_data['coffee_package'] = package['name']

    application_text = f"""
<b>📋 НОВАЯ ЗАЯВКА — КОФЕ-БРЕЙК</b>

<b>Пакет:</b> {package['name']}
<b>Время заявки:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}

<i>Клиент запросил обратный звонок через бота.</i>
"""

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=application_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке заявки кофе-брейк: {e}")

    confirmation_text = f"""✅ <b>Заявка принята!</b>

Вы выбрали: <b>{package['name']}</b>

Менеджер свяжется с вами в ближайшее время для уточнения деталей и расчёта стоимости. 🙌
"""

    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(confirmation_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def wine_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Винные мероприятия"""
    query = update.callback_query
    await query.answer()

    wine_text = """🍷 <b>ВИННЫЕ МЕРОПРИЯТИЯ</b>

<b>Винные дегустации:</b>
Познакомьтесь с лучшими винами мира под руководством сомелье.

<b>Винное казино:</b>
Интерактивная игра с дегустацией редких вин.

<b>Винный вечер:</b>
Романтичное мероприятие с подбором вин к блюдам.

Все мероприятия проводятся профессионалами с опытом!
"""

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(wine_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def pricing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Стоимость"""
    query = update.callback_query
    await query.answer()

    pricing_text = """💰 <b>СТОИМОСТЬ УСЛУГ</b>

<b>🥂 Стандарт</b>
• 1 профессиональный бармен
• До 30 гостей
• 100 коктейлей
• Цена: <b>65 000 ₽</b>

<b>💼 Бизнес</b>
• 1 профессиональный бармен
• До 100 гостей
• 200 коктейлей
• Цена: <b>100 000 ₽</b>

<b>👑 Премиум</b>
• 2 профессиональных бармена
• 100+ гостей
• 200+ коктейлей
• 4 вида авторской настойки по 1 л
• 6 л фирменного лимонада
• Цена: <b>125 000 ₽</b>

<i>Точная стоимость рассчитывается индивидуально. Свяжитесь с нами для консультации.</i>
"""

    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку", callback_data='application')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(pricing_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Наши работы"""
    query = update.callback_query
    await query.answer()
    
    portfolio_text = """📸 <b>НАШИ РАБОТЫ</b>

Мы организовали более 150 мероприятий:
• 45 свадеб
• 60 корпоративных событий
• 35 частных мероприятий
• 15 винных дегустаций

Все наши клиенты остались довольны качеством сервиса!

Посмотрите отзывы наших клиентов ⭐
"""
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(portfolio_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def reviews(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отзывы"""
    query = update.callback_query
    await query.answer()
    
    reviews_text = "⭐ <b>ОТЗЫВЫ КЛИЕНТОВ</b>\n\n"
    
    for review in REVIEWS:
        reviews_text += f"<b>{review['name']}</b> {review['rating']}\n"
        reviews_text += f"<i>{review['text']}</i>\n\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(reviews_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена"""
    await update.message.reply_text("Операция отменена. Введите /start для начала.")
    return ConversationHandler.END


def main() -> None:
    """Запуск бота"""
    # Получаем токен из переменной окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен!")

    # Создаем приложение
    application = Application.builder().token(token).build()

    # ConversationHandler для заявок
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(services, pattern='^services$'),
            CallbackQueryHandler(services, pattern='^application$'),
        ],
        states={
            CHOOSING_SERVICE: [
                CallbackQueryHandler(service_selected, pattern='^service_'),
                CallbackQueryHandler(coffee_package_detail, pattern='^coffee_pkg_'),
                CallbackQueryHandler(coffee_apply, pattern='^coffee_apply_'),
                CallbackQueryHandler(services, pattern='^services$'),
            ],
            ENTERING_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_guests)],
            ENTERING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_name)],
            ENTERING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_date)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_phone)],
            CHOOSING_PACKAGE: [
                CallbackQueryHandler(package_detail, pattern='^pkg_detail_'),
                CallbackQueryHandler(package_selected, pattern='^package_'),
                CallbackQueryHandler(back_to_packages, pattern='^back_to_packages$'),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(menu, pattern='^menu$'),
        ],
    )

    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(menu, pattern='^menu$'))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(cocktails, pattern='^cocktails$'))
    application.add_handler(CallbackQueryHandler(cocktails_alcoholic, pattern='^cocktails_alcoholic$'))
    application.add_handler(CallbackQueryHandler(cocktails_nonalcoholic, pattern='^cocktails_nonalcoholic$'))
    application.add_handler(CallbackQueryHandler(cocktails_presentation, pattern='^cocktails_presentation$'))
    application.add_handler(CallbackQueryHandler(wine_events, pattern='^wine_events$'))
    application.add_handler(CallbackQueryHandler(pricing, pattern='^pricing$'))
    application.add_handler(CallbackQueryHandler(portfolio, pattern='^portfolio$'))
    application.add_handler(CallbackQueryHandler(reviews, pattern='^reviews$'))

    # Запуск
    application.run_polling()

if __name__ == '__main__':
    main()
