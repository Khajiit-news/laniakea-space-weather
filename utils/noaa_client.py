import requests

class NOAAClient:
    def __init__(self):
        self.base_url = "https://services.swpc.noaa.gov"
        self.headers = {"User-Agent": "Laniakea-Space-Weather-Bot/2.0"}

    def get_solar_wind_and_mag(self):
        """Сбор данных с приоритетом на SOLAR-1 с защитой от пустых значений"""
        wind_url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"
        mag_url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"
        
        try:
            wind_response = requests.get(wind_url, headers=self.headers, timeout=15).json()
            mag_response = requests.get(mag_url, headers=self.headers, timeout=15).json()
            
            # Фильтруем данные, чтобы оставить только SOLAR-1
            solar1_wind = [d for d in wind_response if d.get("source") == "SOLAR1"]
            solar1_mag = [d for d in mag_response if d.get("source") == "SOLAR1"]
            
            # Ищем первые валидные данные параметров ветра (с конца)
            valid_speed = 0.0
            valid_density = 0.0
            
            for entry in reversed(solar1_wind):
                speed = entry.get("speed")
                density = entry.get("density")
                
                # Отсекаем None и заглушки. Скорость и плотность должны быть > 0
                if speed is not None and density is not None:
                    if float(speed) > 0 and float(density) > 0:
                        valid_speed = float(speed)
                        valid_density = float(density)
                        break
            
            # Ищем первые валидные данные магнитного поля (с конца)
            valid_bz = 0.0
            
            for entry in reversed(solar1_mag):
                bz = entry.get("bz")
                
                # Отсекаем None и системные заглушки. bz МОЖЕТ быть отрицательным!
                if bz is not None and float(bz) != -9999:
                    valid_bz = float(bz)
                    break
            
            return {
                "source": "SOLAR-1", # Добавляем источник для отчета
                "speed": valid_speed,
                "density": valid_density,
                "bz": valid_bz
            }
            
        except Exception as e:
            print(f"Ошибка при чтении данных SOLAR-1: {e}")
            return None

    def get_kp_index(self):
        """Забирает последний актуальный Kp-индекс (исключая нулевые выбросы)"""
        url = f"{self.base_url}/json/planetary_k_index_1m.json"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            
            for entry in reversed(data):
                val = float(entry.get("estimated_kp", 0))
                if val > 0:
                    return val
            
            return float(data[-1].get("estimated_kp", 0))
            
        except Exception as e:
            print(f"Ошибка получения Kp-индекса: {e}")
            return None

    def get_swx_report(self):
        """Скачивает свежий текстовый обзор NOAA"""
        url = "https://services.swpc.noaa.gov/text/discussion.txt"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.text
        except Exception as e:
            print(f"Ошибка чтения discussion.txt: {e}")
            return "Обзор временно недоступен."
