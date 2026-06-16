import telebot
import os
import requests
from datetime import datetime

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

bot = telebot.TeleBot(TOKEN)

def send_to_webhook(name, phone, date, time, people_count, comment):
    try:
        payload = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'name': name,
            'phone': phone,
            'date': date,
            'time': time,
            'people_count': people_count,
            'comment': comment
        }
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print(f"Заявка отправлена: {name}, {phone}")
            return True
        else:
            print(f"Ошибка отправки: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ошибка отправки заявки: {e}")
        return False

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("Оставить заявку"))
    bot.send_message(message.chat.id, "Привет! Добро пожаловать в ВОЛНЫ!", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Оставить заявку")
def request_name(message):
    msg = bot.send_message(message.chat.id, "Как тебя зовут?")
    bot.register_next_step_handler(msg, process_name)

def process_name(message):
    name = message.text
    msg = bot.send_message(message.chat.id, "Какой твой номер телефона?")
    bot.register_next_step_handler(msg, process_phone, name)

def process_phone(message, name):
    phone = message.text
    msg = bot.send_message(message.chat.id, "На какую дату? (ДД.ММ.ГГГГ)")
    bot.register_next_step_handler(msg, process_date, name, phone)

def process_date(message, name, phone):
    date = message.text
    msg = bot.send_message(message.chat.id, "На какое время? (ЧЧ:МММ)")
    bot.register_next_step_handler(msg, process_time, name, phone, date)

def process_time(message, name, phone, date):
    time = message.text
    msg = bot.send_message(message.chat.id, "Сколько человек?")
    bot.register_next_step_handler(msg, process_people, name, phone, date, time)

def process_people(message, name, phone, date, time):
    people_count = message.text
    msg = bot.send_message(message.chat.id, "Пожелания? (или 'нет')")
    bot.register_next_step_handler(msg, process_comment, name, phone, date, time, people_count)

def process_comment(message, name, phone, date, time, people_count):
    comment = message.text if message.text.lower() != 'нет' else ''
    send_to_webhook(name, phone, date, time, people_count, comment)
    bot.send_message(message.chat.id, "Спасибо! Заявка принята.")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling(skip_pending=True)