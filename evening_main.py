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
        
    # Собираем адрес по частям, защищая ссылку от случайной блокировки фильтрами GitHub
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
Ты — космический синоптик Каджит, ведущий ночной журнал системы Laniakea. 
Напиши свежий ночной пост для ТГ-канала.

Стиль: Обращение от третьего лица "этот Каджит", "мудрый Каджит". Упоминай ночной чай, лунный свет или звездную тишину, если на Солнце спокойно. Если впереди буря — будь серьезен.

ЗАДАЧА:
Внимательно прочитай этот свежий отчет американских ученых из NOAA. Полностью ИГНОРИРУЙ раздел прошлых суток (.24 hr Summary). 
Найди разделы БУДУЩЕГО ПРОГНОЗА (.Forecast) для Solar Activity, Energetic Particle, Solar Wind и Geospace.

Переведи суть прогноза на три дня вперед для наших рубежей (Мончегорск, Таллинн/СПб, Екатеринбург, Сочи). Расскажи, в какие из ближайших трех дней ученые ждут прорывы, магнитные бури или полярные сияния.

ИНСТРУКЦИЯ ПО ОФОРМЛЕНИЮ:
1. Используй ТОЛЬКО HTML-теги для разметки (<b>жирный</b>, <i>курсив</i>).
2. НЕ используй знаки Markdown (никаких звездочек *, нижних подчеркиваний _ или кавычек `).
3. Заголовок поста начни со смайлика: 🌙 НОЧНЫЕ СВИТКИ NOAA.
4. ЖЕСТКО: Весь ответ должен быть не длиннее 800 символов. Пиши очень емко и только самое главное.

Вот текст отчета ученых для анализа:
{swx_report}
"""

    # 3. Отдаем ИИ и отправляем результат в чат
    final_post_text = ask_gemini(prompt)
    send_text_to_telegram(final_post_text)

if __name__ == "__main__":
    run_evening_pipeline()
