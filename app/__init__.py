from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.routes import iot_device

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    @app.route("/")
    def home():
        return "Hydrosee backend is running", 200

    
    # Enable CORS untuk Flutter
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    # from app.routes import auth, detection, history, registration_device
    from app.routes import auth, weather, upload_image, iot_device
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    # app.register_blueprint(iot_device.bp, url_prefix='/api/registration_device')
    app.register_blueprint(iot_device.bp, url_prefix='/api/iot_device')
    app.register_blueprint(weather.bp, url_prefix='/api/weather')
    app.register_blueprint(upload_image.bp, url_prefix='/api/upload_image')
    # app.register_blueprint(detection.bp, url_prefix='/api/detection')
    # app.register_blueprint(history.bp, url_prefix='/api/history')
    
    return app