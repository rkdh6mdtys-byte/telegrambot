import telebot
from telebot import types

TOKEN = "8717077678:AAHI7-puYr1ucjLwzBzwHmEr16pQeDCTPlU"
ADMIN_ID = 6133417158

bot = telebot.TeleBot(TOKEN)

user_data = {}
user_state = {}


def main_menu():
    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton("🍸 Услуги", callback_data="services"),
        types.InlineKeyboardButton("🍹 Коктейльная карта", callback_data="cocktails")
    )

    kb.add(
        types.InlineKeyboardButton("🍷 Винные мероприятия", callback_data="wine"),
        types.InlineKeyboardButton("💰 Стоимость", callback_data="price")
    )

    kb.add(
        types.InlineKeyboardButton("📄 Презентация", callback_data="presentation"),
        types.InlineKeyboardButton("📸 Наши работы", callback_data="works")
    )

    kb.add(
        types.InlineKeyboardButton("⭐ Отзывы", callback_data="reviews"),
        types.InlineKeyboardButton("🎉 Оставить заявку", callback_data="request")
    )

    kb.add(
        types.InlineKeyboardButton("📞 Менеджер", callback_data="manager")
    )

    kb.add(
        types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
    )

    return kb


@bot.message_handler(commands=["start"])
def start(message):

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🚀 Открыть меню", callback_data="menu"))

    text = (
        "🌊 ВОЛНЫ\n\n"
        "Коктейльный сервис и вино\n\n"
        "🍸 Авторские коктейли\n"
        "🍷 Винные дегустации\n"
        "🎲 Винное казино\n\n"
        "📍 Владивосток\n\n"
        "Нажмите кнопку ниже."
    )

    bot.send_message(message.chat.id, text, reply_markup=kb)


@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):

    chat_id = call.message.chat.id

    if call.data == "menu":
        bot.send_message(
            chat_id,
            "👇 Выберите интересующий раздел",
            reply_markup=main_menu()
        )

    elif call.data == "back_to_start":
        bot.send_message(
            chat_id,
            "👇 Выберите интересующий раздел",
            reply_markup=main_menu()
        )

    elif call.data == "services":

        kb = types.InlineKeyboardMarkup(row_width=1)

        kb.add(
            types.InlineKeyboardButton("💍 Свадьбы", callback_data="service_wedding"),
            types.InlineKeyboardButton("🏢 Корпоративы", callback_data="service_corp"),
            types.InlineKeyboardButton("🎉 Частные мероприятия", callback_data="service_private")
        )

        kb.add(
            types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
        )

        bot.send_message(
            chat_id,
            "🍸 Выберите интересующую услугу:",
            reply_markup=kb
        )

    elif call.data.startswith("service_"):

        service_names = {
            "service_wedding": "💍 Свадьба",
            "service_corp": "🏢 Корпоратив",
            "service_private": "🎉 Частное мероприятие"
        }

        service = service_names.get(call.data)

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(
                "🎉 Получить расчёт",
                callback_data="request"
            )
        )

        kb.add(
            types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
        )

        bot.send_message(
            chat_id,
            f"{service}\n\n"
            "Мы подготовим барную концепцию под ваше мероприятие.\n\n"
            "Нажмите кнопку ниже для расчёта.",
            reply_markup=kb
        )

    elif call.data == "cocktails":

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
        )

        bot.send_message(
            chat_id,
            "🍹 Коктейльная карта\n\n"
            "🍸 Классика:\n"
            "• Porn Star Martini\n"
            "• Clover Club\n"
            "• Bramble\n"
            "• New York Sour\n"
            "• Whiskey Sour\n"
            "• Aperol Spritz\n"
            "• Daiquiri\n"
            "• Margarita\n"
            "• Negroni\n"
            "• White Russian\n"
            "• Espresso Martini\n"
            "• Paloma\n\n"
            "🍃 Безалкогольные:\n"
            "• Virgin Margarita\n"
            "• Virgin Negroni\n"
            "• Virgin Aperol Spritz\n"
            "• Virgin Daiquiri",
            reply_markup=kb
        )

    elif call.data == "wine":

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
        )

        bot.send_message(
            chat_id,
            "🍷 Винные мероприятия\n\n"
            "• Винные дегустации\n"
            "• Винное казино\n"
            "• Подбор вина под формат мероприятия",
            reply_markup=kb
        )

    elif call.data == "price":

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
        )

        bot.send_message(
            chat_id,
            "💰 Стоимость рассчитывается индивидуально под формат мероприятия и количество гостей.",
            reply_markup=kb
        )

    elif call.data == "presentation":

        try:
            with open("presentation.pdf", "rb") as f:
                bot.send_document(
                    chat_id,
                    f,
                    caption="📄 Презентация ВОЛНЫ"
                )
        except Exception:
            bot.send_message(
                chat_id,
                "📄 Презентация пока не загружена."
            )

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
        )
        bot.send_message(chat_id, "⬅️ Назад", reply_markup=kb)

    elif call.data == "works":

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
        )

        bot.send_message(
            chat_id,
            "📸 Галерея находится в наполнении.",
            reply_markup=kb
        )

    elif call.data == "reviews":

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
        )

        bot.send_message(
            chat_id,
            "⭐ Раздел находится в наполнении.",
            reply_markup=kb
        )

    elif call.data == "manager":

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
        )

        bot.send_message(
            chat_id,
            "📞 Менеджер:\n@justsayheron",
            reply_markup=kb
        )

    elif call.data == "request":

        user_data[chat_id] = {}
        user_state[chat_id] = "name"

        bot.send_message(
            chat_id,
            "👤 Как вас зовут?"
        )


@bot.message_handler(func=lambda m: True)
def form_handler(message):

    chat_id = message.chat.id

    if chat_id not in user_state:
        return

    state = user_state[chat_id]

    if state == "name":

        user_data[chat_id]["name"] = message.text
        user_state[chat_id] = "date"

        bot.send_message(
            chat_id,
            "📅 На какую дату планируется мероприятие?"
        )

    elif state == "date":

        user_data[chat_id]["date"] = message.text
        user_state[chat_id] = "guests"

        bot.send_message(
            chat_id,
            "👥 Сколько будет гостей?"
        )

    elif state == "guests":

        user_data[chat_id]["guests"] = message.text

        username = message.from_user.username or "нет username"

        text = (
            "🚨 НОВАЯ ЗАЯВКА\n\n"
            f"👤 Имя: {user_data[chat_id]['name']}\n"
            f"📅 Дата: {user_data[chat_id]['date']}\n"
            f"👥 Гостей: {user_data[chat_id]['guests']}\n"
            f"💬 Telegram: @{username}"
        )

        bot.send_message(ADMIN_ID, text)

        bot.send_message(
            chat_id,
            "✅ Заявка отправлена. Мы свяжемся с вами в ближайшее время."
        )

        del user_state[chat_id]
        del user_data[chat_id]


print("Бот запущен...")
bot.infinity_polling(skip_pending=True)