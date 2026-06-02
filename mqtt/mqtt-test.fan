include("mqtt-utils.fan")

# MQTT Binary Protocol - use r"."+  := for all packets
<CONNECT_DATA>   ::= b"\x10\x0C\x00\x04MQTT\x04\x02\x00\x3C\x00\x08test_cli"
<CONNACK_DATA>   ::= b"\x20\x02\x00\x00"
<SUBSCRIBE_DATA> ::= b"\x82\x0E\x00\x01\x00\x09test/topic\x00"
<SUBACK_DATA>    ::= b"\x90\x03\x00\x01" + (b"\x00" | b"\x01" | b"\x02" | b"\x63")
<PUBLISH_DATA>   ::= b"\x30\x15\x00\x09test/topicHello MQTT"

# --- 2. High-Level Interaction Logic ---
<start> ::= <mqtt_session>

<mqtt_session> ::= <connect_handshake><interaction_body>

<connect_handshake> ::= <Client:Broker:CONNECT_DATA> <Broker:Client:CONNACK_DATA>

<interaction_body> ::= <sub_exchange> <publish_sequence>

<sub_exchange> ::= <Client:Broker:SUBSCRIBE_DATA> <Broker:Client:SUBACK_DATA>

<publish_sequence> ::= <Client:Broker:PUBLISH_DATA>




