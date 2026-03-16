#!/usr/bin/env python3
"""
Test MetaString deserialization functionality
"""

from vcmi_types import MetaString, EMessage, EMetaText
from serializer import BinaryDeserializer

def test_empty_metastring():
    """Test empty MetaString deserialization"""
    print("Testing empty MetaString...")

    # Create empty MetaString - all vectors empty
    # Serialization order: exact_strings, local_strings, strings_text_id, message, numbers
    data = b'\x00'  # exact_strings: 0
    data += b'\x00'  # local_strings: 0
    data += b'\x00'  # strings_text_id: 0
    data += b'\x00'  # message: 0
    data += b'\x00'  # numbers: 0

    deserializer = BinaryDeserializer(data)
    metastring = MetaString()
    metastring.serialize(deserializer)

    assert metastring.empty()
    assert metastring.to_string() == ""
    print("✓ Empty MetaString test passed")
    return True

def test_simple_raw_string():
    """Test MetaString with simple raw string"""
    print("Testing simple raw string...")

    # Create MetaString with "Hello World"
    # Serialization order: exact_strings, local_strings, strings_text_id, message, numbers
    data = b'\x01'  # exact_strings: 1
    data += b'\x0B'  # "Hello World" length = 11
    data += b'Hello World'
    data += b'\x00'  # local_strings: 0
    data += b'\x00'  # strings_text_id: 0
    data += b'\x01'  # message: 1
    data += b'\x00'  # message[0] = APPEND_RAW_STRING
    data += b'\x00'  # numbers: 0

    deserializer = BinaryDeserializer(data)
    metastring = MetaString()
    metastring.serialize(deserializer)

    assert not metastring.empty()
    assert metastring.to_string() == "Hello World"
    assert metastring.exact_strings == ["Hello World"]
    print("✓ Simple raw string test passed")
    return True

def test_metastring_with_localization():
    """Test MetaString with localization components"""
    print("Testing MetaString with localization...")

    # Create MetaString with: "Found <localized:0:100>!"
    # Use shorter strings to avoid compact integer encoding issues
    data = b'\x02'  # exact_strings: 2
    data += b'\x06'  # "Found " length = 6 (safe single byte)
    data += b'Found '
    data += b'\x03'  # "%s!" length = 3 (safe single byte)
    data += b'%s!'
    data += b'\x01'  # local_strings: 1
    data += b'\x00'  # GENERAL_TXT = 0
    data += b'\xE4\x00'  # text ID = 100 (compact: 0xE4 0x00)
    data += b'\x00'  # strings_text_id: 0
    data += b'\x03'  # message: 3
    data += b'\x00'  # message[0] = APPEND_RAW_STRING
    data += b'\x00'  # message[1] = APPEND_RAW_STRING
    data += b'\x05'  # message[2] = REPLACE_LOCAL_STRING
    data += b'\x00'  # numbers: 0

    deserializer = BinaryDeserializer(data)
    metastring = MetaString()
    metastring.serialize(deserializer)

    assert not metastring.empty()
    assert metastring.to_string() == "Found <localized:0:100>!"
    print("✓ Localization test passed")
    return True

def test_metastring_with_text_id():
    """Test MetaString with text ID"""
    print("Testing MetaString with text ID...")

    # Create MetaString with text ID: "core.test"
    # Serialization order: exact_strings, local_strings, strings_text_id, message, numbers
    data = b'\x00'  # exact_strings: 0
    data += b'\x00'  # local_strings: 0
    data += b'\x01'  # strings_text_id: 1
    data += b'\x09'  # "core.test" length = 9 (safe single byte)
    data += b'core.test'
    data += b'\x01'  # message: 1
    data += b'\x02'  # message[0] = APPEND_TEXTID_STRING
    data += b'\x00'  # numbers: 0

    deserializer = BinaryDeserializer(data)
    metastring = MetaString()
    metastring.serialize(deserializer)

    assert not metastring.empty()
    assert metastring.to_string() == "core.test"
    print("✓ Text ID test passed")
    return True

def test_metastring_with_numbers():
    """Test MetaString with number components"""
    print("Testing MetaString with numbers...")

    # Create MetaString: "HP: 50"
    # Use smaller number and shorter strings to avoid encoding issues
    data = b'\x02'  # exact_strings: 2
    data += b'\x04'  # "HP: " length = 4 (safe single byte)
    data += b'HP: '
    data += b'\x02'  # "%d" length = 2 (safe single byte)
    data += b'%d'
    data += b'\x00'  # local_strings: 0
    data += b'\x00'  # strings_text_id: 0
    data += b'\x03'  # message: 3
    data += b'\x00'  # message[0] = APPEND_RAW_STRING
    data += b'\x00'  # message[1] = APPEND_RAW_STRING
    data += b'\x07'  # message[2] = REPLACE_NUMBER (not REPLACE_TEXTID_STRING which is 6)
    data += b'\x01'  # numbers: 1
    data += b'\x32'  # 50 as compact integer (safe single byte, 0x32 = 50)

    deserializer = BinaryDeserializer(data)
    metastring = MetaString()
    metastring.serialize(deserializer)

    assert not metastring.empty()
    assert metastring.to_string() == "HP: 50"
    assert metastring.numbers == [50]
    print("✓ Numbers test passed")
    return True

def run_all_tests():
    """Run all MetaString tests"""
    print("Running MetaString tests...\n")

    test_empty_metastring()
    test_simple_raw_string()
    test_metastring_with_localization()
    test_metastring_with_text_id()
    test_metastring_with_numbers()

    print("\n✅ All MetaString tests passed!")
    return True

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)