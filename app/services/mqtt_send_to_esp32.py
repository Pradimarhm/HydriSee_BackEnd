import json
import paho.mqtt.client as mqtt
import ssl
import time
from datetime import datetime

from app.config import Config

PORT = 8883

class MqttSendToEsp32:
    client = None
    
    @classmethod
    def wait_until_connected(cls, timeout=5):
        """Tunggu sampai MQTT benar-benar terkoneksi"""
        for _ in range(timeout * 10):
            if cls.client and cls.client.is_connected():
                return True
            time.sleep(0.1)
        return False
    
    @classmethod
    def ensure_connected(cls):
        """Pastikan MQTT selalu terkoneksi. Jika putus → reconnect."""
        if cls.client is None:
            cls.setup_client()
            return

        if not cls.client.is_connected():
            print("⚠ MQTT terputus. Mencoba reconnect...")
            try:
                cls.client.reconnect()
                print("✅ MQTT reconnect berhasil!")
            except Exception as e:
                print(f"❌ MQTT reconnect gagal: {e}")

    @classmethod
    def setup_client(cls):
        if cls.client:
            return  # Sudah di-setup
        
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

    @classmethod
    def send_insect_status(cls, status="ada"):
        # Pastikan client tetap hidup & reconnect jika terputus
        cls.ensure_connected()

        if not cls.client:
            cls.setup_client()

        if status not in ["ada", "tidak ada"]:
            print("Invalid Status. Pakai 'ada' atau 'tidak ada'.")
            return
            
        data = {"status": status}
        payload = json.dumps(data)
        
        if cls.client.is_connected():
            cls.client.publish(Config.MQTT_SEND_TO_ESP, payload, qos=1)
            print(f"[{datetime.now()}] Message sent to {Config.MQTT_SEND_TO_ESP}: {payload}")
        else:
            print(f"[{datetime.now()}] MQTT masih tidak terhubung. Pesan TIDAK terkirim.")
