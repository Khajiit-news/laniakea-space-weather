import requests

class NOAAClient:
    def __init__(self):
        self.base_url = "https://services.swpc.noaa.gov"
        self.headers = {"User-Agent": "Laniakea-Space-Weather-Bot/2.0"}

    def get_solar_wind_and_mag(self):
        """Прямой сбор данных из статических JSON-файлов NOAA"""
        # Используем ссылки из твоего README
        wind_url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"
        mag_url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"
        
        try:
            # Загружаем данные напрямую
            wind_response = requests.get(wind_url, headers=self.headers, timeout=15).json()
            mag_response = requests.get(mag_url, headers=self.headers, timeout=15).json()
            
            # Берем последние данные из массива
            wind_data = wind_response[-1]
            mag_data = mag_response[-1]
            
            return {
                "speed": float(wind_data.get("speed", 0)),
                "density": float(wind_data.get("density", 0)),
                "bz": float(mag_data.get("bz", 0))
            }
        except Exception as e:
            print(f"Ошибка при прямом чтении JSON: {e}")
            return None

    def get_kp_index(self):
        """Забирает текущий планетарный Kp-индекс с защитой"""
        url = f"{self.base_url}/json/planetary_k_index_1m.json"
        try:
            # Добавили headers и увеличили таймаут для стабильности
            kp_data = requests.get(url, headers=self.headers, timeout=10).json()[-1]
            return float(kp_data.get("kp_index", 0))
        except Exception as e:
            print(f"Ошибка получения Kp-индекса: {e}")
            return None # Возвращаем None, чтобы main.py мог корректно обработать отсутствие данных

def get_swx_report(self):
        """Скачивает свежий текстовый обзор NOAA"""
        url = "https://services.swpc.noaa.gov/text/discussion.txt"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.text
        except Exception as e:
            print(f"Ошибка чтения discussion.txt: {e}")
            return "Обзор временно недоступен."
