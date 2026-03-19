#!/usr/bin/env python3
"""
Round-trip serialization tests.

Verifies that deserializing then re-serializing produces identical binary data.
"""

import struct
from serializer import BinaryDeserializer, BinarySerializer, SerializationVersion
from vcmi_types import (
    BattleStart, BattleSetActiveStack, BattleNextRound,
    deserialize_pack, serialize_pack,
    Bonus, BonusList, MetaString, ImagePath,
    CStack, SideInBattle, SiegeInfo, BattleInfo, ObstacleChanges,
    BattleSide, BonusDuration, BonusSource, BonusValueType, BonusLimitEffect,
    BattleUnitTurnReason, BonusNodeType, EGateState,
    BonusCustomSubtype, SpellID, CreatureID, BonusCustomSource, ObjectInstanceID,
    PlayerColor, BattleID,
    Limiter, CCreatureTypeLimiter, TerrainLimiter,
    BONUS_SUBTYPE_VARIANT_TYPES, BONUS_SOURCE_VARIANT_TYPES,
)


def assert_roundtrip(original_data: bytes, description: str):
    """Helper: deserialize then serialize, assert bytes match."""
    pack_obj = deserialize_pack(original_data)
    assert pack_obj is not None, f"Failed to deserialize {description}"
    reserialized = serialize_pack(pack_obj)
    if original_data != reserialized:
        print(f"MISMATCH in {description}!")
        print(f"  Original:     {original_data.hex()}")
        print(f"  Reserialized: {reserialized.hex()}")
        # Find first difference
        for i in range(min(len(original_data), len(reserialized))):
            if original_data[i] != reserialized[i]:
                print(f"  First diff at byte {i}: orig=0x{original_data[i]:02x} vs re=0x{reserialized[i]:02x}")
                break
        if len(original_data) != len(reserialized):
            print(f"  Length: orig={len(original_data)} vs re={len(reserialized)}")
        assert False, f"Round-trip mismatch for {description}"
    print(f"  OK: {description}")


def test_compact_integer_roundtrip():
    """Test compact integer encoding/decoding round-trip."""
    print("\n=== Compact Integer Round-Trip ===")

    test_values = [0, 1, 42, 63, 64, 100, 127, 128, 500, 8191, 16383, -1, -42, -63, -64, -500]

    for val in test_values:
        ser = BinarySerializer(version=SerializationVersion.CURRENT)
        ser.integer(val)
        data = ser.get_bytes()

        deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
        result = deser.integer()
        assert result == val, f"Compact integer round-trip failed: {val} -> {result}"

    print(f"  OK: {len(test_values)} values tested")


def test_string_roundtrip():
    """Test string encoding/decoding round-trip (including interning)."""
    print("\n=== String Round-Trip ===")

    # Test basic strings
    for s in ["", "Hello", "World", "test123", "utf8: \u00e9\u00e8\u00ea"]:
        ser = BinarySerializer(version=SerializationVersion.CURRENT)
        ser.string(s)
        data = ser.get_bytes()

        deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
        result = deser.string()
        assert result == s, f"String round-trip failed: {s!r} -> {result!r}"

    # Test string interning (same string written twice)
    ser = BinarySerializer(version=SerializationVersion.CURRENT)
    ser.string("hello")
    ser.string("world")
    ser.string("hello")  # Should be a reference
    data = ser.get_bytes()

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    s1 = deser.string()
    s2 = deser.string()
    s3 = deser.string()
    assert s1 == "hello" and s2 == "world" and s3 == "hello"

    print("  OK: basic strings + interning")


def test_vector_roundtrip():
    """Test vector round-trip."""
    print("\n=== Vector Round-Trip ===")

    ser = BinarySerializer(version=SerializationVersion.CURRENT)
    ser.vector([1, 2, 3, 4, 5], int)
    data = ser.get_bytes()

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    result = deser.vector([], int)
    assert result == [1, 2, 3, 4, 5]

    # String vector
    ser = BinarySerializer(version=SerializationVersion.CURRENT)
    ser.vector(["Hello", "World"], str)
    data = ser.get_bytes()

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    result = deser.vector([], str)
    assert result == ["Hello", "World"]

    print("  OK: int and string vectors")


def test_variant_roundtrip():
    """Test variant round-trip."""
    print("\n=== Variant Round-Trip ===")

    # Test BonusCustomSubtype (index 0)
    original = BonusCustomSubtype(42)
    ser = BinarySerializer(version=SerializationVersion.CURRENT)
    ser.variant(original, BONUS_SUBTYPE_VARIANT_TYPES)
    data = ser.get_bytes()

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    result = deser.variant(None, BONUS_SUBTYPE_VARIANT_TYPES)
    assert isinstance(result, BonusCustomSubtype)
    assert result.value == 42

    # Test SpellID (index 1)
    original = SpellID(10)
    ser = BinarySerializer(version=SerializationVersion.CURRENT)
    ser.variant(original, BONUS_SUBTYPE_VARIANT_TYPES)
    data = ser.get_bytes()

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    result = deser.variant(None, BONUS_SUBTYPE_VARIANT_TYPES)
    assert isinstance(result, SpellID)
    assert result.value == 10

    print("  OK: variant types")


def test_battlesetactivestack_roundtrip():
    """Test BattleSetActiveStack round-trip."""
    print("\n=== BattleSetActiveStack Round-Trip ===")

    # Compact encoding for all integers
    data = bytes([
        0x00,        # Not null
        0x00,        # Pointer ID = 0
        0x86, 0x01,  # Type ID = 134
        0x01,        # Battle ID = 1
        0x05,        # Stack ID = 5
        0x01,        # Reason = 1 (MORALE)
    ])
    assert_roundtrip(data, "BattleSetActiveStack(battle=1, stack=5, reason=1)")


def test_battlenextround_roundtrip():
    """Test BattleNextRound round-trip."""
    print("\n=== BattleNextRound Round-Trip ===")

    data = bytes([
        0x00,        # Not null
        0x00,        # Pointer ID = 0
        0x85, 0x01,  # Type ID = 133
        0x03,        # Battle ID = 3
    ])
    assert_roundtrip(data, "BattleNextRound(battle=3)")


def test_battlestart_null_info_roundtrip():
    """Test BattleStart with null BattleInfo round-trip."""
    print("\n=== BattleStart (null info) Round-Trip ===")

    data = bytes([
        0x00,        # Not null (pack)
        0x00,        # Pointer ID = 0
        0x84, 0x01,  # Type ID = 132
        0x01,        # Battle ID = 1
        0x01,        # BattleInfo is null
    ])
    assert_roundtrip(data, "BattleStart(battle=1, info=null)")


def test_limiter_roundtrip():
    """Test limiter pointer round-trip."""
    print("\n=== Limiter Round-Trip ===")

    # Null limiter
    ser = BinarySerializer(version=SerializationVersion.CURRENT)
    ser.pointer(None, Limiter)
    data = ser.get_bytes()

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    result = deser.pointer(None, Limiter)
    assert result is None

    # Reserialized should match
    ser2 = BinarySerializer(version=SerializationVersion.CURRENT)
    ser2.pointer(result, Limiter)
    assert ser2.get_bytes() == data
    print("  OK: null limiter")

    # CCreatureTypeLimiter
    data = bytes([
        0x00,  # not null
        0x00,  # pointer ID: 0
        0x3e,  # type ID: 62 (CCreatureTypeLimiter)
        0x0a,  # creatureID: 10
        0x01,  # includeUpgrades: True
    ])
    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    result = deser.pointer(None, Limiter)
    assert isinstance(result, CCreatureTypeLimiter)
    assert result.creatureID == 10
    assert result.includeUpgrades == True

    ser2 = BinarySerializer(version=SerializationVersion.CURRENT)
    ser2.pointer(result, Limiter)
    assert ser2.get_bytes() == data, f"Mismatch: {ser2.get_bytes().hex()} != {data.hex()}"
    print("  OK: CCreatureTypeLimiter(10, True)")

    # TerrainLimiter
    data = bytes([
        0x00,        # not null
        0x01,        # pointer ID: 1
        0xC0, 0x00,  # type ID: 64 (2-byte compact)
        0x04,        # terrain string length
    ]) + b'sand'     # terrain = "sand" -> index 1

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    result = deser.pointer(None, Limiter)
    assert isinstance(result, TerrainLimiter)
    assert result.terrainType == 1  # "sand" -> 1

    ser2 = BinarySerializer(version=SerializationVersion.CURRENT)
    # Set pointer ID counter to match expected
    ser2.pointer(result, Limiter)
    assert ser2.get_bytes() == data, f"Mismatch: {ser2.get_bytes().hex()} != {data.hex()}"
    print("  OK: TerrainLimiter(sand)")


def test_bonus_roundtrip():
    """Test Bonus serialization round-trip."""
    print("\n=== Bonus Round-Trip ===")

    # Build a Bonus manually and verify round-trip via serializer
    ser = BinarySerializer(version=SerializationVersion.CURRENT)

    # Write a minimal bonus
    ser.integer(1)   # duration = PERMANENT
    ser.integer(42)  # type
    ser.integer(0)   # subtype variant index (BonusCustomSubtype)
    ser.integer(5)   # subtype value
    ser.integer(4)   # source = CREATURE_ABILITY
    ser.integer(10)  # val
    ser.integer(0)   # sid variant index (BonusCustomSource)
    ser.integer(0)   # sid value

    # MetaString (empty)
    ser.integer(0)  # exact_strings count
    ser.integer(0)  # local_strings count
    ser.integer(0)  # strings_text_id count
    ser.integer(0)  # message count
    ser.integer(0)  # numbers count

    # ImagePath (v >= 883)
    ser.integer(int(8))  # type = IMAGE
    ser.string("")       # name
    ser.string("")       # originalName

    # hidden (v >= 888)
    ser.bool_(False)

    # additional_info (empty vector)
    ser.integer(0)

    ser.integer(0)   # turnsRemain
    ser.integer(0)   # val_type = ADDITIVE_VALUE
    ser.string("")   # stacking
    ser.integer(0)   # effect_range = NO_LIMIT

    ser.bool_(True)  # limiter = null
    ser.bool_(True)  # propagator = null
    ser.bool_(True)  # updater = null
    ser.bool_(True)  # propagationUpdater = null
    ser.integer(17)  # target_source_type = OTHER

    data = ser.get_bytes()

    # Deserialize
    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    bonus = Bonus()
    bonus.serialize(deser)

    assert bonus.type == 42
    assert bonus.val == 10
    assert isinstance(bonus.subtype, BonusCustomSubtype)
    assert bonus.subtype.value == 5

    # Re-serialize
    ser2 = BinarySerializer(version=SerializationVersion.CURRENT)
    bonus.serialize(ser2)
    reserialized = ser2.get_bytes()

    assert data == reserialized, f"Bonus round-trip mismatch!\n  orig: {data.hex()}\n  re:   {reserialized.hex()}"
    print("  OK: minimal Bonus")


def test_metastring_roundtrip():
    """Test MetaString round-trip."""
    print("\n=== MetaString Round-Trip ===")

    ser = BinarySerializer(version=SerializationVersion.CURRENT)
    ser.vector(["test string"], str)  # exact_strings
    ser.integer(0)  # local_strings count
    ser.vector(["vcmi.bonus.name"], str)  # strings_text_id
    ser.vector([0, 2], int)  # message: [APPEND_RAW_STRING, APPEND_TEXTID_STRING]
    ser.integer(0)  # numbers count

    data = ser.get_bytes()

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    ms = MetaString()
    ms.serialize(deser)

    assert ms.exact_strings == ["test string"]
    assert ms.strings_text_id == ["vcmi.bonus.name"]
    assert ms.message == [0, 2]

    ser2 = BinarySerializer(version=SerializationVersion.CURRENT)
    ms.serialize(ser2)
    assert ser2.get_bytes() == data
    print("  OK: MetaString with exact + textid strings")


def test_side_in_battle_roundtrip():
    """Test SideInBattle round-trip."""
    print("\n=== SideInBattle Round-Trip ===")

    ser = BinarySerializer(version=SerializationVersion.CURRENT)
    ser.integer(0)    # color
    ser.integer(1)    # hero_id
    ser.integer(2)    # army_object_id
    ser.integer(0)    # cast_spells_count
    ser.integer(0)    # used_spells_history (empty)
    ser.integer(0)    # enchanter_counter
    ser.integer(100)  # initial_mana
    ser.integer(0)    # additional_mana

    data = ser.get_bytes()

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    side = SideInBattle()
    side.serialize(deser)

    assert side.color.value == 0
    assert side.hero_id.value == 1
    assert side.initial_mana == 100

    ser2 = BinarySerializer(version=SerializationVersion.CURRENT)
    side.serialize(ser2)
    assert ser2.get_bytes() == data
    print("  OK: SideInBattle")


def test_cstack_roundtrip():
    """Test CStack round-trip."""
    print("\n=== CStack Round-Trip ===")

    ser = BinarySerializer(version=SerializationVersion.CURRENT)
    ser.integer(5)    # id
    ser.integer(100)  # type_id (CreatureID)
    ser.integer(20)   # count
    ser.integer(0)    # side (ATTACKER)
    ser.integer(42)   # position hex
    ser.integer(80)   # first_hp_left
    ser.bool_(True)   # alive

    data = ser.get_bytes()

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    stack = CStack()
    stack.serialize(deser)

    assert stack.id == 5
    assert stack.type_id.value == 100
    assert stack.count == 20
    assert stack.alive == True

    ser2 = BinarySerializer(version=SerializationVersion.CURRENT)
    stack.serialize(ser2)
    assert ser2.get_bytes() == data
    print("  OK: CStack")


def test_map_roundtrip():
    """Test map round-trip."""
    print("\n=== Map Round-Trip ===")

    ser = BinarySerializer(version=SerializationVersion.CURRENT)
    ser.map_({1: 10, 2: 20, 3: 30}, int, int)
    data = ser.get_bytes()

    deser = BinaryDeserializer(data, version=SerializationVersion.CURRENT)
    result = deser.map_({}, int, int)
    assert result == {1: 10, 2: 20, 3: 30}
    print("  OK: map {int: int}")


def run_all_tests():
    """Run all round-trip tests."""
    print("=" * 60)
    print("Round-Trip Serialization Tests")
    print("=" * 60)

    try:
        test_compact_integer_roundtrip()
        test_string_roundtrip()
        test_vector_roundtrip()
        test_variant_roundtrip()
        test_map_roundtrip()
        test_battlesetactivestack_roundtrip()
        test_battlenextround_roundtrip()
        test_battlestart_null_info_roundtrip()
        test_limiter_roundtrip()
        test_bonus_roundtrip()
        test_metastring_roundtrip()
        test_side_in_battle_roundtrip()
        test_cstack_roundtrip()

        print("\n" + "=" * 60)
        print("All round-trip tests passed!")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
