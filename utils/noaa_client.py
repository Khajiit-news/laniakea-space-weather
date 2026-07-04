import requests

class NOAAClient:
    def __init__(self):
        self.base_url = "https://services.swpc.noaa.gov"
        self.headers = {"User-Agent": "Laniakea-Space-Weather-Bot/2.0"}

    def get_solar_wind_and_mag(self):
        """Сбор данных с принудительной фильтрацией нулей"""
        wind_url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"
        mag_url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"
        
        try:
            wind_response = requests.get(wind_url, headers=self.headers, timeout=15).json()
            mag_response = requests.get(mag_url, headers=self.headers, timeout=15).json()
            
            # Берем только SOLAR1
            solar1_wind = [d for d in wind_response if d.get("source") == "SOLAR1"]
            solar1_mag = [d for d in mag_response if d.get("source") == "SOLAR1"]
            
            speed, density, bz = 0.0, 0.0, 0.0
            
            # Ищем ВЕТЕР (скорость > 200, чтобы отсечь мусор)
            for entry in reversed(solar1_wind):
                s = float(entry.get("speed", 0))
                d = float(entry.get("density", 0))
                if s > 200 and d > 0: # Реалистичные данные ветра
                    speed, density = s, d
                    break
            
            # Ищем МАГНИТНОЕ ПОЛЕ (Bz не может быть 0, если спутник работает)
            for entry in reversed(solar1_mag):
                b = entry.get("bz")
                if b is not None and float(b) != 0 and float(b) != -9999:
                    bz = float(b)
                    break
            
            return {
                "source": "SOLAR-1",
                "speed": speed,
                "density": density,
                "bz": bz
            }
        except Exception as e:
            print(f"Ошибка получения данных: {e}")
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
