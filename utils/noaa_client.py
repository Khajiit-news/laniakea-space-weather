import requests

class NOAAClient:
    def __init__(self):
        self.base_url = "https://services.swpc.noaa.gov"
        self.headers = {"User-Agent": "Laniakea-Space-Weather-Bot/2.0"}

    def get_solar_wind_and_mag(self):
        """Сбор данных с приоритетом на SOLAR-1"""
        wind_url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"
        mag_url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"
        
        try:
            wind_response = requests.get(wind_url, headers=self.headers, timeout=15).json()
            mag_response = requests.get(mag_url, headers=self.headers, timeout=15).json()
            
            # Фильтруем данные, чтобы оставить только SOLAR-1
            solar1_wind = [d for d in wind_response if d.get("source") == "SOLAR1"]
            solar1_mag = [d for d in mag_response if d.get("source") == "SOLAR1"]
            
            # Берем последние из отфильтрованных данных
            wind_data = solar1_wind[-1] if solar1_wind else {}
            mag_data = solar1_mag[-1] if solar1_mag else {}
            
            return {
                "source": "SOLAR-1", # Добавляем источник для отчета
                "speed": float(wind_data.get("speed", 0)),
                "density": float(wind_data.get("density", 0)),
                "bz": float(mag_data.get("bz", 0))
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
        
        # Идем с конца списка к началу, чтобы найти первое не нулевое значение
        for entry in reversed(data):
            val = float(entry.get("estimated_kp", 0))
            if val > 0:
                return val
        
        # Если все нули, возвращаем последнее значение из списка как есть
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
