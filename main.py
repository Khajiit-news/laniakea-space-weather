import datetime
from utils.noaa_client import NOAAClient
from utils.matrix import get_sdo_matrix, get_spot_positions_on_image

def run_pipeline():
    # 1. Инициализируем клиент NOAA
    noaa = NOAAClient()
    
    # 2. Собираем физические параметры ветра и магнитного поля
    space_weather = noaa.get_solar_wind_and_mag()
    kp_index = noaa.get_kp_index()
    
    # Дефолтные значения на случай сбоя сети
    speed = space_weather["speed"] if space_weather else 0
    density = space_weather["density"] if space_weather else 0
    bz = space_weather["bz"] if space_weather else 0
    
    # 3. Расчет динамического давления плазмы
    pressure = (1.672 * 10**-6) * density * (speed ** 2)
    
    # 4. Расчет сдвига овала полярных сияний
    shift_south = "Минимальный"
    if bz < -5 or pressure > 4: 
        shift_south = "Средний (Доходит до СПб/Таллина)"
    if bz < -8 or pressure > 7: 
        shift_south = "Заметный (Дыхание космоса в Екатеринбурге)"
    if bz < -12 or pressure > 12: 
        shift_south = "Сильный (Видно даже в Москве)"
        
    # 5. Сбор данных об активных регионах и пятнах
    all_spots = get_spot_positions_on_image()
    
    # Ищем Delta-структуры, которые могут выдать мощную вспышку
    delta_spots = [spot for spot in all_spots if "Delta" in spot["mag_class"]]
    
    # =========================================================================
    # АВТОМАТИЧЕСКИЙ ТРИГГЕР СМЕНЫ РЕЖИМА (ALERT OVERRIDE)
    # =========================================================================
    is_event_trigger = False
    event_reason = ""
    override_spectrum = None
    
    # Триггер 1: Физическая буря прямо сейчас
    if speed > 600 or bz < -7:
        is_event_trigger = True
        event_reason = "ГЕОМАГНИТНЫЙ ШТОРМ / ВЫСОКОСКОРОСТНОЙ ПОТОК"
        override_spectrum = "0193"  # Корональные дыры и ветер (Юпитер)
        
    # Триггер 2: Обнаружены крупные взрывоопасные Delta-группы
    if len(delta_spots) > 0:
        is_event_trigger = True
        # Берем самую большую Delta-группу для фокуса
        primary_threat = max(delta_spots, key=lambda s: s["area"])
        event_reason = f"ЭКСТРЕМАЛЬНАЯ ВСПЫШЕЧНАЯ ОПАСНОСТЬ (Регион {primary_threat['region']} [{primary_threat['mag_class']}])"
        override_spectrum = "0094"  # Меркурий (94 Å) — экстремальный нагрев вспышек X-класса
        
    # =========================================================================
    # ВЫБОР СПЕКТРА: БАЗОВЫЙ ПЛАНЕТАРНЫЙ ИЛИ АВАРИЙНЫЙ
    # =========================================================================
    current_weekday = datetime.datetime.utcnow().weekday()
    sdo_matrix = get_sdo_matrix()
    
    if is_event_trigger and override_spectrum:
        wave_num = override_spectrum
        # Ищем метаданные для переопределенного спектра в матрице
        meta_source = next((item for item in sdo_matrix.values() if item["spectrum_id"] == wave_num), sdo_matrix[current_weekday])
        planet_gov = f"{meta_source['planet']} (ALERT OVERRIDE: {event_reason})"
        focus_text = f"СРОЧНЫЙ СНИМОК: {meta_source['focus']}"
        color_text = meta_source["color"]
    else:
        # Штатный режим по дню недели
        today_meta = sdo_matrix[current_weekday]
        wave_num = today_meta["spectrum_id"]
        planet_gov = today_meta["planet"]
        focus_text = today_meta["focus"]
        color_text = today_meta["color"]
        
    sun_image = f"https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_{wave_num}.jpg"
    image_type = f"live_sun_{wave_num}" if not is_event_trigger else f"alert_sun_{wave_num}"
    
    # Формируем финальный пакет данных
    raw_time = datetime.datetime.utcnow()
    formatted_time = raw_time.strftime("%d.%m.%Y %H:%M UTC")
    
    payload = {
        "status": "success",
        "time": formatted_time,
        "source": "Центр прогнозирования космической погоды (NOAA) & Laniakea Engine",
        "is_alert": is_event_trigger,
        "alert_reason": event_reason,
        
        "metrics": {
            "kp_index": kp_index,
            "bz_index": bz,
            "wind_speed": speed,
            "dynamic_pressure": round(pressure, 2),
            "aurora_shift": shift_south
        },
        
        "image_data": {
            "url": sun_image,
            "type": image_type,
            "angstrom": wave_num
        },
        
        "astrology_meta": {
            "weekday_id": current_weekday,
            "planet_governor": planet_gov,
            "spectrum_color": color_text,
            "physical_focus": focus_text
        },
        
        # Передаем координаты ВСЕХ активных пятен, чтобы Gemini понимал, что и где на диске находится
        "active_regions": all_spots,
        
        "critical_points": {
            "Murmansk_68N": "В зоне каспа (прямое втекание)",
            "Tallinn_SPb_59N": "На границе щита",
            "Ekaterinburg_56N": "Ожидание искры",
            "Sochi_43N": "Под защитой ядра поля"
        }
    }
    
    return payload

if __name__ == "__main__":
    # Локальный тест при запуске файла напрямую
    import json
    result = run_pipeline()
    print(json.dumps(result, indent=4, ensure_ascii=False))
