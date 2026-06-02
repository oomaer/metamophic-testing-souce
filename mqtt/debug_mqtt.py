#!/usr/bin/env python3
"""Debug MQTT broker responses"""
import socket

# Connect first
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2)
sock.connect(("localhost", 1883))

# CONNECT
connect = b"\x10\x0c\x00\x04MQTT\x04\x02\x00<\x00\x08test_cli"
print(f"Sending CONNECT: {connect.hex(' ')}")
sock.send(connect)
response = sock.recv(1024)
print(f"CONNACK response: {response.hex(' ')}\n")

# SUBSCRIBE
subscribe = b"\x82\x0e\x00\x01\x00\x09test/topic\x00"
print(f"Sending SUBSCRIBE: {subscribe.hex(' ')}")
sock.send(subscribe)
response = sock.recv(1024)
print(f"SUBACK response: {response.hex(' ')}")

sock.close()