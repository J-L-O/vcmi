"""
RL Training Loop for VCMI Battle AI

Accepts connections from multiple game clients, receives game state,
picks an action, and sends it back. Currently returns DEFEND for every
active stack as a placeholder for a real RL policy.
"""

import logging
from tcp_server import VCMITCPServer, BattleAIHandler
from vcmi_types import (
    BattleStart, BattleAction, MakeAction, EActionType, BattleSide,
    serialize_pack, BattleID,
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RLBattleHandler(BattleAIHandler):
    """
    RL training handler. Receives game state from clients and returns actions.
    Currently always returns DEFEND as a placeholder policy.
    """

    def __init__(self, server: VCMITCPServer):
        self.server = server

    def handle_battle_start(self, battle_id: int, battle_info: BattleStart, client_id: str = "unknown") -> None:
        logger.info(f"[{client_id}] Battle started, ID={battle_id}")

        if battle_info.info:
            info = battle_info.info
            logger.info(f"[{client_id}]   Round: {info.round}")
            logger.info(f"[{client_id}]   Active stack: {info.active_stack}")
            logger.info(f"[{client_id}]   Stacks: {len(info.stacks)}")

            for stack in info.stacks:
                logger.info(
                    f"[{client_id}]     Stack {stack.id}: "
                    f"count={stack.count}, side={stack.side.name}, "
                    f"pos={stack.position.hex}, hp={stack.first_hp_left}"
                )

            # Find the active stack to determine side
            active_stack_id = info.active_stack
            active_side = BattleSide.ATTACKER
            for stack in info.stacks:
                if stack.id == active_stack_id:
                    active_side = stack.side
                    break

            # Pick action (placeholder: always DEFEND)
            action = self._select_action(battle_id, info, active_stack_id, active_side)

            # Build and send MakeAction pack
            pack = MakeAction()
            pack.ba = action
            pack.battle_id = BattleID(battle_id)
            pack._pack_pointer_id = 0
            pack._pack_type_id = 198

            data = serialize_pack(pack)
            logger.info(f"[{client_id}] Sending action: {action.action_type.name} "
                        f"for stack {action.stack_number} ({len(data)} bytes)")
            self.server.send_response(data, client_id)

    def _select_action(self, battle_id, battle_info, stack_id, side):
        """
        Select an action for the active stack.
        This is the hook point for a real RL policy.
        Currently always returns DEFEND.
        """
        return BattleAction.make_defend(stack_id, side)

    def handle_battle_next_round(self, battle_id: int, client_id: str = "unknown") -> None:
        logger.info(f"[{client_id}] Next round, battle={battle_id}")

    def handle_set_active_stack(self, battle_id: int, stack_id: int, client_id: str = "unknown") -> None:
        logger.info(f"[{client_id}] Active stack: {stack_id}, battle={battle_id}")


def main():
    server = VCMITCPServer(host='127.0.0.1', port=65432)
    handler = RLBattleHandler(server)
    server.set_handler(handler)

    logger.info("Starting RL training loop server...")
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Training loop interrupted")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
