import json
import paho.mqtt.client as mqtt
import ssl

BROKER = "7f2287ee7e7a4e9381d52e6ca949cf11.s1.eu.hivemq.cloud"
PORT = 8883
TOPIC = "serangga/deteksi"

USERNAME = "hydrosee_20251411"
PASS = "Hs*14_11_2025"

client = mqtt.Client()

client.username_pw_set(USERNAME, PASS)

client.tls_set(cert_reqs=ssl.CERT_NONE)
client.tls_insecure_set(True)

client.connect(BROKER, PORT, 60)

client.loop_start()

# MQTT CallBack
def send_message():
    data = {"status": "ada"}
    
    payload = json.dumps(data)
    client.publish(TOPIC, payload, qos=1)
    print("Pesan terkirim:", payload)
    
send_message()

client.loop_stop()

# client.loop_forever()
client.disconnect()