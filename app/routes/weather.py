from flask import Blueprint, request, jsonify
from app.services import WeatherService 
import requests  

bp = Blueprint('weather', __name__)

@bp.route('/post', methods=['POST'])
def fetch_weather():
    data = request.get_json()
    lat = data.get("lat")
    lon = data.get("lon")

    if lat is None or lon is None:
        return jsonify({"error": "lat/lon required"}), 400

    try:
        lat = float(lat)
        lon = float(lon)
    except:
        return jsonify({"error": "lat/lon invalid"}), 400

    weather = WeatherService.get_full_weather_and_location                                              (lat, lon)
    
    print(weather)

    return jsonify(weather), 200    


@bp.route('/get', methods=['GET'])
def get_weather():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        
        if lat is None or lon is None:
            return jsonify({"error": "Latitude dan Longitude wajib disediakan"}), 400
        
        result = WeatherService.get_full_weather_and_location(lat, lon)
        
        if "error" in result and "Client Error" in result['error']:
            # Untuk error 401 Unauthorized
            return jsonify(result), 401
    
        if "error" in result:
            return jsonify(result), 500

        return jsonify(result), 200
    except:
        return jsonify({'error': 'lat/lon invalid'}), 400
    
    # data = WeatherService.get_weather(lat, lon)
    # return jsonify(data), 200
