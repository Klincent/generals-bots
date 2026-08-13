#!/usr/bin/env python3
"""Deterministic V4.1 tactics key and binary pack codec.

The key deliberately uses only information reproducible from the competition
observation plus the candidate action. Runtime-only hidden state must not enter
this key; otherwise an offline tactical miner could not reproduce it honestly.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import Iterable

MAGIC = b"JURAJV4\0"
PACK_VERSION = 3
TACTICS_KIND = 2
TACTICS_SCHEMA_VERSION = 1
HEADER = struct.Struct("<8s6I8I")
RECORD = struct.Struct("<QhH")
MASK64 = (1 << 64) - 1


@dataclass(frozen=True, order=True)
class TacticRecord:
    key: int
    value: int
    visits: int


def mix64(x: int) -> int:
    x = (int(x) + 0x9E3779B97F4A7C15) & MASK64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & MASK64
    return (x ^ (x >> 31)) & MASK64


def army_bucket(a: int) -> int:
    a = int(a)
    if a <= 1:
        return 0
    if a <= 3:
        return 1
    if a <= 7:
        return 2
    if a <= 15:
        return 3
    if a <= 31:
        return 4
    if a <= 63:
        return 5
    if a <= 127:
        return 6
    return 7


def tactic_key(*, dest_owner: int, dest_type: int, source_army: int,
               dest_army: int, split: bool, own_general_distance: int,
               enemy_general_visible: bool, contact_visible: bool,
               source_degree: int, dest_degree: int) -> int:
    """Build schema-v1 key from observation-reproducible tactical context."""
    fields = (
        int(dest_owner) & 0x3,
        int(dest_type) & 0x7,
        army_bucket(source_army) & 0x7,
        army_bucket(dest_army) & 0x7,
        int(bool(split)),
        min(31, max(0, int(own_general_distance))),
        int(bool(enemy_general_visible)),
        int(bool(contact_visible)),
        min(7, max(0, int(source_degree))),
        min(7, max(0, int(dest_degree))),
    )
    # Fixed-width packing: 2,3,3,3,1,5,1,1,3,3 bits = 25 bits.
    shifts = (0, 2, 5, 8, 11, 12, 17, 18, 19, 22)
    packed = 0
    for value, shift in zip(fields, shifts):
        packed |= value << shift
    packed |= TACTICS_SCHEMA_VERSION << 56
    return mix64(packed)


def _checksum(payload: bytes) -> int:
    value = 2166136261
    for byte in payload:
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def normalize_records(records: Iterable[TacticRecord]) -> list[TacticRecord]:
    """Sort/deduplicate records; duplicate keys are support-weighted averaged."""
    grouped: dict[int, list[TacticRecord]] = {}
    for record in records:
        if not 0 <= int(record.key) <= MASK64:
            raise ValueError("invalid tactic key")
        if not -32768 <= int(record.value) <= 32767:
            raise ValueError("tactic value outside int16")
        if not 1 <= int(record.visits) <= 65535:
            raise ValueError("tactic visits outside uint16")
        grouped.setdefault(int(record.key), []).append(record)
    out: list[TacticRecord] = []
    for key, rows in grouped.items():
        visits = min(65535, sum(int(row.visits) for row in rows))
        denom = sum(int(row.visits) for row in rows)
        mean = sum(int(row.value) * int(row.visits) for row in rows) / denom
        value = max(-32768, min(32767, int(round(mean))))
        out.append(TacticRecord(key, value, visits))
    out.sort(key=lambda row: row.key)
    return out


def serialize_tactics(records: Iterable[TacticRecord]) -> bytes:
    rows = normalize_records(records)
    payload = b"".join(RECORD.pack(row.key, row.value, row.visits) for row in rows)
    reserved = [TACTICS_SCHEMA_VERSION] + [0] * 7
    return HEADER.pack(MAGIC, PACK_VERSION, TACTICS_KIND, len(rows), 0,
                       len(payload), _checksum(payload), *reserved) + payload


def deserialize_tactics(data: bytes) -> list[TacticRecord]:
    if len(data) < HEADER.size:
        raise ValueError("truncated tactics header")
    magic, version, kind, count, hash_size, payload_bytes, checksum, *reserved = HEADER.unpack_from(data)
    if (magic != MAGIC or version != PACK_VERSION or kind != TACTICS_KIND or
            hash_size != 0 or reserved[0] != TACTICS_SCHEMA_VERSION):
        raise ValueError("incompatible tactics header")
    payload = data[HEADER.size:]
    if payload_bytes != count * RECORD.size or len(payload) != payload_bytes:
        raise ValueError("corrupt tactics size")
    if _checksum(payload) != checksum:
        raise ValueError("corrupt tactics checksum")
    rows = [TacticRecord(*RECORD.unpack_from(payload, i * RECORD.size)) for i in range(count)]
    if any(rows[i - 1].key >= rows[i].key for i in range(1, len(rows))):
        raise ValueError("tactics records not strictly sorted")
    return rows
