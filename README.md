# Server-Client Network Speed Test

This project consists of a server and client designed to measure and report network speed using both TCP and UDP protocols. The server broadcasts its availability via UDP and accepts requests over both UDP and TCP to test the download speed. The client listens for the server's offer and performs file download tests using both UDP and TCP, reporting transfer times and speeds.

## Server:
The server listens for incoming connections on specified ports and handles UDP and TCP download requests. It broadcasts its availability over UDP, and the client can request file data over both protocols.

### Server Features:
* Broadcasts server availability using UDP every second
* Listens for UDP requests and sends file data in segments
* Accepts TCP connections and sends file data in chunks
* Provides a progress report on data transfer completion

### Server Ports:
* UDP Broadcast Port: 12345
* UDP Data Port: 15000
* TCP Data Port: 16000

## Client:

The client listens for UDP offers from the server, retrieves server information, and performs file download tests over both UDP and TCP.

### Client Features:
* Listens for UDP broadcasts from the server
* Connects to the server using UDP and TCP to download data
* Reports download times and network speeds in bits per second

### Client Configuration:
* UDP Timeout: 20 seconds
* Buffer Size: 1024 bytes
* Default UDP Broadcast Port: 12345

### Usage Instructions:
1. Run the server:
* Launch the server application first. The server will start broadcasting its availability over UDP and listen for incoming requests.
* The server will listen on ports 15000 (UDP) and 16000 (TCP).

2. Run the client:
* Launch the client application after starting the server. The client will listen for UDP broadcasts from the server.
* Once the server's offer is detected, the client will perform download tests using both UDP and TCP and report the results.

### Dependencies:
* Python 3.x
* No additional libraries required (Standard Python libraries used: socket, struct, threading, time)

### Example Output:

1. Server (Console):
Server started, listening on IP address 192.168.1.100
UDP Broadcast started...
UDP Server listening on port 15000
TCP Server listening on port 16000

2. Client (Console):
Client started, listening for server offers...
Offer received from 192.168.1.100: UDP port 15000, TCP port 16000
✔ TCP transfer #1 complete: 1024 bytes received in 0.10 seconds at 81920.00 bits/second.
✔ UDP transfer #1 complete: 1024 bytes received in 0.08 seconds at 102400.00 bits/second.

### Notes:
* The server's UDP broadcast will occur every second.
* The client will automatically connect to the server once it detects the broadcast.
* You can modify the buffer size and timeout configurations in the source code for testing different network conditions.