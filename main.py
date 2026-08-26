import os
import time
import random
import datetime
import requests
from google import genai
from utils.noaa_client import NOAAClient
from utils.matrix import get_sdo_matrix, get_spot_positions_on_image

# Загрузка ключей
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = genai.Client()

def ask_gemini(prompt_text):
    """Генерация с прыжком между моделями, повторными попытками и защитой от 503"""
    models = [
        'gemini-2.5-flash',
        'gemini-2.0-flash', 
        'gemini-1.5-pro',   
        'gemini-1.5-flash',
        'gemini-1.5-flash-8b'
    ]
    max_retries_for_503 = 2 
    
    for model in models:
        for attempt in range(max_retries_for_503):
            try:
                print(f"Попытка через {model} (попытка {attempt + 1})...")
                response = client.models.generate_content(model=model, contents=prompt_text)
                return response.text
            except Exception as e:
                error_msg = str(e)
                print(f"Ошибка {model}: {error_msg}")
                
                if "503" in error_msg or "UNAVAILABLE" in error_msg:
                    wait_time = 5 * (attempt + 1) 
                    print(f"Модель {model} перегружена. Ждем {wait_time} сек...")
                    time.sleep(wait_time)
                    continue 
                else:
                    print(f"Модель {model} недоступна. Переключаемся на следующую...")
                    break 
                    
    return "Космический штиль. Системы ИИ временно недоступны из-за солнечных помех. Ждите обновлений."

def send_to_telegram(text, image_url):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Ключи Telegram не настроены.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": image_url, "caption": text, "parse_mode": "HTML"}
    requests.post(url, json=payload, timeout=10)
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Ответ Telegram: {response.status_code}")
        if response.status_code != 200:
            print(f"Текст ошибки от Telegram: {response.text}")
    except Exception as e:
        print(f"Сбой сети при отправке в Telegram: {e}")

def run_pipeline():
    noaa = NOAAClient()
    
    # 1. Собираем физику
    space_weather = noaa.get_solar_wind_and_mag()
    kp_index = noaa.get_kp_index()
    
    if space_weather is None or kp_index is None:
        print("Данные NOAA недоступны. Прерываю работу.")
        return
        
    speed = space_weather["speed"]
    density = space_weather["density"]
    bz = space_weather["bz"]
    pressure = (1.672 * 10**-6) * density * (speed ** 2)
    
    # Расчет рубежей обороны
    shift_south = "Штиль. Мончегорск — на передовой сияний, Таллинн/СПб — в зоне ожидания, Екатеринбург (Уральский рубеж) — под защитой, Coчи — глубокий тыл."
    if bz < -5 or pressure > 4:
        shift_south = "Среднее смещение. Накрывает Мончегорск, дотягивается до Таллинна и СПб. На Уральском рубеже (Екатеринбург) сгущаются тени."
    if bz < -8 or pressure > 7:
        shift_south = "Серьезный прорыв. Овал горит над Балтийским рубежом (Таллинн, СПб). На Уральском рубеже (Екатеринбург) открытый космос."
    if bz < -12 or pressure > 12:
        shift_south = "Экстремальный шторм века. Пробивает всё до Екатеринбурга, сияние катится к Москве, в Сочи с тревогой смотрят на небо."

    # Сбор данных об активных регионах
    all_spots = get_spot_positions_on_image()
    delta_spots = []
    if all_spots:
        for spot in all_spots:
            if isinstance(spot, dict) and spot.get("mag_class"):
                if "Delta" in str(spot["mag_class"]):
                    delta_spots.append(spot)

    # 2. Проверяем, есть ли критическая угроза (Alert)
    is_event_trigger = False
    event_reason = ""
    override_spectrum = None
    
    if speed > 600 or bz < -7:
        is_event_trigger = True
        event_reason = "ГЕОМАГНИТНЫЙ ШТОРМ"
        override_spectrum = "0193"
        
    if len(delta_spots) > 0:
        is_event_trigger = True
        primary_threat = max(delta_spots, key=lambda s: s.get("area", 0) if s.get("area") else 0)
        event_reason = f"ЭКСТРЕМАЛЬНАЯ ВСПЫШЕЧНАЯ ОПАСНОСТЬ (Регион {primary_threat.get('region')})"
        override_spectrum = "0094"

    # 3. УМНЫЙ РЕЖИМ ТИШИНЫ: Проверяем, плановое ли сейчас время (12:00 по Таллину = 09:00 UTC)
    current_hour_utc = datetime.datetime.utcnow().hour
    is_scheduled_time = (current_hour_utc == 9)

    # Если время не плановое И тревоги нет — тихо засыпаем
    if not is_scheduled_time and not is_event_trigger:
        print(f"На Солнце всё спокойно (Ветер: {speed} км/с, Bz: {bz}). Сейчас {current_hour_utc}:00 UTC. Не плановое время. Монитор засыпает.")
        return

    # 4. Выбираем спектр SDO
    current_weekday = datetime.datetime.utcnow().weekday()
    sdo_matrix = get_sdo_matrix()
    
    if is_event_trigger and override_spectrum:
        wave_num = override_spectrum
        meta_source = next((item for item in sdo_matrix.values() if item["spectrum_id"] == wave_num), sdo_matrix.get(current_weekday))
        planet_gov = f"{meta_source['planet']} (КРИТИЧЕСКИЙ ПЕРЕХВАТ)"
        focus_text = f"🚨 ЭКСТРЕННЫЙ СНИМОК: {meta_source['focus']}"
        color_text = meta_source["color"]
    else:
        today_meta = sdo_matrix.get(current_weekday, sdo_matrix)
        wave_num = today_meta["spectrum_id"]
        planet_gov = today_meta["planet"]
        focus_text = today_meta["focus"]
        color_text = today_meta["color"]

    # Исправленный, настоящий URL снимка Солнца с серверов НАСА
    ts = int(datetime.datetime.utcnow().timestamp())
    sun_image = f"https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_{wave_num}.jpg?t={ts}"

    # Собираем информацию о пятнах
    spots_info = ""
    if all_spots:
        for s in all_spots[:3]:
            spots_info += f"- Рег. {s.get('region')} ({s.get('mag_class')}), пл. {s.get('area', 0)} в {s.get('text_quadrant')}\n"

    # Текстовый отчет
    swx_report = noaa.get_swx_report() or "Нет данных обзора."

    # 5. Собираем ТЕКСТ-ИНСТРУКЦИЮ для Gemini
    prompt = f"""
Ты — космический синоптик Каджит, ведущий журнал системы Laniakea. Напиши пост для ТГ.
Стиль: обращение от третьего лица "этот Каджит", "мудрый Каджит".
Атмосфера: упоминай чай и сладости, если спокойно, но будь предельно серьезен, если шторм.

ЗАГОЛОВОК:
{"🚨 СИГНАЛ ТРЕВОГИ: " + event_reason if is_event_trigger else "☀️ ЕЖЕДНЕВНЫЙ ОБЗОР СОЛНЦА"}

Данные и Физика:
Магнитное поле (Bz): {bz} нТл, скорость ветра: {speed} км/с, давление: {round(pressure, 2)} нПа, Kp={kp_index}.
Овал сияний: {shift_south}
Контекст: Управляет {planet_gov}. Спектр SDO: {wave_num}A ({color_text} цвет). Фокус дня: {focus_text}.

Активные пятна:
{spots_info if spots_info else "Чистый диск."}

Краткая научная суть из сводок (перевари емко):
{swx_report[:400] if not is_event_trigger else "Внимание сфокусировано на критических показателях приборов!"}

ЖЕСТКИЕ ОБЯЗАТЕЛЬСТВА ДЛЯ KHAJIIT ENGINE:
1. Сразу после заголовка выведи красивую цитату с точным временем замеров. Возьми время из научной сводки (строка :Issued: в тексте ниже). Читатели должны видеть точное время UTC.
2. Включи в текст ультра-короткую расшифровку: Bz — куда дует поле (если минус — ворота для бури открыты), Kp — уровень тряски планеты от 0 до 9. Выдели это красиво.
3. Разложи физику по нашим рубежам (Мончегорск, Таллинн/СПб, Екатеринбург, Сочи). Используй эмодзи в начале ключевых строк.
4. Используй ТОЛЬКО HTML-теги для разметки (<b>жирный</b>, <i>курсив</i>). НЕ используй Markdown (*, _, `).
5. ЛИМИТ: Твой ответ со всеми тегами должен быть НЕ ДЛИННЕЕ 750 СИМВОЛОВ. Пиши максимально сжато.

Текст отчета для поиска времени:
{swx_report}
"""
    final_post_text = ask_gemini(prompt)
    send_to_telegram(final_post_text, sun_image)

if __name__ == "__main__":
    run_pipeline()
