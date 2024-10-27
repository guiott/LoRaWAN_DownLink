Python code example about downlink message sending to a class C LoRaWAN node.
It requires chirpsatck-api.
Installing the latest version of chirpstack-api for Python (pip install chirpstack-api) also installs its dependencies, in particular grpcio. If you are working on a machine with a Linux kernel 5.15.xx, the latest version is not compatible with the compiler. To install chirpstack-api you must first install a previous version of grpcio, for example: 
pip install grpcio==1.58.0
and then a version of chirpstack-api compatible with the dependencies version: 
pip install chirpstack-api==4.3.0

Remeber to enable all LoRaWAN Class C features on both gateway (LoRaWAN Network Settings) 

![image](https://github.com/user-attachments/assets/f5a21bea-48c9-4baa-80e5-9011b4b2a242)

and network server (Device Support Class C)

![image](https://github.com/user-attachments/assets/d592f8fc-5c72-47dc-adec-ebda24dfa0aa)

after node join it must uplink a message to gateway before start receiving downlinks continuosly.



