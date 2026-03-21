"""
RL Training Loop for VCMI Battle AI

Accepts connections from multiple game clients, receives game state,
picks an action, and sends it back. Currently returns DEFEND for every
active stack as a placeholder for a real RL policy.
"""

import logging
from tcp_server import VCMITCPServer, BattleAIHandler
from vcmi_types import (
    BattleStart, BattleStateForAI, BattleAction, MakeAction,
    EActionType, BattleSide, serialize_pack, BattleID,
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

    def handle_battle_state(self, state: BattleStateForAI, client_id: str = "unknown") -> None:
        logger.info(f"[{client_id}] BattleStateForAI: battle={state.battle_id}, "
                     f"round={state.round}, active_stack={state.active_stack_id}, "
                     f"stacks={len(state.stacks)}, obstacles={len(state.obstacles)}, "
                     f"reachable={len(state.reachable_hexes)}")

        for s in state.stacks:
            logger.info(
                f"[{client_id}]   Stack {s.id}: creature={s.creature_id}, "
                f"count={s.count}, pos={s.position}, "
                f"side={'ATK' if s.side == 0 else 'DEF'}, "
                f"alive={s.alive}, hp={s.first_hp_left}/{s.max_hp}, "
                f"atk={s.attack}, def={s.defense}, spd={s.speed}"
            )

        active_side = BattleSide(state.active_side)

        # Pick action (placeholder: always DEFEND)
        action = self._select_action(state, state.active_stack_id, active_side)

        # Build and send MakeAction pack
        pack = MakeAction()
        pack.ba = action
        pack.battle_id = BattleID(state.battle_id)
        pack._pack_pointer_id = 0
        pack._pack_type_id = 198

        data = serialize_pack(pack)
        logger.info(f"[{client_id}] Sending action: {action.action_type.name} "
                    f"for stack {action.stack_number} ({len(data)} bytes)")
        self.server.send_response(data, client_id)

    def _select_action(self, state, stack_id, side):
        """
        Select an action for the active stack.
        This is the hook point for a real RL policy.
        Currently always returns DEFEND.
        """
        return BattleAction.make_defend(stack_id, side)

    def handle_battle_start(self, battle_id: int, battle_info: BattleStart, client_id: str = "unknown") -> None:
        logger.info(f"[{client_id}] BattleStart received (legacy), ID={battle_id}")

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
