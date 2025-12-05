import json
import paho.mqtt.client as mqtt
import ssl
from datetime import datetime

from app.config import Config

PORT = 8883

class MqttSendToEsp32:
    client = None
    
    @classmethod
    def setup_client(cls):
        if cls.client:
            return # Sudah di setup
        
        cls.client = mqtt.Client()

        cls.client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASS)

        cls.client.tls_set(cert_reqs=ssl.CERT_NONE)
        cls.client.tls_insecure_set(True)
        
        try:
            cls.client.connect(Config.MQTT_BROKER, PORT, 60)
            cls.client.loop_start()
            print("MQTT Client loop (Sending Data)...")
        except Exception as e:
            print(f"Failed to connect MQTT for sending: {e}")

    # MQTT CallBack
    @classmethod
    def send_insect_status(cls, status="ada"):
        if not cls.client:
            cls.setup_client()
            
        if status not in ["ada", "tidak ada"]:
            print("Invalid Status. Pakai 'ada' atau 'tidak ada'.")
            
        data = {"status": "tidak"}        
        payload = json.dumps(data)
        
        if cls.client.is_connected():
            cls.client.publish(Config.MQTT_SEND_TO_ESP, payload, qos=1)
            print(f"[{datetime.now()}] Message sent to {Config.MQTT_SEND_TO_ESP}: {payload}")
        else:
            print(f"[{datetime.now()}] Failed to send message: MQTT client is not connected.")
        # client.publish(Config.MQTT_SEND_TO_ESP, payload, qos=1)
        # print("Pesan terkirim:", payload)
        
    # send_message()

    # client.loop_stop()

    # client.loop_forever()
    # client.disconnect()