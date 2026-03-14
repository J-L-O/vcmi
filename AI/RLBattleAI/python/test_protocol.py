"""
Test suite for VCMI protocol implementation

Tests the deserialization of various pack types and data structures.
"""

import struct
from serializer import BinaryDeserializer, SerializationVersion, pack as print_pack
from vcmi_types import (
    BattleStart, BattleSetActiveStack, BattleInfo, CStack, SideInBattle,
    CPACK_TYPE_REGISTRY, create_pack_from_type_id
)


def test_basic_types():
    """Test basic type deserialization"""
    print("\n=== Testing Basic Types ===")

    # Test bool
    data = b'\x01'
    deserializer = BinaryDeserializer(data)
    result = deserializer.load_bool()
    assert result == True, "Bool test failed"
    print(f"✓ Bool: {result}")

    # Test uint8
    data = struct.pack('>B', 42)
    deserializer = BinaryDeserializer(data)
    result = deserializer.load_uint8()
    assert result == 42, "Uint8 test failed"
    print(f"✓ Uint8: {result}")

    # Test int32
    data = struct.pack('<i', -12345)
    deserializer = BinaryDeserializer(data)
    result = deserializer.load_int32()
    assert result == -12345, "Int32 test failed"
    print(f"✓ Int32: {result}")

    # Test uint32
    data = struct.pack('<I', 12345)
    deserializer = BinaryDeserializer(data)
    result = deserializer.load_uint32()
    assert result == 12345, "Uint32 test failed"
    print(f"✓ Uint32: {result}")

    # Test int64
    data = struct.pack('<q', -123456789012345)
    deserializer = BinaryDeserializer(data)
    result = deserializer.load_int64()
    assert result == -123456789012345, "Int64 test failed"
    print(f"✓ Int64: {result}")

    # Test float64
    data = struct.pack('<d', 3.14159265359)
    deserializer = BinaryDeserializer(data)
    result = deserializer.load_float64()
    assert abs(result - 3.14159265359) < 0.0001, "Float64 test failed"
    print(f"✓ Float64: {result}")

    # Test string (using compact encoding for length)
    data = bytes([0x05]) + b'Hello'  # Compact encoded length = 5
    deserializer = BinaryDeserializer(data)
    result = deserializer.load_string()
    assert result == "Hello", "String test failed"
    print(f"✓ String: {result}")


def test_compact_integer():
    """Test compact integer encoding"""
    print("\n=== Testing Compact Integer Encoding ===")

    # Single byte (0-63)
    for value in [0, 1, 42, 63]:
        # Create manually encoded value
        data = bytes([value & 0x3f])
        deserializer = BinaryDeserializer(data, version=SerializationVersion.COMPACT_INTEGER_SERIALIZATION)
        result = deserializer.load_integer()
        assert result == value, f"Compact integer test failed for {value}"
        print(f"✓ Compact integer {value}: {result}")

    # Two bytes (64-8191)
    for value in [64, 100, 500, 8191]:
        # Manually encode
        byte1 = 0x80 | (value & 0x7f)
        byte2 = (value >> 7) & 0x3f
        data = bytes([byte1, byte2])
        deserializer = BinaryDeserializer(data, version=SerializationVersion.COMPACT_INTEGER_SERIALIZATION)
        result = deserializer.load_integer()
        assert result == value, f"Compact integer test failed for {value}"
        print(f"✓ Compact integer {value}: {result}")

    # Negative value
    value = -42
    # Manually encode negative value
    abs_value = abs(value)
    data = bytes([abs_value & 0x3f | 0x40])  # Set sign bit
    deserializer = BinaryDeserializer(data, version=SerializationVersion.COMPACT_INTEGER_SERIALIZATION)
    result = deserializer.load_integer()
    assert result == value, f"Compact negative integer test failed for {value}"
    print(f"✓ Compact negative integer {value}: {result}")


def test_pack_deserialization():
    """Test pack deserialization"""
    print("\n=== Testing Pack Deserialization ===")

    # Test BattleSetActiveStack
    # Format: [null_flag:1][ptr_id:compact][type_id:compact][battle_id:compact][stack:compact][ask_interface:1]
    # Using compact encoding for all integers
    test_data = bytes([
        0x00,  # Not null
        0x00,  # Pointer ID = 0 (compact)
        0x86, 0x01,  # Type ID = 134 (BattleSetActiveStack, compact encoded)
        0x01,  # Battle ID = 1 (compact)
        0x05,  # Stack ID = 5 (compact)
        0x01,  # Ask player interface = True
    ])

    deserializer = BinaryDeserializer(test_data)
    print_pack(test_data)

    # Load null check
    is_null = deserializer.load_bool()
    assert is_null == False, "Pack null check failed"

    # Load pointer ID
    pointer_id = deserializer.load_integer()
    assert pointer_id == 0, f"Pointer ID incorrect: {pointer_id}"

    # Load type ID
    type_id = deserializer.load_integer()
    assert type_id == 134, f"Type ID incorrect: {type_id}"

    # Create pack instance
    pack = create_pack_from_type_id(type_id)
    assert pack is not None, "Failed to create pack from type ID"
    assert isinstance(pack, BattleSetActiveStack), "Wrong pack type created"

    # Deserialize pack
    print(f"Before serialize - reason: {pack.reason}")
    pack.serialize(deserializer)
    print(f"After serialize - reason: {pack.reason}")

    # Verify pack contents
    assert pack.battle_id.to_int() == 1, f"Battle ID incorrect: {pack.battle_id.to_int()}"
    assert pack.stack == 5, f"Stack ID incorrect: {pack.stack}"
    assert pack.reason == 1, f"Reason incorrect: {pack.reason}"

    print(f"✓ BattleSetActiveStack:")
    print(f"  Battle ID: {pack.battle_id.to_int()}")
    print(f"  Stack ID: {pack.stack}")
    print(f"  Reason: {pack.reason}")


def test_simple_battle_start():
    """Test simplified BattleStart deserialization"""
    print("\n=== Testing Simple BattleStart ===")

    # Simplified BattleStart with minimal info (BattleInfo is null)
    # Format: [null_flag:1][ptr_id:compact][type_id:compact][battle_id:compact][info_null_flag:1]
    test_data = bytes([
        0x00,  # Not null
        0x00,  # Pointer ID = 0 (compact)
        0x84, 0x01,  # Type ID = 132 (BattleStart, compact encoded)
        0x01,  # Battle ID = 1 (compact)
        0x01,  # BattleInfo is null
    ])

    deserializer = BinaryDeserializer(test_data)
    print_pack(test_data)

    # Load null check
    is_null = deserializer.load_bool()
    assert is_null == False

    # Load pointer ID
    pointer_id = deserializer.load_integer()
    assert pointer_id == 0

    # Load type ID
    type_id = deserializer.load_integer()
    assert type_id == 132

    # Create and deserialize pack
    pack = create_pack_from_type_id(type_id)
    pack.serialize(deserializer)

    assert isinstance(pack, BattleStart)
    assert pack.battle_id.to_int() == 1
    assert pack.info is None

    print(f"✓ BattleStart:")
    print(f"  Battle ID: {pack.battle_id.to_int()}")
    print(f"  Has info: {pack.info is not None}")


def test_vector_deserialization():
    """Test vector (list) deserialization"""
    print("\n=== Testing Vector Deserialization ===")

    # Create a vector of integers: [1, 2, 3, 4, 5]
    # Use compact encoding for everything
    data = bytes([0x05])  # Length = 5 (compact encoded)
    for i in range(1, 6):
        # Compact encode values 1-5 as single bytes
        data += bytes([i & 0x3f])

    deserializer = BinaryDeserializer(data, version=SerializationVersion.COMPACT_INTEGER_SERIALIZATION)
    result = deserializer.load_vector(int)

    assert result == [1, 2, 3, 4, 5], f"Vector test failed: {result}"
    print(f"✓ Vector: {result}")

    # Create a vector of strings (using compact encoding for lengths)
    data = bytes([0x02])  # Length = 2 (compact encoded)
    data += bytes([0x05]) + b'Hello'  # Length = 5, string = "Hello"
    data += bytes([0x05]) + b'World'  # Length = 5, string = "World"

    deserializer = BinaryDeserializer(data)
    result = deserializer.load_vector(str)

    assert result == ["Hello", "World"], f"String vector test failed: {result}"
    print(f"✓ String vector: {result}")


def test_type_registry():
    """Test type registry"""
    print("\n=== Testing Type Registry ===")

    # Test that all registered types can be created
    for type_id, pack_class in CPACK_TYPE_REGISTRY.items():
        pack = create_pack_from_type_id(type_id)
        assert pack is not None, f"Failed to create pack for type ID {type_id}"
        assert isinstance(pack, pack_class), f"Wrong class for type ID {type_id}"
        print(f"✓ Type ID {type_id}: {pack_class.__name__}")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("VCMI Protocol Test Suite")
    print("=" * 60)

    try:
        test_basic_types()
        test_compact_integer()
        test_pack_deserialization()
        test_simple_battle_start()
        test_vector_deserialization()
        test_type_registry()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
