import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # Firebase Configuration
    FIREBASE_CREDENTIALS = os.getenv('FIREBASE_CREDENTIALS', 'firebase_credentials/serviceAccountKey.json')
    FIREBASE_DATABASE_URL = os.getenv('FIREBASE_DATABASE_URL', 'https://hydrosee-projects-default-rtdb.asia-southeast1.firebasedatabase.app')
    
    
    # MQTT Configuration
    MQTT_BROKER = "7f2287ee7e7a4e9381d52e6ca949cf11.s1.eu.hivemq.cloud"
    MQTT_USERNAME = "hydrosee_20251411"
    MQTT_PASS = "Hs*14_11_2025"
    
    # MQTT Topics
    MQTT_SEND_TO_ESP = "serangga/deteksi"
    MQTT_FIREBASE = "iot/esp32/dht11"
    
    # api weather
    WEATHER_API = "5fabd5b9dae76c1711272b9c943e6e17"
    
    # ML Model Configuration
    MODEL_PATH = 'ml_models/insect_detection_model.h5'
    LABELS_PATH = 'ml_models/labels.txt'

# For Firebase JS SDK v7.20.0 and later, measurementId is optional
# const firebaseConfig = {
#   apiKey: "AIzaSyCv1eP5mXvViGjsvIJCJcWh2KX3vYWYJfM",
#   authDomain: "hydrosee-projects.firebaseapp.com",
#   databaseURL: "https://hydrosee-projects-default-rtdb.asia-southeast1.firebasedatabase.app",
#   projectId: "hydrosee-projects",
#   storageBucket: "hydrosee-projects.firebasestorage.app",
#   messagingSenderId: "715197041903",
#   appId: "1:715197041903:web:2934f51cd5acda79fcdf1a",
#   measurementId: "G-YG7Z3MYCD2"
# };