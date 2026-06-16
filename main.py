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
    'standard_30': {
        'name': 'Стандарт (30 человек)',
        'barmen': 1,
        'guests': 30,
        'cocktails': 100,
        'price': '15000 ₽'
    },
    'standard_100': {
        'name': 'Стандарт (100 человек)',
        'barmen': 1,
        'guests': 100,
        'cocktails': 200,
        'price': '35000 ₽'
    },
    'premium': {
        'name': 'Премиум (100+ человек)',
        'barmen': 2,
        'guests': '100+',
        'cocktails': '200+',
        'tinctures': '4 вида по 1л',
        'lemonade': 'лимонад',
        'price': '60000 ₽'
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
    
    service_map = {
        'service_wedding': '💒 Свадьба',
        'service_corporate': '🏢 Корпоративы',
        'service_private': '🎂 Частные мероприятия',
        'service_coffee': '☕ Кофе-брейки'
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
    
    packages_text = "Выберите пакет услуг:\n\n"
    
    package_keys = list(PACKAGES.keys())
    for key, package in PACKAGES.items():
        packages_text += f"<b>{package['name']}</b>\n"
        packages_text += f"Барменов: {package['barmen']}\n"
        packages_text += f"Гостей: {package['guests']}\n"
        packages_text += f"Коктейлей: {package['cocktails']}\n"
        packages_text += f"Цена: {package['price']}\n\n"

    keyboard = []
    buttons = [InlineKeyboardButton(PACKAGES[key]['name'], callback_data=f'package_{key}') for key in package_keys]
    for i in range(0, len(buttons), 2):
        keyboard.append(buttons[i:i + 2])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(packages_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return CHOOSING_PACKAGE

async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пакет выбран, заявка готова"""
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

Менеджер свяжется с вами в ближайшее время!
"""
    
    keyboard = [[InlineKeyboardButton("В главное меню", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(confirmation_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    return ConversationHandler.END

async def cocktails(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Коктейльная карта"""
    query = update.callback_query
    await query.answer()
    
    cocktails_text = """🍹 <b>КОКТЕЙЛЬНАЯ КАРТА</b>

<b>Классические коктейли:</b>
• Маргарита
• Мохито
• Дайкири
• Космополитен

<b>Авторские коктейли:</b>
• Владивостокский закат
• Волна удачи
• Морской бриз
• Тихоокеанский рай

<b>Безалкогольные:</b>
• Мокито
• Лимонад
• Фруктовый микс
"""
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(cocktails_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

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

<b>Пакет "Стандарт" (30 человек)</b>
• 1 профессиональный бармен
• 100 коктейлей
• Цена: 15 000 ₽

<b>Пакет "Стандарт" (100 человек)</b>
• 1 профессиональный бармен
• 200 коктейлей
• Цена: 35 000 ₽

<b>Пакет "Премиум" (100+ человек)</b>
• 2 профессиональных барменов
• 200+ коктейлей
• 4 вида настойки по 1л
• Лимонад
• Цена: 60 000 ₽

<i>Цены указаны без учета доставки. Точная стоимость рассчитывается индивидуально.</i>
"""
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='menu')]]
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
            CHOOSING_SERVICE: [CallbackQueryHandler(service_selected, pattern='^service_')],
            ENTERING_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_guests)],
            ENTERING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_name)],
            ENTERING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_date)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, entering_phone)],
            CHOOSING_PACKAGE: [CallbackQueryHandler(package_selected, pattern='^package_')]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(menu, pattern='^menu$'))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(cocktails, pattern='^cocktails$'))
    application.add_handler(CallbackQueryHandler(wine_events, pattern='^wine_events$'))
    application.add_handler(CallbackQueryHandler(pricing, pattern='^pricing$'))
    application.add_handler(CallbackQueryHandler(portfolio, pattern='^portfolio$'))
    application.add_handler(CallbackQueryHandler(reviews, pattern='^reviews$'))
    application.add_handler(CallbackQueryHandler(services, pattern='^application$'))
    
    # Запуск
    application.run_polling()

if __name__ == '__main__':
    main()
