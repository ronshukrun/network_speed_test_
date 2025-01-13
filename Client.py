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
    """
    Performs a UDP speed test by sending a request and receiving data packets from the server.
    Records transfer statistics for later analysis.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            # Create and send the request packet to the server
            request_packet = struct.pack('!IBQ', MAGIC_COOKIE, REQUEST_TYPE, file_size)
            udp_sock.sendto(request_packet, (server_ip, udp_port))

            start_time = time.time()
            received_packets = 0
            total_packets = (file_size + BUFFER_SIZE - 1) // BUFFER_SIZE
            udp_sock.settimeout(1)

            while True:
                try:
                    # Receive data from the server (up to BUFFER_SIZE * 2 bytes at a time)
                    data, _ = udp_sock.recvfrom(BUFFER_SIZE * 2)

                    # Process the packet
                    if len(data) >= 21:
                        magic_cookie, msg_type, total_segments, current_segment = struct.unpack('!IBQQ', data)
                        if magic_cookie == MAGIC_COOKIE and msg_type == PAYLOAD_TYPE:
                            received_packets += 1  # Increment received packet count

                            # If all packets have been received, break out of the loop
                            if received_packets == total_segments:
                                break
                    else:
                        # Log a warning for short packets
                        print(f"{Colors.WARNING}⚠️ Received a short packet (length: {len(data)} bytes), skipping...{Colors.ENDC}")

                except socket.timeout:
                    # Stop the download if no packet is received within 1 second
                    print(f"{Colors.WARNING}⏰ No packet received for 1 second, stopping UDP download...{Colors.ENDC}")
                    break

            # Calculate total download time and success rate
            total_time = time.time() - start_time
            success_rate = (received_packets / total_packets) * 100 if total_packets > 0 else 0

            # Save the statistics for this connection
            stats.append((id_connection, total_time, success_rate))

            # Print a summary of the UDP transfer
            print(f"{Colors.OKGREEN}✔ UDP transfer #{id_connection} complete: {received_packets}/{total_packets} packets received ({success_rate:.2f}% success rate) in {total_time:.2f} seconds.{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}❌ Error during UDP download: {e}{Colors.ENDC}")


# Function to initiate the speed test
def initiate_speed_test(server_ip, tcp_port, udp_port, file_size):
    """
    Initiates both TCP and UDP download tests.
    Creates separate threads for each test and records their statistics.
    """
    stats = []  # List to store statistics for TCP and UDP transfers

    # Create threads for TCP and UDP downloads with unique connection IDs
    tcp_thread = threading.Thread(target=tcp_download, args=(server_ip, tcp_port, file_size, 1, stats))
    udp_thread = threading.Thread(target=udp_download, args=(server_ip, udp_port, file_size, 2, stats))

    tcp_thread.start()
    udp_thread.start()

    tcp_thread.join()
    udp_thread.join()

    # Print final summary
    print(f"{Colors.OKCYAN}All transfers completed. Summary:{Colors.ENDC}")
    for conn_id, duration, result in stats:
        if len(result) == 2:
            # For TCP stats
            speed = result[1]
            print(f"{Colors.BOLD}TCP Connection #{conn_id}: Time: {duration:.2f} seconds, Speed: {speed:.2f} bits/second.{Colors.ENDC}")
        else:
            # For UDP stats
            success_rate = result[1]
            print(f"{Colors.BOLD}UDP Connection #{conn_id}: Time: {duration:.2f} seconds, Success Rate: {success_rate:.2f}%.{Colors.ENDC}")


def main():
    """
    Main function that starts the client, receives server offers,
    and initiates the speed test based on user input.
    """
    server_ip, tcp_port, udp_port = listen_for_offers()

    if server_ip is None or tcp_port is None:
        print(f"{Colors.WARNING}No server found. Exiting...{Colors.ENDC}")
        return

    try:
        file_size = int(input(f"{Colors.OKBLUE}Enter file size for download (in bytes): {Colors.ENDC}"))
    except ValueError:
        print(f"{Colors.FAIL}Invalid file size entered. Please enter a valid integer.{Colors.ENDC}")
        return

    print(f"{Colors.OKCYAN}Starting speed test with file size: {file_size} bytes.{Colors.ENDC}")
    initiate_speed_test(server_ip, tcp_port, udp_port, file_size)

if __name__ == "__main__":
    main()
