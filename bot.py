import telebot
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import logging
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

bot = telebot.TeleBot(TOKEN)

def init_sheets():
    try:
        if not GOOGLE_SHEETS_CREDENTIALS:
            logger.error("GOOGLE_SHEETS_CREDENTIALS не задан")
            return None
        creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        logger.info("Учётные данные Google Sheets успешно разобраны (project_id: %s)", creds_dict.get("project_id"))
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        logger.info("Подключение к Google Sheets установлено")
        return sheet
    except json.JSONDecodeError as e:
        logger.error("Ошибка разбора GOOGLE_SHEETS_CREDENTIALS (невалидный JSON): %s", e)
        return None
    except Exception as e:
        logger.error("Ошибка подключения к Google Sheets: %s", e)
        return None

def save_to_sheets(name, phone, date, time, people_count, comment):
    try:
        sheet = init_sheets()
        if sheet is None:
            logger.warning("Сохранение пропущено: нет подключения к Google Sheets")
            return False
        row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, phone, date, time, people_count, comment]
        sheet.append_row(row)
        logger.info("Заявка сохранена: %s, %s", name, phone)
        return True
    except Exception as e:
        logger.error("Ошибка сохранения в Google Sheets: %s", e)
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
    logger.info("Бот запускается...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except telebot.apihelper.ApiTelegramException as e:
            if "Conflict" in str(e) or "409" in str(e):
                logger.error("Конфликт: другой экземпляр бота уже запущен (409). Повтор через 30 секунд...")
                time.sleep(30)
            else:
                logger.error("Ошибка Telegram API: %s. Повтор через 15 секунд...", e)
                time.sleep(15)
        except Exception as e:
            logger.error("Неожиданная ошибка: %s. Повтор через 15 секунд...", e)
            time.sleep(15)