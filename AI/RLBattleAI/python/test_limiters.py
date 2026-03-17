#!/usr/bin/env python3
"""
Test Limiter deserialization functionality
"""

import vcmi_types
from serializer import BinaryDeserializer, SerializationVersion

def test_null_limiter():
    """Test null limiter deserialization"""
    print("Testing null limiter...")

    # Null limiter: null check + pointer ID + type ID (but not used for null)
    data = b'\x01'  # null check: True (1)

    deserializer = BinaryDeserializer(data, SerializationVersion.CURRENT)
    result = deserializer.load_pointer(vcmi_types.Limiter)

    assert result is None
    print("✓ Null limiter test passed")
    return True

def test_creature_type_limiter():
    """Test CreatureTypeLimiter deserialization"""
    print("Testing CreatureTypeLimiter...")

    # Limiter: null check (0) + pointer ID (0) + type ID (62) + limiter data
    # Use compact encoding (version >= 5)
    # Value 10 and 62 are small enough for single-byte encoding
    data = b'\x00'  # null check: False (0)
    data += b'\x00'  # pointer ID: 0 (compact encoding)
    data += b'\x3e'  # type ID: 62 (compact encoding)
    data += b'\x0a'  # creature ID: 10 (compact encoding)
    data += b'\x01'  # includeUpgrades: True (1)

    deserializer = BinaryDeserializer(data, SerializationVersion.CURRENT)
    result = deserializer.load_pointer(vcmi_types.Limiter)

    print(f"Result: {result}")
    print(f"Result type: {type(result)}")

    assert result is not None
    assert isinstance(result, vcmi_types.CCreatureTypeLimiter)
    assert result.creatureID == 10
    assert result.includeUpgrades == True
    print(f"✓ CreatureTypeLimiter test passed: {result}")
    return True

def test_terrain_limiter():
    """Test TerrainLimiter deserialization"""
    print("Testing TerrainLimiter...")

    # Limiter: null check (0) + pointer ID (1) + type ID (64) + limiter data
    # Type ID 64 is TerrainLimiter
    # Note: 64 requires 2 bytes in compact encoding: 0xC0 0x00
    data = b'\x00'  # null check: False (0)
    data += b'\x01'  # pointer ID: 1 (compact encoding)
    data += b'\xC0\x00'  # type ID: 64 (2-byte compact encoding: 0xC0 0x00)
    data += b'\x01'  # terrain type: 1 (compact encoding)

    deserializer = BinaryDeserializer(data, SerializationVersion.CURRENT)
    result = deserializer.load_pointer(vcmi_types.Limiter)

    assert result is not None
    assert isinstance(result, vcmi_types.TerrainLimiter)
    assert result.terrainType == 1
    print(f"✓ TerrainLimiter test passed: {result}")
    return True

def run_all_tests():
    """Run all limiter tests"""
    print("Running limiter tests...\n")

    test_null_limiter()
    test_creature_type_limiter()
    test_terrain_limiter()

    print("\n✅ All limiter tests passed!")
    return True

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
