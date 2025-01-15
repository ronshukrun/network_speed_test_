import socket
import struct
import threading
import time
import os


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'


# Configuration constants
MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4

BROADCAST_PORT = 12345
SERVER_UDP_PORT = 15000
SERVER_TCP_PORT = 16000
BUFFER_SIZE = 1024  # Size of each data chunk sent
BROADCAST_INTERVAL = 1  # Seconds between UDP offer broadcasts


# Get the server's local IP address
def get_local_ip():
    """
    Retrieves the local IP address of the server by establishing a UDP connection
    to an external server and using the local address.

    Returns:
        str: Local IP address of the server.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:  # create UDP socket and use IPv4 protocol
        try:
            s.connect(("8.8.8.8", 80))  # try to connect to DNS server with port 80
            return s.getsockname()[0]
        except Exception:
            return "0.0.0.0"


# UDP offer Broadcast Function
# The function's role is to broadcast a UDP offer message every second to announce the existence of the server and
# announce the ports on which it is listening.
def udp_offer_broadcast():
    """
    Broadcasts a UDP offer message every second to announce the server's availability
    and the ports it is listening on. The message is sent in a binary format that includes
    the magic cookie, message type, and ports.

    This function runs indefinitely in a separate thread and is responsible for sending
    broadcast offers to all devices on the network at regular intervals.
    """
    offer_message = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_TYPE, SERVER_UDP_PORT,
                                SERVER_TCP_PORT)  # The UDP message is packaged using struct.pack. It packages data into binary format.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,
                                1)  # The socket broadcasts the message to all devices on the network
            # # udp_sock.bind(("0.0.0.0", 0))
            # udp_sock.bind(("0.0.0.0", BROADCAST_PORT))
            print(Colors.OKBLUE + "UDP Broadcast started..."+ Colors.ENDC)
            while True:
                udp_sock.sendto(offer_message, ('<broadcast>',
                                                BROADCAST_PORT))  # The socket sends the offer message (offer_message) to anyone listening on the UDP port.
                time.sleep(BROADCAST_INTERVAL)  # The program waits a period of time before sending another message.
    except Exception as e:
        print(Colors.FAIL + f"Error in UDP broadcast: {e}" + Colors.ENDC)


# Function to Start UDP Server
def udp_server():
    """
    Starts the UDP server, binding it to the specified UDP port. The server listens for
    incoming requests from clients and processes them in separate threads.

    This function runs indefinitely, accepting UDP packets, and delegating the processing
    to the `handle_udp_request` function.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            udp_sock.bind(("0.0.0.0", SERVER_UDP_PORT))
            print(Colors.OKBLUE + f"UDP Server listening on port {SERVER_UDP_PORT}" + Colors.ENDC)
            while True:
                data, client_address = udp_sock.recvfrom(
                    BUFFER_SIZE)  # The data that the client sent is stored in data and the address of the client that sent the data is stored in client_address.
                threading.Thread(target=handle_udp_request, args=(data, client_address), daemon=True).start()
    except Exception as e:
        print(Colors.FAIL + f"Error in UDP server: {e}" + Colors.ENDC)


# UDP Request Handler
def handle_udp_request(data, client_address):
    """
    Handles incoming UDP requests, validates the data, and sends file segments to the client.

    The function processes the request by checking the magic cookie and message type,
    then sends the requested file in segments, each with a header containing information
    such as the total number of segments and the current segment number.

    Args:
        data (bytes): The data received in the UDP request.
        client_address (tuple): The address of the client sending the request.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            if len(data) != 13:  # Magic cookie - 4 B, Message type - 1 B and File size - 8 B
                print(Colors.FAIL + "Invalid UDP request." + Colors.ENDC)
                return

            magic_cookie, msg_type, file_size = struct.unpack('!IBQ',
                                                              data)  # Information return back to parts Magic cookie, Message type and File size.
            if magic_cookie != MAGIC_COOKIE or msg_type != REQUEST_TYPE:
                print(Colors.FAIL + "Invalid UDP request header." + Colors.ENDC)
                return

            print(Colors.OKCYAN + f"UDP request received for {file_size} bytes from {client_address}" + Colors.ENDC)
            total_segments = (file_size + BUFFER_SIZE - 1) // BUFFER_SIZE  # Calculating the number of segments required to send the file

            for segment_number in range(total_segments):
                payload_header = struct.pack('!IBQQ', MAGIC_COOKIE, PAYLOAD_TYPE, total_segments,
                                             segment_number)  # Packing data into a binary structure (to send it over the network)
                # Create the payload for the current segment, ensuring it doesn't exceed the remaining file size
                # The payload consists of 'B' characters, and its length is determined by the smallest of BUFFER_SIZE or the remaining file size.
                payload = b'B' * min(BUFFER_SIZE, file_size - (segment_number * BUFFER_SIZE))
                udp_sock.sendto(payload_header + payload,
                                client_address)  # The information is sent (the header + payload) to the client address via UDP.

            print(Colors.OKGREEN + f"UDP transfer to {client_address} completed." + Colors.ENDC)

    except Exception as e:
        print(Colors.FAIL + f"Error in UDP request handler: {e}" + Colors.ENDC)


## TCP
# Function to Start TCP Server
def tcp_server():
    """
    Starts the TCP server, listening for incoming TCP connections on the specified TCP port.

    The server accepts new client connections, and for each connection, it creates a
    new thread to handle the client request. The client request involves receiving a
    file size and sending the corresponding number of bytes.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:  # create TCP socket and use IPv4 protocol
            tcp_sock.bind(("0.0.0.0", SERVER_TCP_PORT))
            tcp_sock.listen()  # Server wait to TCP request
            print(Colors.OKBLUE + f"TCP Server listening on port {SERVER_TCP_PORT}" + Colors.ENDC)

            while True:
                client_socket, client_address = tcp_sock.accept()  # Accepts a new TCP connection, returns a client socket and client address
                print(Colors.WARNING + f"New TCP connection from {client_address}" + Colors.ENDC)
                threading.Thread(target=handle_tcp_client, args=(client_socket,), daemon=True).start()
    except Exception as e:
        print(Colors.FAIL + f"Error in TCP server: {e}" + Colors.ENDC)


# TCP Client Handler Function
def handle_tcp_client(client_socket):
    """
    Handles incoming TCP client connections, receives the requested file size from
    the client, and sends the file in chunks of a specified buffer size.

    The function ensures that the file is sent in full, and each chunk is sent until
    the complete file size is reached.

    Args:
        client_socket (socket.socket): The socket object representing the client connection.
    """
    try:
        data = client_socket.recv(
            BUFFER_SIZE).decode().strip()  # Receive data from the client, decode it to a string, and strip any whitespace or newline characters.
        if not data.isdigit():
            print(Colors.FAIL + "Invalid TCP request received." + Colors.ENDC)
            return

        file_size = int(data)
        print(Colors.OKCYAN + f"TCP request received for {file_size} bytes." + Colors.ENDC)

        # if data is not number:
        # try:
        #     file_size = int(data)
        # except ValueError:
        #     print("Invalid input received, expected a number.")
        #     client_socket.close()
        #     return

        bytes_sent = 0
        while bytes_sent < file_size:  # Check that the entire file has been sent to the client in full.
            chunk = b'A' * min(BUFFER_SIZE, file_size - bytes_sent)
            client_socket.sendall(chunk)
            bytes_sent += len(chunk)

        print(Colors.OKGREEN + f"TCP transfer completed. {file_size} bytes sent." + Colors.ENDC)
    except Exception as e:
        print(Colors.FAIL + f"Error handling TCP connection: {e}" + Colors.ENDC)
    finally:
        client_socket.close()


# Main function to start both servers
def main():
    """
    Main entry point for the server application.
    """
    print(Colors.HEADER + f"Server started, listening on IP address {get_local_ip()}" + Colors.ENDC)
    threading.Thread(target=udp_offer_broadcast, daemon=True).start()
    threading.Thread(target=udp_server, daemon=True).start()
    tcp_server()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(Colors.WARNING + "\nServer shutting down..."+ Colors.ENDC)
    except Exception as e:
        print(Colors.FAIL + f"Unexpected server error: {e}" + Colors.ENDC)
    finally:
        print(Colors.OKGREEN + "Server terminated." + Colors.ENDC)
