"""
VCMI Data Type Definitions

This module defines Python classes corresponding to VCMI game data structures
used in network communication. All serialize() methods are bidirectional -
they work with both BinaryDeserializer (reading) and BinarySerializer (writing).
"""

from typing import List, Optional, Set, Dict
from dataclasses import dataclass, field
from enum import IntEnum
from serializer import (
    Serializeable, BinaryDeserializer, BinarySerializer,
    pack, SerializationVersion,
)
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

    def serialize(self, h):
        self.type = h.integer(self.type)
        self.name = h.string(self.name)
        self.originalName = h.string(self.originalName)

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

    def serialize(self, h):
        pass  # Base limiter has no fields

    def __repr__(self):
        return f"{self.__class__.__name__}()"


@Serializeable.register_type(49)
class AnyOfLimiter(Limiter):
    """Requires at least one of the child limiters to be true"""

    def __init__(self):
        super().__init__()
        self.limiters = []

    def serialize(self, h):
        self.limiters = h.vector(self.limiters, Limiter)

    def __repr__(self):
        return f"AnyOfLimiter({len(self.limiters)} children)"


@Serializeable.register_type(50)
class NoneOfLimiter(Limiter):
    """Requires none of the child limiters to be true"""

    def __init__(self):
        super().__init__()
        self.limiters = []

    def serialize(self, h):
        self.limiters = h.vector(self.limiters, Limiter)

    def __repr__(self):
        return f"NoneOfLimiter({len(self.limiters)} children)"


@Serializeable.register_type(51)
class OppositeSideLimiter(Limiter):
    """Applies only to creatures of enemy army during combat"""

    def __init__(self):
        super().__init__()
        self.owner = None

    def serialize(self, h):
        if h.version < SerializationVersion.OPPOSITE_SIDE_LIMITER_OWNER:
            self.owner = h.integer(self.owner if self.owner is not None else 0)

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

    def serialize(self, h):
        self.limiters = h.vector(self.limiters, Limiter)

    def __repr__(self):
        return f"AllOfLimiter({len(self.limiters)} children)"


@Serializeable.register_type(62)
class CCreatureTypeLimiter(Limiter):
    """Applies only to stacks of given creature type (and optionally its upgrades)"""

    def __init__(self):
        super().__init__()
        self.creatureID = 0
        self.includeUpgrades = False

    def serialize(self, h):
        self.creatureID = h.integer(self.creatureID)
        self.includeUpgrades = h.bool_(self.includeUpgrades)

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

    def serialize(self, h):
        self.type = h.integer(self.type)
        self.subtype = h.integer(self.subtype)
        self.source = h.integer(self.source)
        self.sid = h.integer(self.sid)
        self.isSubtypeRelevant = h.bool_(self.isSubtypeRelevant)
        self.isSourceRelevant = h.bool_(self.isSourceRelevant)
        self.isSourceIDRelevant = h.bool_(self.isSourceIDRelevant)

    def __repr__(self):
        return f"HasAnotherBonusLimiter(type={self.type}, source={self.source})"


# ============================================================================
# Terrain / Faction ID helpers (bidirectional string <-> int conversion)
# ============================================================================

TERRAIN_JSON_KEY_TO_INDEX = {
    "dirt": 0, "sand": 1, "grass": 2, "snow": 3, "swamp": 4,
    "rough": 5, "subterra": 6, "lava": 7, "water": 8, "rock": 9,
}
TERRAIN_INDEX_TO_JSON_KEY = {v: k for k, v in TERRAIN_JSON_KEY_TO_INDEX.items()}

FACTION_JSON_KEY_TO_INDEX = {
    "castle": 0, "rampart": 1, "tower": 2, "inferno": 3,
    "necropolis": 4, "dungeon": 5, "stronghold": 6, "fortress": 7,
    "conflux": 8, "neutral": 9, "random": -1,
}
FACTION_INDEX_TO_JSON_KEY = {v: k for k, v in FACTION_JSON_KEY_TO_INDEX.items()}


def handle_terrain_id(h, value) -> int:
    """Bidirectional terrain ID: string on wire, int in Python."""
    if h.is_writing:
        if value == -1:
            h.string("")
        elif value == -4:
            h.string("native")
        else:
            h.string(TERRAIN_INDEX_TO_JSON_KEY.get(value, ""))
        return value
    else:
        terrain_str = h.string("")
        if terrain_str == "":
            return -1
        elif terrain_str == "native":
            return -4
        return TERRAIN_JSON_KEY_TO_INDEX.get(terrain_str, -1)


def handle_faction_id(h, value) -> int:
    """Bidirectional faction ID: string on wire, int in Python."""
    if h.is_writing:
        h.string(FACTION_INDEX_TO_JSON_KEY.get(value, ""))
        return value
    else:
        faction_str = h.string("")
        return FACTION_JSON_KEY_TO_INDEX.get(faction_str, -1)


# Keep old names for backward compatibility
def deserialize_terrain_id(deserializer):
    return handle_terrain_id(deserializer, 0)

def deserialize_faction_id(deserializer):
    return handle_faction_id(deserializer, 0)


@Serializeable.register_type(64)
class TerrainLimiter(Limiter):
    """Applies only to creatures that are on specified terrain"""

    def __init__(self):
        super().__init__()
        self.terrainType = 0

    def serialize(self, h):
        self.terrainType = handle_terrain_id(h, self.terrainType)

    def __repr__(self):
        return f"TerrainLimiter(terrainType={self.terrainType})"


@Serializeable.register_type(65)
class FactionLimiter(Limiter):
    """Applies only to creatures of given faction"""

    def __init__(self):
        super().__init__()
        self.faction = 0

    def serialize(self, h):
        self.faction = handle_faction_id(h, self.faction)

    def __repr__(self):
        return f"FactionLimiter(faction={self.faction})"


@Serializeable.register_type(66)
class CCreatureLevelLimiter(Limiter):
    """Applies only to creatures of given level range"""

    def __init__(self):
        super().__init__()
        self.minLevel = 0
        self.maxLevel = 0

    def serialize(self, h):
        self.minLevel = h.integer(self.minLevel)
        self.maxLevel = h.integer(self.maxLevel)

    def __repr__(self):
        return f"CCreatureLevelLimiter(min={self.minLevel}, max={self.maxLevel})"


@Serializeable.register_type(67)
class CCreatureAlignmentLimiter(Limiter):
    """Applies only to creatures of given alignment"""

    def __init__(self):
        super().__init__()
        self.alignment = EAlignment.ANY

    def serialize(self, h):
        self.alignment = EAlignment(h.integer(int(self.alignment)))

    def __repr__(self):
        return f"CCreatureAlignmentLimiter(alignment={self.alignment})"


@Serializeable.register_type(68)
class RankRangeLimiter(Limiter):
    """Applies to creatures with min <= Rank <= max"""

    def __init__(self):
        super().__init__()
        self.minRank = 0
        self.maxRank = 0

    def serialize(self, h):
        self.minRank = h.integer(self.minRank)
        self.maxRank = h.integer(self.maxRank)

    def __repr__(self):
        return f"RankRangeLimiter(min={self.minRank}, max={self.maxRank})"


@Serializeable.register_type(69)
class UnitOnHexLimiter(Limiter):
    """Works only on selected hexes"""

    def __init__(self):
        super().__init__()
        self.applicableHexes = []

    def serialize(self, h):
        self.applicableHexes = h.vector(self.applicableHexes, int)

    def __repr__(self):
        return f"UnitOnHexLimiter({len(self.applicableHexes)} hexes)"


@Serializeable.register_type(55)
class HasChargesLimiter(Limiter):
    """Works with bonuses that consume charges"""

    def __init__(self):
        super().__init__()
        self.chargeCost = 1

    def serialize(self, h):
        self.chargeCost = h.integer(self.chargeCost)

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

    def serialize(self, h):
        self.nodeType = BonusNodeType(h.integer(int(self.nodeType)))

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

    def serialize(self, h):
        self.valPer20 = h.integer(self.valPer20)
        self.stepSize = h.integer(self.stepSize)

    def __repr__(self):
        return f"GrowsWithLevelUpdater(valPer20={self.valPer20}, stepSize={self.stepSize})"


@Serializeable.register_type(44)
class TimesHeroLevelUpdater(IUpdater):
    """Updater that multiplies bonus by hero level"""

    def __init__(self):
        super().__init__()
        self.stepSize = 1

    def serialize(self, h):
        self.stepSize = h.integer(self.stepSize)

    def __repr__(self):
        return f"TimesHeroLevelUpdater(stepSize={self.stepSize})"


@Serializeable.register_type(45)
class TimesStackLevelUpdater(IUpdater):
    """Updater that multiplies bonus by stack level"""

    def __init__(self):
        super().__init__()

    def serialize(self, h):
        pass

    def __repr__(self):
        return "TimesStackLevelUpdater()"


@Serializeable.register_type(46)
class OwnerUpdater(IUpdater):
    """Updater for owner-based bonuses"""

    def __init__(self):
        super().__init__()

    def serialize(self, h):
        pass

    def __repr__(self):
        return "OwnerUpdater()"


@Serializeable.register_type(245)
class TimesHeroLevelDivideStackLevelUpdater(IUpdater):
    """Updater that multiplies by hero level and divides by stack level"""

    def __init__(self):
        super().__init__()
        self.stepSize = 1
        self.divideStackLevel = None

    def serialize(self, h):
        self.stepSize = h.integer(self.stepSize)
        self.divideStackLevel = h.pointer(self.divideStackLevel, IUpdater)

    def __repr__(self):
        return f"TimesHeroLevelDivideStackLevelUpdater(stepSize={self.stepSize})"


@Serializeable.register_type(246)
class DivideStackLevelUpdater(IUpdater):
    """Updater that divides bonus by stack level"""

    def __init__(self):
        super().__init__()

    def serialize(self, h):
        pass

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

    def serialize(self, h):
        self.minimum = h.integer(self.minimum)
        self.maximum = h.integer(self.maximum)
        self.stepSize = h.integer(self.stepSize)

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

    def serialize(self, h):
        self.minimum = h.integer(self.minimum)
        self.maximum = h.integer(self.maximum)
        self.stepSize = h.integer(self.stepSize)
        self.filteredLevel = h.integer(self.filteredLevel)
        self.filteredCreature = h.integer(self.filteredCreature)
        self.filteredFaction = h.integer(self.filteredFaction)

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
    """Terrain type identifier"""
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
    local_strings: List[tuple] = field(default_factory=list)
    strings_text_id: List[str] = field(default_factory=list)
    message: List[int] = field(default_factory=list)
    numbers: List[int] = field(default_factory=list)

    def serialize(self, h):
        self.exact_strings = h.vector(self.exact_strings, str)

        # local_strings: vector of (EMetaText, ui32) pairs
        if h.is_reading:
            count = h.integer()
            self.local_strings = []
            for _ in range(count):
                meta_text_int = h.integer()
                ui32_value = h.integer()
                self.local_strings.append((EMetaText(meta_text_int), ui32_value))
        else:
            h.integer(len(self.local_strings))
            for meta_text, ui32_value in self.local_strings:
                h.integer(int(meta_text))
                h.integer(ui32_value)

        self.strings_text_id = h.vector(self.strings_text_id, str)
        self.message = h.vector(self.message, int)
        self.numbers = h.vector(self.numbers, int)

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
                if exact_index < len(self.exact_strings):
                    replacement = self.exact_strings[exact_index]
                    for i in range(len(result)):
                        if '%s' in result[i]:
                            result[i] = result[i].replace('%s', replacement, 1)
                    exact_index += 1
            elif msg == EMessage.REPLACE_LOCAL_STRING:
                if local_index < len(self.local_strings):
                    meta_text, ui32_value = self.local_strings[local_index]
                    replacement = f"<localized:{meta_text.value}:{ui32_value}>"
                    for i in range(len(result)):
                        if '%s' in result[i]:
                            result[i] = result[i].replace('%s', replacement, 1)
                    local_index += 1
            elif msg == EMessage.REPLACE_TEXTID_STRING:
                if text_id_index < len(self.strings_text_id):
                    replacement = self.strings_text_id[text_id_index]
                    for i in range(len(result)):
                        if '%s' in result[i]:
                            result[i] = result[i].replace('%s', replacement, 1)
                    text_id_index += 1
            elif msg == EMessage.REPLACE_NUMBER:
                if number_index < len(self.numbers):
                    replacement = str(self.numbers[number_index])
                    for i in range(len(result)):
                        if '%d' in result[i]:
                            result[i] = result[i].replace('%d', replacement, 1)
                            break
                    number_index += 1
            elif msg == EMessage.REPLACE_POSITIVE_NUMBER:
                if number_index < len(self.numbers):
                    value = self.numbers[number_index]
                    replacement = ('+' if value > 0 else '') + str(value)
                    for i in range(len(result)):
                        if '%+d' in result[i]:
                            result[i] = result[i].replace('%+d', replacement, 1)
                    number_index += 1

        return ''.join(result)

    def empty(self) -> bool:
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

    def serialize(self, h):
        self.x = h.integer(self.x)
        self.y = h.integer(self.y)
        self.z = h.integer(self.z)


@dataclass
class BattleHex:
    """Battle field hex position"""
    def __init__(self):
        self.hex: int = 0

    def serialize(self, h):
        self.hex = h.integer(self.hex)


@dataclass
class BattleHexArray:
    """Array of battle hex positions"""
    def __init__(self):
        self.hexes: List[int] = []

    def serialize(self, h):
        self.hexes = h.vector(self.hexes, int)


# ============================================================================
# Bonus subtype/sid variant type lists (shared between serialize methods)
# ============================================================================

BONUS_SUBTYPE_VARIANT_TYPES = [
    BonusCustomSubtype, SpellID, CreatureID, PrimarySkill,
    TerrainId, GameResID, SpellSchool, BonusTypeID,
]

BONUS_SOURCE_VARIANT_TYPES = [
    BonusCustomSource, SpellID, CreatureID, ArtifactID,
    CampaignScenarioID, SecondarySkill, HeroTypeID, Obj,
    ObjectInstanceID, BuildingTypeUniqueID, BattleField, ArtifactInstanceID,
]


@dataclass
class Bonus(Serializeable):
    """Bonus effect on an object"""
    type: int = 0
    subtype: object = None
    val: int = 0
    val_type: BonusValueType = BonusValueType.ADDITIVE_VALUE
    duration: BonusDuration = BonusDuration.PERMANENT
    source: BonusSource = BonusSource.OTHER
    sid: object = None
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

    def serialize(self, h):
        self.duration = BonusDuration(h.integer(int(self.duration)))
        self.type = h.integer(self.type)
        self.subtype = h.variant(self.subtype, BONUS_SUBTYPE_VARIANT_TYPES)
        self.source = BonusSource(h.integer(int(self.source)))
        self.val = h.integer(self.val)
        self.sid = h.variant(self.sid, BONUS_SOURCE_VARIANT_TYPES)

        self.description = h.object_(self.description, MetaString)

        if h.version >= SerializationVersion.CUSTOM_BONUS_ICONS:
            self.custom_icon_path = h.object_(self.custom_icon_path, ImagePath)

        if h.version >= SerializationVersion.BONUS_HIDDEN:
            self.hidden = h.bool_(self.hidden)

        self.additional_info = h.vector(self.additional_info, int)
        self.turnsRemain = h.integer(self.turnsRemain)
        self.val_type = BonusValueType(h.integer(int(self.val_type)))
        self.stacking = h.string(self.stacking)
        self.effect_range = BonusLimitEffect(h.integer(int(self.effect_range)))

        self.limiter = h.pointer(self.limiter, Limiter)
        self.propagator = h.pointer(self.propagator, IPropagator)
        self.updater = h.pointer(self.updater, IUpdater)
        self.propagationUpdater = h.pointer(self.propagationUpdater, IUpdater)
        self.target_source_type = BonusSource(h.integer(int(self.target_source_type)))


@dataclass
class BonusList(Serializeable):
    """List of bonus effects"""
    bonuses: List[Bonus] = field(default_factory=list)

    def serialize(self, h):
        self.bonuses = h.vector(self.bonuses, Bonus)


# ============================================================================
# Battle-Related Structures
# ============================================================================

@dataclass
class SideInBattle(Serializeable):
    """Information about one side in battle"""
    cb: int = 0
    color: PlayerColor = field(default_factory=lambda: PlayerColor(255))
    hero_id: ObjectInstanceID = field(default_factory=lambda: ObjectInstanceID(-1))
    army_object_id: ObjectInstanceID = field(default_factory=lambda: ObjectInstanceID(-1))
    cast_spells_count: int = 0
    used_spells_history: List[int] = field(default_factory=list)
    enchanter_counter: int = 0
    initial_mana: int = 0
    additional_mana: int = 0

    def serialize(self, h):
        self.color = PlayerColor(h.integer(self.color.value))
        self.hero_id = ObjectInstanceID(h.integer(self.hero_id.value))
        self.army_object_id = ObjectInstanceID(h.integer(self.army_object_id.value))
        self.cast_spells_count = h.integer(self.cast_spells_count)
        self.used_spells_history = h.vector(self.used_spells_history, int)
        self.enchanter_counter = h.integer(self.enchanter_counter)
        self.initial_mana = h.integer(self.initial_mana)
        self.additional_mana = h.integer(self.additional_mana)


@dataclass
class SiegeInfo(Serializeable):
    """Siege battle information"""
    wall_state: Dict[int, int] = field(default_factory=dict)
    gate_state: EGateState = EGateState.CLOSED

    def serialize(self, h):
        self.wall_state = h.map_(self.wall_state, int, int)
        self.gate_state = EGateState(h.integer(int(self.gate_state)))


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

    def serialize(self, h):
        self.id = h.integer(self.id)
        self.type_id = CreatureID(h.integer(self.type_id.value))
        self.count = h.integer(self.count)
        self.side = BattleSide(h.integer(int(self.side)))
        self.position = h.object_(self.position, BattleHex)
        self.first_hp_left = h.integer(self.first_hp_left)
        self.alive = h.bool_(self.alive)


@dataclass
class ObstacleChanges(Serializeable):
    """Changes to battlefield obstacles"""
    obstacle_id: int = 0
    obstacle_type: int = 0

    def serialize(self, h):
        self.obstacle_id = h.integer(self.obstacle_id)
        self.obstacle_type = h.integer(self.obstacle_type)


@dataclass
class UnitChanges(Serializeable):
    """Changes to battle units"""
    unit_id: int = 0
    count: int = 0
    hp_left: int = 0

    def serialize(self, h):
        self.unit_id = h.integer(self.unit_id)
        self.count = h.integer(self.count)
        self.hp_left = h.integer(self.hp_left)


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

    def serialize(self, h):
        self.id = ObjectInstanceID(h.integer(self.id.value))
        self.temp_owner = PlayerColor(h.integer(self.temp_owner.value if isinstance(self.temp_owner, PlayerColor) else self.temp_owner))
        self.name = h.string(self.name)
        self.level = h.integer(self.level)
        self.experience = h.integer(self.experience)


@dataclass
class CArmedInstance(Serializeable):
    """Armed instance (army)"""
    id: ObjectInstanceID = field(default_factory=lambda: ObjectInstanceID(0))

    def serialize(self, h):
        self.id = ObjectInstanceID(h.integer(self.id.value))


@dataclass
class CGTownInstance(Serializeable):
    """Town instance"""
    id: ObjectInstanceID = field(default_factory=lambda: ObjectInstanceID(0))
    name: str = ""

    def serialize(self, h):
        self.id = ObjectInstanceID(h.integer(self.id.value))
        self.name = h.string(self.name)


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
    battlefield_type: str = ""
    terrain_type: str = ""
    tactics_side: BattleSide = BattleSide.NONE
    tactic_distance: int = 0
    node_type: BonusNodeType = BonusNodeType.UNKNOWN
    exported_bonuses: BonusList = field(default_factory=BonusList)
    replay_allowed: bool = False

    def serialize(self, h):
        try:
            self.battle_id = BattleID(h.integer(self.battle_id.value))

            # Sides: fixed array of 2
            self.sides = h.fixed_array(self.sides, SideInBattle, 2)

            self.round = h.integer(self.round)
            self.active_stack = h.integer(self.active_stack)
            self.town_id = ObjectInstanceID(h.integer(self.town_id.value))
            self.tile = h.object_(self.tile, int3)

            # Stacks: vector of non-polymorphic unique_ptrs
            self.stacks = h.raw_ptr_vector(self.stacks, CStack)

            # Obstacles: vector of non-polymorphic shared_ptrs
            self.obstacles = h.shared_ptr_vector(self.obstacles, ObstacleChanges)

            self.siege_info = h.object_(self.siege_info, SiegeInfo)
            self.battlefield_type = h.string(self.battlefield_type)
            self.terrain_type = h.string(self.terrain_type)
            self.tactics_side = BattleSide(h.integer(int(self.tactics_side)))
            self.tactic_distance = h.integer(self.tactic_distance)

            # CBonusSystemNode fields
            self.node_type = BonusNodeType(h.integer(int(self.node_type)))
            self.exported_bonuses = h.object_(self.exported_bonuses, BonusList)

            self.replay_allowed = h.bool_(self.replay_allowed)

            # Debug: remaining bytes on read
            if h.is_reading:
                remaining = len(h.data) - h.position
                if remaining > 0:
                    logger.warning(
                        f"Remaining {remaining} bytes after BattleInfo deserialization"
                    )

        except Exception as e:
            logger.error(f"Error during BattleInfo serialization: {e}")
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


class CPackForServer(CPack):
    """Base class for packs sent to server"""

    def __init__(self):
        super().__init__()
        self.player: int = PlayerColor.NEUTRAL  # PlayerColor num (int32)
        self.request_id: int = 0  # uint32

    def serialize_base(self, h):
        """Serialize the CPackForServer base fields (player + requestID)"""
        self.player = h.integer(self.player)
        self.request_id = h.integer(self.request_id)


# ============================================================================
# Battle Action Types
# ============================================================================

class EActionType(IntEnum):
    """Battle action types matching C++ EActionType (int8_t)"""
    NO_ACTION = 0
    END_TACTIC_PHASE = 1
    RETREAT = 2
    SURRENDER = 3
    HERO_SPELL = 4
    WALK = 5
    WAIT = 6
    DEFEND = 7
    WALK_AND_ATTACK = 8
    SHOOT = 9
    CATAPULT = 10
    MONSTER_SPELL = 11
    BAD_MORALE = 12
    STACK_HEAL = 13


class DestinationInfo(Serializeable):
    """Target destination for a battle action"""

    def __init__(self):
        super().__init__()
        self.unit_value: int = -1  # int32_t, -1 = no unit
        self.hex_value: BattleHex = BattleHex()

    def serialize(self, h):
        self.unit_value = h.integer(self.unit_value)
        self.hex_value = h.object_(self.hex_value, BattleHex)


class BattleAction(Serializeable):
    """A battle action (defend, walk, attack, etc.)"""

    def __init__(self):
        super().__init__()
        self.side: BattleSide = BattleSide.ATTACKER
        self.stack_number: int = 0  # ui32
        self.action_type: EActionType = EActionType.NO_ACTION
        self.spell: str = ""  # SpellID serialized as string (EntityIdentifierWithEnum)
        self.target: List[DestinationInfo] = []

    def serialize(self, h):
        self.side = BattleSide(h.integer(int(self.side)))
        self.stack_number = h.integer(self.stack_number)
        self.action_type = EActionType(h.integer(int(self.action_type)))
        self.spell = h.string(self.spell)
        # target is std::vector<DestinationInfo> - inline objects
        length = h.integer(len(self.target))
        if h.is_reading:
            self.target = [h.object_(None, DestinationInfo) for _ in range(length)]
        else:
            for t in self.target:
                h.object_(t, DestinationInfo)

    @staticmethod
    def make_defend(stack_id: int, side: BattleSide = BattleSide.ATTACKER) -> 'BattleAction':
        """Create a defend action for the given stack"""
        action = BattleAction()
        action.side = side
        action.stack_number = stack_id
        action.action_type = EActionType.DEFEND
        return action

    @staticmethod
    def make_wait(stack_id: int, side: BattleSide = BattleSide.ATTACKER) -> 'BattleAction':
        """Create a wait action for the given stack"""
        action = BattleAction()
        action.side = side
        action.stack_number = stack_id
        action.action_type = EActionType.WAIT
        return action


@dataclass
class MakeAction(CPackForServer):
    """Pack wrapping a BattleAction, sent from Python to C++ (type ID 198)"""

    def __init__(self):
        super().__init__()
        self.ba: BattleAction = BattleAction()
        self.battle_id: BattleID = BattleID(0)

    def serialize(self, h):
        self.serialize_base(h)
        self.ba = h.object_(self.ba, BattleAction)
        self.battle_id = BattleID(h.integer(self.battle_id.value))


@dataclass
class BattleStart(CPackForClient):
    """Battle start notification pack"""
    battle_id: BattleID = field(default_factory=lambda: BattleID(0))
    info: Optional[BattleInfo] = None

    def serialize(self, h):
        self.battle_id = BattleID(h.integer(self.battle_id.value))
        self.info = h.pointer(self.info, BattleInfo)


@dataclass
class BattleNextRound(CPackForClient):
    """New battle round notification"""
    battle_id: BattleID = field(default_factory=lambda: BattleID(0))

    def serialize(self, h):
        self.battle_id = BattleID(h.integer(self.battle_id.value))


@dataclass
class BattleSetActiveStack(CPackForClient):
    """Notification about which stack should act"""
    battle_id: BattleID = field(default_factory=lambda: BattleID(0))
    stack: int = 0
    reason: BattleUnitTurnReason = BattleUnitTurnReason.TURN_QUEUE

    def serialize(self, h):
        self.battle_id = BattleID(h.integer(self.battle_id.value))
        self.stack = h.integer(self.stack)
        self.reason = BattleUnitTurnReason(h.integer(int(self.reason)))


# Register pack types
Serializeable.__registry__[77] = BattleInfo
Serializeable.__registry__[132] = BattleStart
Serializeable.__registry__[133] = BattleNextRound
Serializeable.__registry__[134] = BattleSetActiveStack
Serializeable.__registry__[198] = MakeAction

# Type ID registry for polymorphic deserialization
CPACK_TYPE_REGISTRY = {
    132: BattleStart,
    133: BattleNextRound,
    134: BattleSetActiveStack,
    198: MakeAction,
}


def create_pack_from_type_id(type_id: int) -> Optional[CPack]:
    """Create a pack instance from its type ID"""
    pack_class = CPACK_TYPE_REGISTRY.get(type_id)
    if pack_class:
        return pack_class()
    return None


# ============================================================================
# Pack Deserialization / Serialization
# ============================================================================

def deserialize_pack(data: bytes, loaded_strings: list = None) -> Optional[CPack]:
    """
    Deserialize a network pack from binary data.

    Args:
        data: Binary data to deserialize
        loaded_strings: Optional list of previously loaded strings for string interning.
                       The C++ serializer maintains string interning across multiple sends,
                       so this list must be preserved across calls for the same connection.

    Returns:
        The deserialized CPack object, or None if deserialization fails
    """
    if len(data) == 0:
        logger.info(f"Received heartbeat message")
        return None

    try:
        deserializer = BinaryDeserializer(data, version=SerializationVersion.CURRENT)

        # Restore string interning state from previous messages on this connection
        if loaded_strings is not None:
            deserializer._loaded_strings = loaded_strings

        # Load pack header: null check + pointer_id + type_id
        is_null = deserializer.load_bool()
        if is_null:
            logger.warning("Received null pack")
            return None

        pointer_id = deserializer.load_integer()
        type_id = deserializer.load_encoded_integer()

        # Create pack instance
        pack_obj = create_pack_from_type_id(type_id)
        if pack_obj is None:
            logger.warning(f"Unknown pack type ID: {type_id}")
            return None

        # Store metadata for round-trip serialization
        pack_obj._pack_pointer_id = pointer_id
        pack_obj._pack_type_id = type_id

        # Deserialize pack data
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


def deserialize_pack_with_strings(data: bytes, loaded_strings: list) -> Optional[CPack]:
    """Convenience wrapper that passes string interning state."""
    return deserialize_pack(data, loaded_strings)


def serialize_pack(pack_obj: CPack) -> bytes:
    """
    Serialize a network pack to binary data.

    Args:
        pack_obj: The CPack object to serialize

    Returns:
        The serialized binary data
    """
    serializer = BinarySerializer(version=SerializationVersion.CURRENT)

    # Write pack header: null check + pointer_id + type_id
    serializer.bool_(False)  # not null

    # Use stored metadata from deserialization if available
    pointer_id = getattr(pack_obj, '_pack_pointer_id', 0)
    type_id = getattr(pack_obj, '_pack_type_id', None)
    if type_id is None:
        # Look up type_id from registry
        for tid, cls in CPACK_TYPE_REGISTRY.items():
            if isinstance(pack_obj, cls):
                type_id = tid
                break
        if type_id is None:
            raise ValueError(f"Unknown pack type: {type(pack_obj).__name__}")

    serializer.integer(pointer_id)
    serializer.integer(type_id)

    # Account for the pack header pointer in the serializer's counter
    serializer._next_pointer_id = max(serializer._next_pointer_id, pointer_id + 1)

    # Serialize pack data
    pack_obj.serialize(serializer)

    return serializer.get_bytes()


if __name__ == "__main__":
    # Test deserialization
    from serializer import SerializationVersion

    # Example: Deserialize a BattleSetActiveStack pack
    test_data = bytes([
        0x00,  # Not null
        0x00, 0x00, 0x00, 0x00,  # Pointer ID = 0
        0x00, 0x86,  # Type ID = 134 (BattleSetActiveStack)
        0x01, 0x00, 0x00, 0x00,  # Battle ID = 1
        0x05, 0x00, 0x00, 0x00,  # Stack ID = 5
        0x01,  # Ask player interface = True
    ])

    pack_result = deserialize_pack(test_data)
    if pack_result:
        print(f"Pack type: {pack_result.__class__.__name__}")
        if isinstance(pack_result, BattleSetActiveStack):
            print(f"Battle ID: {pack_result.battle_id.to_int()}")
            print(f"Stack ID: {pack_result.stack}")
