import requests

class NOAAClient:
    def __init__(self):
        self.base_url = "https://services.swpc.noaa.gov"
        self.headers = {"User-Agent": "Laniakea-Space-Weather-Bot/2.0"}

    def get_solar_wind_and_mag(self):
        wind_url = f"{self.base_url}/json/rtsw/rtsw_wind_1m.json"
        mag_url = f"{self.base_url}/json/rtsw/rtsw_mag_1m.json"
        
        try:
            # Добавляем таймаут и headers
            wind_data = requests.get(wind_url, headers=self.headers, timeout=10).json()[-1]
            mag_data = requests.get(mag_url, headers=self.headers, timeout=10).json()[-1]
            
            # Валидация: если данные пришли, но значения пустые/нечисловые, бросаем ошибку
            speed = float(wind_data.get("speed", 0))
            bz = float(mag_data.get("bz", 0))
            
            if speed == 0 or bz == 0:
                raise ValueError("Получены пустые или нулевые данные от NOAA")
                
            return {
                "speed": speed,
                "density": float(wind_data.get("density", 0)),
                "bz": bz
            }
        except Exception as e:
            print(f"Критическая ошибка NOAA: {e}")
            return None # Теперь main.py поймет, что данных нет

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
