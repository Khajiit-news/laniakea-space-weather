import requests

class NOAAClient:
    def __init__(self):
        self.base_url = "https://services.swpc.noaa.gov"

    def get_solar_wind_and_mag(self):
        """Собирает реальный ветер и магнитное поле (RTSW)"""
        wind_url = f"{self.base_url}/json/rtsw/rtsw_wind_1m.json"
        mag_url = f"{self.base_url}/json/rtsw/rtsw_mag_1m.json"
        
        # Забираем последние точки
        try:
            wind_data = requests.get(wind_url, timeout=5).json()[-1]
            mag_data = requests.get(mag_url, timeout=5).json()[-1]
            return {
                "speed": float(wind_data.get("speed", 0)),
                "density": float(wind_data.get("density", 0)),
                "bz": float(mag_data.get("bz", 0))
            }
        except Exception as e:
            print(f"Ошибка сбора RTSW данных: {e}")
            return None

    def get_kp_index(self):
        """Забирает текущий планетарный Kp-индекс"""
        url = f"{self.base_url}/json/planetary_k_index_1m.json"
        try:
            kp_data = requests.get(url, timeout=5).json()[-1]
            return float(kp_data.get("kp_index", 0))
        except Exception:
            return 0.0
