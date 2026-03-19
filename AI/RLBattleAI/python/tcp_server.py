"""
TCP Server for VCMI Battle AI

This module implements a TCP server that can receive and process
VCMI network packs from the C++ game engine.
"""

import socket
import threading
import struct
import logging
from typing import Optional, Callable, List, Dict
from serializer import pack as print_pack
from vcmi_types import deserialize_pack, serialize_pack, CPack, BattleStart

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VCMIProtocolHandler:
    """
    Handles VCMI protocol-specific operations.
    VCMI sends data in packets where each packet has a length prefix.
    """

    @staticmethod
    def receive_message(sock: socket.socket) -> Optional[bytes]:
        """
        Receive a complete VCMI message from socket.

        VCMI protocol:
        1. First 4 bytes: message length (uint32_t, little-endian)
        2. Remaining bytes: actual message data

        Args:
            sock: Socket to receive from

        Returns:
            The message data, or None if connection closed
        """
        try:
            # Read message length (4 bytes)
            length_data = sock.recv(4, socket.MSG_WAITALL)
            if len(length_data) == 0:
                logger.info("Connection closed by peer")
                return None

            message_length = struct.unpack('<I', length_data)[0]
            logger.info(f"Expecting message of length: {message_length} bytes")
            # Read the actual message data
            data = bytearray()
            remaining = message_length

            while remaining > 0:
                chunk = sock.recv(min(remaining, 4096), socket.MSG_WAITALL)
                if len(chunk) == 0:
                    logger.warning("Connection closed while receiving message")
                    return None

                data.extend(chunk)
                remaining -= len(chunk)

            logger.info(f"Received {len(data)} bytes of data")

            return bytes(data)

        except socket.timeout:
            logger.warning("Socket timeout while receiving message")
            return None
        except Exception as e:
            logger.error(f"Error receiving message: {e}", exc_info=True)
            return None

    @staticmethod
    def send_message(sock: socket.socket, data: bytes) -> bool:
        """
        Send a VCMI message to socket.

        Args:
            sock: Socket to send to
            data: Message data to send

        Returns:
            True if successful, False otherwise
        """
        try:
            # Send length prefix (4 bytes, little-endian)
            length = len(data)
            sock.sendall(struct.pack('<I', length))

            # Send actual data
            sock.sendall(data)

            logger.info(f"Sent message of length: {length} bytes")
            return True

        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
            return False


class BattleAIHandler:
    """
    Base handler for battle AI events.
    Override methods to handle specific battle events.
    """

    def handle_battle_start(self, battle_id: int, battle_info: BattleStart, client_id: str = "unknown") -> None:
        """Handle battle start event"""
        logger.info(f"[{client_id}] Battle started with ID: {battle_id}")
        if battle_info.info:
            logger.info(f"[{client_id}]   Round: {battle_info.info.round}")
            logger.info(f"[{client_id}]   Stacks: {len(battle_info.info.stacks)}")
            logger.info(f"[{client_id}]   Battlefield: {battle_info.info.battlefield_type}")

    def handle_battle_next_round(self, battle_id: int, client_id: str = "unknown") -> None:
        """Handle next round event"""
        logger.info(f"[{client_id}] Battle next round: {battle_id}")

    def handle_set_active_stack(self, battle_id: int, stack_id: int, client_id: str = "unknown") -> None:
        """Handle active stack change event"""
        logger.info(f"[{client_id}] Active stack changed - Battle: {battle_id}, Stack: {stack_id}")

    def handle_unknown_pack(self, pack: CPack, client_id: str = "unknown") -> None:
        """Handle unknown pack types"""
        logger.warning(f"[{client_id}] Received unknown pack type: {pack.__class__.__name__}")


class VCMITCPServer:
    """
    TCP server for receiving VCMI battle AI requests.
    Supports multiple concurrent connections using threading.
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 65432):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.handler = BattleAIHandler()
        self.client_threads: List[threading.Thread] = []
        self.active_connections: Dict[str, socket.socket] = {}
        self.connections_lock = threading.Lock()
        self.thread_counter = 0

    def set_handler(self, handler: BattleAIHandler):
        """Set the event handler"""
        self.handler = handler

    def start(self):
        """Start the TCP server"""
        try:
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)  # Allow up to 10 pending connections

            self.running = True
            logger.info(f"VCMI TCP Server started on {self.host}:{self.port}")
            logger.info("Waiting for connections from VCMI game...")

            # Accept connections in a loop
            while self.running:
                try:
                    # Set timeout to allow checking self.running
                    self.server_socket.settimeout(1.0)
                    client_socket, client_address = self.server_socket.accept()
                    logger.info(f"Connection established from {client_address}")

                    # Create a new thread to handle this client
                    client_id = f"{client_address[0]}:{client_address[1]}"
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address, client_id),
                        daemon=True
                    )
                    thread.start()

                    # Track the thread
                    with self.connections_lock:
                        self.client_threads.append(thread)
                        self.active_connections[client_id] = client_socket

                    logger.info(f"Started thread for client {client_id}, active connections: {len(self.active_connections)}")

                except socket.timeout:
                    # Timeout is expected, allows checking self.running
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error starting server: {e}", exc_info=True)
        finally:
            self.stop()

    def _handle_client(self, client_socket: socket.socket, client_address: tuple, client_id: str):
        """
        Handle a single client connection in a dedicated thread.

        Args:
            client_socket: The client's socket
            client_address: The client's address tuple
            client_id: Unique identifier for this client
        """
        logger.info(f"Handler thread started for {client_id}")

        try:
            while self.running:
                try:
                    # Receive message
                    data = VCMIProtocolHandler.receive_message(client_socket)
                    if data is None:
                        logger.info(f"Client {client_id} disconnected")
                        break

                    # Deserialize pack
                    pack = deserialize_pack(data)
                    if pack is None:
                        logger.warning(f"Failed to deserialize pack from {client_id}")
                        continue

                    # Round-trip check: re-serialize and compare
                    reserialized = serialize_pack(pack)
                    if reserialized == data:
                        logger.info(f"[{client_id}] Round-trip OK ({len(data)} bytes)")
                    else:
                        logger.error(
                            f"[{client_id}] Round-trip MISMATCH! "
                            f"orig={len(data)} bytes, re={len(reserialized)} bytes"
                        )
                        # Find first differing byte
                        for i in range(min(len(data), len(reserialized))):
                            if data[i] != reserialized[i]:
                                logger.error(
                                    f"  First diff at byte {i}: "
                                    f"orig=0x{data[i]:02x} re=0x{reserialized[i]:02x}"
                                )
                                break

                    # Handle pack based on type
                    self._handle_pack(pack, client_id)

                except Exception as e:
                    logger.error(f"Error processing message from {client_id}: {e}", exc_info=True)
                    break

        except Exception as e:
            logger.error(f"Error in client handler for {client_id}: {e}", exc_info=True)
        finally:
            # Clean up the connection
            try:
                client_socket.close()
            except:
                pass

            # Remove from active connections
            with self.connections_lock:
                if client_id in self.active_connections:
                    del self.active_connections[client_id]

            logger.info(f"Handler thread ended for {client_id}, active connections: {len(self.active_connections)}")

    def _handle_pack(self, pack: CPack, client_id: str = "unknown"):
        """
        Handle a deserialized pack.

        Args:
            pack: The deserialized pack
            client_id: The client identifier for logging
        """
        if isinstance(pack, BattleStart):
            battle_id = pack.battle_id.to_int()
            logger.info(f"[{client_id}] BattleStart received")
            self.handler.handle_battle_start(battle_id, pack, client_id)

        elif hasattr(pack, '__class__') and pack.__class__.__name__ == 'BattleNextRound':
            from vcmi_types import BattleNextRound
            if isinstance(pack, BattleNextRound):
                battle_id = pack.battle_id.to_int()
                logger.info(f"[{client_id}] BattleNextRound received")
                self.handler.handle_battle_next_round(battle_id, client_id)

        elif hasattr(pack, '__class__') and pack.__class__.__name__ == 'BattleSetActiveStack':
            from vcmi_types import BattleSetActiveStack
            if isinstance(pack, BattleSetActiveStack):
                battle_id = pack.battle_id.to_int()
                logger.info(f"[{client_id}] BattleSetActiveStack received")
                self.handler.handle_set_active_stack(battle_id, pack.stack, client_id)

        else:
            logger.info(f"[{client_id}] Unknown pack: {pack.__class__.__name__}")
            self.handler.handle_unknown_pack(pack, client_id)

    def send_response(self, data: bytes, client_id: Optional[str] = None) -> bool:
        """
        Send a response to a specific client or all clients.

        Args:
            data: Message data to send
            client_id: Specific client to send to, or None to send to all

        Returns:
            True if successful, False otherwise
        """
        with self.connections_lock:
            if client_id:
                # Send to specific client
                if client_id in self.active_connections:
                    return VCMIProtocolHandler.send_message(self.active_connections[client_id], data)
                else:
                    logger.warning(f"Cannot send to client {client_id}: not found")
                    return False
            else:
                # Send to all active clients
                success = True
                for cid, socket in self.active_connections.items():
                    if not VCMIProtocolHandler.send_message(socket, data):
                        success = False
                        logger.warning(f"Failed to send to client {cid}")
                return success

    def broadcast_response(self, data: bytes) -> bool:
        """
        Broadcast a response to all connected clients.

        Args:
            data: Message data to send

        Returns:
            True if sent to at least one client successfully
        """
        return self.send_response(data, client_id=None)

    def stop(self):
        """Stop the server and all client connections"""
        self.running = False

        # Close all client connections
        with self.connections_lock:
            for client_id, client_socket in self.active_connections.items():
                try:
                    client_socket.close()
                    logger.info(f"Closed connection to {client_id}")
                except:
                    pass
            self.active_connections.clear()

        # Wait for all client threads to finish (with timeout)
        for thread in self.client_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)

        self.client_threads.clear()

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None

        logger.info("VCMI TCP Server stopped")

    def get_active_connections(self) -> int:
        """Get the number of active connections"""
        with self.connections_lock:
            return len(self.active_connections)


def main():
    """Main entry point"""
    server = VCMITCPServer(host='127.0.0.1', port=65432)

    # You can create a custom handler to process events
    from vcmi_types import BattleStart

    class MyBattleAIHandler(BattleAIHandler):
        def handle_battle_start(self, battle_id: int, battle_info: BattleStart, client_id: str = "unknown") -> None:
            logger.info("=" * 60)
            logger.info(f"[{client_id}] BATTLE STARTED!")
            logger.info("=" * 60)
            logger.info(f"Battle ID: {battle_id}")
            if battle_info.info:
                logger.info(f"[{client_id}]   Terrain: {battle_info.info.terrain_type}")
                logger.info(f"[{client_id}]   Battlefield: {battle_info.info.battlefield_type}")
                logger.info(f"[{client_id}]   Round: {battle_info.info.round}")
                logger.info(f"[{client_id}]   Stacks: {len(battle_info.info.stacks)}")

                for stack in battle_info.info.stacks:
                    logger.info(
                        f"[{client_id}]     Stack {stack.id}: {stack.count} units, "
                        f"Side: {stack.side.name}, HP: {stack.first_hp_left}"
                    )
            logger.info("=" * 60)
            logger.info(f"[{client_id}] Total active connections: {server.get_active_connections()}")

        def handle_set_active_stack(self, battle_id: int, stack_id: int, client_id: str = "unknown") -> None:
            logger.info(f"[{client_id}] 🎯 Active stack: {stack_id} (Battle: {battle_id})")
            # Here you would typically compute and send a battle action
            # For example:
            # response = self.compute_battle_action(battle_id, stack_id)
            # server.send_response(serialize_action(response), client_id)

    server.set_handler(MyBattleAIHandler())

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
