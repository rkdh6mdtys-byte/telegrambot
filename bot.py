import telebot
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import time
from datetime import datetime

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

bot = telebot.TeleBot(TOKEN)

def init_sheets():
    try:
        creds = Credentials.from_service_account_info(
            json.loads(GOOGLE_SHEETS_CREDENTIALS),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        return sheet
    except Exception as e:
        print(f"Ошибка подключения к Google Sheets: {e}")
        return None

def save_to_sheets(name, phone, date, time, people_count, comment):
    try:
        sheet = init_sheets()
        if sheet is None:
            return False
        row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, phone, date, time, people_count, comment]
        sheet.append_row(row)
        print(f"Заявка сохранена: {name}, {phone}")
        return True
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
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
    save_to_sheets(name, phone, date, time, people_count, comment)
    bot.send_message(message.chat.id, "Спасибо! Заявка принята.")

if __name__ == '__main__':
    print("Бот запущен...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            if "409" in str(e):
                print(f"Ошибка 409: {e}. Повтор через 30 сек...")
                time.sleep(30)
            else:
                print(f"Ошибка: {e}. Повтор через 15 сек...")
                time.sleep(15)
