"""
VCMI Binary Protocol Deserializer

This module provides Python deserialization for VCMI's binary protocol used
in network communication between game clients and servers.
"""

import struct
from typing import TypeVar, Generic, Optional, Dict, List, Set, Tuple
from dataclasses import dataclass, field
from enum import IntEnum
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

T = TypeVar('T')


class SerializationVersion(IntEnum):
    """Serialization version flags"""
    CURRENT = 8
    COMPACT_INTEGER_SERIALIZATION = 5
    COMPACT_STRING_SERIALIZATION = 5


class BinaryDeserializer:
    """
    Main deserializer class for VCMI binary protocol.
    Handles deserialization of primitive types, containers, and complex objects.
    """

    def __init__(self, data: bytes, version: int = SerializationVersion.CURRENT):
        self.data = data
        self.position = 0
        self.version = version
        self.loaded_pointers: Dict[int, 'Serializeable'] = {}
        self.loaded_shared_pointers: Dict[int, 'Serializeable'] = {}
        self.loaded_strings: List[str] = []

    def read(self, size: int) -> bytes:
        """Read raw bytes from the data stream."""
        if self.position + size > len(self.data):
            raise ValueError(f"Attempted to read past end of buffer: {self.position + size} > {len(self.data)}")
        result = self.data[self.position:self.position + size]
        self.position += size
        return result

    def load_int8(self) -> int:
        """Load an 8-bit signed integer."""
        return struct.unpack('<b', self.read(1))[0]

    def load_uint8(self) -> int:
        """Load an 8-bit unsigned integer."""
        return struct.unpack('<B', self.read(1))[0]

    def load_int16(self) -> int:
        """Load a 16-bit signed integer."""
        return struct.unpack('<h', self.read(2))[0]

    def load_uint16(self) -> int:
        """Load a 16-bit unsigned integer."""
        return struct.unpack('<H', self.read(2))[0]

    def load_int32(self) -> int:
        """Load a 32-bit signed integer."""
        return struct.unpack('<i', self.read(4))[0]

    def load_uint32(self) -> int:
        """Load a 32-bit unsigned integer."""
        return struct.unpack('<I', self.read(4))[0]

    def load_int64(self) -> int:
        """Load a 64-bit signed integer."""
        return struct.unpack('<q', self.read(8))[0]

    def load_uint64(self) -> int:
        """Load a 64-bit unsigned integer."""
        return struct.unpack('<Q', self.read(8))[0]

    def load_float32(self) -> float:
        """Load a 32-bit floating point number."""
        return struct.unpack('<f', self.read(4))[0]

    def load_float64(self) -> float:
        """Load a 64-bit floating point number."""
        return struct.unpack('<d', self.read(8))[0]

    def load_bool(self) -> bool:
        """Load a boolean value."""
        return bool(self.load_uint8() != 0)

    def load_encoded_integer(self) -> int:
        """
        Load a variable-length encoded integer (compact serialization).
        Uses variable-length encoding where values > 0x3f use multiple bytes.
        """
        value = 0
        offset = 0

        while True:
            byte_value = self.load_uint8()

            if (byte_value & 0x80) != 0:
                # More bytes follow
                value |= (byte_value & 0x7f) << offset
                offset += 7
            else:
                # Last byte
                value |= (byte_value & 0x3f) << offset
                is_negative = (byte_value & 0x40) != 0

                if is_negative:
                    return -value
                else:
                    return value

    def load_integer(self) -> int:
        """Load an integer with version-aware encoding."""
        if self.version >= SerializationVersion.COMPACT_INTEGER_SERIALIZATION:
            return self.load_encoded_integer()
        else:
            # Fallback to 32-bit integer
            return self.load_int32()

    def load_string(self) -> str:
        """Load a string with version-aware encoding."""
        if self.version >= SerializationVersion.COMPACT_STRING_SERIALIZATION:
            length = self.load_integer()
            if length == 0:
                return ""

            # Check if this is a reference to a previously loaded string
            if length > 0x80000000:  # High bit set indicates a reference
                ref_index = -(length & 0x7FFFFFFF) - 1
                if 0 <= ref_index < len(self.loaded_strings):
                    return self.loaded_strings[ref_index]
                else:
                    raise ValueError(f"Invalid string reference: {ref_index}")

            # New string
            string_data = self.read(length).decode('utf-8')
            self.loaded_strings.append(string_data)
            return string_data
        else:
            # Legacy string format
            length = self.load_integer()
            return self.read(length).decode('utf-8')

    def load_vector(self, element_type: type) -> List:
        """Load a vector (list) of elements."""
        length = self.load_integer()
        logger.debug(f"Loading vector of length {length} at position {self.position}")
        result = []

        for _ in range(length):
            if element_type == bool:
                result.append(self.load_bool())
            elif element_type == int:
                result.append(self.load_integer())
            elif element_type == str:
                result.append(self.load_string())
            elif hasattr(element_type, '__origin__') and element_type.__origin__ == list:
                # Nested list
                result.append(self.load_vector(element_type.__args__[0]))
            else:
                # Assume it's a serializeable class
                result.append(self.load_object(element_type))

        return result

    def load_set(self, element_type: type) -> Set:
        """Load a set of elements."""
        length = self.load_integer()
        result = set()

        for _ in range(length):
            if element_type == int:
                result.add(self.load_integer())
            elif hasattr(element_type, '__origin__') and element_type.__origin__ == list:
                # Nested set of lists
                result.add(tuple(self.load_vector(element_type.__args__[0])))
            else:
                result.add(self.load_object(element_type))

        return result

    def load_map(self, key_type: type, value_type: type) -> Dict:
        """Load a map (dictionary)."""
        length = self.load_integer()
        result = {}

        for _ in range(length):
            key = self._load_typed_value(key_type)
            value = self._load_typed_value(value_type)
            result[key] = value

        return result

    def _load_typed_value(self, value_type: type):
        """Load a value based on its type."""
        if value_type == bool:
            return self.load_bool()
        elif value_type == int:
            return self.load_integer()
        elif value_type == str:
            return self.load_string()
        elif value_type == float:
            return self.load_float64()
        else:
            return self.load_object(value_type)

    def load_optional(self, inner_type: type) -> Optional:
        """Load an optional value."""
        has_value = self.load_bool()
        if has_value:
            return self._load_typed_value(inner_type)
        return None

    def load_object(self, cls: type) -> 'Serializeable':
        """Load a serializeable object."""
        # Check if this is a polymorphic type (has a type ID)
        if hasattr(cls, '__registry__'):
            # Load null check
            is_null = self.load_bool()
            if is_null:
                return None

            # Load pointer ID
            pointer_id = self.load_integer()

            # Check if we've already loaded this pointer
            if pointer_id in self.loaded_pointers:
                return self.loaded_pointers[pointer_id]

            # Load type ID
            type_id = self.load_integer()

            # Get the actual class from registry
            actual_class = cls.__registry__.get(type_id)
            if actual_class is None:
                raise ValueError(f"Unknown type ID: {type_id}")

            # Create instance
            instance = actual_class()

            # Store in loaded pointers
            self.loaded_pointers[pointer_id] = instance

            # Deserialize the object
            instance.serialize(self)

            return instance
        else:
            # Simple object without polymorphism
            instance = cls()
            instance.serialize(self)
            return instance


class Serializeable:
    """Base class for all serializeable objects."""

    __registry__: Dict[int, type] = {}

    def __init__(self, *args, **kwargs):
        """Initialize serializeable object."""
        # Don't call super().__init__() to avoid issues with multiple inheritance
        # Just ignore any extra arguments passed from decorators or parent classes
        pass

    @classmethod
    def register_type(cls, type_id: int):
        """Register a class with a type ID for polymorphic deserialization."""
        cls.__registry__[type_id] = cls
        return cls

    def serialize(self, deserializer: BinaryDeserializer):
        """
        Deserialize this object from the binary stream.
        Subclasses should override this method to load their fields.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.serialize() not implemented")


def pack(data: bytes) -> None:
    """Helper function to print hex representation of binary data."""
    hex_str = ' '.join(f'{b:02x}' for b in data)
    logger.debug(f"Pack data ({len(data)} bytes): {hex_str}")


# Example usage and test
if __name__ == "__main__":
    # Test basic deserialization
    test_data = b'\x01'  # bool True
    deserializer = BinaryDeserializer(test_data)
    result = deserializer.load_bool()
    logger.info(f"Loaded bool: {result}")

    # Test integer with compact encoding
    test_data = b'\x42'  # 66 (single byte, positive)
    deserializer = BinaryDeserializer(test_data, version=5)
    result = deserializer.load_integer()
    logger.info(f"Loaded integer: {result}")

    # Test string
    test_data = b'\x05\x00\x00\x00Hello'  # 5-byte string "Hello"
    deserializer = BinaryDeserializer(test_data)
    result = deserializer.load_string()
    logger.info(f"Loaded string: {result}")
