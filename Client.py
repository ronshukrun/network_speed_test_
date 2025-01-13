# import socket
# import struct
# import threading
# import time
# import os
#
# # Constants for the packet formats and magic cookie
# MAGIC_COOKIE = 0xabcddcba
# OFFER_TYPE = 0x2
# REQUEST_TYPE = 0x3
# PAYLOAD_TYPE = 0x4
# BUFFER_SIZE = 1024
# UDP_TIMEOUT = 5  # Seconds to wait for offers
#
# def listen_for_offers():
#     with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
#         udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
#         udp_sock.bind(("0.0.0.0", 0))  # Bind to any port
#         udp_sock.settimeout(UDP_TIMEOUT)
#
#         print("Client started, listening for server offers...")
#         try:
#             while True:
#                 data, server_address = udp_sock.recvfrom(BUFFER_SIZE)
#                 if len(data) >= 9:
#                     magic_cookie, msg_type = struct.unpack('!IB', data[:5])
#                     if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_TYPE:
#                         udp_port, tcp_port = struct.unpack('!HH', data[5:9])
#                         print(f"Offer received from {server_address[0]}: UDP port {udp_port}, TCP port {tcp_port}")
#                         return server_address[0], tcp_port
#         except socket.timeout:
#             print("No server offer received within timeout period.")
#             return None, None
#
# def tcp_download(server_ip, tcp_port, file_size):
#     try:
#         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:
#             tcp_sock.connect((server_ip, tcp_port))
#             tcp_sock.sendall(f"{file_size}\n".encode())
#             start_time = time.time()
#
#             bytes_received = 0
#             while bytes_received < file_size:
#                 data = tcp_sock.recv(BUFFER_SIZE)
#                 if not data:
#                     break
#                 bytes_received += len(data)
#
#             total_time = time.time() - start_time
#             print(f"TCP download complete: {bytes_received} bytes in {total_time:.2f} seconds")
#
#     except Exception as e:
#         print(f"Error during TCP download: {e}")
#
#
#
#
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'


import os
import socket
import struct
import threading
import time

# Constants for the packet formats and magic cookie
MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4
BUFFER_SIZE = 1024
UDP_TIMEOUT = 20
SERVER_UDP_PORT = int(os.getenv('SERVER_UDP_PORT', 15000))


def listen_for_offers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.bind(("0.0.0.0", SERVER_UDP_PORT))
        udp_sock.settimeout(UDP_TIMEOUT)

        print(f"{Colors.OKCYAN}Client started, listening for server offers...{Colors.ENDC}")
        try:
            while True:
                try:
                    data, server_address = udp_sock.recvfrom(BUFFER_SIZE)
                    if len(data) >= 9:
                        # Attempt to unpack the data
                        magic_cookie, msg_type, udp_port, tcp_port = struct.unpack('!IBHH', data)
                        # msg_type (ip,port)
                        if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_TYPE:
                            print(
                                f"{Colors.OKGREEN}✔️ Offer received from {server_address[0]}: UDP port {udp_port}, TCP port {tcp_port}{Colors.ENDC}")
                            return server_address[0], udp_port, tcp_port
                        else:
                            print(
                                f"{Colors.WARNING}⚠️ Received packet from {server_address[0]} but it is not a valid offer.{Colors.ENDC}")

                # - struct.error: occurs if the data size or format doesn't match the unpack format.
                # - Exception: handles any general errors (e.g., network errors or socket issues).
                except struct.error:
                    print(f"{Colors.FAIL}❌ Invalid packet structure received, ignoring...{Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.FAIL}❌ Unexpected error while listening for offers: {e}{Colors.ENDC}")

        except socket.timeout:
            print(f"{Colors.WARNING}⏰ No server offer received within timeout period.{Colors.ENDC}")
            return None, None


# Perform TCP download
def tcp_download(server_ip, tcp_port, file_size, id_connection, stats):
    """
    Performs a file download over TCP and records the transfer statistics.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:
            tcp_sock.connect((server_ip, tcp_port))  # Waiting until the connection is confirmed (Blocking Call)
            # sendall() - accepts data in binary format only.
            # encode()- converts the string to Bytes data
            tcp_sock.sendall(f"{file_size}\n".encode())  # Send file size as a string

            start_time = time.time()

            bytes_received = 0
            while bytes_received < file_size:
                data = tcp_sock.recv(BUFFER_SIZE)
                if not data:
                    break
                bytes_received += len(data)

            total_time = time.time() - start_time  # Calculate total download time
            speed = (bytes_received * 8) / total_time if total_time > 0 else 0  # speed =  bits/second

            stats.append((id_connection, total_time, speed))

            # Print formatted output with colors
            print(f"{Colors.OKGREEN}✔ TCP transfer #{id_connection} complete: {bytes_received} bytes received in {total_time:.2f} seconds at {speed:.2f} bits/second.{Colors.ENDC}")

    except socket.error as e:
        print(f"{Colors.BOLD}{Colors.FAIL}❌ TCP connection error: {e}{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.BOLD}{Colors.FAIL}❌ Error during TCP download: {e}{Colors.ENDC}")


# Function to request and receive UDP data
def udp_download(server_ip, udp_port, file_size, id_connection, stats):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            request_packet = struct.pack('!IBQ', MAGIC_COOKIE, REQUEST_TYPE, file_size)
            udp_sock.sendto(request_packet, (server_ip, udp_port))

            start_time = time.time()
            received_packets = 0
            total_packets = (file_size + BUFFER_SIZE - 1) // BUFFER_SIZE
            udp_sock.settimeout(1)

            while True:
                try:
                    data, _ = udp_sock.recvfrom(2048)
                    if len(data) < 21:
                        continue
                    magic_cookie, msg_type, total_segments, current_segment = struct.unpack('!IBQQ', data[:21])
                    if magic_cookie == MAGIC_COOKIE and msg_type == PAYLOAD_TYPE:
                        received_packets += 1
                        if received_packets == total_segments:
                            break
                except socket.timeout:
                    break

            total_time = time.time() - start_time
            success_rate = (received_packets / total_packets) * 100 if total_packets > 0 else 0
            print(
                f"UDP download complete: {received_packets}/{total_packets} packets received ({success_rate:.2f}% success rate) in {total_time:.2f} seconds")

    except Exception as e:
        print(f"Error during UDP download: {e}")

