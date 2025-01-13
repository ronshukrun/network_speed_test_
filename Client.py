import socket
import struct
import threading
import time
import os

# Constants for the packet formats and magic cookie
MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
BUFFER_SIZE = 1024
UDP_TIMEOUT = 5  # Seconds to wait for offers

def listen_for_offers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.bind(("0.0.0.0", 0))  # Bind to any port
        udp_sock.settimeout(UDP_TIMEOUT)

        print("Client started, listening for server offers...")
        try:
            while True:
                data, server_address = udp_sock.recvfrom(BUFFER_SIZE)
                if len(data) >= 9:
                    magic_cookie, msg_type = struct.unpack('!IB', data[:5])
                    if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_TYPE:
                        udp_port, tcp_port = struct.unpack('!HH', data[5:9])
                        print(f"Offer received from {server_address[0]}: UDP port {udp_port}, TCP port {tcp_port}")
                        return server_address[0], tcp_port
        except socket.timeout:
            print("No server offer received within timeout period.")
            return None, None

def tcp_download(server_ip, tcp_port, file_size):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:
            tcp_sock.connect((server_ip, tcp_port))
            tcp_sock.sendall(f"{file_size}\n".encode())
            start_time = time.time()

            bytes_received = 0
            while bytes_received < file_size:
                data = tcp_sock.recv(BUFFER_SIZE)
                if not data:
                    break
                bytes_received += len(data)

            total_time = time.time() - start_time
            print(f"TCP download complete: {bytes_received} bytes in {total_time:.2f} seconds")

    except Exception as e:
        print(f"Error during TCP download: {e}")
