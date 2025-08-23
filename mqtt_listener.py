#!/usr/bin/env python3
#Test code to listen to MQTT messages and parse device status
# Usage: python mqtt_listener.py
import paho.mqtt.client as mqtt
import json
import time
import logging
from colorama import Fore, Style, init
init(autoreset=False)

# Importing colorama for colored output in terminal

# Configurazione base del logging
logging.basicConfig(
    level=logging.INFO,  # livello minimo da mostrare
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

# Parametri MQTT
BROKER = "192.168.222.5"
PORT = 1883
TOPIC = "application/d9821a50-729b-4330-aab1-21c0562795de/device/001bc50670113a39/event/#"

# Funzione di parsing
def parse_device_status(mqtt_payload: str) -> str:
    try:
        data = json.loads(mqtt_payload)
        obj = data.get("object", {})
        device_type = obj.get("DeviceType", {}).get("value", "?")
        device_num = obj.get("DeviceNum", {}).get("value", "?")
        device_status = obj.get("DeviceStatus", {}).get("value", "?")
        if  device_status == "ON":
                        print(Fore.GREEN)
        elif device_status == "OFF":
                        print(Fore.RED)
        elif device_status == "OK":
                        print(Fore.YELLOW)

        return f"Dev: {device_type} - Num: {device_num} - Stat: {device_status}"
    except json.JSONDecodeError:
        return "Errore: payload non valido JSON"

# Callback connessione
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Connesso al broker MQTT")
        client.subscribe(TOPIC)
        print(f"📡 Sottoscritto al topic: {TOPIC}")
    else:
        print("❌ Connessione fallita, codice:", rc)

# Callback messaggi
def on_message(client, userdata, msg):
    #print("\n--- Messaggio ricevuto ---")
    payload = msg.payload.decode("utf-8")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return #ignora payload non JSON

    # UPLINK (solo DeviceStatus ON/OFF)
    if msg.topic.endswith("/up"):
        type = data.get("object", {}).get("DeviceType", {}).get("value")
        num = data.get("object", {}).get("DeviceNum", {}).get("value")
        status = data.get("object", {}).get("DeviceStatus", {}).get("value")

        if status == "ON":
            print(Fore.GREEN+"⬆️ Dev: "+type+" - Num: "+ num+" - Stat: "+status+Style.RESET_ALL)
        elif status == "OFF":
            print(Fore.RED+"⬆️ Dev: "+type+" - Num: "+ num+" - Stat: "+status+Style.RESET_ALL)

    # ACK
    elif msg.topic.endswith("/ack"):
        print(Fore.GREEN + "✅ ACK ricevuto" + Style.RESET_ALL)

    # TXACK
    elif msg.topic.endswith("/txack"):
        print(Fore.YELLOW + "📡 TXACK gateway" + Style.RESET_ALL)


# Callback disconnessione
def on_disconnect(client, userdata, rc, properties=None):
    print("⚠️ Disconnesso dal broker. Tentativo di riconnessione...")
    while True:
        try:
            client.reconnect()
            print("🔄 Riconnesso al broker MQTT")
            break
        except:
            print("⏳ Riconnessione fallita, nuovo tentativo tra 5s...")
            time.sleep(5)

# Configurazione client MQTT (API v2)
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

# Connessione iniziale
client.connect(BROKER, PORT, 60)

# Loop infinito
client.loop_forever()