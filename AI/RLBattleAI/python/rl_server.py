"""
Reinforcement Learning Training Loop Server

This module implements a training loop that:
1. Accepts connections from multiple game clients
2. Receives game state from clients and deserializes it
3. Picks an action, serializes it and sends it back to the client
"""

import socket
import threading
import struct
import logging
import time
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, field

from tcp_server import VCMIProtocolHandler, BattleAIHandler
from vcmi_types import (
    BattleStart, BattleSetActiveStack, BattleNextRound,
    MakeAction, BattleAction, BattleActionDestination,
    BattleID, BattleSide, EActionType,
    serialize_pack, deserialize_pack
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ClientState:
    """State for a connected client"""
    battle_id: Optional[BattleID] = None
    active_stack: Optional[int] = None
    battle_info: Optional['BattleInfo'] = None
    loaded_strings: list = field(default_factory=list)  # Persist string references acrosspackets


class RLTrainingHandler(BattleAIHandler):
    """
    Handler for RL training that processes game state and returns actions.
    """

    def __init__(self, server: 'RLTrainingServer'):
        super().__init__()
        self.server = server
        self.client_states: Dict[str, ClientState] = {}

    def get_or_create_state(self, client_id: str) -> ClientState:
        """Get or create client state"""
        if client_id not in self.client_states:
            self.client_states[client_id] = ClientState()
        return self.client_states[client_id]

    def handle_battle_start(self, battle_id: int, battle_info: BattleStart, client_id: str = "unknown") -> None:
        """Handle battle start event - this is when C++ AI waits for an action"""
        state = self.get_or_create_state(client_id)
        state.battle_id = battle_info.battle_id
        state.battle_info = battle_info.info
        logger.info(f"[{client_id}] Battle started: {battle_id}")
        super().handle_battle_start(battle_id, battle_info, client_id)

        # The active_stack field in BattleInfo tells us which stack should act
        active_stack_id = -1
        if battle_info.info and hasattr(battle_info.info, 'active_stack'):
            active_stack_id = battle_info.info.active_stack
            logger.info(f"[{client_id}] Active stack from BattleInfo: {active_stack_id}")
        else:
            logger.warning(f"[{client_id}] No active_stack in BattleInfo, using -1")

        # The C++ AI sends BattleStart and waits for MakeAction
        # Send a defend action with the correct stack ID
        action = self.create_defend_action(battle_id, active_stack_id, client_id)
        if action:
            self.server.send_action(action, client_id)

    def handle_battle_next_round(self, battle_id: int, client_id: str = "unknown") -> None:
        """Handle next round event"""
        state = self.get_or_create_state(client_id)
        logger.info(f"[{client_id}] Battle next round: {battle_id}")
        super().handle_battle_next_round(battle_id, client_id)

    def handle_set_active_stack(self, battle_id: int, stack_id: int, client_id: str = "unknown") -> None:
        """Handle active stack change"""
        state = self.get_or_create_state(client_id)
        state.active_stack = stack_id
        logger.info(f"[{client_id}] Active stack: {stack_id} (Battle: {battle_id})")
        super().handle_set_active_stack(battle_id, stack_id, client_id)

        # Also send action here for BattleSetActiveStack packs if needed
        action = self.create_defend_action(battle_id, stack_id, client_id)
        if action:
            self.server.send_action(action, client_id)

    def handle_unknown_pack(self, pack, client_id: str = "unknown") -> None:
        """Handle unknown pack types"""
        logger.warning(f"[{client_id}] Unknown pack type: {type(pack).__name__}")

    def create_defend_action(self, battle_id: int, stack_id: int, client_id: str) -> Optional[bytes]:
        """
        Create a defend action for the given stack.
        For now, this always returns a DEFEND action.
        """
        state = self.get_or_create_state(client_id)

        battle_action = BattleAction(
            side=BattleSide.ATTACKER,
            stack_number=stack_id,
            action_type=EActionType.DEFEND,
            spell=-1,
            target=[]
        )

        make_action = MakeAction(
            ba=battle_action,
            battle_id=BattleID(battle_id) if state.battle_id is None else state.battle_id
        )
        make_action.player = 255
        make_action.request_id = 0

        make_action._pack_pointer_id = 0
        make_action._pack_type_id = 198

        try:
            serialized = serialize_pack(make_action)
            logger.info(f"[{client_id}] Created DEFEND action for stack {stack_id}, serialized {len(serialized)} bytes")
            logger.debug(f"[{client_id}] Bytes: {serialized.hex()}")
            return serialized
        except Exception as e:
            logger.error(f"[{client_id}] Failed to serialize action: {e}", exc_info=True)
            return None


class RLTrainingServer:
    """
    RL Training server that handles multiple game client connections.

    Accepts connections from game clients, receives game state,
    and sends back actions.
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 65432):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.handler = RLTrainingHandler(self)
        self.client_threads: list = []
        self.active_connections: Dict[str, socket.socket] = {}
        self.connections_lock = threading.Lock()
        self.client_buffers: Dict[str, bytes] = {}

    def start(self):
        """Start the TCP server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)

            self.running = True
            logger.info(f"RL Training Server started on {self.host}:{self.port}")
            logger.info("Waiting for game client connections...")

            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client_socket, client_address = self.server_socket.accept()
                    client_id = f"{client_address[0]}:{client_address[1]}"
                    logger.info(f"Connection established from {client_address}")

                    # Add connection BEFORE starting thread to avoid race condition
                    with self.connections_lock:
                        self.active_connections[client_id] = client_socket

                    # Create a new thread to handle this client
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address, client_id),
                        daemon=True
                    )
                    thread.start()

                    # Track the thread
                    with self.connections_lock:
                        self.client_threads.append(thread)

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
        """Handle a single client connection"""
        logger.info(f"Handler thread started for {client_id}")
        state = self.handler.get_or_create_state(client_id)

        try:
            while self.running:
                try:
                    data = VCMIProtocolHandler.receive_message(client_socket)
                    if data is None:
                        logger.info(f"Client {client_id} disconnected")
                        break

                    # Deserialize pack with persistent string state
                    pack, state.loaded_strings = deserialize_pack(data, state.loaded_strings)
                    if pack is None:
                        continue

                    self._handle_pack(pack, client_id)

                except Exception as e:
                    logger.error(f"Error processing message from {client_id}: {e}", exc_info=True)
                    break

        except Exception as e:
            logger.error(f"Error in client handler for {client_id}: {e}", exc_info=True)
        finally:
            try:
                client_socket.close()
            except:
                pass

            with self.connections_lock:
                if client_id in self.active_connections:
                    del self.active_connections[client_id]

            logger.info(f"Handler thread ended for {client_id}, active connections: {len(self.active_connections)}")

    def _handle_pack(self, pack, client_id: str):
        """Handle a deserialized pack"""
        if isinstance(pack, BattleStart):
            battle_id = pack.battle_id.to_int()
            self.handler.handle_battle_start(battle_id, pack, client_id)

        elif isinstance(pack, BattleNextRound):
            battle_id = pack.battle_id.to_int()
            self.handler.handle_battle_next_round(battle_id, client_id)

        elif isinstance(pack, BattleSetActiveStack):
            battle_id = pack.battle_id.to_int()
            self.handler.handle_set_active_stack(battle_id, pack.stack, client_id)

        else:
            self.handler.handle_unknown_pack(pack, client_id)

    def send_action(self, data: bytes, client_id: str) -> bool:
        """Send an action to a specific client"""
        with self.connections_lock:
            if client_id in self.active_connections:
                result = VCMIProtocolHandler.send_message(self.active_connections[client_id], data)
                if result:
                    logger.info(f"[{client_id}] Action sent successfully")
                return result
            else:
                logger.warning(f"Cannot send to client {client_id}: not found")
                return False

    def stop(self):
        """Stop the server"""
        self.running = False

        with self.connections_lock:
            for client_id, client_socket in self.active_connections.items():
                try:
                    client_socket.close()
                    logger.info(f"Closed connection to {client_id}")
                except:
                    pass
            self.active_connections.clear()
            self.client_buffers.clear()

        for thread in self.client_threads:
            if thread.is_alive():
                thread.join(timeout=2.0)

        self.client_threads.clear()

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None

        logger.info("RL Training Server stopped")

    def get_active_connections(self) -> int:
        """Get the number of active connections"""
        with self.connections_lock:
            return len(self.active_connections)


def main():
    """Main entry point"""
    server = RLTrainingServer(host='127.0.0.1', port=65432)

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    finally:
        server.stop()


if __name__ == "__main__":
    main()