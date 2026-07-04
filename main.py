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
# GEMINI_API_KEY подхватывается автоматически SDK

client = genai.Client()

def ask_gemini(prompt_text):
    """Генерация с прыжком между моделями, повторными попытками и защитой от 503"""
    
    # Расширенный список моделей: от самых умных/новых к самым безотказным
    models = [
        'gemini-2.5-flash',
        'gemini-2.0-flash',   # Добавлена стабильная 2.0 на случай отсутствия 2.5
        'gemini-1.5-pro',     # Pro версия имеет другие серверные лимиты
        'gemini-1.5-flash',
        'gemini-1.5-flash-8b' # Очень быстрая и легкая модель, редко бывает перегружена
    ]
    
    max_retries_for_503 = 2 # Сколько раз стучаться в перегруженную модель перед сменой
    
    for model in models:
        for attempt in range(max_retries_for_503):
            try:
                print(f"Попытка через {model} (попытка {attempt + 1})...")
                response = client.models.generate_content(model=model, contents=prompt_text)
                return response.text
            
            except Exception as e:
                error_msg = str(e)
                print(f"Ошибка {model}: {error_msg}")
                
                # Если сервер перегружен (503), делаем паузу и пробуем снова
                if "503" in error_msg or "UNAVAILABLE" in error_msg:
                    wait_time = 5 * (attempt + 1) # Ждем 5 сек, потом 10 сек...
                    print(f"Модель {model} перегружена. Ждем {wait_time} сек...")
                    time.sleep(wait_time)
                    continue # Идем на следующий круг attempt
                    
                # Если модель не найдена (404) или другая ошибка - не ждем, меняем модель
                else:
                    print(f"Модель {model} недоступна. Переключаемся на следующую...")
                    break # Выходим из цикла попыток, идем к следующей модели в списке
                    
    return "Космический штиль. Системы ИИ временно недоступны из-за солнечных помех. Ждите обновлений."

def send_to_telegram(text, image_url):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Ключи Telegram не настроены.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": image_url, "caption": text, "parse_mode": "HTML"}
    requests.post(url, json=payload, timeout=10)

def run_pipeline():
    # Джиттер (0-7 минут)
    wait_time = random.randint(0, 420)
    print(f"Ожидание {wait_time} секунд...")
    time.sleep(wait_time)

def run_pipeline():
    noaa = NOAAClient()
    
# 1. Собираем физику и научные обзоры
    space_weather = noaa.get_solar_wind_and_mag()
    kp_index = noaa.get_kp_index()
    
    # ПРОВЕРКА: Если NOAA не ответила, не идем дальше
    if space_weather is None or kp_index is None:
        print("Данные NOAA недоступны. Прерываю работу.")
        return

    # Достаем текстовый обзор ученых
    swx_report = "Нет данных обзора."
    # (оставь свою логику try/except здесь как есть)
    
    speed = space_weather["speed"]
    density = space_weather["density"]
    bz = space_weather["bz"]
    pressure = (1.672 * 10**-6) * density * (speed ** 2)
    
    # Рубежи космической обороны
    shift_south = "Штиль. Мончегорск — на передовой сияний, Таллинн/СПб — в зоне ожидания, Екатеринбург (Уральский рубеж) — под защитой, Сочи — глубокий тыл."
    if bz < -5 or pressure > 4: 
        shift_south = "Среднее смещение. Накрывает Мончегорск, дотягивается до Таллинна и СПб. На Уральском рубеже (Екатеринбург) сгущаются тени."
    if bz < -8 or pressure > 7: 
        shift_south = "Серьезный прорыв. Овал горит над Балтийским рубежом (Таллинн, СПб). На Уральском рубеже (Екатеринбург) открытый космос."
    if bz < -12 or pressure > 12: 
        shift_south = "Экстремальный шторм века. Пробивает всё до Екатеринбурга, сияние катится к Москве, в Сочи с тревогой смотрят на небо."
        
    # Безопасный сбор данных об активных регионах
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

    # ... (код выше: сбор данных NOAA, Kp-индекс, расчет давления и т.д.)

    # 4. Выбираем спектр и planetary-метаданные
    current_weekday = datetime.datetime.utcnow().weekday()
    sdo_matrix = get_sdo_matrix()
    
    if is_event_trigger and override_spectrum:
        wave_num = override_spectrum
        meta_source = next((item for item in sdo_matrix.values() if item["spectrum_id"] == wave_num), sdo_matrix.get(current_weekday))
        planet_gov = f"{meta_source['planet']} (КРИТИЧЕСКИЙ ПЕРЕХВАТ)"
        focus_text = f"🚨 ЭКСТРЕННЫЙ СНИМОК: {meta_source['focus']}"
        color_text = meta_source["color"]
    else:
        today_meta = sdo_matrix.get(current_weekday, sdo_matrix[0])
        wave_num = today_meta["spectrum_id"]
        planet_gov = today_meta["planet"]
        focus_text = today_meta["focus"]
        color_text = today_meta["color"]
        
    # 4. Формируем URL с "анти-кэш" меткой времени
    # Добавление ?time=... заставляет сервер отдать актуальный файл, а не старый из кэша
    ts = int(datetime.datetime.utcnow().timestamp())
    sun_image = f"https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_{wave_num}.jpg?t={ts}"
    image_type = "live_sun_" + wave_num
    
    # 5. Собираем ТЕКСТ-ИНСТРУКЦИЮ для Gemini
    spots_info = ""
    if all_spots:
        for s in all_spots[:3]:
            spots_info += f"- Рег. {s.get('region')} ({s.get('mag_class')}), пл. {s.get('area', 0)} в {s.get('text_quadrant')}\n"

    # 5. Собираем ТЕКСТ-ИНСТРУКЦИЮ для Gemini
    spots_info = ""
    if all_spots:
        for s in all_spots[:3]:
            spots_info += f"- Рег. {s.get('region')} ({s.get('mag_class')}), пл. {s.get('area', 0)} в {s.get('text_quadrant')}\n"

    prompt = f"""
Ты — космический синоптик Каджит, ведущий журнал системы Laniakea. Напиши пост для ТГ.
Стиль: обращение от третьего лица "этот Каджит", "мудрый Каджит". 
Добавь немного атмосферы: упоминай чай и сладости, если спокойно, или будь серьезен, если шторм.

{"🚨 СИГНАЛ ТРЕВОГИ: " + event_reason if is_event_trigger else "☀️ ЕЖЕДНЕВНЫЙ ОБЗОР СОЛНЦА"}

Данные и Физика:
Магнитное поле (Bz): <b>{bz} нТл</b>, скорость: <b>{speed} км/с</b>, давление: <b>{round(pressure, 2)} нПа</b>, Kp={kp_index}.

Овал сияний: {shift_south}

Контекст: Управляет {planet_gov}. Спектр SDO: {wave_num}A ({color_text} цвет). Фокус дня: {focus_text}.

Активные пятна:
{spots_info if spots_info else "Чистый диск."}

Научный обзор NOAA (кратко перевари суть, не цитируй весь текст):
{swx_report[:1000]}

ИНСТРУКЦИЯ:
1. Смешай цифры, научный обзор и наши рубежи (Мончегорск, Таллинн/СПб, Екатеринбург, Сочи).
2. Используй ТОЛЬКО HTML-теги для разметки (<b>жирный</b>, <i>курсив</i>, <blockquote>цитата</blockquote>).
3. НЕ используй Markdown (*, _, `).
4. ЖЕСТКО: Весь ответ не длиннее 750 символов. Пиши емко.
"""

    final_post_text = ask_gemini(prompt)
    send_to_telegram(final_post_text, sun_image)

if __name__ == "__main__":
    run_pipeline()
