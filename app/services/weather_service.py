from app.config import Config
import requests

class WeatherService:
    
    WEATHER_API_BASE = "https://api.openweathermap.org/data"
    GEO_API_BASE = "http://api.openweathermap.org/geo/1.0"
    
    @staticmethod
    def fetch_data(url):
        try:
            if "OneCall" in url:
                url += "&units=metric"
            if "lang" not in url:
                url += "&lang=id"

            res = requests.get(url, timeout=10)
            res.raise_for_status()
            return res.json()
        
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
        
    @staticmethod
    def get_location_name(lat, lon):
        url = f"{WeatherService.GEO_API_BASE}/reverse?lat={lat}&lon={lon}&limit=1&appid={Config.WEATHER_API}"
        
        data = WeatherService.fetch_data(url)
        
        if 'error' in data:
            return {"city": "Lokasi Error", "state": ""}
        
        if data and isinstance(data, list) and len(data) > 0:
            location = data[0]
            return {
                # Mengambil nama kota
                "city": location.get("name", "Lokasi Tidak Dikenal"),
                # Mengambil nama provinsi (state)
                "state": location.get("state", ""),
            }
        
        return {"city": "Lokasi Tidak Ditemukan", "state": ""}
    
    @staticmethod
    def get_full_weather_and_location(lat, lon):
        """Menggabungkan panggilan Lokasi (Reverse Geocoding) dan Cuaca (One Call API 3.0)."""
        
        # 1. Panggil API Lokasi
        location_data = WeatherService.get_location_name(lat, lon)
        
        # 2. Panggil API Cuaca (One Call 3.0)
        # Tambahkan exclude=minutely,alerts untuk menghemat bandwidth
        weather_url = f"{WeatherService.WEATHER_API_BASE}/3.0/onecall?lat={lat}&lon={lon}&appid={Config.WEATHER_API}&exclude=minutely,alerts"
        weather_data = WeatherService.fetch_data(weather_url)

        # Cek jika ada error dari panggilan cuaca
        if 'error' in weather_data:
            # Gabungkan error dengan data lokasi yang mungkin sudah didapat
            return {"error": weather_data['error'], "location": location_data}

        # 3. Gabungkan hasil
        return {
            "location": location_data,
            "forecast": weather_data,
        }

    # @staticmethod
    # def get_weather(lat, lon):
    #     url = f"{WeatherService.WEATHER_API_BASE}/3.0/onecall?lat={lat}&lon={lon}&appid={Config.WEATHER_API}"
    #     return WeatherService.fetch_data(url)
        # url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={Config.WEATHER_API}&units=metric"
        # url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={Config.WEATHER_API}"
        # # res = requests.get(url)
        # # return res.json()
        # try:
        #     res = requests.get(url, timeout=5)
        #     res.raise_for_status()
        #     return res.json()
        # except requests.exceptions.RequestException as e:
        #     return {"error": str(e)}