import requests

class NOAAClient:
    def __init__(self):
        self.base_url = "https://services.swpc.noaa.gov"
        self.headers = {"User-Agent": "Laniakea-Space-Weather-Bot/2.0"}

    import json

def get_solar_wind_and_mag(self):
        """Сбор данных с серверов ACE"""
        # Если это URL, используем requests
        wind_url = "https://services.swpc.noaa.gov/json/ace/swepam/ace_swepam_1h.json"
        mag_url = "https://services.swpc.noaa.gov/json/ace/mag/ace_mag_1h.json"
        
        try:
            # Загружаем данные по ссылкам
            wind_response = requests.get(wind_url, headers=self.headers, timeout=15).json()
            mag_data = requests.get(mag_url, headers=self.headers, timeout=15).json()
            
            speed, density, bz = 0.0, 0.0, 0.0
            
            # Поиск по ветру
            for entry in reversed(wind_response):
                s = float(entry.get("speed") or entry.get("plasma_speed") or 0)
                d = float(entry.get("density") or 0)
                if s > 200 and d > 0:
                    speed, density = s, d
                    break
            
            # Поиск по магнитному полю
            for entry in reversed(mag_data):
                b = entry.get("bz") or entry.get("bz_gsm")
                if b is not None and float(b) not in [0, -9999.9, -9999]:
                    bz = float(b)
                    break
            
            return {
                "source": "ACE",
                "speed": speed,
                "density": density,
                "bz": bz
            }
        except Exception as e:
            print(f"Ошибка получения данных ACE: {e}")
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
