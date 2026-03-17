"""
VCMI Data Type Definitions

This module defines Python classes corresponding to VCMI game data structures
used in network communication.
"""

from typing import List, Optional, Set, Dict
from dataclasses import dataclass, field
from enum import IntEnum
from serializer import Serializeable, BinaryDeserializer, pack, SerializationVersion
import logging


# ============================================================================
# Resource Path Types
# ============================================================================

class EResType(IntEnum):
    """Resource type enum matching C++ EResType"""
    TEXT = 0
    JSON = 1
    ANIMATION = 2
    MASK = 3
    CAMPAIGN = 4
    MAP = 5
    BMP_FONT = 6
    TTF_FONT = 7
    IMAGE = 8
    VIDEO = 9
    VIDEO_LOW_QUALITY = 10
    SOUND = 11
    ARCHIVE_VID = 12
    ARCHIVE_ZIP = 13
    ARCHIVE_SND = 14
    ARCHIVE_LOD = 15
    ARCHIVE_PAK = 16
    PALETTE = 17
    SAVEGAME = 18
    DIRECTORY = 19
    ERM = 20
    ERT = 21
    ERS = 22
    LUA = 23
    AI_MODEL = 24
    OTHER = 25
    UNDEFINED = 26


class ImagePath(Serializeable):
    """Image resource path matching C++ ImagePath (ResourcePathTempl<EResType::IMAGE>)"""

    def __init__(self):
        self.type: int = EResType.IMAGE
        self.name: str = ""
        self.originalName: str = ""

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize ImagePath from binary format"""
        self.type = deserializer.load_integer()  # EResType
        self.name = deserializer.load_string()   # uppercase name without extension
        self.originalName = deserializer.load_string()  # original case name

    def __repr__(self):
        return f"ImagePath({self.name})"

logger = logging.getLogger(__name__)


# ============================================================================
# Limiter Types
# ============================================================================

@Serializeable.register_type(48)
class Limiter(Serializeable):
    """Base class for all limiters"""

    def __init__(self):
        pass

    def serialize(self, deserializer: BinaryDeserializer):
        """Base limiter serialization - to be overridden by subclasses"""
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}()"


@Serializeable.register_type(49)
class AnyOfLimiter(Limiter):
    """Requires at least one of the child limiters to be true"""

    def __init__(self):
        super().__init__()
        self.limiters = []

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize AnyOfLimiter"""
        # Load vector of child limiters
        self.limiters = deserializer.load_vector(Limiter)

    def __repr__(self):
        return f"AnyOfLimiter({len(self.limiters)} children)"


@Serializeable.register_type(50)
class NoneOfLimiter(Limiter):
    """Requires none of the child limiters to be true"""

    def __init__(self):
        super().__init__()
        self.limiters = []

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize NoneOfLimiter"""
        # Load vector of child limiters
        self.limiters = deserializer.load_vector(Limiter)

    def __repr__(self):
        return f"NoneOfLimiter({len(self.limiters)} children)"


@Serializeable.register_type(51)
class OppositeSideLimiter(Limiter):
    """Applies only to creatures of enemy army during combat"""

    def __init__(self):
        super().__init__()
        # Owner field is only present in old versions
        self.owner = None

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize OppositeSideLimiter"""
        # Check if owner field is present in this version
        if deserializer.version < SerializationVersion.OPPOSITE_SIDE_LIMITER_OWNER:
            # Load owner field (PlayerColor) for old versions
            self.owner = deserializer.load_integer()

    def __repr__(self):
        if self.owner is not None:
            return f"OppositeSideLimiter(owner={self.owner})"
        return f"OppositeSideLimiter()"


@Serializeable.register_type(61)
class AllOfLimiter(Limiter):
    """Requires all of the child limiters to be true"""

    def __init__(self):
        super().__init__()
        self.limiters = []

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize AllOfLimiter"""
        # Load vector of child limiters
        self.limiters = deserializer.load_vector(Limiter)

    def __repr__(self):
        return f"AllOfLimiter({len(self.limiters)} children)"


@Serializeable.register_type(62)
class CCreatureTypeLimiter(Limiter):
    """Applies only to stacks of given creature type (and optionally its upgrades)"""

    def __init__(self):
        super().__init__()
        self.creatureID = 0
        self.includeUpgrades = False

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize CreatureTypeLimiter"""
        # Load creature ID
        self.creatureID = deserializer.load_integer()
        # Load includeUpgrades flag
        self.includeUpgrades = deserializer.load_bool()

    def __repr__(self):
        return f"CCreatureTypeLimiter(creatureID={self.creatureID}, includeUpgrades={self.includeUpgrades})"


@Serializeable.register_type(63)
class HasAnotherBonusLimiter(Limiter):
    """Applies only to nodes that have another bonus working"""

    def __init__(self):
        super().__init__()
        self.type = 0
        self.subtype = 0
        self.source = 0
        self.sid = 0
        self.isSubtypeRelevant = False
        self.isSourceRelevant = False
        self.isSourceIDRelevant = False

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize HasAnotherBonusLimiter"""
        # Load bonus type
        self.type = deserializer.load_integer()
        # Load bonus subtype
        self.subtype = deserializer.load_integer()
        # Load bonus source
        self.source = deserializer.load_integer()
        # Load bonus source ID
        self.sid = deserializer.load_integer()
        # Load relevance flags
        self.isSubtypeRelevant = deserializer.load_bool()
        self.isSourceRelevant = deserializer.load_bool()
        self.isSourceIDRelevant = deserializer.load_bool()

    def __repr__(self):
        return f"HasAnotherBonusLimiter(type={self.type}, source={self.source})"


TERRAIN_JSON_KEY_TO_INDEX = {
    "dirt": 0,
    "sand": 1,
    "grass": 2,
    "snow": 3,
    "swamp": 4,
    "rough": 5,
    "subterra": 6,
    "lava": 7,
    "water": 8,
    "rock": 9,
}

FACTION_JSON_KEY_TO_INDEX = {
    "castle": 0,
    "rampart": 1,
    "tower": 2,
    "inferno": 3,
    "necropolis": 4,
    "dungeon": 5,
    "stronghold": 6,
    "fortress": 7,
    "conflux": 8,
    "neutral": 9,
    "random": -1,
}


def deserialize_terrain_id(deserializer: BinaryDeserializer) -> int:
    """Deserialize a TerrainId from the binary stream.
    
    C++ TerrainId serializes as:
    - "" (empty string) -> -1 (NONE)
    - "native" -> -4 (NATIVE_TERRAIN)
    - Otherwise, the JSON key (e.g., "dirt", "grass") -> index
    """
    terrain_str = deserializer.load_string()
    
    if terrain_str == "":
        return -1  # NONE
    elif terrain_str == "native":
        return -4  # NATIVE_TERRAIN
    else:
        return TERRAIN_JSON_KEY_TO_INDEX.get(terrain_str, -1)


def deserialize_faction_id(deserializer: BinaryDeserializer) -> int:
    """Deserialize a FactionID from the binary stream.
    
    C++ FactionID serializes as a string (the JSON key like "castle", "rampart", etc.)
    """
    faction_str = deserializer.load_string()
    return FACTION_JSON_KEY_TO_INDEX.get(faction_str, -1)


@Serializeable.register_type(64)
class TerrainLimiter(Limiter):
    """Applies only to creatures that are on specified terrain"""

    def __init__(self):
        super().__init__()
        self.terrainType = 0

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize TerrainLimiter"""
        # Load terrain type (serialized as string in C++)
        self.terrainType = deserialize_terrain_id(deserializer)

    def __repr__(self):
        return f"TerrainLimiter(terrainType={self.terrainType})"


@Serializeable.register_type(65)
class FactionLimiter(Limiter):
    """Applies only to creatures of given faction"""

    def __init__(self):
        super().__init__()
        self.faction = 0

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize FactionLimiter"""
        # Load faction ID (serialized as string in C++)
        self.faction = deserialize_faction_id(deserializer)

    def __repr__(self):
        return f"FactionLimiter(faction={self.faction})"


@Serializeable.register_type(66)
class CCreatureLevelLimiter(Limiter):
    """Applies only to creatures of given level range"""

    def __init__(self):
        super().__init__()
        self.minLevel = 0
        self.maxLevel = 0

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize CreatureLevelLimiter"""
        # Load min level
        self.minLevel = deserializer.load_integer()
        # Load max level
        self.maxLevel = deserializer.load_integer()

    def __repr__(self):
        return f"CCreatureLevelLimiter(min={self.minLevel}, max={self.maxLevel})"


@Serializeable.register_type(67)
class CCreatureAlignmentLimiter(Limiter):
    """Applies only to creatures of given alignment"""

    def __init__(self):
        super().__init__()
        self.alignment = EAlignment.ANY

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize CreatureAlignmentLimiter"""
        # Load alignment
        self.alignment = EAlignment(deserializer.load_integer())

    def __repr__(self):
        return f"CCreatureAlignmentLimiter(alignment={self.alignment})"


@Serializeable.register_type(68)
class RankRangeLimiter(Limiter):
    """Applies to creatures with min <= Rank <= max"""

    def __init__(self):
        super().__init__()
        self.minRank = 0
        self.maxRank = 0

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize RankRangeLimiter"""
        # Load min rank
        self.minRank = deserializer.load_integer()
        # Load max rank
        self.maxRank = deserializer.load_integer()

    def __repr__(self):
        return f"RankRangeLimiter(min={self.minRank}, max={self.maxRank})"


@Serializeable.register_type(69)
class UnitOnHexLimiter(Limiter):
    """Works only on selected hexes"""

    def __init__(self):
        super().__init__()
        self.applicableHexes = []

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize UnitOnHexLimiter"""
        # Load applicable hexes vector
        self.applicableHexes = deserializer.load_vector(int)

    def __repr__(self):
        return f"UnitOnHexLimiter({len(self.applicableHexes)} hexes)"


@Serializeable.register_type(55)
class HasChargesLimiter(Limiter):
    """Works with bonuses that consume charges"""

    def __init__(self):
        super().__init__()
        self.chargeCost = 1

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize HasChargesLimiter"""
        # Load charge cost
        self.chargeCost = deserializer.load_integer()

    def __repr__(self):
        return f"HasChargesLimiter(chargeCost={self.chargeCost})"


# ============================================================================
# Propagator Classes
# ============================================================================

class BonusNodeType(IntEnum):
    """Type of bonus node in the bonus system tree"""
    NONE = -1
    UNKNOWN = 0
    STACK_INSTANCE = 1
    STACK_BATTLE = 2
    ARMY = 3
    ARTIFACT = 4
    CREATURE = 5
    ARTIFACT_INSTANCE = 6
    HERO = 7
    PLAYER = 8
    TEAM = 9
    TOWN_AND_VISITOR = 10
    BATTLE_WIDE = 11
    COMMANDER = 12
    GLOBAL_EFFECTS = 13
    BOAT = 14
    TOWN = 15


class BonusDuration(IntEnum):
    """Duration of bonus (bitflags)"""
    PERMANENT = 1 << 0
    ONE_BATTLE = 1 << 1
    ONE_DAY = 1 << 2
    ONE_WEEK = 1 << 3
    N_TURNS = 1 << 4
    N_DAYS = 1 << 5
    UNTIL_BEING_ATTACKED = 1 << 6
    UNTIL_ATTACK = 1 << 7
    STACK_GETS_TURN = 1 << 8
    COMMANDER_KILLED = 1 << 9
    UNTIL_OWN_ATTACK = 1 << 10


class BonusSource(IntEnum):
    """Source of bonus"""
    ARTIFACT = 0
    ARTIFACT_INSTANCE = 1
    OBJECT_TYPE = 2
    OBJECT_INSTANCE = 3
    CREATURE_ABILITY = 4
    TERRAIN_NATIVE = 5
    TERRAIN_OVERLAY = 6
    SPELL_EFFECT = 7
    TOWN_STRUCTURE = 8
    HERO_BASE_SKILL = 9
    SECONDARY_SKILL = 10
    HERO_SPECIAL = 11
    ARMY = 12
    CAMPAIGN_BONUS = 13
    STACK_EXPERIENCE = 14
    COMMANDER = 15
    GLOBAL = 16
    OTHER = 17


class BonusValueType(IntEnum):
    """Type of bonus value"""
    ADDITIVE_VALUE = 0
    BASE_NUMBER = 1
    PERCENT_TO_ALL = 2
    PERCENT_TO_BASE = 3
    PERCENT_TO_SOURCE = 4
    PERCENT_TO_TARGET_TYPE = 5
    INDEPENDENT_MAX = 6
    INDEPENDENT_MIN = 7


class BonusLimitEffect(IntEnum):
    """Limit effect for bonus"""
    NO_LIMIT = 0
    ONLY_DISTANCE_FIGHT = 1
    ONLY_MELEE_FIGHT = 2


class BattleUnitTurnReason(IntEnum):
    """Reason for battle unit turn"""
    TURN_QUEUE = 0
    MORALE = 1
    HERO_SPELLCAST = 2
    UNIT_SPELLCAST = 3
    AUTOMATIC_ACTION = 4


class EAlignment(IntEnum):
    """Alignment"""
    ANY = -1
    GOOD = 0
    EVIL = 1
    NEUTRAL = 2


class IPropagator(Serializeable):
    """Base class for bonus propagators"""

    def __init__(self):
        pass


@Serializeable.register_type(60)
class CPropagatorNodeType(IPropagator):
    """Propagator that specifies a node type"""

    def __init__(self):
        super().__init__()
        self.nodeType = BonusNodeType.UNKNOWN

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize CPropagatorNodeType"""
        # Load node type (BonusNodeType enum)
        self.nodeType = BonusNodeType(deserializer.load_integer())

    def __repr__(self):
        return f"CPropagatorNodeType(nodeType={self.nodeType})"


# ============================================================================
# Updater Classes
# ============================================================================

class IUpdater(Serializeable):
    """Base class for bonus updaters"""

    def __init__(self):
        pass


@Serializeable.register_type(43)
class GrowsWithLevelUpdater(IUpdater):
    """Updater that grows bonus value with hero level"""

    def __init__(self):
        super().__init__()
        self.valPer20 = 0
        self.stepSize = 1

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize GrowsWithLevelUpdater"""
        self.valPer20 = deserializer.load_integer()
        self.stepSize = deserializer.load_integer()

    def __repr__(self):
        return f"GrowsWithLevelUpdater(valPer20={self.valPer20}, stepSize={self.stepSize})"


@Serializeable.register_type(44)
class TimesHeroLevelUpdater(IUpdater):
    """Updater that multiplies bonus by hero level"""

    def __init__(self):
        super().__init__()
        self.stepSize = 1

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize TimesHeroLevelUpdater"""
        # Always load stepSize in current version
        self.stepSize = deserializer.load_integer()

    def __repr__(self):
        return f"TimesHeroLevelUpdater(stepSize={self.stepSize})"


@Serializeable.register_type(45)
class TimesStackLevelUpdater(IUpdater):
    """Updater that multiplies bonus by stack level"""

    def __init__(self):
        super().__init__()

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize TimesStackLevelUpdater"""
        pass  # No additional fields

    def __repr__(self):
        return "TimesStackLevelUpdater()"


@Serializeable.register_type(46)
class OwnerUpdater(IUpdater):
    """Updater for owner-based bonuses"""

    def __init__(self):
        super().__init__()

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize OwnerUpdater"""
        pass  # No additional fields

    def __repr__(self):
        return "OwnerUpdater()"


@Serializeable.register_type(245)
class TimesHeroLevelDivideStackLevelUpdater(IUpdater):
    """Updater that multiplies by hero level and divides by stack level"""

    def __init__(self):
        super().__init__()
        self.stepSize = 1
        self.divideStackLevel = None

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize TimesHeroLevelDivideStackLevelUpdater"""
        # Always load stepSize in current version
        self.stepSize = deserializer.load_integer()
        # Then deserialize the nested DivideStackLevelUpdater
        self.divideStackLevel = deserializer.load_pointer(IUpdater)

    def __repr__(self):
        return f"TimesHeroLevelDivideStackLevelUpdater(stepSize={self.stepSize})"


@Serializeable.register_type(246)
class DivideStackLevelUpdater(IUpdater):
    """Updater that divides bonus by stack level"""

    def __init__(self):
        super().__init__()

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize DivideStackLevelUpdater"""
        pass  # No additional fields

    def __repr__(self):
        return "DivideStackLevelUpdater()"


@Serializeable.register_type(249)
class TimesStackSizeUpdater(IUpdater):
    """Updater that multiplies bonus by stack size"""

    def __init__(self):
        super().__init__()
        self.minimum = 0
        self.maximum = 0
        self.stepSize = 1

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize TimesStackSizeUpdater"""
        self.minimum = deserializer.load_integer()
        self.maximum = deserializer.load_integer()
        self.stepSize = deserializer.load_integer()

    def __repr__(self):
        return f"TimesStackSizeUpdater(min={self.minimum}, max={self.maximum}, stepSize={self.stepSize})"


@Serializeable.register_type(250)
class TimesArmySizeUpdater(IUpdater):
    """Updater that multiplies bonus by army size"""

    def __init__(self):
        super().__init__()
        self.minimum = 0
        self.maximum = 0
        self.stepSize = 1
        self.filteredLevel = -1
        self.filteredCreature = 0
        self.filteredFaction = 0

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize TimesArmySizeUpdater"""
        self.minimum = deserializer.load_integer()
        self.maximum = deserializer.load_integer()
        self.stepSize = deserializer.load_integer()
        self.filteredLevel = deserializer.load_integer()
        self.filteredCreature = deserializer.load_integer()  # CreatureID
        self.filteredFaction = deserializer.load_integer()  # FactionID

    def __repr__(self):
        return f"TimesArmySizeUpdater(min={self.minimum}, max={self.maximum}, stepSize={self.stepSize}, filteredLevel={self.filteredLevel})"


# ============================================================================
# Core Type Enums
# ============================================================================

class BattleSide(IntEnum):
    """Side in battle (attacker/defender)"""
    NONE = -1
    ATTACKER = 0
    DEFENDER = 1


# ============================================================================
# Identifier Classes for Variant Types
# ============================================================================

class BonusCustomSubtype:
    """Bonus custom subtype identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"BonusCustomSubtype({self.value})"

    def __repr__(self):
        return self.to_string()


class SpellID:
    """Spell identifier"""
    NONE = -1

    def __init__(self, value: int = -1):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"SpellID({self.value})"

    def __repr__(self):
        return self.to_string()


class CreatureID:
    """Creature identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"CreatureID({self.value})"

    def __repr__(self):
        return self.to_string()


class PrimarySkill:
    """Primary skill identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"PrimarySkill({self.value})"

    def __repr__(self):
        return self.to_string()


class TerrainId:
    """Terrain type identifier - flexible wrapper to handle any value"""
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

    def to_int(self) -> int:
        return self.value

    def __int__(self):
        return self.value

    def to_string(self) -> str:
        return f"TerrainId({self.value})"

    def __repr__(self):
        return self.to_string()


class GameResID:
    """Game resource identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"GameResID({self.value})"

    def __repr__(self):
        return self.to_string()


class SpellSchool:
    """Spell school identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"SpellSchool({self.value})"

    def __repr__(self):
        return self.to_string()


class BonusTypeID:
    """Bonus type identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"BonusTypeID({self.value})"

    def __repr__(self):
        return self.to_string()


class BonusCustomSource:
    """Bonus custom source identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"BonusCustomSource({self.value})"

    def __repr__(self):
        return self.to_string()


class ArtifactID:
    """Artifact identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"ArtifactID({self.value})"

    def __repr__(self):
        return self.to_string()


class CampaignScenarioID:
    """Campaign scenario identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"CampaignScenarioID({self.value})"

    def __repr__(self):
        return self.to_string()


class SecondarySkill:
    """Secondary skill identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"SecondarySkill({self.value})"

    def __repr__(self):
        return self.to_string()


class HeroTypeID:
    """Hero type identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"HeroTypeID({self.value})"

    def __repr__(self):
        return self.to_string()


class Obj:
    """Object identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"Obj({self.value})"

    def __repr__(self):
        return self.to_string()


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

    def to_string(self) -> str:
        return f"ObjectInstanceID({self.value})"

    def __repr__(self):
        return self.to_string()


class BuildingTypeUniqueID:
    """Building type unique identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"BuildingTypeUniqueID({self.value})"

    def __repr__(self):
        return self.to_string()


class BattleField:
    """Battle field identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"BattleField({self.value})"

    def __repr__(self):
        return self.to_string()


class ArtifactInstanceID:
    """Artifact instance identifier"""
    def __init__(self, value: int = 0):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"ArtifactInstanceID({self.value})"

    def __repr__(self):
        return self.to_string()


# ============================================================================
# Core Type Enums (Module-level exports)
# ============================================================================

class EMessage(IntEnum):
    """MetaString message types"""
    APPEND_RAW_STRING = 0
    APPEND_LOCAL_STRING = 1
    APPEND_TEXTID_STRING = 2
    APPEND_NUMBER = 3
    REPLACE_RAW_STRING = 4
    REPLACE_LOCAL_STRING = 5
    REPLACE_TEXTID_STRING = 6
    REPLACE_NUMBER = 7
    REPLACE_POSITIVE_NUMBER = 8
    APPEND_EOL = 9


class EMetaText(IntEnum):
    """MetaString text types for localization"""
    GENERAL_TXT = 0
    ARRAY_TXT = 1
    ADVOB_TXT = 2
    JK_TXT = 3


# ============================================================================
# Player Color Class
# ============================================================================

class PlayerColor:
    """Player colors"""
    NEUTRAL = 255
    CANNOT_DETERMINE = 254

    def __init__(self, value: int = 255):
        self.value = value

    def to_int(self) -> int:
        return self.value

    def to_string(self) -> str:
        return f"PlayerColor({self.value})"

    def __eq__(self, other):
        if isinstance(other, PlayerColor):
            return self.value == other.value
        return False

    def __repr__(self):
        return self.to_string()


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


# ============================================================================
# MetaString Implementation
# ============================================================================

@dataclass
class MetaString(Serializeable):
    """String formatting class that supports transfer over network with localization"""

    exact_strings: List[str] = field(default_factory=list)
    local_strings: List[tuple] = field(default_factory=list)  # (EMetaText, ui32)
    strings_text_id: List[str] = field(default_factory=list)
    message: List[int] = field(default_factory=list)  # EMessage
    numbers: List[int] = field(default_factory=list)

    def serialize(self, deserializer: BinaryDeserializer):
        """Deserialize MetaString from binary format"""
        # Serialize exact strings (vector of strings)
        exact_strings_count = deserializer.load_integer()
        self.exact_strings = [deserializer.load_string() for _ in range(exact_strings_count)]

        # Serialize local strings (vector of pairs<EMetaText, ui32>)
        local_strings_count = deserializer.load_integer()
        self.local_strings = []
        for _ in range(local_strings_count):
            meta_text_int = deserializer.load_integer()
            ui32_value = deserializer.load_integer()
            self.local_strings.append((EMetaText(meta_text_int), ui32_value))

        # Serialize strings text ID (vector of strings)
        strings_text_id_count = deserializer.load_integer()
        self.strings_text_id = [deserializer.load_string() for _ in range(strings_text_id_count)]

        # Serialize messages (vector of EMessage)
        message_count = deserializer.load_integer()
        self.message = [deserializer.load_integer() for _ in range(message_count)]

        # Serialize numbers (vector of int64_t)
        numbers_count = deserializer.load_integer()
        self.numbers = [deserializer.load_integer() for _ in range(numbers_count)]

    def to_string(self) -> str:
        """Convert MetaString to user-readable string"""
        result = []
        exact_index = 0
        local_index = 0
        text_id_index = 0
        number_index = 0

        for msg in self.message:
            if msg == EMessage.APPEND_RAW_STRING:
                if exact_index < len(self.exact_strings):
                    result.append(self.exact_strings[exact_index])
                    exact_index += 1
            elif msg == EMessage.APPEND_LOCAL_STRING:
                if local_index < len(self.local_strings):
                    meta_text, ui32_value = self.local_strings[local_index]
                    # Simple translation - would need to call text library
                    result.append(f"<localized:{meta_text.value}:{ui32_value}>")
                    local_index += 1
            elif msg == EMessage.APPEND_TEXTID_STRING:
                if text_id_index < len(self.strings_text_id):
                    result.append(self.strings_text_id[text_id_index])
                    text_id_index += 1
            elif msg == EMessage.APPEND_NUMBER:
                if number_index < len(self.numbers):
                    result.append(str(self.numbers[number_index]))
                    number_index += 1
            elif msg == EMessage.APPEND_EOL:
                result.append('\n')
            elif msg == EMessage.REPLACE_RAW_STRING:
                # Replace first '%s' with exact string
                if exact_index < len(self.exact_strings):
                    replacement = self.exact_strings[exact_index]
                    for i in range(len(result)):
                        if '%s' in result[i]:
                            result[i] = result[i].replace('%s', replacement, 1)
                    exact_index += 1
            elif msg == EMessage.REPLACE_LOCAL_STRING:
                # Replace first '%s' with localized string
                if local_index < len(self.local_strings):
                    meta_text, ui32_value = self.local_strings[local_index]
                    replacement = f"<localized:{meta_text.value}:{ui32_value}>"
                    for i in range(len(result)):
                        if '%s' in result[i]:
                            result[i] = result[i].replace('%s', replacement, 1)
                    local_index += 1
            elif msg == EMessage.REPLACE_TEXTID_STRING:
                # Replace first '%s' with text ID
                if text_id_index < len(self.strings_text_id):
                    replacement = self.strings_text_id[text_id_index]
                    for i in range(len(result)):
                        if '%s' in result[i]:
                            result[i] = result[i].replace('%s', replacement, 1)
                    text_id_index += 1
            elif msg == EMessage.REPLACE_NUMBER:
                # Replace first '%d' with number
                if number_index < len(self.numbers):
                    replacement = str(self.numbers[number_index])
                    for i in range(len(result)):
                        if '%d' in result[i]:
                            result[i] = result[i].replace('%d', replacement, 1)
                            break  # Only replace the first occurrence
                    number_index += 1
            elif msg == EMessage.REPLACE_POSITIVE_NUMBER:
                # Replace first '%+d' with number (with + prefix for positive values)
                if number_index < len(self.numbers):
                    value = self.numbers[number_index]
                    replacement = ('+' if value > 0 else '') + str(value)
                    for i in range(len(result)):
                        if '%+d' in result[i]:
                            result[i] = result[i].replace('%+d', replacement, 1)
                    number_index += 1

        return ''.join(result)

    def empty(self) -> bool:
        """Returns true if current string is empty"""
        return len(self.message) == 0 and len(self.exact_strings) == 0

    def __repr__(self):
        return f"MetaString({self.to_string()})"


class BattleFieldType(IntEnum):
    """Battlefield types"""
    NONE = 0
    SANDBOX = 1


class SlotID(IntEnum):
    """Army slot identifiers"""
    COMMANDER_SLOT_PLACEHOLDER = -2


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

    def __repr__(self):
        return f"BattleID({self.value})"


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
    subtype: object = None  # Will be one of: BonusCustomSubtype, SpellID, CreatureID, PrimarySkill, TerrainId, GameResID, SpellSchool, BonusTypeID
    val: int = 0
    val_type: BonusValueType = BonusValueType.ADDITIVE_VALUE
    duration: BonusDuration = BonusDuration.PERMANENT
    source: BonusSource = BonusSource.OTHER
    sid: object = None  # Will be one of: BonusCustomSource, SpellID, CreatureID, ArtifactID, CampaignScenarioID, SecondarySkill, HeroTypeID, Obj, ObjectInstanceID, BuildingTypeUniqueID, BattleField, ArtifactInstanceID
    description: MetaString = field(default_factory=MetaString)
    custom_icon_path: ImagePath = field(default_factory=ImagePath)
    hidden: bool = False
    additional_info: List[int] = field(default_factory=list)
    turnsRemain: int = 0
    stacking: str = field(default_factory=str)
    effect_range: BonusLimitEffect = BonusLimitEffect.NO_LIMIT
    limiter: Limiter = field(default_factory=Limiter)
    propagator: IPropagator = field(default_factory=IPropagator)
    updater: IUpdater = field(default_factory=IUpdater)
    propagationUpdater: IUpdater = field(default_factory=IUpdater)
    target_source_type: BonusSource = BonusSource.OTHER

    def serialize(self, deserializer: BinaryDeserializer):
        # Complete bonus deserialization matching C++ implementation
        self.duration = BonusDuration(deserializer.load_integer())  # BonusDuration::Type (2 bytes)
        self.type = deserializer.load_integer()      # BonusType (2 bytes, but loaded as integer)

        # Load BonusSubtypeID as VariantIdentifier
        # VariantIdentifier<BonusCustomSubtype, SpellID, CreatureID, PrimarySkill, TerrainId, GameResID, SpellSchool, BonusTypeID>
        subtype_variant_types = [
            BonusCustomSubtype,
            SpellID,
            CreatureID,
            PrimarySkill,
            TerrainId,
            GameResID,
            SpellSchool,
            BonusTypeID
        ]
        self.subtype = deserializer.load_variant(subtype_variant_types)

        self.source = BonusSource(deserializer.load_integer())    # BonusSource (1 byte)
        self.val = deserializer.load_integer()       # si32 (4 bytes)

        # Load BonusSourceID as VariantIdentifier
        # VariantIdentifier<BonusCustomSource, SpellID, CreatureID, ArtifactID, CampaignScenarioID, SecondarySkill, HeroTypeID, Obj, ObjectInstanceID, BuildingTypeUniqueID, BattleField, ArtifactInstanceID>
        source_variant_types = [
            BonusCustomSource,
            SpellID,
            CreatureID,
            ArtifactID,
            CampaignScenarioID,
            SecondarySkill,
            HeroTypeID,
            Obj,
            ObjectInstanceID,
            BuildingTypeUniqueID,
            BattleField,
            ArtifactInstanceID
        ]
        self.sid = deserializer.load_variant(source_variant_types)

        # Load description (MetaString) - complex string with localization support
        self.description = MetaString()
        self.description.serialize(deserializer)

        # Load customIconPath (ImagePath) - conditional field based on version
        if deserializer.version >= SerializationVersion.CUSTOM_BONUS_ICONS:
            self.custom_icon_path = ImagePath()
            self.custom_icon_path.serialize(deserializer)
        else:
            self.custom_icon_path = ImagePath()  # Default empty ImagePath

        # Load hidden (bool) - conditional field based on version
        if deserializer.version >= SerializationVersion.BONUS_HIDDEN:
            self.hidden = deserializer.load_bool()
        else:
            self.hidden = False

        # Load additional_info (CAddInfo - vector of si32)
        self.additional_info = deserializer.load_vector(int)
        
        self.turnsRemain = deserializer.load_integer()  # si16 (2 bytes, but loaded as integer)
        self.val_type = BonusValueType(deserializer.load_integer())      # BonusValueType (1 byte)
        self.stacking = deserializer.load_string()  # String
        self.effect_range = BonusLimitEffect(deserializer.load_integer())  # BonusLimitEffect (1 byte)

        # Load limiter (TLimiterPtr) - polymorphic pointer type
        self.limiter = deserializer.load_pointer(Limiter)
        if self.limiter is not None:
            logger.debug(f"Bonus.serialize: bonus type={self.type}, limiter type={type(self.limiter).__name__}, value={self.limiter}")

        # Load propagator (TPropagatorPtr) - polymorphic pointer type
        self.propagator = deserializer.load_pointer(IPropagator)
        if self.propagator is not None:
            logger.debug(f"Bonus.serialize: bonus type={self.type}, propagator type={type(self.propagator).__name__}, value={self.propagator}")

        # Load updater (TUpdaterPtr) - polymorphic pointer type
        self.updater = deserializer.load_pointer(IUpdater)
        if self.updater is not None:
            logger.debug(f"Bonus.serialize: bonus type={self.type}, updater type={type(self.updater).__name__}, value={self.updater}")

        # Load propagationUpdater (TUpdaterPtr) - polymorphic pointer type
        self.propagationUpdater = deserializer.load_pointer(IUpdater)
        if self.propagationUpdater is not None:
            logger.debug(f"Bonus.serialize: bonus type={self.type}, propagationUpdater type={type(self.propagationUpdater).__name__}, value={self.propagationUpdater}")

        self.target_source_type = BonusSource(deserializer.load_integer())  # BonusSource (1 byte)


@dataclass
class BonusList(Serializeable):
    """List of bonus effects"""
    bonuses: List[Bonus] = field(default_factory=list)

    def serialize(self, deserializer: BinaryDeserializer):
        # Load vector of bonuses manually (Bonus is not polymorphic)
        length = deserializer.load_integer()
        self.bonuses = []
        for _ in range(length):
            bonus = deserializer.load_pointer(Bonus)
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
    node_type: BonusNodeType = BonusNodeType.UNKNOWN
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
            self.node_type = BonusNodeType(deserializer.load_integer())
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
        self.info = deserializer.load_pointer(BattleInfo)
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
    reason: BattleUnitTurnReason = BattleUnitTurnReason.TURN_QUEUE

    def serialize(self, deserializer: BinaryDeserializer):
        self.battle_id = BattleID(deserializer.load_integer())
        self.stack = deserializer.load_integer()
        self.reason = BattleUnitTurnReason(deserializer.load_integer())


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
