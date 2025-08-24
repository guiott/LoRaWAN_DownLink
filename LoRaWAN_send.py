#!/usr/bin/env python3
import grpc
import time
import datetime
import json
import threading
import paho.mqtt.client as mqtt
from chirpstack_api import api
from colorama import Fore, Style, init

import argparse

# --- Argomenti da linea di comando ---
parser = argparse.ArgumentParser(description="LoRaWAN Control Script")
parser.add_argument("-d", "--debug", action="store_true", help="Abilita output di debug")
parser.add_argument("-s", "--single", type=str, help='Invia un singolo comando, es: "R:1:ON"')
args = parser.parse_args()
DEBUG = args.debug
SINGLE_CMD = args.single

init(autoreset=True)

import logging

# Configuro il logger: ERROR e superiori finiscono su file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('lorawan_errors.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# --- CONFIG ---
import credentials
import config
server = credentials.server
dev_eui = credentials.dev_eui
api_token = credentials.api_token
BROKER = credentials.mqtt_broker
PORT = 1883
TOPIC = f"application/+/device/{dev_eui}/event/#"
TIMEOUT = getattr(config, "timeout", 15)  # secondi di attesa uplink
DELAY = getattr(config, "delay", 5)      # secondi tra comandi
devices = config.DEVICES
# ----------------

# Variabili di sincronizzazione
uplink_received = threading.Event()

def timeNow():
    return datetime.datetime.now().strftime("%H:%M:%S")

# --- gRPC ---
def get_grpc_channel():
    return grpc.insecure_channel(server)

def send_data_to_device(client, dev_eui, payload, metadata):
    try:
        req = api.EnqueueDeviceQueueItemRequest(
            queue_item=api.DeviceQueueItem(
                dev_eui=dev_eui,
                f_port=10,
                confirmed=True,
                data=payload.encode("utf-8")
            )
        )
        resp = client.Enqueue(req, metadata=metadata)
        if DEBUG:
            print(Fore.CYAN+"["+timeNow()+"] ===================="+Style.RESET_ALL)
            print(f"[{timeNow()}] 📡 {Fore.YELLOW}Sent: {Fore.GREEN}{payload}{Style.RESET_ALL}, QueueItemID: {resp.id}")
        return True
    except grpc.RpcError as e:
        logger.error(f"Errore inviando {payload}: {e.code()} - {e.details()}")
        if DEBUG:
            print(f"[{timeNow()}] ❌ Errore inviando {Fore.RED}{payload}{Style.RESET_ALL}: {e.code()} - {e.details()}")
        return False

# --- MQTT ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(TOPIC)
        if DEBUG:
            print(f"[{timeNow()}] 📡 Sottoscritto a {TOPIC}")
    else:
        if DEBUG:
            print("❌ Connessione MQTT fallita:", rc)

def on_message(client, userdata, msg):
    global uplink_received
    payload = msg.payload.decode("utf-8")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return

    # ACK → solo log informativo
    if msg.topic.endswith("/ack"):
        if DEBUG:
            print(Fore.YELLOW + "["+timeNow()+"]" + " ✅ ACK ricevuto" + Style.RESET_ALL)

    # TXACK → log informativo
    elif msg.topic.endswith("/txack"):
        if DEBUG:
            print(Fore.YELLOW + "["+timeNow()+"]" + " 📡 TXACK gateway" + Style.RESET_ALL)

    # UPLINK → consideriamo il comando eseguito
    elif msg.topic.endswith("/up"):
        status = data.get("object", {}).get("DeviceStatus", {}).get("value")
        type_ = data.get("object", {}).get("DeviceType", {}).get("value")
        num = data.get("object", {}).get("DeviceNum", {}).get("value")

        # Verifica se lo stato corrisponde al comando inviato
        expected = userdata.get("expected_status")
        if status == expected:
            color = Fore.GREEN if status == "ON" else Fore.RED
            if DEBUG:
                print(color + f"[{timeNow()}] ⬆️  Comando eseguito: {type_}-{num} -> {status}" + Style.RESET_ALL)
            uplink_received.set()

def on_disconnect(client, userdata, rc, properties=None):
    if DEBUG:
        print("⚠️ Disconnesso dal broker. Tentativo di riconnessione...")
    while True:
        try:
            client.reconnect()
            if DEBUG:
                print("🔄 Riconnesso al broker MQTT")
            break
        except:
            if DEBUG:
                print("⏳ Riconnessione fallita, nuovo tentativo tra 5s...")
            time.sleep(5)

# --- Main ---
def main():
    # --- MQTT setup ---
    mqtt_client = mqtt.Client(userdata={"expected_status": None})
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.connect(BROKER, PORT, 60)
    mqtt_thread = threading.Thread(target=mqtt_client.loop_forever, daemon=True)
    mqtt_thread.start()

    # --- gRPC setup ---
    with get_grpc_channel() as channel:
        device_client = api.DeviceServiceStub(channel)
        metadata = [('authorization', 'Bearer ' + api_token)]

        # Costruisci la lista dei payload da inviare
        if SINGLE_CMD:
            payloads = [SINGLE_CMD]
        else:
            payloads = [f"{devType}:{devNum}:{state}" 
                        for devType, devNum in devices 
                        for state in ("ON", "OFF")]

        # Ciclo su tutti i payload
        for payload in payloads:
            success = False
            expected_state = payload.split(":")[-1]
            mqtt_client.user_data_set({"expected_status": expected_state})

            for attempt in range(config.retries):
                uplink_received.clear()

                sent = send_data_to_device(device_client, dev_eui, payload, metadata)
                if not sent:
                    logger.error(f"Errore invio comando, passo al prossimo")  
                    if DEBUG:
                        print(f"[{timeNow()}] ⚠️ Errore invio comando, passo al prossimo")                        
                    break

                if DEBUG:
                    print(f"[{timeNow()}] ⏳ Attendo uplink conferma (timeout {TIMEOUT}s)... [Tentativo {attempt+1}/{config.retries}]")

                if uplink_received.wait(timeout=TIMEOUT):
                    if DEBUG:
                        print(f"[{timeNow()}] 🎉 Comando confermato dal device: {payload}")
                    success = True
                    break
                else:
                    logger.warning(f"Nessun uplink confermato per {payload} tentativo {attempt+1}")  
                    if DEBUG:
                        print(Fore.MAGENTA+"["+timeNow()+"] ⚠️  Nessun uplink confermato per "+payload+" tentativo "+str(attempt+1)+Style.RESET_ALL)
                    if attempt < config.retries - 1:
                        if DEBUG:
                            print(f"[{timeNow()}] 🔄 Riprovo tra {config.retry_delay}s...")
                        time.sleep(config.retry_delay)

            if not success:
                logger.error(f"Comando fallito dopo {config.retries} tentativi: {payload}")
                if DEBUG:
                    print(f"[{timeNow()}] ❌ Comando fallito dopo {config.retries} tentativi: {payload}")

            # pausa obbligatoria tra comandi per non saturare la rete
            time.sleep(DELAY)

    if DEBUG:
        print("=========================================Completato ✅")
if __name__ == "__main__":
    main()