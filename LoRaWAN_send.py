import sys
n = len(sys.argv)
devType = 'H'
devNum = '1'
devStatus = 'OFF'
if n > 1:
  devType = sys.argv[1]
  if n > 2:
    devNum = sys.argv[2]
    if n > 3:
      devStatus = sys.argv[3]

import grpc
from chirpstack_api import api
import binascii
import datetime

# Configuration.
#rename config.py_TEMPLATE config.py and edit your keys accordingly
import config
server = config.server
dev_eui = config.dev_eui 
api_token = config.api_token

# Connect without using TLS.
def get_grpc_channel():
    return grpc.insecure_channel(server)

# Send data to device with ChirpStack API
def send_data_to_device(dev_eui, payload):
    # Create gRPC channel and stub for DeviceQueue service
    with get_grpc_channel() as channel:
        client = api.DeviceServiceStub(channel)

        # Add authentication header API key
        metadata = [('authorization', 'Bearer ' + api_token)]

        # paylod queing request
        req = api.EnqueueDeviceQueueItemRequest(
            queue_item=api.DeviceQueueItem(
                dev_eui=dev_eui,
                f_port=10,  # LoRaWAN port
                confirmed=True,  # confirmation request
                data=payload.encode(encoding="utf-8")
            )
        )

        # send credential
        resp = client.Enqueue(req, metadata=metadata)
        # resp = client.Enqueue(req, metadata=auth_token)
        print("Sent: ", payload,  "ID: ", {resp.id})

def dispHelp():
   print("Usage:\n Relay = R\n  1:2\n LED = L\n  r,g,R,G,B\n DIG = D\n  1,2,P\n All OFF = A")

if __name__ == "__main__":
    # Send payload
    a = datetime.datetime.now().strftime("%H:%M:%S")
    if devType in ['R','L','D','A']:
      a = "{}:{}:{}".format(devType,devNum,devStatus )
      send_data_to_device(dev_eui, a)
    else:
       dispHelp()