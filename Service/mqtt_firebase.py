import json
import firebase_admin
from firebase_admin import credentials, db
import paho.mqtt.client as mqtt
from datetime import datetime


# firebase setup
cred = credentials.Certificate("hydrosee-projects-firebase-adminsdk-fbsvc-dc95d05e8e.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://hydrosee-projects-default-rtdb.asia-southeast1.firebasedatabase.app"
})
# firebase_admin.initialize_app(cred)

ref = db.reference("devices/esp32")

# MQTT CallBack
def on_message(client, userdata, msg):
    # payload = json.loads(msg.payload.decode())

    # data = {
    #     "temperature": payload["temp"],
    #     "humidity": payload["hum"],
    #     "timestamp": payload["time"]
    # }

    # ref.set(data)  # update realtime
    # print("Updated Firebase:", data)
    # print(f"[{datetime.now()}] MQTT Message Received: {data}")
    
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[{datetime.now()}] Topic: {msg.topic}, Payload: {payload}")

        data = {
            "temperature": payload["temp"],
            "humidity": payload["hum"],
            "timestamp": payload["time"]
        }
        
        if all(k in payload for k in ("temp", "hum", "time")):
            ref.set(data)
            
            print(f"[{datetime.now()}] MQTT Topic {msg.topic} Received: {data}")
        else:
            # print("Invalid payload:", payload)
            print(f"[{datetime.now()}] Invalid payload received: {payload}, Topic: {msg.topic}")


        # ref.set(data)  # update realtime
        # print("Updated Firebase:", data)
        # print(f"[{datetime.now()}] MQTT Message Received: {data}")
        
    except Exception as e:
        print(f"[{datetime.now()}] Error processing MQTT message:", e)
        
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT Connected successfully")
        client.subscribe("iot/esp32/dht11", qos=1)
        print("Subscribed to topic: iot/esp32/dht11")
    else:
        print("MQTT Connect failed with code", rc)

def on_disconnect(client, userdata, rc):
    print(f"MQTT Disconnected with code {rc}, trying to reconnect...")
    # try:
    #     client.reconnect()
    # except Exception as e:
    #     print("Reconnect failed:", e)







# MQTT Setup
client = mqtt.Client()
client.username_pw_set("hydrosee_20251411", "Hs*14_11_2025")

client.tls_set()

client.connect("7f2287ee7e7a4e9381d52e6ca949cf11.s1.eu.hivemq.cloud", 8883, keepalive=60)
# client.subscribe("iot/esp32/dht11", qos=1)
client.on_message = on_message
client.on_connect = on_connect
client.on_disconnect = on_disconnect

# RECONNECT OTOMATIS
client.reconnect_delay_set(min_delay=1, max_delay=120)

print("MQTT Client Running...")
client.loop_forever()