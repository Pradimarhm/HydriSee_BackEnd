import json
from firebase_admin import credentials, firestore
import paho.mqtt.client as mqtt
from datetime import datetime
import threading

# config
from app.config import Config

class MqttFirebase:

    client = mqtt.Client()
    db_client = None

    # MQTT CallBack
    @staticmethod
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print(f"[{datetime.now()}] Received message on topic: {msg.topic}")
            print(f"[{datetime.now()}] Payload: {payload}")
            
            # --- EKSTRAKSI DEVICE ID SECARA DINAMIS ---
            topic_parts = msg.topic.split('/')
            
            # Cek jika ini pesan sensor (iot/DEVICE_ID/dht11)
            if topic_parts[0] == 'iot' and len(topic_parts) == 3 and topic_parts[2] == 'dht11':
                device_id = topic_parts[1]
                print(f"[{datetime.now()}] Processing sensor data for device: {device_id}")
                
            # Cek jika ini pesan LWT (hydrosee/status/DEVICE_ID/lwt)
            elif topic_parts[0] == 'hydrosee' and topic_parts[1] == 'status' and len(topic_parts) == 4 and topic_parts[3] == 'lwt':
                device_id = topic_parts[2]
                print(f"[{datetime.now()}] Processing LWT for device: {device_id}")
            else:
                print(f"[{datetime.now()}] Unknown topic structure: {msg.topic}")
                return
            
            # Referensi dokumen device
            device_ref = MqttFirebase.db_client.collection("devices").document(device_id)
            
            # Cek apakah dokumen device ada
            device_doc = device_ref.get()
            if not device_doc.exists:
                print(f"[{datetime.now()}] WARNING: Device {device_id} not found in Firestore!")
                return

            # --- LOGIKA LWT: MENDETEKSI STATUS OFFLINE ---
            if topic_parts[0] == 'hydrosee' and topic_parts[3] == 'lwt':
                status = payload.get("status", "unknown")
                
                device_ref.update({
                    "status": status,
                    "lastSeen": firestore.SERVER_TIMESTAMP
                })
                
                print(f"[{datetime.now()}] Device {device_id} status updated to: {status}")
                return
            
            # --- LOGIKA DATA SENSOR (ONLINE) ---
            # if all(k in payload for k in ("temp", "hum", "time", "status")):
            if all(k in payload for k in ("temp", "hum", "timestamp", "status")):
                
                # Parse timestamp
                timestamp_str = payload["timestamp"]
                timestamp_dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

                # sensor_data = {
                #     "temp": float(payload["temp"]),
                #     "hum": float(payload["hum"]),
                #     "timestamp": timestamp_dt 
                # }
                
                # # 1. Simpan data historis ke sub-koleksi 'readings'
                # readings_ref = device_ref.collection("readings")
                # readings_ref.add(sensor_data)
                # print(f"[{datetime.now()}] Historical data saved to readings subcollection")

                # 2. Update status/data utama perangkat
                device_ref.update({
                    "lastTemp": float(payload["temp"]),
                    "lastHum": float(payload["hum"]),
                    "status": payload["status"], 
                    "lastSeen": firestore.SERVER_TIMESTAMP 
                })
                
                print(f"[{datetime.now()}] Device {device_id} - Temp: {payload['temp']}°C, Hum: {payload['hum']}%, Status: {payload['status']}")
                
            else:
                print(f"[{datetime.now()}] Invalid payload received: {payload}, Topic: {msg.topic}")
                
        except json.JSONDecodeError as e:
            print(f"[{datetime.now()}] JSON decode error: {e}")
        except Exception as e:
            print(f"[{datetime.now()}] Error processing MQTT message: {e}")
            import traceback
            traceback.print_exc()
            
    @staticmethod
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("MQTT Connected successfully")
        
            # Subscribe untuk semua device
            client.subscribe("iot/+/dht11", qos=1)
            print("Subscribed to sensor topic: iot/+/dht11")
            
            # Subscribe LWT untuk semua device
            client.subscribe("hydrosee/status/+/lwt", qos=1)
            print("Subscribed to LWT topic: hydrosee/status/+/lwt")
            
        else:
            print(f"[{datetime.now()}] MQTT Connect failed with code {rc}")

    @staticmethod
    def on_disconnect(client, userdata, rc):
        print(f"[{datetime.now()}] MQTT Disconnected with code {rc}")
        if rc != 0:
            print(f"[{datetime.now()}] Unexpected disconnect, trying to reconnect...")

    @classmethod
    def start_mqtt_client(cls):
        try:
            # Inisialisasi Firestore client
            cls.db_client = firestore.client() 
            print(f"[{datetime.now()}] Firebase Firestore client initialized successfully")
        except Exception as e:
            print(f"[{datetime.now()}] FAILED to initialize Firestore client: {e}")
            return
        
        # MQTT Setup
        cls.client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASS)
        cls.client.tls_set()
        
        # Set callback
        cls.client.on_message = cls.on_message
        cls.client.on_connect = cls.on_connect
        cls.client.on_disconnect = cls.on_disconnect
        
        try:
            print(f"[{datetime.now()}] Connecting to MQTT Broker: {Config.MQTT_BROKER}")
            cls.client.connect(Config.MQTT_BROKER, 8883, keepalive=60)
            
            cls.client.loop_start()
            print(f"[{datetime.now()}] MQTT Client loop started (Receiving data)...")
        except Exception as e:
            print(f"[{datetime.now()}] Failed to connect MQTT: {e}")
            import traceback
            traceback.print_exc()