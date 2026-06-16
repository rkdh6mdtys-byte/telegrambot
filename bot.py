import telebot
from telebot import types
import json
import os
from datetime import datetime

TOKEN = "8717077678:AAHI7-puYr1ucjLwzBzwHmEr16pQeDCTPlU"
ADMIN_ID = 6133417158
SPREADSHEET_ID = "1ayVDaEaArcZQ_NtfuDO0TydlZYI4U2nuTbfldVvX76A"

bot = telebot.TeleBot(TOKEN)

user_data = {}
user_state = {}

def save_to_sheets(name, date, guests, username, package):
    # TODO: Fix Google Sheets credentials and re-enable this
    print(f"⏸️ Google Sheets временно отключена. Заявка не сохранена: {name}")
    return True

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
        bot.send_message(chat_id, "👇 Выберите интересующий раздел", reply_markup=main_menu())
    elif call.data == "back_to_start":
        bot.send_message(chat_id, "👇 Выберите интересующий раздел", reply_markup=main_menu())
    elif call.data == "services":
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("💍 Свадьбы", callback_data="service_wedding"),
            types.InlineKeyboardButton("🏢 Корпоративы", callback_data="service_corp"),
            types.InlineKeyboardButton("🎉 Частные мероприятия", callback_data="service_private")
        )
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start"))
        bot.send_message(chat_id, "🍸 Выберите интересующую услугу:", reply_markup=kb)
    elif call.data.startswith("service_"):
        service_names = {
            "service_wedding": "💍 Свадьба",
            "service_corp": "🏢 Корпоратив",
            "service_private": "🎉 Частное мероприятие"
        }
        service = service_names.get(call.data)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎉 Получить расчёт", callback_data="request"))
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start"))
        bot.send_message(chat_id, f"{service}\n\nМы подготовим барную концепцию под ваше мероприятие.\n\nНажмите кнопку ниже для расчёта.", reply_markup=kb)
    elif call.data == "cocktails":
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("🍸 Классика", callback_data="cocktails_classic"),
            types.InlineKeyboardButton("🍃 Безалкогольные", callback_data="cocktails_nonalc")
        )
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start"))
        bot.send_message(chat_id, "🍹 Коктейльная карта\n\nВыберите категорию:", reply_markup=kb)
    elif call.data == "cocktails_classic":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="cocktails"))
        bot.send_message(chat_id, "🍸 Классика:\n• Porn Star Martini\n• Clover Club\n• Bramble\n• New York Sour\n• Whiskey Sour\n• Aperol Spritz\n• Daiquiri\n• Margarita\n• Negroni\n• White Russian\n• Espresso Martini\n• Paloma", reply_markup=kb)
    elif call.data == "cocktails_nonalc":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="cocktails"))
        bot.send_message(chat_id, "🍃 Безалкогольные:\n• Virgin Margarita\n• Virgin Negroni\n• Virgin Aperol Spritz\n• Virgin Daiquiri", reply_markup=kb)
    elif call.data == "wine":
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("🍷 Винные дегустации", callback_data="wine_tasting"),
            types.InlineKeyboardButton("🎲 Винное казино", callback_data="wine_casino"),
            types.InlineKeyboardButton("🍇 Подбор вина", callback_data="wine_selection")
        )
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start"))
        bot.send_message(chat_id, "🍷 Винные мероприятия\n\nВыберите интересующую услугу:", reply_markup=kb)
    elif call.data == "wine_tasting":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="wine"))
        bot.send_message(chat_id, "🍷 Винные дегустации\n\nПрофессиональная дегустация вин с сомелье.\nПодходит для корпоративов и частных мероприятий.", reply_markup=kb)
    elif call.data == "wine_casino":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="wine"))
        bot.send_message(chat_id, "🎲 Винное казино\n\nИнтерактивная игра с винами и призами.\nРазвлечение для гостей вашего мероприятия.", reply_markup=kb)
    elif call.data == "wine_selection":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="wine"))
        bot.send_message(chat_id, "🍇 Подбор вина\n\nИндивидуальный подбор вин под формат вашего мероприятия.\nКонсультация сомелье включена.", reply_markup=kb)
    elif call.data == "price":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start"))
        bot.send_message(chat_id, "💰 Пакеты услуг\n\n🟢 БАЗОВЫЙ ПАКЕТ - 65 000₽\n• 1 профессиональный бармен\n• До 30 человек\n• 100 коктейлей\n• 6-8 часов работы\n\n🔵 СТАНДАРТНЫЙ ПАКЕТ - 100 000₽\n• 1 профессиональный бармен\n• До 100 человек\n• 200 коктейлей\n• 6-8 часов работы\n\n🟣 ПРЕМИУМ ПАКЕТ - 125 000₽\n• 2 профессиональных бармена\n• 100+ человек\n• 200+ коктейлей\n• 4 вида настоек по 1л\n• 6л лимонада\n• 6-8 часов работы", reply_markup=kb)
    elif call.data == "presentation":
        try:
            with open("presentation.pdf", "rb") as f:
                bot.send_document(chat_id, f, caption="📄 Презентация ВОЛНЫ")
        except Exception:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start"))
            bot.send_message(chat_id, "📄 Презентация пока не загружена.", reply_markup=kb)
    elif call.data == "works":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start"))
        bot.send_message(chat_id, "📸 Галерея находится в наполнении.", reply_markup=kb)
    elif call.data == "reviews":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start"))
        bot.send_message(chat_id, "⭐ Раздел находится в наполнении.", reply_markup=kb)
    elif call.data == "manager":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start"))
        bot.send_message(chat_id, "📞 Менеджер:\n@justsayheron", reply_markup=kb)
    elif call.data == "request":
        user_data[chat_id] = {}
        user_state[chat_id] = "name"
        bot.send_message(chat_id, "👤 Как вас зовут?")

@bot.message_handler(func=lambda m: True)
def form_handler(message):
    chat_id = message.chat.id
    if chat_id not in user_state:
        return
    state = user_state[chat_id]
    if state == "name":
        user_data[chat_id]["name"] = message.text
        user_state[chat_id] = "date"
        bot.send_message(chat_id, "📅 На какую дату планируется мероприятие?")
    elif state == "date":
        user_data[chat_id]["date"] = message.text
        user_state[chat_id] = "guests"
        bot.send_message(chat_id, "👥 Сколько будет гостей?")
    elif state == "guests":
        user_data[chat_id]["guests"] = message.text
        username = message.from_user.username or "нет username"
        try:
            guests_count = int(user_data[chat_id]['guests'])
        except:
            guests_count = 0
        if guests_count <= 30:
            package = "🟢 БАЗОВЫЙ ПАКЕТ - 65 000₽"
        elif guests_count <= 100:
            package = "🔵 СТАНДАРТНЫЙ ПАКЕТ - 100 000₽"
        else:
            package = "🟣 ПРЕМИУМ ПАКЕТ - 125 000₽"
        text = (
            "🚨 НОВАЯ ЗАЯВКА\n\n"
            f"👤 Имя: {user_data[chat_id]['name']}\n"
            f"📅 Дата: {user_data[chat_id]['date']}\n"
            f"👥 Гостей: {user_data[chat_id]['guests']}\n"
            f"💬 Telegram: @{username}\n"
            f"📦 Рекомендуемый пакет: {package}"
        )
        bot.send_message(ADMIN_ID, text)
        save_to_sheets(
            user_data[chat_id]['name'],
            user_data[chat_id]['date'],
            user_data[chat_id]['guests'],
            username,
            package
        )
        bot.send_message(
            chat_id,
            f"✅ Заявка отправлена. Мы свяжемся с вами в ближайшее время.\n\n"
            f"Рекомендуемый пакет для вас:\n{package}\n\n/start"
        )
        del user_state[chat_id]
        del user_data[chat_id]

print("Бот запущен...")
bot.infinity_polling(skip_pending=True)
