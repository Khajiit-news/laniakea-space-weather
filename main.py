import os
import datetime
import requests
from google import genai
from utils.noaa_client import NOAAClient
from utils.matrix import get_sdo_matrix, get_spot_positions_on_image

# Инициализируем клиент (он автоматически берет GEMINI_API_KEY из окружения)
client = genai.Client()

def ask_gemini(prompt_text):
    """Генерация через современный SDK google-genai"""
    try:
        # Используем модель 1.5-flash — она быстрая, стабильная и везде доступная
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt_text,
        )
        return response.text
    except Exception as e:
        print(f"Критическая ошибка Gemini SDK: {e}")
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
        "parse_mode": "HTML"
    }
    
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code != 200:
            print(f"Ошибка TG API: {res.text}")
        else:
            print("Пост успешно отправлен в Telegram!")
    except Exception as e:
        print(f"Ошибка отправки в TG: {e}")

def run_pipeline():
    noaa = NOAAClient()
    
    # 1. Собираем физику и научные обзоры
    space_weather = noaa.get_solar_wind_and_mag()
    kp_index = noaa.get_kp_index()
    
    # Достаем текстовый обзор ученых за прошедшие сутки (события, вспышки)
    swx_report = "Нет данных обзора."
    try:
        if hasattr(noaa, 'get_swx_report'):
            swx_report = noaa.get_swx_report()
        elif hasattr(noaa, 'get_latest_report'):
            swx_report = noaa.get_latest_report()
    except Exception as e:
        print(f"Не удалось достать текстовый обзор: {e}")
    
    speed = space_weather["speed"] if space_weather else 0
    density = space_weather["density"] if space_weather else 0
    bz = space_weather["bz"] if space_weather else 0
    pressure = (1.672 * 10**-6) * density * (speed ** 2)
    
    # Рубежи космической обороны для ИИ
    shift_south = "Штиль. Мончегорск — на передовой сияний, Таллинн/СПб — в зоне ожидания, Екатеринбург (Уральский рубеж) — под защитой, Сочи — глубокий тыл."
    if bz < -5 or pressure > 4: 
        shift_south = "Среднее смещение. Накрывает Мончегорск, дотягивается до Таллинна и СПб. На Уральском рубеже (Екатеринбург) сгущаются тени."
    if bz < -8 or pressure > 7: 
        shift_south = "Серьезный прорыв. Овал горит над Балтийским рубежом (Таллинн, СПб). На Уральском рубеже (Екатеринбург) открытый космос."
    if bz < -12 or pressure > 12: 
        shift_south = "Экстремальный шторм века. Пробивает всё до Екатеринбурга, сияние катится к Москве, в Сочи с тревогой смотрят на небо."
        
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
        event_reason = "ГЕОМАГНИТНЫЙ ШТОРМ"
        override_spectrum = "0193"
        
    if len(delta_spots) > 0:
        is_event_trigger = True
        primary_threat = max(delta_spots, key=lambda s: s.get("area", 0) if s.get("area") else 0)
        event_reason = f"ЭКСТРЕМАЛЬНАЯ ВСПЫШЕЧНАЯ ОПАСНОСТЬ (Регион {primary_threat.get('region')})"
        override_spectrum = "0094"

    # 3. Определяем время: теперь плановый обзор выходит строго после обновления NOAA в 9 UTC (12:00 Таллин)
    current_hour_utc = datetime.datetime.utcnow().hour
    is_scheduled_time = True 
    
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
        for s in all_spots[:3]:
            spots_info += f"- Рег. {s.get('region')} ({s.get('mag_class')}), пл. {s.get('area', 0)} в {s.get('text_quadrant')}\n"

    prompt = f"""
Ты — космический синоптик Каджит, ведущий журнал системы Laniakea. Напиши пост для ТГ.
Стиль: обращение от третьего лица "этот Каджит", "мудрый Каджит".
Формат: жирный шрифт для ключевых фраз, короткие абзацы.
ФОРМАТИРОВАНИЕ: Используй ТОЛЬКО HTML-теги для разметки. 
- Жирный текст делай через <b>главная фраза</b>
- Цитаты или выжимки ученых оформляй через <i>текст цитаты</i>
НЕ используй маркеры Markdown (*, _, `), только HTML!

ЖЕСТКОЕ ОГРАНИЧЕНИЕ: Весь твой ответ должен быть не длиннее 750 символов! Пиши максимально емко, лаконично, без «воды».

{"🚨 СИГНАЛ ТРЕВОГИ: " + event_reason if is_event_trigger else "☀️ ЕЖЕДНЕВНЫЙ ОБЗОР СОЛНЦА"}

Текущие параметры: Kp={kp_index}, Bz={bz} nT, Скорость={speed} км/с, Давление={round(pressure, 2)} nPa.
Овал сияний: {shift_south}

Контекст: Управляет {planet_gov}. Спектр SDO: {wave_num}A ({color_text} цвет). Фокус дня: {focus_text}.

Текстовый отчет ученых за сутки (сделай из него ОДНУ ультра-краткую выжимку главного события):
{swx_report}

Активные пятна:
{spots_info if spots_info else "Чистый диск."}

Задача: Кратко перевари научный отчет и выдай выжимку сути за сутки. Обыграй цифры и овал сияний через наши рубежи. Обязательно упомяни Мончегорск (Заполярье), Таллинн и СПб (Балтийский рубеж), Екатеринбург (Уральский рубеж) и Сочи (тыл). Каждый день описывай их состояние по-новому, живо и атмосферно, но КРАТКО, чтобы уложиться в лимит знаков!
"""

    final_post_text = ask_gemini(prompt)
    send_to_telegram(final_post_text, sun_image)

if __name__ == "__main__":
    run_pipeline()
