"""Redacted classification for devices this integration does not command.

Published Allone RF shade commands are order ``rf control`` with value1
380000 (open), 380001 (close) and 380002 (stop). This repository sends those
commands only for device type 34 that shares a type 30 or 67 hub UID.
``ha-powermate-p2`` documents the same command for types 34, 35, 39 and 42.
Type 35 is also documented as a position motor, and type 127 is not in either
command map. Nothing here builds a hardware command.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
import re
from typing import Any

from .control import is_allone_tv, is_rf_curtain

# Types ha-powermate-p2 treats as RF shades. Not an allowlist for this
# integration: only type 34 is implemented, and only with a shared hub UID.
POWERMATE_RF_DEVICE_TYPES = frozenset({"34", "35", "39", "42"})
_IMPLEMENTED_CURTAIN_TYPE = "34"
_ALLONE_HUB_TYPES = {"30": "allone", "67": "allone_pro"}
_RF_VALUE_SHAPES = {
    380000: "known_rf_open",
    380001: "known_rf_close",
    380002: "known_rf_stop",
}
_ORDER_ALLOWLIST = frozenset(
    {
        "rf control",
        "open",
        "close",
        "stop",
        "ir control",
        "on",
        "off",
        "set property",
        "move to level",
        "fast move to level",
        "fast color temperature",
    }
)
_LABEL_KEYS = frozenset(
    {
        "company",
        "brand",
        "manufacturer",
        "vendor",
        "deviceTypeName",
        "devTypeName",
        "typeName",
        "categoryName",
        "productType",
        "productTypeName",
        "modelType",
    }
)
_TYPE_KEYS = frozenset(
    {
        "deviceType",
        "devType",
        "type",
        "category",
        "deviceCategory",
        "subDeviceType",
        "subDevType",
    }
)
_VALUE_KEYS = frozenset({"value1", "value2", "value3", "value4"})
_DIAGNOSTIC_VALUE_ALLOWLIST = frozenset(_RF_VALUE_SHAPES)
_MAX_DEPTH = 3
_MAX_MAPPING_KEYS = 40
_MAX_LIST_SCAN = 100
_MAX_COLLECTIONS = 30

_REASON_TYPE_127 = "type_127_has_no_published_command_mapping"
_REASON_POWERMATE_NOT_ENABLED = (
    "powermate_rf_type_is_not_enabled_in_this_integration"
)
_REASON_ALLONE_CHILD = "allone_child_without_a_command_in_this_integration"


@dataclass(frozen=True, slots=True)
class DeviceRowSummary:
    """Structural fingerprint of a device row. Values that can carry secrets are omitted."""

    field_names: tuple[str, ...] = ()
    labels: tuple[tuple[str, str], ...] = ()
    type_fields: tuple[tuple[str, str], ...] = ()
    value_shapes: tuple[tuple[str, str], ...] = ()
    collections: tuple[tuple[str, str, int, int, tuple[str, ...]], ...] = ()
    allowlisted_orders: tuple[str, ...] = ()
    unlisted_order_present: bool = False
    nested_value_shapes: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-ready view with no identifiers or payloads."""

        return {
            "field_names": list(self.field_names),
            "labels": dict(self.labels),
            "type_fields": dict(self.type_fields),
            "value_shapes": dict(self.value_shapes),
            "collections": [
                {
                    "name": name,
                    "kind": kind,
                    "length": length,
                    "scanned": scanned,
                    "child_keys": list(child_keys),
                }
                for name, kind, length, scanned, child_keys in self.collections
            ],
            "allowlisted_orders": list(self.allowlisted_orders),
            "unlisted_order_present": self.unlisted_order_present,
            "nested_value_shapes": dict(self.nested_value_shapes),
        }


def _safe_label(value: Any) -> str | None:
    """Keep a short product label and drop identifiers, addresses and codes."""

    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or len(text) > 64:
        return None
    if any(character in text for character in "@/\\"):
        return None
    if re.fullmatch(r"[0-9a-fA-F]{16,}", text):
        return None
    if re.fullmatch(r"-?\d{6,}", text):
        return None
    return text


def _type_token(value: Any) -> str | None:
    """Keep a short numeric type code and drop long identifiers."""

    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int) and -100000 < value < 100000:
        return str(value)
    if isinstance(value, str) and re.fullmatch(r"-?\d{1,6}", value.strip()):
        return value.strip()
    return None


def _value_shape(value: Any) -> str:
    """Classify a status number without retaining an unrecognized value."""

    if isinstance(value, str):
        stripped = value.strip()
        if re.fullmatch(r"-?\d+", stripped):
            return _value_shape(int(stripped))
        return "empty" if stripped == "" else "text"
    if isinstance(value, bool) or value is None:
        return "empty" if value is None else "bool"
    if isinstance(value, int):
        if value in _RF_VALUE_SHAPES:
            return _RF_VALUE_SHAPES[value]
        if value == 0:
            return "zero"
        if 0 <= value <= 100:
            return "percent"
        return "other_number"
    return "other"


def _allowlisted_order(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = " ".join(value.split())
    return token if token in _ORDER_ALLOWLIST else None


@dataclass
class _SummaryAccumulator:
    field_names: set[str] = field(default_factory=set)
    labels: dict[str, str] = field(default_factory=dict)
    type_fields: dict[str, str] = field(default_factory=dict)
    value_shapes: dict[str, str] = field(default_factory=dict)
    collections: dict[str, tuple[str, int, int, tuple[str, ...]]] = field(
        default_factory=dict
    )
    orders: set[str] = field(default_factory=set)
    unlisted_order: bool = False
    nested_shapes: dict[str, set[str]] = field(default_factory=dict)

    def add_order(self, value: Any) -> None:
        token = _allowlisted_order(value)
        if token is not None:
            self.orders.add(token)
        elif value not in (None, ""):
            self.unlisted_order = True

    def add_shape(self, path: str, value: Any, *, top_level: bool) -> None:
        shape = _value_shape(value)
        if top_level:
            self.value_shapes.setdefault(path, shape)
            return
        self.nested_shapes.setdefault(path, set()).add(shape)

    def finish(self) -> DeviceRowSummary:
        collections = tuple(
            (name, kind, length, scanned, child_keys)
            for name, (kind, length, scanned, child_keys) in sorted(
                self.collections.items()
            )
        )[:_MAX_COLLECTIONS]
        return DeviceRowSummary(
            field_names=tuple(sorted(self.field_names)),
            labels=tuple(sorted(self.labels.items())),
            type_fields=tuple(sorted(self.type_fields.items())),
            value_shapes=tuple(sorted(self.value_shapes.items())),
            collections=collections,
            allowlisted_orders=tuple(sorted(self.orders)),
            unlisted_order_present=self.unlisted_order,
            nested_value_shapes=tuple(
                (path, ",".join(sorted(shapes)))
                for path, shapes in sorted(self.nested_shapes.items())
            ),
        )


def _remember_collection(
    accumulator: _SummaryAccumulator,
    path: str,
    kind: str,
    length: int,
    scanned: int,
    child_keys: list[str],
) -> None:
    if not path or len(accumulator.collections) >= _MAX_COLLECTIONS:
        return
    current = accumulator.collections.get(path)
    keys = tuple(sorted(set(child_keys))[:_MAX_MAPPING_KEYS])
    if current is None or len(keys) > len(current[3]):
        accumulator.collections[path] = (kind, length, scanned, keys)


def _walk(value: Any, path: str, depth: int, accumulator: _SummaryAccumulator) -> None:
    if depth > _MAX_DEPTH:
        return
    leaf_name = path.rsplit(".", 1)[-1]
    if path and leaf_name in _VALUE_KEYS:
        accumulator.add_shape(path, value, top_level=depth == 1)
    if path and leaf_name == "order":
        accumulator.add_order(value)
    if depth == 1 and leaf_name in _LABEL_KEYS:
        label = _safe_label(value)
        if label is not None:
            accumulator.labels.setdefault(path, label)
    if depth >= 1 and leaf_name in _TYPE_KEYS:
        token = _type_token(value)
        if token is not None:
            accumulator.type_fields.setdefault(path, token)

    if isinstance(value, Mapping):
        keys = [key for key in value if isinstance(key, str) and len(key) <= 64]
        _remember_collection(
            accumulator, path, "mapping", len(keys), min(len(keys), _MAX_MAPPING_KEYS), keys
        )
        if depth == _MAX_DEPTH:
            return
        for key in keys:
            child = f"{path}.{key}" if path else key
            _walk(value[key], child, depth + 1, accumulator)
        return

    if isinstance(value, list):
        child_keys: list[str] = []
        scanned = min(len(value), _MAX_LIST_SCAN)
        for item in value[:_MAX_LIST_SCAN]:
            if isinstance(item, Mapping):
                for key in item:
                    if (
                        isinstance(key, str)
                        and len(key) <= 64
                        and key not in child_keys
                    ):
                        child_keys.append(key)
        _remember_collection(
            accumulator, path, "list", len(value), scanned, child_keys
        )
        if depth == _MAX_DEPTH:
            return
        # Walk each item's fields under the list name. Do not reuse the list
        # path for the item itself; that would replace this list record.
        for item in value[:_MAX_LIST_SCAN]:
            if not isinstance(item, Mapping):
                continue
            for key in item:
                if not isinstance(key, str) or len(key) > 64:
                    continue
                _walk(item[key], f"{path}.{key}" if path else key, depth + 1, accumulator)


def summarize_device_rows(*rows: Mapping[str, Any]) -> DeviceRowSummary:
    """Summarize one or more raw device rows without keeping their payloads."""

    accumulator = _SummaryAccumulator()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        for key in row:
            if isinstance(key, str) and len(key) <= 64:
                accumulator.field_names.add(key)
        _walk(row, "", 0, accumulator)
    return accumulator.finish()


def merge_summaries(primary: DeviceRowSummary, extra: DeviceRowSummary) -> DeviceRowSummary:
    """Combine fingerprints when two partial device rows describe one device."""

    labels = dict(primary.labels)
    for key, value in extra.labels:
        labels.setdefault(key, value)
    type_fields = dict(primary.type_fields)
    for key, value in extra.type_fields:
        type_fields.setdefault(key, value)
    value_shapes = dict(primary.value_shapes)
    for key, value in extra.value_shapes:
        value_shapes.setdefault(key, value)
    collections = {item[0]: item[1:] for item in primary.collections}
    for name, kind, length, scanned, child_keys in extra.collections:
        current = collections.get(name)
        if current is None or len(child_keys) > len(current[3]):
            collections[name] = (kind, length, scanned, child_keys)
    nested: dict[str, set[str]] = {}
    for source in (primary.nested_value_shapes, extra.nested_value_shapes):
        for path, shapes in source:
            nested.setdefault(path, set()).update(shapes.split(","))
    return DeviceRowSummary(
        field_names=tuple(sorted(set(primary.field_names) | set(extra.field_names))),
        labels=tuple(sorted(labels.items())),
        type_fields=tuple(sorted(type_fields.items())),
        value_shapes=tuple(sorted(value_shapes.items())),
        collections=tuple(
            (name, kind, length, scanned, child_keys)
            for name, (kind, length, scanned, child_keys) in sorted(collections.items())
        ),
        allowlisted_orders=tuple(
            sorted(set(primary.allowlisted_orders) | set(extra.allowlisted_orders))
        ),
        unlisted_order_present=(
            primary.unlisted_order_present or extra.unlisted_order_present
        ),
        nested_value_shapes=tuple(
            (path, ",".join(sorted(shapes)))
            for path, shapes in sorted(nested.items())
        ),
    )


def hub_association(device: Any, devices: Iterable[Any]) -> str:
    """Report whether a device shares its hardware UID with an Allone hub.

    The UID itself is not returned. A hub row is reported as itself and is
    not treated as its own child.
    """

    if device.device_type in _ALLONE_HUB_TYPES and device.cloud_uid:
        return f"self_{_ALLONE_HUB_TYPES[device.device_type]}"
    if not device.cloud_uid:
        return "missing_control_uid"
    matched: set[str] = set()
    for hub in devices:
        if hub.uid == device.uid or not hub.cloud_uid:
            continue
        if hub.cloud_uid == device.cloud_uid and hub.device_type in _ALLONE_HUB_TYPES:
            matched.add(hub.device_type)
    if "67" in matched:
        return "allone_pro"
    if "30" in matched:
        return "allone"
    return "none"


def cover_classification(device: Any, devices: Iterable[Any]) -> dict[str, Any]:
    """Describe cover support. This never selects a command payload."""

    devices = tuple(devices)
    association = hub_association(device, devices)
    reason: str | None = None
    if is_rf_curtain(device, devices):
        cover_command = "rf_open_close_stop"
    elif device.device_type == _IMPLEMENTED_CURTAIN_TYPE:
        cover_command = "position"
    elif is_allone_tv(device, devices) or device.device_type in _ALLONE_HUB_TYPES:
        cover_command = "not_a_cover"
    elif device.device_type == "127":
        cover_command = "withheld"
        reason = _REASON_TYPE_127
    elif device.device_type in POWERMATE_RF_DEVICE_TYPES - {_IMPLEMENTED_CURTAIN_TYPE}:
        cover_command = "withheld"
        reason = _REASON_POWERMATE_NOT_ENABLED
    elif association in {"allone", "allone_pro"}:
        cover_command = "withheld"
        reason = _REASON_ALLONE_CHILD
    else:
        cover_command = "not_a_cover"
    summary = getattr(device, "row_summary", DeviceRowSummary())
    return {
        "hub_association": association,
        "parent_link_present": bool(getattr(device, "parent_uid", "")),
        "cover_command": cover_command,
        "withheld_reason": reason,
        "matches_powermate_rf_type": device.device_type in POWERMATE_RF_DEVICE_TYPES,
        "row": summary.as_dict() if isinstance(summary, DeviceRowSummary) else {},
    }


def diagnostic_number(value: int | None) -> int | str | None:
    """Expose a position or a published RF button code, and redact other numbers."""

    if value is None:
        return None
    if 0 <= value <= 100 or value in _DIAGNOSTIC_VALUE_ALLOWLIST:
        return value
    return "**REDACTED**"
