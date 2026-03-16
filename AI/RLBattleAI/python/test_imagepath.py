#!/usr/bin/env python3
"""
Test ImagePath deserialization functionality
"""

from vcmi_types import ImagePath, EResType
from serializer import BinaryDeserializer, SerializationVersion

def test_empty_imagepath():
    """Test empty ImagePath deserialization"""
    print("Testing empty ImagePath...")

    # Create empty ImagePath
    # Serialization order: type (int32), name (string), originalName (string)
    import struct
    data = struct.pack('<I', EResType.IMAGE)  # type: IMAGE (8) as int32
    data += b'\x00'  # name length: 0
    data += b'\x00'  # originalName length: 0

    deserializer = BinaryDeserializer(data, SerializationVersion.CURRENT)
    imagepath = ImagePath()
    imagepath.serialize(deserializer)

    assert imagepath.type == EResType.IMAGE
    assert imagepath.name == ""
    assert imagepath.originalName == ""
    print("✓ Empty ImagePath test passed")
    return True

def test_imagepath_with_name():
    """Test ImagePath with a name using legacy string format (no compact encoding)"""
    print("Testing ImagePath with name (legacy format)...")

    # Create ImagePath with "UNIT" using legacy string format (version < 5)
    # Serialization order: type (int32), name (string), originalName (string)
    import struct
    data = struct.pack('<I', EResType.IMAGE)  # type: IMAGE (8) as int32
    # Use legacy string format (version < COMPACT_STRING_SERIALIZATION)
    data += struct.pack('<I', 4)  # name length: 4 (32-bit little-endian)
    data += b'UNIT'  # uppercase name without extension
    data += struct.pack('<I', 4)  # originalName length: 4
    data += b'Unit'  # original case name

    print(f"Test data: {data.hex()}")
    print(f"Test data length: {len(data)}")

    deserializer = BinaryDeserializer(data, version=4)  # Use legacy version
    imagepath = ImagePath()
    imagepath.serialize(deserializer)

    print(f"  Loaded: type={imagepath.type}, name='{imagepath.name}', originalName='{imagepath.originalName}'")

    assert imagepath.type == EResType.IMAGE
    assert imagepath.name == "UNIT"
    assert imagepath.originalName == "Unit"
    print(f"✓ ImagePath with name test passed: {imagepath}")
    return True

def test_imagepath_various_types():
    """Test ImagePath with various resource types using legacy format"""
    print("Testing ImagePath with various resource types (legacy format)...")

    # Test different resource types
    test_cases = [
        (EResType.IMAGE, "UNIT", "Unit"),
        (EResType.ANIMATION, "HERO", "Hero"),
        (EResType.VIDEO, "INTRO", "intro"),
    ]

    for res_type, uppercase_name, original_name in test_cases:
        # Use legacy string format (version < COMPACT_STRING_SERIALIZATION)
        import struct
        data = struct.pack('<I', res_type)  # type as int32
        # Legacy format: 32-bit little-endian length
        data += struct.pack('<I', len(uppercase_name))  # name length
        data += uppercase_name.encode('utf-8')  # uppercase name
        data += struct.pack('<I', len(original_name))  # originalName length
        data += original_name.encode('utf-8')  # original name

        deserializer = BinaryDeserializer(data, version=4)  # Use legacy version
        imagepath = ImagePath()
        imagepath.serialize(deserializer)

        assert imagepath.type == res_type
        assert imagepath.name == uppercase_name
        assert imagepath.originalName == original_name
        print(f"✓ {res_type} type test passed: {imagepath}")

    print("✓ Various resource types test passed")
    return True

def run_all_tests():
    """Run all ImagePath tests"""
    print("Running ImagePath tests...\n")

    test_empty_imagepath()
    test_imagepath_with_name()
    test_imagepath_various_types()

    print("\n✅ All ImagePath tests passed!")
    return True

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
