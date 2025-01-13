import socket
import struct
import threading
import time
import os

# Configuration constants
MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4

SERVER_UDP_PORT = int(os.getenv('SERVER_UDP_PORT', 15000))
SERVER_TCP_PORT = int(os.getenv('SERVER_TCP_PORT', 16000))
BUFFER_SIZE = 1024  # Size of each data chunk sent
BROADCAST_INTERVAL = 1  # Seconds between UDP offer broadcasts

# Get the server's local IP address
def get_local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return "0.0.0.0"

# UDP Offer Broadcast Function
def udp_offer_broadcast():
    offer_message = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_TYPE, SERVER_UDP_PORT, SERVER_TCP_PORT)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_sock.bind(("0.0.0.0", 0))
            print("UDP Broadcast started...")
            while True:
                udp_sock.sendto(offer_message, ('<broadcast>', SERVER_UDP_PORT))
                time.sleep(BROADCAST_INTERVAL)
    except Exception as e:
        print(f"Error in UDP broadcast: {e}")

# Function to Start UDP Server
def udp_server():

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            udp_sock.bind(("0.0.0.0", SERVER_UDP_PORT))
            print(f"UDP Server listening on port {SERVER_UDP_PORT}")
            while True:
                data, client_address = udp_sock.recvfrom(BUFFER_SIZE)
                threading.Thread(target=handle_udp_request, args=(data, client_address, udp_sock), daemon=True).start()
    except Exception as e:
        print(f"Error in UDP server: {e}")

# UDP Request Handler
def handle_udp_request(data, client_address, udp_sock):

    try:
        if len(data) != 13 :
            print("Invalid UDP request.")
            return

        magic_cookie, msg_type, file_size = struct.unpack('!IBQ', data)
        if magic_cookie != MAGIC_COOKIE or msg_type != REQUEST_TYPE:
            print("Invalid UDP request header.")
            return

        print(f"UDP request received for {file_size} bytes from {client_address}")
        total_segments = (file_size + BUFFER_SIZE - 1) // BUFFER_SIZE

        for segment_number in range(total_segments):
            payload_header = struct.pack('!IBQQ', MAGIC_COOKIE, PAYLOAD_TYPE, total_segments, segment_number)
            payload = b'B' * min(BUFFER_SIZE, file_size - (segment_number * BUFFER_SIZE))
            udp_sock.sendto(payload_header + payload, client_address)

        print(f"UDP transfer to {client_address} completed.")
    except Exception as e:
        print(f"Error in UDP request handler: {e}")


