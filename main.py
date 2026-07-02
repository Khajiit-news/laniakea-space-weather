import os
import datetime
import requests
import json
from utils.noaa_client import NOAAClient
from utils.matrix import get_sdo_matrix, get_spot_positions_on_image

# Загружаем скрытые ключи из настроек GitHub
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def ask_gemini(prompt_text):
    """Отправляет структурированные цифры в Gemini и просит написать красивый пост"""
    if not GEMINI_API_KEY:
        print("Ключ Gemini не найден, отдаем сырой текст")
        return prompt_text
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Ошибка Gemini: {e}")
        return "Ошибка генерации текста через ИИ."

def send_to_telegram(text, image_url):
    """Отправляет красивый пост с картинкой в ваш Телеграм-канал"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Ключи Telegram не настроены.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": image_url,
        "caption": text,
        "parse_mode": "Markdown"
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
        print("Пост успешно отправлен в Telegram!")
    except Exception as e:
        print(f"Ошибка отправки в TG: {e}")

def run_pipeline():
    noaa = NOAAClient()
    
    # 1. Собираем физику
    space_weather = noaa.get_solar_wind_and_mag()
    kp_index = noaa.get_kp_index()
    
    speed = space_weather["speed"] if space_weather else 0
    density = space_weather["density"] if space_weather else 0
    bz = space_weather["bz"] if space_weather else 0
    pressure = (1.672 * 10**-6) * density * (speed ** 2)
    
    # Рубежи космической обороны и ориентиры аврорального овала для ИИ
    shift_south = "Штиль. Мончегорск — на передовой сияний, Таллинн/СПб — в зоне ожидания, Екатеринбург (Уральский рубеж) — под полной защитой, Сочи — глубокий тыл."
    if bz < -5 or pressure > 4: 
        shift_south = "Среднее смещение. Накрывает Мончегорск и Мурманскую область, дотягивается до Таллинна и СПб. На Уральском рубеже (Екатеринбург) сгущаются космические тени."
    if bz < -8 or pressure > 7: 
        shift_south = "Серьезный прорыв. Овал ярко разгорается над Балтийским рубежом (Таллинн, СПб). На Уральском рубеже (Екатеринбург) чувствуется дыхание открытого космоса. В Сочи всё спокойно."
    if bz < -12 or pressure > 12: 
        shift_south = "Экстремальный шторм века. Пробивает всё от Мончегорска до Таллинна и Екатеринбурга, сияние катится к Москве, даже в глубоком тылу в Сочи начинают с тревогой смотреть на небо."
        
    # Безопасный сбор данных об активных регионах и пятнах
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
        event_reason = "ГЕОМАГНИТНЫЙ ШТОРМ / ВЫСОКОСКОРОСТНОЙ ПОТОК"
        override_spectrum = "0193"
        
    if len(delta_spots) > 0:
        is_event_trigger = True
        primary_threat = max(delta_spots, key=lambda s: s.get("area", 0) if s.get("area") else 0)
        event_reason = f"ЭКСТРЕМАЛЬНАЯ ВСПЫШЕЧНАЯ ОПАСНОСТЬ (Регион {primary_threat.get('region')} [{primary_threat.get('mag_class')}])"
        override_spectrum = "0094"

    # 3. Определяем время: сейчас час планового обзора или нет?
    current_hour_utc = datetime.datetime.utcnow().hour
    is_scheduled_time = (current_hour_utc == 6)
    
    # ГЛАВНЫЙ ФИЛЬТР: Если это не утро, и при этом на Солнце всё спокойно — тихо выходим
    if not is_scheduled_time and not is_event_trigger:
        print("На Солнце всё спокойно. Плановое время не подошло. Монитор засыпает.")
        return

    # 4. Выбираем спектр и planetary-метаданные
    current_weekday = datetime.datetime.utcnow().weekday()
    sdo_matrix = get_sdo_matrix()
    
    if is_event_trigger and override_spectrum:
        wave_num = override_spectrum
        meta_source = next((item for item in sdo_matrix.values() if item["spectrum_id"] == wave_num), sdo_matrix[current_weekday])
        planet_gov = f"{meta_source['planet']} (КРИТИЧЕСКИЙ ПЕРЕХВАТ)"
        focus_text = f"🚨 ЭКСТРЕННЫЙ СНИМОК: {meta_source['focus']}"
        color_text = meta_source["color"]
    else:
        today_meta = sdo_matrix[current_weekday]
        wave_num = today_meta["spectrum_id"]
        planet_gov = today_meta["planet"]
        focus_text = today_meta["focus"]
        color_text = today_meta["color"]
        
    sun_image = f"https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_{wave_num}.jpg"
    
    # 5. Собираем ТЕКСТ-ИНСТРУКЦИЮ для Gemini
    spots_info = ""
    if all_spots:
        for s in all_spots:
            spots_info += f"- Регион {s.get('region')} ({s.get('mag_class')}), площадь {s.get('area', 0)}. Находится в: {s.get('text_quadrant')}\n"

    prompt = f"""
Ты — космический синоптик и мудрый Каджит, ведущий бортовой журнал системы Laniakea. Напиши пост для Телеграма.
Используй свой уникальный стиль (обращение от третьего лица "этот Каджит", "мудрый Каджит").
Сделай текст scannable: используй жирный шрифт для акцентов, разделяй мысли на абзацы и списки.

{"ГОРЯЧИЙ ДЕЖУРНЫЙ СИГНАЛ ТРЕВОГИ!" if is_event_trigger else "ЕЖЕДНЕВНЫЙ УТРЕННИЙ ОБЗОР СОЛНЦА"}

Текущие physical-параметры:
- Индекс Kp: {kp_index}
- Индекс Bz (магнитное поле): {bz} nT
- Скорость ветра: {speed} км/с
- Динамическое давление плазмы: {round(pressure, 2)} nPa
- Сдвиг аврорального овала: {shift_south}

Астрологический контекст дня:
- День под управлением планеты: {planet_gov}
- Смотрим на Солнце в спектре SDO: {wave_num} Ангстрем (в {color_text} цвете)
- Фокус внимания этого дня: {focus_text}

Активные регионы и пятна на диске Солнца:
{spots_info if spots_info else "Чистый диск, явных пятен нет."}

Важная художественная задача для Каджита:
Обыграй текущий сдвиг овала через наши рубежи космической обороны. Вплети в текст упоминания Мончегорска (Заполярье), Таллинна и СПб (Балтийский рубеж), Екатеринбурга (наш нерушимый Уральский рубеж) и Сочи (глубокий тыл). 
ВНИМАНИЕ: Не копируй сухой текст параметров! Прояви фантазию Каджита, каждый раз описывай состояние этих городов по-новому, живо, метафорично и атмосферно, в зависимости от того, спокойное Солнце или бушует шторм. Екатеринбург должен упоминаться как надежный рубеж обороны.

Напиши атмосферный, но точный аналитический пост на основе этих цифр. Если это Тревога (Alert) — сфокусируйся на опасности и квадрантах пятен, которые её вызвали.
"""

    final_post_text = ask_gemini(prompt)
    send_to_telegram(final_post_text, sun_image)

if __name__ == "__main__":
    run_pipeline()
