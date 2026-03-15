"""
VCMI Data Type Definitions

This module defines Python classes corresponding to VCMI game data structures
used in network communication.
"""

from typing import List, Optional, Set, Dict
from dataclasses import dataclass, field
from enum import IntEnum
from serializer import Serializeable, BinaryDeserializer, pack
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Core Type Enums
# ============================================================================

class BattleSide(IntEnum):
    """Side in battle (attacker/defender)"""
    NONE = -1
    ATTACKER = 0
    DEFENDER = 1


# Use simple integer wrappers instead of strict enums for IDs to handle unexpected values
class PlayerColor:
    """Player colors"""
    NEUTRAL = 255
    CANNOT_DETERMINE = 254

    def __init__(self, value: int = 255):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def __eq__(self, other):
        if isinstance(other, PlayerColor):
            return self.value == other.value
        return False

    def __repr__(self):
        return f"PlayerColor({self.value})"


class SpellID:
    """Spell identifiers"""
    NONE = -1

    def __init__(self, value: int = -1):
        self.value = value

    def to_int(self) -> int:
        return self.value


class TerrainId:
    """Terrain type identifiers - flexible wrapper to handle any value"""
    # Common terrain types (for reference)
    DIRT = 0
    GRASS = 1
    SAND = 2
    WATER = 3
    ROCK = 4
    SWAMP = 5
    SNOW = 6
    LAVA = 7

    def __init__(self, value: int = 0):
        self.value = value

    def __int__(self):
        return self.value

    def __repr__(self):
        return f"TerrainId({self.value})"


class EWallState(IntEnum):
    """States of siege wall parts"""
    INTACT = 0
    DAMAGED = 1
    DESTROYED = 2


class EGateState(IntEnum):
    """States of siege gate"""
    CLOSED = 0
    OPEN = 1
    DESTROYED = 2


class BattleFieldType(IntEnum):
    """Battlefield types"""
    NONE = 0
    SANDBOX = 1


class SlotID(IntEnum):
    """Army slot identifiers"""
    COMMANDER_SLOT_PLACEHOLDER = -2


class ObjectInstanceID:
    """Object instance identifiers"""
    NONE = -1

    def __init__(self, value: int = -1):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def __eq__(self, other):
        if isinstance(other, ObjectInstanceID):
            return self.value == other.value
        return False

    def __repr__(self):
        return f"ObjectInstanceID({self.value})"


class BattleID:
    """Battle identifier wrapper"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def __eq__(self, other):
        if isinstance(other, BattleID):
            return self.value == other.value
        return False


class CreatureID:
    """Creature identifier wrapper"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value


# ============================================================================
# Basic Data Structures
# ============================================================================

@dataclass
class int3:
    """3D integer coordinate (x, y, z)"""
    x: int = 0
    y: int = 0
    z: int = 0

    def serialize(self, deserializer: BinaryDeserializer):
        self.x = deserializer.load_integer()
        self.y = deserializer.load_integer()
        self.z = deserializer.load_integer()


@dataclass
class BattleHex:
    """Battle field hex position"""
    def __init__(self):
        self.hex: int = 0

    def serialize(self, deserializer: BinaryDeserializer):
        self.hex = deserializer.load_integer()


@dataclass
class BattleHexArray:
    """Array of battle hex positions"""
    def __init__(self):
        self.hexes: List[int] = []

    def serialize(self, deserializer: BinaryDeserializer):
        length = deserializer.load_integer()
        self.hexes = [deserializer.load_integer() for _ in range(length)]


@dataclass
class Bonus(Serializeable):
    """Bonus effect on an object"""
    type: int = 0
    subtype: int = 0
    val: int = 0
    val_type: int = 0
    duration: int = 0
    source: int = 0
    sid: int = 0
    additional_info: List[int] = field(default_factory=list)
    turnsRemain: int = 0
    targetSourceType: int = 0

    def serialize(self, deserializer: BinaryDeserializer):
        # Complete bonus deserialization matching C++ implementation
        self.duration = deserializer.load_integer()  # BonusDuration::Type (2 bytes, but loaded as integer)
        self.type = deserializer.load_integer()      # BonusType (2 bytes, but loaded as integer)
        self.subtype = deserializer.load_integer()   # BonusSubtypeID
        self.source = deserializer.load_integer()    # BonusSource (1 byte, but loaded as integer)
        self.val = deserializer.load_integer()       # si32 (4 bytes)
        self.sid = deserializer.load_integer()       # BonusSourceID
        
        # Skip description (MetaString) - complex type not fully supported in Python
        # For now, we'll skip this field to maintain proper alignment
        desc_length = deserializer.load_integer()
        if desc_length > 0:
            deserializer.read(desc_length)  # Skip the string data
        
        # Skip customIconPath (ImagePath) - conditional field, skip for now
        # Skip hidden (bool) - conditional field, skip for now
        
        # Load additional_info (CAddInfo - vector of si32)
        self.additional_info = deserializer.load_vector(int)
        
        self.turnsRemain = deserializer.load_integer()  # si16 (2 bytes, but loaded as integer)
        self.val_type = deserializer.load_integer()      # BonusValueType (1 byte, but loaded as integer)
        
        # Skip stacking (std::string) - skip for now
        stacking_length = deserializer.load_integer()
        if stacking_length > 0:
            deserializer.read(stacking_length)  # Skip the string data
        
        # Skip effectRange (BonusLimitEffect) - 1 byte, skip for now
        deserializer.load_integer()
        
        # Skip limiter (TLimiterPtr) - complex pointer type, skip for now
        # Skip propagator (TPropagatorPtr) - complex pointer type, skip for now
        # Skip updater (TUpdaterPtr) - complex pointer type, skip for now
        # Skip propagationUpdater (TUpdaterPtr) - complex pointer type, skip for now
        
        self.targetSourceType = deserializer.load_integer()  # BonusSource (1 byte, but loaded as integer)


@dataclass
class BonusList(Serializeable):
    """List of bonus effects"""
    bonuses: List[Bonus] = field(default_factory=list)

    def serialize(self, deserializer: BinaryDeserializer):
        # Load vector of bonuses manually (Bonus is not polymorphic)
        length = deserializer.load_integer()
        self.bonuses = []
        for _ in range(length):
            bonus = deserializer.load_object(Bonus)
            # bonus.serialize(deserializer)
            self.bonuses.append(bonus)


# ============================================================================
# Battle-Related Structures
# ============================================================================

@dataclass
class SideInBattle(Serializeable):
    """Information about one side in battle"""
    # GameCallbackHolder base class field
    cb: int = 0  # IGameInfoCallback pointer
    color: PlayerColor = field(default_factory=lambda: PlayerColor(255))
    hero_id: ObjectInstanceID = field(default_factory=lambda: ObjectInstanceID(-1))
    army_object_id: ObjectInstanceID = field(default_factory=lambda: ObjectInstanceID(-1))
    cast_spells_count: int = 0
    used_spells_history: List[int] = field(default_factory=list)
    enchanter_counter: int = 0
    initial_mana: int = 0
    additional_mana: int = 0

    def serialize(self, deserializer: BinaryDeserializer):
        logger.debug(f"SideInBattle.serialize() starting at position {deserializer.position}")

        # Load player color (using wrapper class to handle any integer value)
        color_int = deserializer.load_integer()
        self.color = PlayerColor(color_int)
        logger.debug(f"Loaded PlayerColor: {color_int} at position {deserializer.position}")

        # Load hero ID (ObjectInstanceID wrapper)
        hero_id_int = deserializer.load_integer()
        self.hero_id = ObjectInstanceID(hero_id_int)
        logger.debug(f"Loaded hero_id: {hero_id_int} at position {deserializer.position}")

        # Load army object ID (ObjectInstanceID wrapper)
        army_id_int = deserializer.load_integer()
        self.army_object_id = ObjectInstanceID(army_id_int)
        logger.debug(f"Loaded army_object_id: {army_id_int} at position {deserializer.position}")

        # Load cast spells count
        self.cast_spells_count = deserializer.load_integer()
        logger.debug(f"Loaded cast_spells_count: {self.cast_spells_count} at position {deserializer.position}")

        # Load used spells history (vector of SpellID)
        logger.debug(f"Loading used_spells_history vector at position {deserializer.position}")
        self.used_spells_history = deserializer.load_vector(int)
        logger.debug(f"Loaded used_spells_history: {len(self.used_spells_history)} items at position {deserializer.position}")

        # Load enchanter counter
        self.enchanter_counter = deserializer.load_integer()
        logger.debug(f"Loaded enchanter_counter: {self.enchanter_counter} at position {deserializer.position}")

        # Load initial mana
        self.initial_mana = deserializer.load_integer()
        logger.debug(f"Loaded initial_mana: {self.initial_mana} at position {deserializer.position}")

        # Load additional mana
        self.additional_mana = deserializer.load_integer()
        logger.debug(f"Loaded additional_mana: {self.additional_mana} at position {deserializer.position}")
        logger.debug(f"SideInBattle.serialize() completed at position {deserializer.position}")


@dataclass
class SiegeInfo(Serializeable):
    """Siege battle information"""
    wall_state: Dict[int, int] = field(default_factory=dict)  # Map from EWallPart to EWallState
    gate_state: EGateState = EGateState.CLOSED

    def serialize(self, deserializer: BinaryDeserializer):
        # Load wall state map (map<int, int>)
        self.wall_state = deserializer.load_map(int, int)

        # Load gate state
        gate_state_int = deserializer.load_integer()
        self.gate_state = EGateState(gate_state_int)


@dataclass
class CStack(Serializeable):
    """Battle stack (unit)"""
    id: int = 0
    type_id: CreatureID = field(default_factory=lambda: CreatureID(0))
    count: int = 0
    side: BattleSide = BattleSide.NONE
    position: BattleHex = field(default_factory=BattleHex)
    first_hp_left: int = 0
    alive: bool = True
    bonuses: List[Bonus] = field(default_factory=list)

    def serialize(self, deserializer: BinaryDeserializer):
        self.id = deserializer.load_integer()
        type_id_int = deserializer.load_integer()
        self.type_id = CreatureID(type_id_int)
        self.count = deserializer.load_integer()

        side_int = deserializer.load_integer()
        self.side = BattleSide(side_int)

        self.position = BattleHex()
        self.position.serialize(deserializer)

        self.first_hp_left = deserializer.load_integer()
        self.alive = deserializer.load_bool()


@dataclass
class ObstacleChanges(Serializeable):
    """Changes to battlefield obstacles"""
    obstacle_id: int = 0
    obstacle_type: int = 0

    def serialize(self, deserializer: BinaryDeserializer):
        self.obstacle_id = deserializer.load_integer()
        self.obstacle_type = deserializer.load_integer()


@dataclass
class UnitChanges(Serializeable):
    """Changes to battle units"""
    unit_id: int = 0
    count: int = 0
    hp_left: int = 0

    def serialize(self, deserializer: BinaryDeserializer):
        self.unit_id = deserializer.load_integer()
        self.count = deserializer.load_integer()
        self.hp_left = deserializer.load_integer()


# ============================================================================
# Complex Game Objects
# ============================================================================

@dataclass
class CGHeroInstance(Serializeable):
    """Hero instance"""
    id: ObjectInstanceID = field(default_factory=lambda: ObjectInstanceID(0))
    temp_owner: PlayerColor = PlayerColor.NEUTRAL
    name: str = ""
    level: int = 1
    experience: int = 0

    def serialize(self, deserializer: BinaryDeserializer):
        id_int = deserializer.load_integer()
        self.id = ObjectInstanceID(id_int)
        owner_int = deserializer.load_integer()
        self.temp_owner = PlayerColor(owner_int)
        self.name = deserializer.load_string()
        self.level = deserializer.load_integer()
        self.experience = deserializer.load_integer()
        logger.debug(f"Loaded CGHeroInstance: id={id_int}, owner={owner_int}")


@dataclass
class CArmedInstance(Serializeable):
    """Armed instance (army)"""
    id: ObjectInstanceID = field(default_factory=lambda: ObjectInstanceID(0))

    def serialize(self, deserializer: BinaryDeserializer):
        id_int = deserializer.load_integer()
        self.id = ObjectInstanceID(id_int)
        logger.debug(f"Loaded CArmedInstance id: {id_int}")


@dataclass
class CGTownInstance(Serializeable):
    """Town instance"""
    id: ObjectInstanceID = field(default_factory=lambda: ObjectInstanceID(0))
    name: str = ""

    def serialize(self, deserializer: BinaryDeserializer):
        id_int = deserializer.load_integer()
        self.id = ObjectInstanceID(id_int)
        self.name = deserializer.load_string()
        logger.debug(f"Loaded CGTownInstance: id={id_int}, name={self.name}")


# ============================================================================
# Battle Info
# ============================================================================

@dataclass
class BattleInfo(Serializeable):
    """Complete battle information"""
    battle_id: BattleID = field(default_factory=lambda: BattleID(0))
    sides: List[SideInBattle] = field(default_factory=list)
    round: int = 0
    active_stack: int = 0
    town_id: ObjectInstanceID = field(default_factory=lambda: ObjectInstanceID(-1))
    tile: int3 = field(default_factory=int3)
    stacks: List[CStack] = field(default_factory=list)
    obstacles: List[ObstacleChanges] = field(default_factory=list)
    siege_info: SiegeInfo = field(default_factory=SiegeInfo)
    battlefield_type: str = ""  # VCMI encodes this as string (e.g., "BA:B")
    terrain_type: TerrainId = field(default_factory=lambda: TerrainId(0))
    tactics_side: BattleSide = BattleSide.NONE
    tactic_distance: int = 0
    # CBonusSystemNode fields
    node_type: int = 0
    exported_bonuses: BonusList = field(default_factory=BonusList)
    replay_allowed: bool = False

    def serialize(self, deserializer: BinaryDeserializer):
        try:
            # Load battle ID
            logger.debug(f"Starting BattleInfo deserialization at position {deserializer.position}")
            self.battle_id = BattleID(deserializer.load_integer())
            logger.debug(f"After battle_id: position {deserializer.position}")

            # Load sides (2 elements - attacker and defender)
            sides = []
            for i in range(2):
                logger.debug(f"Loading side {i} at position {deserializer.position}")
                side = SideInBattle()
                side.serialize(deserializer)
                sides.append(side)
                logger.debug(f"After side {i}: position {deserializer.position}")
            self.sides = sides

            # Load basic battle info
            logger.debug(f"Loading basic battle info at position {deserializer.position}")
            self.round = deserializer.load_integer()
            self.active_stack = deserializer.load_integer()
            logger.debug(f"After round/active_stack: position {deserializer.position}")

            # Load town ID (ObjectInstanceID)
            town_id_int = deserializer.load_integer()
            self.town_id = ObjectInstanceID(town_id_int)
            logger.debug(f"After town_id: position {deserializer.position}")

            # Load tile position
            self.tile = int3()
            self.tile.serialize(deserializer)
            logger.debug(f"After tile: position {deserializer.position}")

            # Load stacks - these are polymorphic unique_ptr<CStack>
            stacks_length = deserializer.load_integer()
            logger.debug(f"Loading {stacks_length} stacks at position {deserializer.position}")
            self.stacks = []
            for i in range(stacks_length):
                # Load unique_ptr using proper pointer handling
                # unique_ptr format: [null_check:1][pointer_id:compact_int][...object data...]
                is_null = deserializer.load_bool()
                if not is_null:
                    pointer_id = deserializer.load_integer()

                    # Check if we've already loaded this pointer
                    if pointer_id in deserializer.loaded_pointers:
                        stack = deserializer.loaded_pointers[pointer_id]
                    else:
                        # Create and deserialize the stack
                        stack = CStack()
                        deserializer.loaded_pointers[pointer_id] = stack
                        stack.serialize(deserializer)
                    self.stacks.append(stack)
            logger.debug(f"After stacks: position {deserializer.position}")

            # Load obstacles - these are polymorphic shared_ptr<CObstacleInstance>
            obstacles_length = deserializer.load_integer()
            logger.debug(f"Loading {obstacles_length} obstacles at position {deserializer.position}")
            self.obstacles = []
            for i in range(obstacles_length):
                # Load shared_ptr using proper pointer handling
                # shared_ptr format: [null_check:1][pointer_id:compact_int][...object data...]
                is_null = deserializer.load_bool()
                if not is_null:
                    pointer_id = deserializer.load_integer()

                    # Check if we've already loaded this shared pointer
                    if pointer_id in deserializer.loaded_shared_pointers:
                        obstacle = deserializer.loaded_shared_pointers[pointer_id]
                    else:
                        # Create and deserialize the obstacle
                        obstacle = ObstacleChanges()
                        deserializer.loaded_shared_pointers[pointer_id] = obstacle
                        obstacle.serialize(deserializer)
                    self.obstacles.append(obstacle)
            logger.debug(f"After obstacles: position {deserializer.position}")

            # Load siege info
            logger.debug(f"Loading siege info at position {deserializer.position}")
            self.siege_info = SiegeInfo()
            self.siege_info.serialize(deserializer)
            logger.debug(f"After siege info: position {deserializer.position}")

            # Load battlefield and terrain type
            # battlefield_type is encoded as string in VCMI (e.g., "BA:B")
            self.battlefield_type = deserializer.load_string()
            logger.debug(f"Loaded battlefield_type as string: {self.battlefield_type}")

            # terrain_type_int = deserializer.load_integer()
            self.terrain_type = deserializer.load_string()  # TerrainId(terrain_type_int)

            logger.debug(f"After battlefield/terrain type: position {deserializer.position}")

            # Load tactics info
            self.tactics_side = BattleSide(deserializer.load_integer())
            self.tactic_distance = deserializer.load_integer()
            logger.debug(f"After tactics: position {deserializer.position}")

            # Load CBonusSystemNode fields (static_cast<CBonusSystemNode&>(*this))
            logger.debug(f"Loading CBonusSystemNode fields at position {deserializer.position}")
            self.node_type = deserializer.load_integer()
            self.exported_bonuses = BonusList()
            self.exported_bonuses.serialize(deserializer)
            logger.debug(f"After bonuses: position {deserializer.position}")

            # Load replay flag
            self.replay_allowed = deserializer.load_bool()
            logger.debug(f"After replay_allowed: position {deserializer.position}")
            logger.debug(f"BattleInfo deserialization completed at position {deserializer.position}")

            # Debug: Show remaining bytes
            remaining_bytes = len(deserializer.data) - deserializer.position
            if remaining_bytes > 0:
                remaining_data = deserializer.data[deserializer.position:]
                logger.warning(f"Remaining {remaining_bytes} bytes after BattleInfo deserialization: {remaining_data.hex()}")

        except Exception as e:
            logger.error(f"Error during BattleInfo deserialization at position {deserializer.position}: {e}")
            raise


# ============================================================================
# Network Pack Types
# ============================================================================

class CPack(Serializeable):
    """Base class for network packs"""
    pass


class CPackForClient(CPack):
    """Base class for packs sent to client"""
    pass


@dataclass
class BattleStart(CPackForClient):
    """Battle start notification pack"""
    battle_id: BattleID = field(default_factory=lambda: BattleID(0))
    info: Optional[BattleInfo] = None

    def serialize(self, deserializer: BinaryDeserializer):
        logger.debug(f"BattleStart.serialize() starting at position {deserializer.position}")
        self.battle_id = BattleID(deserializer.load_integer())
        logger.debug(f"After battle_id: position {deserializer.position}")

        # Load BattleInfo (polymorphic unique_ptr)
        # Use load_object which properly handles pointer deserialization
        self.info = deserializer.load_object(BattleInfo)
        logger.debug(f"After BattleInfo.deserialize: position {deserializer.position}")
        logger.debug(f"BattleStart.serialize() completed at position {deserializer.position}")


@dataclass
class BattleNextRound(CPackForClient):
    """New battle round notification"""
    battle_id: BattleID = field(default_factory=lambda: BattleID(0))

    def serialize(self, deserializer: BinaryDeserializer):
        self.battle_id = BattleID(deserializer.load_integer())


@dataclass
class BattleSetActiveStack(CPackForClient):
    """Notification about which stack should act"""
    battle_id: BattleID = field(default_factory=lambda: BattleID(0))
    stack: int = 0
    reason: int = 0  # BattleUnitTurnReason

    def serialize(self, deserializer: BinaryDeserializer):
        self.battle_id = BattleID(deserializer.load_integer())
        self.stack = deserializer.load_integer()
        self.reason = deserializer.load_integer()


# Register pack types after class definition
Serializeable.__registry__[77] = BattleInfo
Serializeable.__registry__[132] = BattleStart
Serializeable.__registry__[133] = BattleNextRound
Serializeable.__registry__[134] = BattleSetActiveStack

# Type ID registry for polymorphic deserialization
CPACK_TYPE_REGISTRY = {
    132: BattleStart,
    133: BattleNextRound,
    134: BattleSetActiveStack,
}


def create_pack_from_type_id(type_id: int) -> Optional[CPack]:
    """Create a pack instance from its type ID"""
    pack_class = CPACK_TYPE_REGISTRY.get(type_id)
    if pack_class:
        return pack_class()
    return None


# ============================================================================
# Helper Functions
# ============================================================================

def deserialize_pack(data: bytes) -> Optional[CPack]:
    """
    Deserialize a network pack from binary data.

    Args:
        data: Binary data received from network

    Returns:
        The deserialized CPack object, or None if deserialization fails
    """
    if len(data) == 0:
        logger.info(f"Received heartbeat message")
        return None

    try:
        # Create deserializer with SerializationVersion imported directly
        from serializer import BinaryDeserializer, SerializationVersion
        deserializer = BinaryDeserializer(data, version=SerializationVersion.CURRENT)

        # Load null check for CPack pointer
        is_null = deserializer.load_bool()
        if is_null:
            logger.warning("Received null pack")
            return None

        # Load pointer ID
        pointer_id = deserializer.load_integer()

        # Load type ID
        type_id = deserializer.load_encoded_integer()

        # Create pack instance
        pack_obj = create_pack_from_type_id(type_id)
        if pack_obj is None:
            logger.warning(f"Unknown pack type ID: {type_id}")
            return None

        # Deserialize pack data
        if pack_obj is not None:
            pack_obj.serialize(deserializer)

        # Check if we consumed all data
        if deserializer.position != len(data):
            logger.warning(
                f"Did not consume all data: {deserializer.position}/{len(data)} bytes"
            )

        logger.info(f"Successfully deserialized pack: {pack_obj.__class__.__name__}")
        return pack_obj

    except Exception as e:
        logger.error(f"Failed to deserialize pack: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    # Test deserialization
    from serializer import SerializationVersion

    # Example: Deserialize a BattleSetActiveStack pack
    # Format: [null_flag:1][ptr_id:4][type_id:2][battle_id:4][stack:4][ask_interface:1]
    test_data = bytes([
        0x00,  # Not null
        0x00, 0x00, 0x00, 0x00,  # Pointer ID = 0
        0x00, 0x86,  # Type ID = 134 (BattleSetActiveStack)
        0x01, 0x00, 0x00, 0x00,  # Battle ID = 1
        0x05, 0x00, 0x00, 0x00,  # Stack ID = 5
        0x01,  # Ask player interface = True
    ])

    pack = deserialize_pack(test_data)
    if pack:
        print(f"Pack type: {pack.__class__.__name__}")
        if isinstance(pack, BattleSetActiveStack):
            print(f"Battle ID: {pack.battle_id.to_int()}")
            print(f"Stack ID: {pack.stack}")
            print(f"Ask interface: {pack.ask_player_interface}")
