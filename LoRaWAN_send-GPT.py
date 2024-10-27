import grpc
import chirpstack_api.api.device_pb2 as device_pb2
import chirpstack_api.api.deviceQueue_pb2 as deviceQueue_pb2
import chirpstack_api.api.deviceQueue_pb2_grpc as deviceQueue_pb2_grpc
import chirpstack_api.common.common_pb2 as common_pb2
import binascii

# Configuration.
#rename config.py_TEMPLATE config.py and edit your keys accordingly
import config
CHIRPSTACK_SERVER = config.server
DEV_EUI = config.dev_eui 
API_KEY = config.api_token

# Payload da inviare (convertito in byte)
payload_hex = "01020304"  # Esempio di payload in formato esadecimale
payload_bytes = binascii.unhexlify(payload_hex)

# Crea il canale di comunicazione gRPC
def get_grpc_channel():
    return grpc.insecure_channel(CHIRPSTACK_SERVER)

# Funzione per inviare il messaggio alla coda del dispositivo
def send_data_to_device(dev_eui, payload):
    # Crea il canale e il client gRPC
    with get_grpc_channel() as channel:
        # Aggiungi l'header di autenticazione con l'API key
        metadata = [('authorization', 'Bearer ' + API_KEY)]

        # Crea lo stub del servizio DeviceQueue
        client = deviceQueue_pb2_grpc.DeviceQueueServiceStub(channel)
        
        # Crea la richiesta per inserire il payload nella coda del dispositivo
        req = deviceQueue_pb2.EnqueueDeviceQueueItemRequest(
            device_queue_item=deviceQueue_pb2.DeviceQueueItem(
                dev_eui=dev_eui,
                f_port=10,  # Imposta la porta LoRaWAN (può variare a seconda della tua applicazione)
                confirmed=True,  # Se vuoi una conferma del messaggio
                data=payload
            )
        )

        # Invia la richiesta con le credenziali API
        resp = client.Enqueue(req, metadata=metadata)
        print(f"Messaggio inviato, ID coda: {resp.id}")

if __name__ == "__main__":
    # Esegue l'invio del payload
    send_data_to_device(DEV_EUI, payload_bytes)