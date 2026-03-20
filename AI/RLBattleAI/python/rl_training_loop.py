"""
Reinforcement Learning Training Loop for VCMI Battle AI

This module implements a training loop that:
1. Accepts connections from multiple game clients
2. Receives and deserializes game state from clients
3. Picks actions (currently always returns DEFEND)
4. Serializes and sends actions back to clients
"""

import socket
import threading
import struct
import logging
import time
from typing import Optional, Dict, List
from dataclasses import dataclass
from collections import defaultdict

from tcp_server import VCMIProtocolHandler, BattleAIHandler, VCMITCPServer
from vcmi_types import (
    deserialize_pack, serialize_battle_action,
    BattleStart, BattleSetActiveStack, BattleNextRound,
    BattleAction, BattleActionDestination, BattleHex,
    EActionType, BattleSide
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ClientState:
    """State for a single game client"""
    client_id: str
    current_battle_id: Optional[int] = None
    active_stack_id: Optional[int] = None
    battle_info: Optional[BattleStart] = None
    action_count: int = 0
    pending_action: Optional[BattleAction] = None


class RLBattleAIHandler(BattleAIHandler):
    """
    Battle AI handler that implements a reinforcement learning training loop.

    For now, it always returns DEFEND actions, but the structure is in place
    to implement more sophisticated RL algorithms.
    """

    def __init__(self):
        super().__init__()
        self.client_states: Dict[str, ClientState] = {}
        self.states_lock = threading.Lock()
        self.total_actions_sent = 0

    def _get_or_create_client_state(self, client_id: str) -> ClientState:
        """Get or create client state for a given client ID"""
        with self.states_lock:
            if client_id not in self.client_states:
                self.client_states[client_id] = ClientState(client_id=client_id)
                logger.info(f"Created new client state for {client_id}")
            return self.client_states[client_id]

    def handle_battle_start(self, battle_id: int, battle_info: BattleStart, client_id: str = "unknown") -> None:
        """Handle battle start event - update client state"""
        state = self._get_or_create_client_state(client_id)
        state.current_battle_id = battle_id
        state.battle_info = battle_info
        state.action_count = 0

        logger.info(f"[{client_id}] Battle {battle_id} started")
        if battle_info.info:
            logger.info(f"[{client_id}]   Round: {battle_info.info.round}")
            logger.info(f"[{client_id}]   Stacks: {len(battle_info.info.stacks)}")

    def handle_battle_next_round(self, battle_id: int, client_id: str = "unknown") -> None:
        """Handle next round event"""
        state = self._get_or_create_client_state(client_id)
        logger.info(f"[{client_id}] Battle {battle_id} - Next round")

    def handle_set_active_stack(self, battle_id: int, stack_id: int, client_id: str = "unknown") -> None:
        """
        Handle active stack change - this is where we decide on an action.

        This is called when a stack becomes active and needs to take an action.
        We need to compute and send an action back to the client.
        """
        state = self._get_or_create_client_state(client_id)
        state.current_battle_id = battle_id
        state.active_stack_id = stack_id

        logger.info(f"[{client_id}] Battle {battle_id} - Active stack: {stack_id}")

        # Compute action using RL policy (currently always DEFEND)
        action = self._compute_action(state, stack_id)

        # Store that we need to send this action back
        state.pending_action = action
        logger.info(f"[{client_id}] Computed action: {action.action_type.name}")

    def _compute_action(self, state: ClientState, stack_id: int) -> BattleAction:
        """
        Compute the next action using the RL policy.

        For now, this always returns a DEFEND action.
        In the future, this will use the RL model to select actions.

        Args:
            state: Current client state
            stack_id: ID of the active stack

        Returns:
            BattleAction to execute
        """
        # TODO: Replace this with actual RL model inference
        # For now, always return DEFEND

        action = BattleAction()
        action.side = BattleSide.ATTACKER  # TODO: Determine correct side
        action.stack_number = stack_id
        action.action_type = EActionType.DEFEND
        action.spell.value = -1  # No spell
        action.target = []  # No target for DEFEND

        return action

    def get_pending_action(self, client_id: str) -> Optional[BattleAction]:
        """Get and clear the pending action for a client"""
        with self.states_lock:
            if client_id in self.client_states:
                state = self.client_states[client_id]
                if hasattr(state, 'pending_action'):
                    action = state.pending_action
                    delattr(state, 'pending_action')
                    return action
        return None

    def get_client_stats(self) -> Dict:
        """Get statistics for all clients"""
        with self.states_lock:
            return {
                'num_clients': len(self.client_states),
                'total_actions': self.total_actions_sent,
                'clients': {
                    cid: {
                        'battle_id': state.current_battle_id,
                        'actions': state.action_count
                    }
                    for cid, state in self.client_states.items()
                }
            }


class RLTrainingServer(VCMITCPServer):
    """
    TCP server specialized for RL training.

    Extends the base VCMITCPServer to add RL-specific functionality:
    - Action computation after receiving game state
    - Automatic response sending
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 65432):
        super().__init__(host, port)
        self.rl_handler = RLBattleAIHandler()
        self.set_handler(self.rl_handler)

    def _handle_client(self, client_socket: socket.socket, client_address: tuple, client_id: str):
        """
        Handle a single client connection with RL-specific logic.

        Overrides base class to automatically send actions after processing state.
        """
        logger.info(f"RL handler thread started for {client_id}")

        try:
            while self.running:
                try:
                    # Receive message (game state from client)
                    data = VCMIProtocolHandler.receive_message(client_socket)
                    if data is None:
                        logger.info(f"Client {client_id} disconnected")
                        break

                    # Deserialize pack (game state)
                    pack = deserialize_pack(data)
                    if pack is None:
                        logger.warning(f"Failed to deserialize pack from {client_id}")
                        continue

                    # Handle pack and potentially compute action
                    self._handle_pack_and_send_action(
                        pack, client_id, client_socket
                    )

                except Exception as e:
                    logger.error(f"Error processing message from {client_id}: {e}", exc_info=True)
                    break

        except Exception as e:
            logger.error(f"Error in RL client handler for {client_id}: {e}", exc_info=True)
        finally:
            # Clean up
            try:
                client_socket.close()
            except:
                pass

            with self.connections_lock:
                if client_id in self.active_connections:
                    del self.active_connections[client_id]

            logger.info(f"RL handler thread ended for {client_id}")

    def _handle_pack_and_send_action(self, pack, client_id: str, client_socket: socket.socket):
        """
        Handle a pack and send back an action if needed.

        Args:
            pack: The deserialized pack
            client_id: Client identifier
            client_socket: Socket to send response on
        """
        from vcmi_types import BattleNextRound

        if isinstance(pack, BattleStart):
            battle_id = pack.battle_id.to_int()
            logger.info(f"[{client_id}] BattleStart received")
            self.rl_handler.handle_battle_start(battle_id, pack, client_id)

        elif isinstance(pack, BattleNextRound):
            battle_id = pack.battle_id.to_int()
            logger.info(f"[{client_id}] BattleNextRound received")
            self.rl_handler.handle_battle_next_round(battle_id, client_id)

        elif isinstance(pack, BattleSetActiveStack):
            battle_id = pack.battle_id.to_int()
            stack_id = pack.stack
            logger.info(f"[{client_id}] BattleSetActiveStack received")

            # Handle the active stack event (computes action)
            self.rl_handler.handle_set_active_stack(battle_id, stack_id, client_id)

            # Get the computed action and send it back
            action = self.rl_handler.get_pending_action(client_id)
            if action:
                self._send_action(action, client_socket, client_id)
            else:
                logger.warning(f"[{client_id}] No action computed for stack {stack_id}")

        else:
            logger.info(f"[{client_id}] Unknown pack: {pack.__class__.__name__}")
            self.rl_handler.handle_unknown_pack(pack, client_id)

    def _send_action(self, action: BattleAction, client_socket: socket.socket, client_id: str):
        """
        Serialize and send an action back to the client.

        Args:
            action: The BattleAction to send
            client_socket: Socket to send on
            client_id: Client identifier for logging
        """
        try:
            # Serialize the action
            action_data = serialize_battle_action(action)
            logger.debug(f"[{client_id}] Serialized action: {action.action_type.name} ({len(action_data)} bytes)")

            # Send using VCMI protocol
            success = VCMIProtocolHandler.send_message(client_socket, action_data)

            if success:
                self.rl_handler.total_actions_sent += 1
                logger.info(f"[{client_id}] Sent action: {action.action_type.name} for stack {action.stack_number}")
            else:
                logger.error(f"[{client_id}] Failed to send action")

        except Exception as e:
            logger.error(f"[{client_id}] Error sending action: {e}", exc_info=True)

    def get_stats(self) -> Dict:
        """Get server statistics"""
        stats = self.rl_handler.get_client_stats()
        stats['active_connections'] = self.get_active_connections()
        return stats


def main():
    """Main entry point for RL training server"""
    import argparse

    parser = argparse.ArgumentParser(description='VCMI RL Training Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=65432, help='Port to bind to')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    server = RLTrainingServer(host=args.host, port=args.port)

    logger.info("=" * 60)
    logger.info("VCMI RL Training Server")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info("Ready to accept connections from VCMI game clients...")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("\nServer interrupted by user")
    finally:
        # Print final statistics
        stats = server.get_stats()
        logger.info("\n" + "=" * 60)
        logger.info("Final Statistics:")
        logger.info("=" * 60)
        logger.info(f"Total clients: {stats['num_clients']}")
        logger.info(f"Total actions sent: {stats['total_actions']}")
        server.stop()


if __name__ == "__main__":
    main()
