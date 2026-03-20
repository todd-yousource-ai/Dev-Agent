

```python
# src/consensus_engine/__init__.py
"""Consensus engine package."""
```

```python
# src/consensus_engine/contracts/__init__.py
"""
Contract infrastructure package for Consensus Dev Agent.

Exports ContractBase, registry functions, and validation utilities.
All contract classes must inherit from ContractBase and be registered
via the ContractRegistry before use.

Security assumptions:
- All external input (dicts, JSON strings) is untrusted and validated.
- Deserialization fails closed on malformed or unexpected input.
- No eval/exec of any kind — all deserialization is explicit field mapping.
"""

from consensus_engine.contracts.base import ContractBase
from consensus_engine.contracts.registry import ContractRegistry
from consensus_engine.contracts.schema_export import (
    export_all_schemas,
    export_schema,
    validate_schema_consistency,
)

# Module-level convenience functions that delegate to the singleton registry.
# Allocation: singleton registry is a single dict — minimal footprint. [OI-13]

_registry = ContractRegistry()


def register(contract_cls: type) -> type:
    """Register a ContractBase subclass by name. Returns the class (usable as decorator)."""
    _registry.register(contract_cls)
    return contract_cls


def get(name: str) -> type:
    """Look up a registered contract class by name. Raises KeyError if not found."""
    return _registry.get(name)


def list_contracts() -> list:
    """Return sorted list of registered contract names."""
    return _registry.list_contracts()


def validate_dict(name: str, data: dict) -> list:
    """Validate a dict against a named contract. Returns list of error strings."""
    return _registry.validate_dict(name, data)


def get_registry() -> ContractRegistry:
    """Return the module-level singleton registry instance."""
    return _registry


__all__ = [
    "ContractBase",
    "ContractRegistry",
    "register",
    "get",
    "list_contracts",
    "validate_dict",
    "get_registry",
    "export_schema",
    "export_all_schemas",
    "validate_schema_consistency",
]
```

```python
# src/consensus_engine/contracts/base.py
"""
ContractBase — foundational dataclass base for all consensus engine contracts.

Security assumptions:
- All deserialization input is untrusted. Fields are validated against
  declared types; unexpected keys are rejected.
- No use of eval/exec — deserialization is explicit field-by-field mapping.
- validate() is fail-closed: unknown or missing fields produce errors.
- JSON parsing uses stdlib json with no custom decoders that could execute code.
- to_dict()/to_json() never include secrets; contract dataclasses must not
  hold secret material. This is enforced by convention and review.

Failure behavior:
- from_dict / from_json raise ValueError with context on malformed input.
- validate() returns a list of human-readable error strings (empty = valid).
- schema() is a pure classmethod; no side effects.

Allocation notes [OI-13]:
- No caches or buffers. Schema is computed on each call (contracts are small).
"""

from __future__ import annotations

import dataclasses
import json
import enum
import typing
from typing import Any, ClassVar, Optional, Union, get_type_hints


def _is_optional(field_type: Any) -> tuple[bool, Any]:
    """Check if a type is Optional[X] and return (True, X) or (False, original)."""
    origin = getattr(field_type, "__origin__", None)
    if origin is Union:
        args = field_type.__args__
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            return True, non_none[0]
    return False, field_type


def _python_type_to_json_schema(field_type: Any) -> dict:
    """
    Convert a Python type annotation to a JSON Schema fragment.

    Supports: str, int, float, bool, None, Optional[T], list[T], dict[str, T],
    enum subclasses, and nested ContractBase subclasses.

    Returns a conservative schema. Unknown types map to empty schema {} (any).
    No allocation beyond the returned dict. [OI-13]
    """
    if field_type is type(None):
        return {"type": "null"}

    # Handle Optional
    is_opt, inner = _is_optional(field_type)
    if is_opt:
        inner_schema = _python_type_to_json_schema(inner)
        return {"anyOf": [inner_schema, {"type": "null"}]}

    # Handle Union (non-Optional)
    origin = getattr(field_type, "__origin__", None)

    if origin is Union:
        args = field_type.__args__
        return {"anyOf": [_python_type_to_json_schema(a) for a in args]}

    # Primitives
    if field_type is str:
        return {"type": "string"}
    if field_type is int:
        return {"type": "integer"}
    if field_type is float:
        return {"type": "number"}
    if field_type is bool:
        return {"type": "boolean"}

    # list / List[T]
    if origin is list:
        args = getattr(field_type, "__args__", None)
        if args:
            return {"type": "array", "items": _python_type_to_json_schema(args[0])}
        return {"type": "array"}

    # dict / Dict[str, T]
    if origin is dict:
        args = getattr(field_type, "__args__", None)
        if args and len(args) == 2:
            return {
                "type": "object",
                "additionalProperties": _python_type_to_json_schema(args[1]),
            }
        return {"type": "object"}

    # Enum subclass
    if isinstance(field_type, type) and issubclass(field_type, enum.Enum):
        return {"type": "string", "enum": [e.value for e in field_type]}

    # Nested ContractBase subclass
    if isinstance(field_type, type) and issubclass(field_type, ContractBase):
        return field_type.schema()

    # Bare list/dict without subscript
    if field_type is list:
        return {"type": "array"}
    if field_type is dict:
        return {"type": "object"}

    # Fallback — permissive but documented
    return {}


def _serialize_value(value: Any) -> Any:
    """
    Recursively serialize a value to JSON-safe primitives.

    Handles: primitives, enums, ContractBase instances, lists, dicts.
    No secret material should reach here (enforced by convention). [OI-13]
    """
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, ContractBase):
        return value.to_dict()
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, tuple):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _serialize_value(v) for k, v in value.items()}
    # Fallback: attempt str conversion for safety; never repr secrets
    return str(value)


def _deserialize_value(value: Any, field_type: Any) -> Any:
    """
    Recursively deserialize a JSON-safe value into the target Python type.

    Raises ValueError with context on type mismatch or malformed data.
    No eval/exec — all conversions are explicit. [OI-13]
    """
    # Handle Optional
    is_opt, inner = _is_optional(field_type)
    if is_opt:
        if value is None:
            return None
        return _deserialize_value(value, inner)

    if value is None:
        # Non-optional field received None — caller must validate
        return None

    # Enum
    if isinstance(field_type, type) and issubclass(field_type, enum.Enum):
        try:
            return field_type(value)
        except (ValueError, KeyError) as exc:
            raise ValueError(
                f"Invalid enum value '{value}' for {field_type.__name__}: {exc}"
            ) from exc

    # Nested ContractBase
    if isinstance(field_type, type) and issubclass(field_type, ContractBase):
        if not isinstance(value, dict):
            raise ValueError(
                f"Expected dict for nested contract {field_type.__name__}, "
                f"got {type(value).__name__}"
            )
        return field_type.from_dict(value)

    origin = getattr(field_type, "__origin__", None)

    # list[T]
    if origin is list:
        if not isinstance(value, list):
            raise ValueError(
                f"Expected list, got {type(value).__name__}"
            )
        args = getattr(field_type, "__args__", None)
        if args:
            return [_deserialize_value(item, args[0]) for item in value]
        return list(value)

    # dict[K, V]
    if origin is dict:
        if not isinstance(value, dict):
            raise ValueError(
                f"Expected dict, got {type(value).__name__}"
            )
        args = getattr(field_type, "__args__", None)
        if args and len(args) == 2:
            return {
                str(k): _deserialize_value(v, args[1]) for k, v in value.items()
            }
        return dict(value)

    # Primitives — coerce with bounds checking
    if field_type is bool:
        if not isinstance(value, bool):
            raise ValueError(f"Expected bool, got {type(value).__name__}: {value!r}")
        return value
    if field_type is int:
        if isinstance(value, bool):
            raise ValueError(f"Expected int, got bool: {value!r}")
        if not isinstance(value, (int, float)):
            raise ValueError(f"Expected int, got {type(value).__name__}: {value!r}")
        return int(value)
    if field_type is float:
        if isinstance(value, bool):
            raise ValueError(f"Expected float, got bool: {value!r}")
        if not isinstance(value, (int, float)):
            raise ValueError(f"Expected float, got {type(value).__name__}: {value!r}")
        return float(value)
    if field_type is str:
        if not isinstance(value, str):
            raise ValueError(f"Expected str, got {type(value).__name__}: {value!r}")
        return value

    # Bare list/dict without type args
    if field_type is list:
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value).__name__}")
        return list(value)
    if field_type is dict:
        if not isinstance(value, dict):
            raise ValueError(f"Expected dict, got {type(value).__name__}")
        return dict(value)

    # Union (non-Optional) — try each variant
    if origin is Union:
        args = field_type.__args__
        errors = []
        for variant in args:
            try:
                return _deserialize_value(value, variant)
            except (ValueError, TypeError) as exc:
                errors.append(str(exc))
        raise ValueError(
            f"Value {value!r} did not match any variant of Union: {errors}"
        )

    return value


@dataclasses.dataclass
class ContractBase:
    """
    Base class for all contract dataclasses in the consensus engine.

    Subclasses must be decorated with @dataclasses.dataclass.
    ClassVar and InitVar fields are excluded from serialization.

    Security:
    - validate() is called by from_dict/from_json; invalid data is rejected.
    - Unexpected keys in input dicts are rejected (deny-by-default).
    - No dynamic attribute setting beyond declared dataclass fields.
    """

    # Subclasses can override to provide a custom contract name.
    # Not serialized. [OI-13: single string, negligible allocation]
    _contract_name: ClassVar[str] = ""

    @classmethod
    def contract_name(cls) -> str:
        """Return the contract name. Defaults to class name if not overridden."""
        return cls._contract_name or cls.__name__

    def to_dict(self) -> dict:
        """
        Serialize this contract instance to a plain dict.

        All values are recursively converted to JSON-safe primitives.
        ClassVar and InitVar fields are excluded.
        """
        result = {}  # [OI-13: proportional to field count, small]
        for f in dataclasses.fields(self):
            value = getattr(self, f.name)
            result[f.name] = _serialize_value(value)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ContractBase":
        """
        Deserialize a dict into a contract instance.

        Fails closed:
        - Raises ValueError on unexpected keys (deny-by-default).
        - Raises ValueError on type mismatches.
        - Calls validate() and raises ValueError if validation fails.

        Input is untrusted; no eval/exec.
        """
        if not isinstance(data, dict):
            raise ValueError(
                f"ContractBase.from_dict expected dict, got {type(data).__name__}"
            )

        fields_map = {f.name: f for f in dataclasses.fields(cls)}
        type_hints = get_type_hints(cls)

        # Deny unexpected keys
        unexpected = set(data.keys()) - set(fields_map.keys())
        if unexpected:
            raise ValueError(
                f"Unexpected keys for {cls.__name__}: {sorted(unexpected)}"
            )

        kwargs = {}  # [OI-13: proportional to field count]
        for name, field in fields_map.items():
            field_type = type_hints.get(name, field.type)
            if name in data:
                try:
                    kwargs[name] = _deserialize_value(data[name], field_type)
                except (ValueError, TypeError) as exc:
                    raise ValueError(
                        f"Field '{name}' in {cls.__name__}: {exc}"
                    ) from exc
            else:
                # Check if field has a default
                if (
                    field.default is not dataclasses.MISSING
                    or field.default_factory is not dataclasses.MISSING
                ):
                    continue  # dataclass will use its default
                else:
                    raise ValueError(
                        f"Missing required field '{name}' for {cls.__name__}"
                    )

        instance = cls(**kwargs)

        # Fail closed: validate after construction
        errors = instance.validate()
        if errors:
            raise ValueError(
                f"Validation failed for {cls.__name__}: {errors}"
            )

        return instance

    def to_json(self) -> str:
        """
        Serialize to a JSON string.

        Uses sort_keys for deterministic output. No secrets in output (by convention).
        """
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, json_str: str) -> "ContractBase":
        """
        Deserialize from a JSON string.

        Fails closed on malformed JSON. Input is untrusted.
        Delegates to from_dict for field-level validation.
        """
        if not isinstance(json_str, str):
            raise ValueError(
                f"from_json expected str, got {type(json_str).__name__}"
            )
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON for {cls.__name__}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"JSON root must be object for {cls.__name__}, got {type(data).__name__}"
            