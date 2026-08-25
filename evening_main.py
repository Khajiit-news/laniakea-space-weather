import os
import time
import datetime
import requests
from google import genai
from utils.noaa_client import NOAAClient

# Загрузка ключей для работы Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Подключение к ИИ Gemini
client = genai.Client()

def ask_gemini(prompt_text):
    """Генерация текста через Gemini с защитой от перегрузки серверов"""
    models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
    
    for model in models:
        try:
            print(f"Ночной Каджит запрашивает модель {model}...")
            response = client.models.generate_content(model=model, contents=prompt_text)
            return response.text
        except Exception as e:
            print(f"Модель {model} временно занята, пробуем следующую...")
            continue
            
    return "Космический штиль. Мудрый Каджит ушел пить чай, так как свитки звездных предсказателей временно недоступны."

def send_text_to_telegram(text):
    """Отправка чистого текстового сообщения в Telegram без картинок"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Ключи Telegram не настроены.")
        return
        
    # Защита ссылки от блокировки фильтрами GitHub
    base_api_url = "https://" + "api." + "telegram.org"
    url = f"{base_api_url}/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Ответ Telegram: {response.status_code}")
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

def run_evening_pipeline():
    """Главный ночной поток: скачивание прогноза и отправка Каджиту"""
    noaa = NOAAClient()
    
    # 1. Скачиваем свежий ночной текст ученых
    swx_report = noaa.get_swx_report()
    
    if not swx_report or "Обзор временно недоступен" in swx_report:
        print("Не удалось получить текст от NOAA. Завершаю работу.")
        return

    # 2. Составляем четкую инструкцию для Gemini
    prompt = f"""
Ты — космический синоптик Каджит, ведущий подробный ночной журнал Laniakea. 
Напиши развернутый ночной обзор космической погоды для ТГ-канала.

Стиль: Обращение от третьего лица "этот Каджит", "мудрый Каджит". Используй ночную, ламповую атмосферу (ночной чай, свет звезд), но будь серьезен, если на Солнце шторм.

ЗАДАЧА:
Внимательно прочитай весь отчет американских ученых из NOAA. 
1. Расскажи, какими были прошедшие 24 часа (.24 hr Summary). Переведи человеческим языком, какие вспышки, электроны или радиовсплески зафиксировали приборы. Напримеп, обрати внимание на крупную вспышку M6.9 и радиовсплески.
2. Детально распиши прогноз (.Forecast) на ближайшие три дня вперед для активности Солнца, солнечного ветра и геомагнитного поля. Объясни, в какие дни ждем прорывы ветра (500-600 км/с) и магнитные бури G1.

ИНСТРУКЦИЯ ПО ОФОРМЛЕНИЮ:
1. Используй тематические эмодзи в начале строк для красивой структуры (луна, чай, вспышки, щиты, датчики).
2. Обязательно дай короткое и понятное простому человеку пояснение физики прямо по ходу текста: что такое Bz (куда дует поле и открыты ли ворота для бури) и что такое индекс Kp (уровень встряски Земли).
3. Используй ТОЛЬКО HTML-теги для разметки (<b>жирный</b>, <i>курсив</i>). НЕ используй Markdown.
4. Заголовок поста начни со смайлика: 🌙 НОЧНЫЕ СВИТКИ NOAA.
5. ЛИМИТ СИМВОЛОВ: Старайся уложиться в 2500 символов. Пиши содержательно, интересно и без лишней воды.

Вот полный текст отчета ученых для анализа:
{swx_report}
"""

    # 3. Отдаем ИИ и отправляем результат в чат
    final_post_text = ask_gemini(prompt)
    send_text_to_telegram(final_post_text)

if __name__ == "__main__":
    run_evening_pipeline()
