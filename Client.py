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
BROADCAST_PORT = 12345


def listen_for_offers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.bind(("", BROADCAST_PORT))
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
            print(
                f"{Colors.OKGREEN}✔ TCP transfer #{id_connection} complete: {bytes_received} bytes received in {total_time:.2f} seconds at {speed:.2f} bits/second.{Colors.ENDC}")

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

                    payload_struct_format = '!IBQQ'
                    payload_protocol_length = struct.calcsize(payload_struct_format)
                    # Process the packet
                    if len(data) >= payload_protocol_length:
                        magic_cookie, msg_type, total_segments, current_segment = struct.unpack(payload_struct_format,
                                                                                                data[
                                                                                                :payload_protocol_length])
                        if magic_cookie == MAGIC_COOKIE and msg_type == PAYLOAD_TYPE:
                            received_packets += 1  # Increment received packet count

                            # If all packets have been received, break out of the loop
                            if received_packets == total_segments:
                                break
                    else:
                        # Log a warning for short packets
                        print(
                            f"{Colors.WARNING}⚠️ Received a short packet (length: {len(data)} bytes), skipping...{Colors.ENDC}")

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
            print(
                f"{Colors.OKGREEN}✔ UDP transfer #{id_connection} complete: {received_packets}/{total_packets} packets received ({success_rate:.2f}% success rate) in {total_time:.2f} seconds.{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}❌ Error during UDP download: {e}{Colors.ENDC}")


# Function to initiate the speed test
def initiate_speed_test(server_ip, tcp_port, udp_port, file_size, tcp_threads, udp_threads):
    """
    Initiates both TCP and UDP download tests.
    Creates separate threads for each test and records their statistics.
    """
    tcp_stats = []  # List to store statistics for TCP transfers
    udp_stats = []  # List to store statistics for UDP transfers

    # Create and start TCP threads
    tcp_threads_list = [
        threading.Thread(target=tcp_download, args=(server_ip, tcp_port, file_size, i + 1, tcp_stats))
        for i in range(tcp_threads)
    ]

    # Create and start UDP threads
    udp_threads_list = [
        threading.Thread(target=udp_download, args=(server_ip, udp_port, file_size, i + 1, udp_stats))
        for i in range(udp_threads)
    ]

    # Start all TCP and UDP threads
    for thread in tcp_threads_list + udp_threads_list:
        thread.start()

    # Wait for all threads to complete
    for thread in tcp_threads_list + udp_threads_list:
        thread.join()

    # Print final summary
    print(f"{Colors.OKCYAN}All transfers completed. Summary:{Colors.ENDC}")
    for conn_id, duration, speed in tcp_stats:
        print(
            f"{Colors.BOLD}TCP Connection #{conn_id}: Time: {duration:.2f} seconds, Speed: {speed:.2f} bits/second.{Colors.ENDC}")
    for conn_id, duration, success_rate in udp_stats:
        print(
            f"{Colors.BOLD}UDP Connection #{conn_id}: Time: {duration:.2f} seconds, Success Rate: {success_rate:.2f}%.{Colors.ENDC}")


def main():
    """
    Main function that starts the client, receives server offers,
    and initiates the speed test based on user input.
    """
    print(f"{Colors.HEADER}Welcome to the Speed Test Client!{Colors.ENDC}")

    # Get valid inputs for file size, number of UDP threads, and TCP threads
    file_size = get_valid_input("Enter file size for download (in bytes): ")
    udp_threads = get_valid_input("Enter the number of UDP threads: ")
    tcp_threads = get_valid_input("Enter the number of TCP threads: ")

    # Receive the server offer
    server_ip, udp_port, tcp_port = listen_for_offers()

    if server_ip is None or tcp_port is None:
        print(f"{Colors.WARNING}No server found. Exiting...{Colors.ENDC}")
        return

    print(f"{Colors.OKCYAN}Starting speed test with file size: {file_size} bytes.{Colors.ENDC}")
    initiate_speed_test(server_ip, tcp_port, udp_port, file_size, udp_threads, tcp_threads)


def get_valid_input(prompt):
    while True:
        try:
            num = int(input(f"{Colors.OKBLUE}{prompt}{Colors.ENDC}"))  # Request user input
            if num > 0:
                print(f"{Colors.OKGREEN}✔️ Valid input: {num}{Colors.ENDC}")
                return num  # Return the number if it is valid (positive integer)
            else:
                print(f"{Colors.WARNING}⚠️ The number must be greater than 0.{Colors.ENDC}")
        except ValueError:
            print(f"{Colors.FAIL}❌ Invalid input! Please enter a valid integer.{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}❌ Unexpected error: {e}{Colors.ENDC}")


if __name__ == "__main__":
    main()
