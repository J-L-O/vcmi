"""
VCMI Binary Protocol Serializer/Deserializer

Bidirectional serialization supporting both reading and writing.
Each serialize() method uses a handler `h` whose methods work in both directions:
  - Deserialization: h.integer(self.x) reads from stream, returns new value
  - Serialization:   h.integer(self.x) writes value to stream, returns same value
This mirrors the C++ pattern where `h & field` works for both directions.
"""

import struct
from typing import TypeVar, Dict, List, Set
from enum import IntEnum
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SerializationVersion(IntEnum):
    """Serialization version flags - simplified subset of C++ ESerializationVersion"""
    CURRENT = 873 + 15  # Corresponds to C++ CURRENT = HOTA_MAP_STACK_COUNT
    RELEASE_160 = 873
    CUSTOM_BONUS_ICONS = RELEASE_160 + 10  # 883
    SERVER_STATISTICS = RELEASE_160 + 11  # 884
    OPPOSITE_SIDE_LIMITER_OWNER = RELEASE_160 + 12  # 885
    BONUS_HIDDEN = RELEASE_160 + 15  # 888
    COMPACT_INTEGER_SERIALIZATION = 5
    COMPACT_STRING_SERIALIZATION = 5


# ============================================================================
# Deserialization Handler
# ============================================================================

class BinaryDeserializer:
    """
    Deserializer for VCMI binary protocol.
    Implements the bidirectional handler interface for reading.
    """
    is_reading = True
    is_writing = False

    def __init__(self, data: bytes, version: int = SerializationVersion.CURRENT):
        self.data = data
        self.position = 0
        self.version = version
        self._loaded_pointers: Dict[int, 'Serializeable'] = {}
        self._loaded_shared_pointers: Dict[int, 'Serializeable'] = {}
        self._loaded_strings: List[str] = []

    # --- Raw read helpers ---

    def _read(self, size: int) -> bytes:
        if self.position + size > len(self.data):
            raise ValueError(
                f"Read past end of buffer: {self.position + size} > {len(self.data)}"
            )
        result = self.data[self.position:self.position + size]
        self.position += size
        return result

    def _read_fmt(self, fmt: str):
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self._read(size))[0]

    # --- Bidirectional interface (value param is ignored on read) ---

    def int8(self, value=0) -> int:
        return self._read_fmt('<b')

    def uint8(self, value=0) -> int:
        return self._read_fmt('<B')

    def int16(self, value=0) -> int:
        return self._read_fmt('<h')

    def uint16(self, value=0) -> int:
        return self._read_fmt('<H')

    def int32(self, value=0) -> int:
        return self._read_fmt('<i')

    def uint32(self, value=0) -> int:
        return self._read_fmt('<I')

    def int64(self, value=0) -> int:
        return self._read_fmt('<q')

    def uint64(self, value=0) -> int:
        return self._read_fmt('<Q')

    def float32(self, value=0.0) -> float:
        return self._read_fmt('<f')

    def float64(self, value=0.0) -> float:
        return self._read_fmt('<d')

    def bool_(self, value=False) -> bool:
        return bool(self._read_fmt('<B') != 0)

    def _decode_integer(self) -> int:
        """Variable-length encoded integer (compact serialization)."""
        value = 0
        offset = 0
        while True:
            byte_value = self._read_fmt('<B')
            if (byte_value & 0x80) != 0:
                value |= (byte_value & 0x7f) << offset
                offset += 7
            else:
                value |= (byte_value & 0x3f) << offset
                is_negative = (byte_value & 0x40) != 0
                return -value if is_negative else value

    def integer(self, value=0) -> int:
        """Version-aware integer: compact if version >= 5, else int32."""
        if self.version >= SerializationVersion.COMPACT_INTEGER_SERIALIZATION:
            return self._decode_integer()
        return self.int32()

    def string(self, value="") -> str:
        """Version-aware string with interning support."""
        if self.version >= SerializationVersion.COMPACT_STRING_SERIALIZATION:
            length = self.integer()
            if length == 0:
                return ""
            if length < 0:
                # String reference (previously loaded)
                ref_index = -length - 1
                if 0 <= ref_index < len(self._loaded_strings):
                    return self._loaded_strings[ref_index]
                raise ValueError(f"Invalid string reference: {ref_index}")
            string_data = self._read(length).decode('utf-8')
            self._loaded_strings.append(string_data)
            return string_data
        else:
            length = self.integer()
            return self._read(length).decode('utf-8')

    def vector(self, values, element_type) -> list:
        """Deserialize a vector of elements."""
        length = self.integer()
        return [self._typed_value(None, element_type) for _ in range(length)]

    def set_(self, values, element_type) -> set:
        """Deserialize a set of elements."""
        length = self.integer()
        return {self._typed_value(None, element_type) for _ in range(length)}

    def map_(self, values, key_type, value_type) -> dict:
        """Deserialize a map."""
        length = self.integer()
        result = {}
        for _ in range(length):
            k = self._typed_value(None, key_type)
            v = self._typed_value(None, value_type)
            result[k] = v
        return result

    def _typed_value(self, value, value_type):
        """Dispatch to the correct method based on type."""
        if value_type == bool:
            return self.bool_()
        elif value_type == int:
            return self.integer()
        elif value_type == str:
            return self.string()
        elif value_type == float:
            return self.float64()
        elif hasattr(value_type, '__origin__') and value_type.__origin__ == list:
            return self.vector([], value_type.__args__[0])
        else:
            return self.pointer(None, value_type)

    def variant(self, value, variant_classes):
        """Deserialize a variant (type index + integer value)."""
        type_index = self.integer()
        if type_index < 0 or type_index >= len(variant_classes):
            raise ValueError(
                f"Invalid variant index: {type_index} (0-{len(variant_classes)-1})"
            )
        int_value = self.integer()
        return variant_classes[type_index](int_value)

    def pointer(self, value, cls):
        """Deserialize a polymorphic pointer (null + ptr_id + type_id + data)."""
        is_null = self.bool_()
        if is_null:
            return None

        pointer_id = self.integer()
        if pointer_id in self._loaded_pointers:
            return self._loaded_pointers[pointer_id]

        type_id = self.integer()

        # Determine actual class
        if cls in Serializeable.__registry__.values():
            actual_class = Serializeable.__registry__.get(type_id)
            if actual_class is None:
                raise ValueError(f"Unknown type ID: {type_id}")
        else:
            actual_class = cls

        instance = actual_class()
        instance._ptr_id = pointer_id
        instance._serialized_type_id = type_id
        self._loaded_pointers[pointer_id] = instance
        instance.serialize(self)
        return instance

    def raw_ptr_vector(self, values, cls) -> list:
        """Deserialize vector of non-polymorphic unique_ptrs (no type_id)."""
        length = self.integer()
        result = []
        for _ in range(length):
            is_null = self.bool_()
            if is_null:
                result.append(None)
            else:
                pointer_id = self.integer()
                if pointer_id in self._loaded_pointers:
                    result.append(self._loaded_pointers[pointer_id])
                else:
                    obj = cls()
                    obj._ptr_id = pointer_id
                    self._loaded_pointers[pointer_id] = obj
                    obj.serialize(self)
                    result.append(obj)
        return result

    def shared_ptr_vector(self, values, cls) -> list:
        """Deserialize vector of non-polymorphic shared_ptrs (no type_id)."""
        length = self.integer()
        result = []
        for _ in range(length):
            is_null = self.bool_()
            if is_null:
                result.append(None)
            else:
                pointer_id = self.integer()
                if pointer_id in self._loaded_shared_pointers:
                    result.append(self._loaded_shared_pointers[pointer_id])
                else:
                    obj = cls()
                    obj._ptr_id = pointer_id
                    self._loaded_shared_pointers[pointer_id] = obj
                    obj.serialize(self)
                    result.append(obj)
        return result

    def object_(self, value, cls):
        """Deserialize an inline (non-pointer) object."""
        obj = cls()
        obj.serialize(self)
        return obj

    def fixed_array(self, values, cls, count) -> list:
        """Deserialize a fixed-size array of inline objects."""
        return [self.object_(None, cls) for _ in range(count)]

    # --- Backward-compatible aliases for existing test code ---

    def read(self, size):
        return self._read(size)

    def load_bool(self):
        return self.bool_()

    def load_uint8(self):
        return self.uint8()

    def load_int8(self):
        return self.int8()

    def load_int16(self):
        return self.int16()

    def load_uint16(self):
        return self.uint16()

    def load_int32(self):
        return self.int32()

    def load_uint32(self):
        return self.uint32()

    def load_int64(self):
        return self.int64()

    def load_uint64(self):
        return self.uint64()

    def load_float32(self):
        return self.float32()

    def load_float64(self):
        return self.float64()

    def load_integer(self):
        return self.integer()

    def load_encoded_integer(self):
        return self._decode_integer()

    def load_string(self):
        return self.string()

    def load_vector(self, element_type):
        return self.vector([], element_type)

    def load_set(self, element_type):
        return self.set_(set(), element_type)

    def load_map(self, key_type, value_type):
        return self.map_({}, key_type, value_type)

    def load_variant(self, variant_classes):
        return self.variant(None, variant_classes)

    def load_pointer(self, cls):
        return self.pointer(None, cls)

    # Backward-compatible property access
    @property
    def loaded_pointers(self):
        return self._loaded_pointers

    @property
    def loaded_shared_pointers(self):
        return self._loaded_shared_pointers

    @property
    def loaded_strings(self):
        return self._loaded_strings


# ============================================================================
# Serialization Handler
# ============================================================================

class BinarySerializer:
    """
    Serializer for VCMI binary protocol.
    Implements the bidirectional handler interface for writing.
    """
    is_reading = False
    is_writing = True

    def __init__(self, version: int = SerializationVersion.CURRENT):
        self.buffer = bytearray()
        self.version = version
        self._saved_pointers: Dict[int, int] = {}        # id(obj) -> pointer_id
        self._saved_shared_pointers: Dict[int, int] = {}  # id(obj) -> pointer_id
        self._saved_strings: Dict[str, int] = {}           # string -> index
        self._next_pointer_id = 0
        self._next_shared_pointer_id = 0

    def _write(self, data: bytes):
        self.buffer.extend(data)

    def _write_fmt(self, fmt: str, value):
        self.buffer.extend(struct.pack(fmt, value))

    def get_bytes(self) -> bytes:
        """Return the serialized data as bytes."""
        return bytes(self.buffer)

    # --- Bidirectional interface (writes value, returns same value) ---

    def int8(self, value) -> int:
        self._write_fmt('<b', value)
        return value

    def uint8(self, value) -> int:
        self._write_fmt('<B', value)
        return value

    def int16(self, value) -> int:
        self._write_fmt('<h', value)
        return value

    def uint16(self, value) -> int:
        self._write_fmt('<H', value)
        return value

    def int32(self, value) -> int:
        self._write_fmt('<i', value)
        return value

    def uint32(self, value) -> int:
        self._write_fmt('<I', value)
        return value

    def int64(self, value) -> int:
        self._write_fmt('<q', value)
        return value

    def uint64(self, value) -> int:
        self._write_fmt('<Q', value)
        return value

    def float32(self, value) -> float:
        self._write_fmt('<f', value)
        return value

    def float64(self, value) -> float:
        self._write_fmt('<d', value)
        return value

    def bool_(self, value) -> bool:
        self._write_fmt('<B', 1 if value else 0)
        return value

    def _encode_integer(self, value: int):
        """Write a variable-length encoded integer (compact serialization)."""
        abs_value = abs(value)
        is_negative = value < 0
        while abs_value > 0x3f:
            self._write_fmt('<B', 0x80 | (abs_value & 0x7f))
            abs_value >>= 7
        final_byte = abs_value & 0x3f
        if is_negative:
            final_byte |= 0x40
        self._write_fmt('<B', final_byte)

    def integer(self, value) -> int:
        """Version-aware integer: compact if version >= 5, else int32."""
        if self.version >= SerializationVersion.COMPACT_INTEGER_SERIALIZATION:
            self._encode_integer(value)
        else:
            self.int32(value)
        return value

    def string(self, value) -> str:
        """Version-aware string with interning support."""
        if self.version >= SerializationVersion.COMPACT_STRING_SERIALIZATION:
            if value == "":
                self.integer(0)
                return value
            if value in self._saved_strings:
                ref_index = self._saved_strings[value]
                self.integer(-(ref_index + 1))
                return value
            string_data = value.encode('utf-8')
            self.integer(len(string_data))
            self._write(string_data)
            self._saved_strings[value] = len(self._saved_strings)
            return value
        else:
            string_data = value.encode('utf-8')
            self.integer(len(string_data))
            self._write(string_data)
            return value

    def vector(self, values, element_type) -> list:
        """Serialize a vector of elements."""
        self.integer(len(values))
        for v in values:
            self._typed_value(v, element_type)
        return values

    def set_(self, values, element_type) -> set:
        """Serialize a set of elements."""
        self.integer(len(values))
        for v in values:
            self._typed_value(v, element_type)
        return values

    def map_(self, values, key_type, value_type) -> dict:
        """Serialize a map."""
        self.integer(len(values))
        for k, v in values.items():
            self._typed_value(k, key_type)
            self._typed_value(v, value_type)
        return values

    def _typed_value(self, value, value_type):
        """Dispatch to the correct method based on type."""
        if value_type == bool:
            self.bool_(value)
        elif value_type == int:
            self.integer(value)
        elif value_type == str:
            self.string(value)
        elif value_type == float:
            self.float64(value)
        elif hasattr(value_type, '__origin__') and value_type.__origin__ == list:
            self.vector(value, value_type.__args__[0])
        else:
            self.pointer(value, value_type)

    def variant(self, value, variant_classes):
        """Serialize a variant (type index + integer value)."""
        type_index = None
        for i, cls in enumerate(variant_classes):
            if isinstance(value, cls):
                type_index = i
                break
        if type_index is None:
            raise ValueError(f"Value type {type(value).__name__} not in variant classes")
        self.integer(type_index)
        self.integer(value.value)
        return value

    def _get_or_assign_pointer_id(self, obj) -> tuple:
        """Get existing pointer_id or assign a new one. Returns (id, is_new)."""
        obj_id = id(obj)
        if obj_id in self._saved_pointers:
            return self._saved_pointers[obj_id], False

        # Use stored ID from deserialization if available, else assign new
        if hasattr(obj, '_ptr_id'):
            pointer_id = obj._ptr_id
        else:
            pointer_id = self._next_pointer_id
        self._next_pointer_id = max(self._next_pointer_id, pointer_id + 1)
        self._saved_pointers[obj_id] = pointer_id
        return pointer_id, True

    def pointer(self, value, cls):
        """Serialize a polymorphic pointer (null + ptr_id + type_id + data)."""
        if value is None:
            self.bool_(True)
            return None

        self.bool_(False)
        pointer_id, is_new = self._get_or_assign_pointer_id(value)
        self.integer(pointer_id)

        if not is_new:
            return value  # Back-reference, already serialized

        # Write type_id
        if hasattr(value, '_serialized_type_id'):
            type_id = value._serialized_type_id
        else:
            type_id = self._lookup_type_id(value, cls)
        self.integer(type_id)

        value.serialize(self)
        return value

    def _lookup_type_id(self, obj, base_cls):
        """Look up the type ID for a polymorphic object from the registry."""
        obj_class = type(obj)
        for tid, cls in Serializeable.__registry__.items():
            if cls is obj_class:
                return tid
        # Fallback: look up the base class
        for tid, cls in Serializeable.__registry__.items():
            if cls is base_cls:
                return tid
        raise ValueError(f"No type ID found for {obj_class.__name__}")

    def raw_ptr_vector(self, values, cls) -> list:
        """Serialize vector of non-polymorphic unique_ptrs (no type_id)."""
        self.integer(len(values))
        for obj in values:
            if obj is None:
                self.bool_(True)
            else:
                self.bool_(False)
                pointer_id, is_new = self._get_or_assign_pointer_id(obj)
                self.integer(pointer_id)
                if is_new:
                    obj.serialize(self)
        return values

    def shared_ptr_vector(self, values, cls) -> list:
        """Serialize vector of non-polymorphic shared_ptrs (no type_id)."""
        self.integer(len(values))
        for obj in values:
            if obj is None:
                self.bool_(True)
            else:
                self.bool_(False)
                obj_id = id(obj)
                if obj_id in self._saved_shared_pointers:
                    self.integer(self._saved_shared_pointers[obj_id])
                else:
                    if hasattr(obj, '_ptr_id'):
                        pointer_id = obj._ptr_id
                    else:
                        pointer_id = self._next_shared_pointer_id
                    self._next_shared_pointer_id = max(
                        self._next_shared_pointer_id, pointer_id + 1
                    )
                    self._saved_shared_pointers[obj_id] = pointer_id
                    self.integer(pointer_id)
                    obj.serialize(self)
        return values

    def object_(self, value, cls):
        """Serialize an inline (non-pointer) object."""
        value.serialize(self)
        return value

    def fixed_array(self, values, cls, count) -> list:
        """Serialize a fixed-size array of inline objects."""
        for obj in values:
            obj.serialize(self)
        return values


# ============================================================================
# Base class for serializable types
# ============================================================================

class Serializeable:
    """Base class for all serializeable objects."""

    __registry__: Dict[int, type] = {}

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def register_type(cls, type_id: int):
        """Register a class with a type ID for polymorphic deserialization."""
        def decorator(target_class):
            cls.__registry__[type_id] = target_class
            return target_class
        return decorator

    def serialize(self, h):
        """
        Bidirectional serialize method. Works with both BinaryDeserializer
        and BinarySerializer. Subclasses must override this.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.serialize() not implemented")


# ============================================================================
# Helper
# ============================================================================

def pack(data: bytes) -> None:
    """Helper function to print hex representation of binary data."""
    hex_str = ' '.join(f'{b:02x}' for b in data)
    logger.debug(f"Pack data ({len(data)} bytes): {hex_str}")
