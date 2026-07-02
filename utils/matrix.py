import requests
import datetime
import math

def get_sdo_matrix():
    """Возвращает прецизионную матрицу соответствий планет, спектров SDO и физики"""
    return {
        0: {
            "spectrum_id": "0335",
            "color": "королевском синем",
            "planet": "Луна",
            "focus": "анализ высокой короны, поиск скрытых резервов и накопления сил плазмы"
        },
        1: {
            "spectrum_id": "0304",
            "color": "ярко-красном",
            "planet": "Марс",
            "focus": "активность хромосферы, взрывные протуберанцы и выбросы плазменных нитей"
        },
        2: {
            "spectrum_id": "0094",
            "color": "изумрудно-зеленом",
            "planet": "Меркурий",
            "focus": "высокотемпературные зоны (6 млн К), экстремальные вспышки класса X и ментальная концентрация"
        },
        3: {
            "spectrum_id": "0193",
            "color": "бронзовом янтарном",
            "planet": "Юпитер",
            "focus": "корональные дыры, плотность и расширение сквозного солнечного ветра"
        },
        4: {
            "spectrum_id": "0211",
            "color": "пурпурном фиолетовом",
            "planet": "Венера",
            "focus": "контраст магнитных пустот и активных петель, гармония и баланс сил короны"
        },
        5: {
            "spectrum_id": "0131",
            "color": "бирюзово-синем",
            "planet": "Сатурн",
            "focus": "структура раскаленных плазменных нитей в жестких магнитных ловушках, удержание структуры"
        },
        6: {
            "spectrum_id": "0171",
            "color": "золотом",
            "planet": "Солнце",
            "focus": "чистые корональные петли, триумф энергии, ювелирные арки плазмы"
        }
    }

def get_spot_positions_on_image():
    """
    Парсит солнечные регионы из NOAA и переводит их координаты 
    в пиксели (для картинки 1024x1024) и понятные для ИИ квадранты.
    """
    url = "https://services.swpc.noaa.gov/json/solar_regions.json"
    try:
        regions = requests.get(url, timeout=5).json()
        if not regions:
            return []
            
        # Берем только самые свежие наблюдения
        latest_date = regions[-1]['observed_date']
        current_spots = [r for r in regions if r['observed_date'] == latest_date]
    except Exception as e:
        print(f"Ошибка получения координат пятен: {e}")
        return []
    
    image_size = 1024
    center = image_size // 2
    radius = 420  # Радиус диска Солнца на снимке SDO в пикселях
    
    detected_spots = []
    
    for spot in current_spots:
        raw_loc = spot.get('location')
        if not raw_loc or len(raw_loc) < 6:
            continue
            
        mag_class = spot.get('mag_class', 'Beta')
        region_num = spot.get('region')
        area = spot.get('area', 0)
        
        # Определяем знаки полусфер
        lat_sign = 1 if 'N' in raw_loc else -1
        lon_sign = -1 if 'E' in raw_loc else 1  # На картах SDO Восток слева, Запад справа
        
        try:
            lat_deg = int(raw_loc[1:3])
            lon_deg = int(raw_loc[4:6])
        except ValueError:
            continue
            
        # Перевод сферических координат в ортогональную проекцию на плоскость кадра
        lat_rad = math.radians(lat_deg)
        lon_rad = math.radians(lon_deg)
        
        x_pixel = center + int(radius * math.sin(lon_rad) * math.cos(lat_rad) * lon_sign)
        y_pixel = center - int(radius * math.sin(lat_rad) * lat_sign)
        
        quadrant_y = "Верхний (Север)" if lat_sign == 1 else "Нижний (Юг)"
        quadrant_x = "Левый (Восток)" if lon_sign == -1 else "Правый (Запад)"
        
        detected_spots.append({
            "region": region_num,
            "mag_class": mag_class,
            "area": area,
            "raw_location": raw_loc,
            "text_quadrant": f"{quadrant_y} {quadrant_x} квадрант",
            "pixel_coords": (x_pixel, y_pixel)
        })
        
    return detected_spots
