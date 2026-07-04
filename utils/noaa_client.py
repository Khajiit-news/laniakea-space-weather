import requests

class NOAAClient:
    def __init__(self):
        self.base_url = "https://services.swpc.noaa.gov"
        self.headers = {"User-Agent": "Laniakea-Space-Weather-Bot/2.0"}

    def get_solar_wind_and_mag(self):
        """Сбор данных с поиском первой валидной строки с конца файла"""
        wind_url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"
        mag_url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"
        
        try:
            wind_response = requests.get(wind_url, headers=self.headers, timeout=15).json()
            mag_response = requests.get(mag_url, headers=self.headers, timeout=15).json()
            
            # Фильтруем данные SOLAR1
            solar1_wind = [d for d in wind_response if d.get("source") == "SOLAR1"]
            solar1_mag = [d for d in mag_response if d.get("source") == "SOLAR1"]
            
            # Поиск данных ветра (скорость и плотность)
            speed, density = 0.0, 0.0
            for entry in reversed(solar1_wind):
                # Проверяем, что значения не пустые и не являются ошибкой (-9999)
                s = entry.get("speed")
                d = entry.get("density")
                if s is not None and d is not None and float(s) > 0 and float(d) > 0:
                    speed, density = float(s), float(d)
                    break
            
            # Поиск Bz
            bz = 0.0
            for entry in reversed(solar1_mag):
                b = entry.get("bz")
                # Bz может быть отрицательным, поэтому проверяем только на None и -9999
                if b is not None and float(b) != -9999:
                    bz = float(b)
                    break
            
            return {
                "source": "SOLAR-1",
                "speed": speed,
                "density": density,
                "bz": bz
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
