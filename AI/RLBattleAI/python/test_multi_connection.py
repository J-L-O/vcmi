"""
Test script for multi-connection TCP server.

This script demonstrates the server's ability to handle multiple
concurrent connections by simulating multiple VCMI game clients.
"""

import socket
import threading
import time
import struct


def test_client(client_id: int, host: str = '127.0.0.1', port: int = 65432):
    """
    Simulate a VCMI game client connecting to the server.

    Args:
        client_id: Unique identifier for this client
        host: Server host address
        port: Server port
    """
    try:
        print(f"[Client {client_id}] Connecting to {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print(f"[Client {client_id}] Connected!")

        # Simulate sending some data
        test_message = f"Test message from client {client_id}".encode('utf-8')

        # Send with VCMI protocol (length prefix + data)
        length = len(test_message)
        sock.sendall(struct.pack('<I', length))
        sock.sendall(test_message)
        print(f"[Client {client_id}] Sent message: {test_message.decode('utf-8')}")

        # Keep connection alive for a bit
        time.sleep(2)

        # Close connection
        sock.close()
        print(f"[Client {client_id}] Disconnected")

    except Exception as e:
        print(f"[Client {client_id}] Error: {e}")


def main():
    """Main test function"""
    print("=" * 60)
    print("Multi-Connection TCP Server Test")
    print("=" * 60)
    print("\nThis test will create multiple simultaneous connections")
    print("to demonstrate the server's multi-client capability.\n")

    # Number of clients to simulate
    num_clients = 5

    # Start all clients simultaneously using threads
    print(f"Starting {num_clients} clients...\n")
    threads = []

    for i in range(1, num_clients + 1):
        thread = threading.Thread(target=test_client, args=(i,))
        threads.append(thread)
        thread.start()
        # Small delay between starting clients
        time.sleep(0.1)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
