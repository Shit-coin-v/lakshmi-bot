import os
from datetime import date

from celery import shared_task
import requests
from dotenv import load_dotenv

from main.models import CustomUser

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


@shared_task
def send_birthday_congratulations():
    today = date.today()
    birthday_users = CustomUser.objects.filter(birth_date__month=today.month, birth_date__day=today.day)

    for user in birthday_users:
        if not user.telegram_id:
            continue

        message = f"🎉 Поздравляем тебя с Днём Рождения, {user.full_name or 'друг'}! Желаем счастья, здоровья и успехов! 🎂"

        payload = {
            "chat_id": user.telegram_id,
            "text": message,
        }

        try:
            response = requests.post(BASE_URL, data=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user.telegram_id}: {e}")
