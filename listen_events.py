#!/usr/bin/env python3
import grpc
import datetime
from chirpstack_api import api
from colorama import Fore, Style, init
import credentials

init(autoreset=True)

# Config
server = credentials.server          # es: "localhost:8080"
api_token = credentials.api_token
dev_eui = credentials.dev_eui        # il device che vuoi monitorare

def get_grpc_channel():
    return grpc.insecure_channel(server)

def listen_events():
    with get_grpc_channel() as channel:
        client = api.ApplicationServiceStub(channel)
        metadata = [('authorization', 'Bearer ' + api_token)]

        # Stream eventi del device
        req = api.StreamDeviceEventsRequest(dev_eui=dev_eui)
        for event in client.StreamDeviceEvents(req, metadata=metadata):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if event.HasField("ack"):
                print(f"[{now}] {Fore.GREEN}✅ ACK ricevuto:{Style.RESET_ALL} {event.ack}")
            elif event.HasField("txack"):
                print(f"[{now}] {Fore.YELLOW}📡 TXACK dal gateway:{Style.RESET_ALL} {event.txack}")
            else:
                print(f"[{now}] {event}")

if __name__ == "__main__":
    print(f"🎧 Ascolto eventi per device {Fore.CYAN}{dev_eui}{Style.RESET_ALL}...")
    listen_events()