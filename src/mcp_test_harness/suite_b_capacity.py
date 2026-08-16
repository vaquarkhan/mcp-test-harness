"""Suite B remainder — capacity ledger + known-carrier media attestation."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from mcp_test_harness.assertions import MCPAssertionError

# Tiny deterministic "unsigned" luminance bucket marker for fixture bytes.
_LSB_SUSPECT_TAG = b"\x00LSB\x01"


def assert_capacity_enforced(
    *,
    sink: str,
    bytes_attempted: int,
    budget_bytes: int,
    admitted_bytes: int,
    denied: bool | None = None,
) -> None:
    """Content-agnostic per-sink budget must throttle/deny over-budget writes."""
    if bytes_attempted <= budget_bytes:
        if denied:
            raise MCPAssertionError(
                f"Capacity falsely denied under budget for sink={sink!r} "
                f"({bytes_attempted}<={budget_bytes})"
            )
        if admitted_bytes > budget_bytes:
            raise MCPAssertionError(
                f"Capacity admitted {admitted_bytes} over budget {budget_bytes} for {sink!r}"
            )
        return
    # Over budget
    if admitted_bytes > budget_bytes:
        raise MCPAssertionError(
            f"Capacity fail-open for sink={sink!r}: admitted {admitted_bytes} > budget {budget_bytes}"
        )
    if denied is False:
        raise MCPAssertionError(
            f"Capacity over-budget for sink={sink!r} was not denied/throttled"
        )


def assert_unsigned_media_suspect(image: bytes) -> None:
    """Known-carrier heuristic: unsigned media with LSB tag is suspect."""
    if not image:
        raise MCPAssertionError("unsigned media check: empty image")
    if _LSB_SUSPECT_TAG not in image and not _high_lsb_entropy_hint(image):
        raise MCPAssertionError(
            "unsigned media not marked suspect (known-carrier LSB/luminance fixture miss)"
        )


def assert_signed_media_exempt(image: bytes, key: bytes | str) -> None:
    """Signed media with matching digest trailer is exempt from suspect bucket."""
    key_b = key.encode("utf-8") if isinstance(key, str) else key
    digest = hashlib.sha256(key_b + image.split(b"\n--SIG--\n")[0]).hexdigest()
    if b"\n--SIG--\n" not in image:
        raise MCPAssertionError("signed media missing signature trailer")
    trail = image.split(b"\n--SIG--\n", 1)[1].decode("ascii", errors="replace").strip()
    if trail != digest:
        raise MCPAssertionError("signed media signature mismatch (not exempt)")


def _high_lsb_entropy_hint(image: bytes) -> bool:
    """Cheap fixture heuristic: alternating LSB-ish pattern in prefix."""
    if len(image) < 16:
        return False
    prefix = image[:64]
    flips = sum(1 for i in range(1, len(prefix)) if (prefix[i] & 1) != (prefix[i - 1] & 1))
    return flips >= len(prefix) // 2


def sign_media_fixture(image: bytes, key: bytes | str) -> bytes:
    """Test helper: attach signature trailer."""
    key_b = key.encode("utf-8") if isinstance(key, str) else key
    digest = hashlib.sha256(key_b + image).hexdigest()
    return image + b"\n--SIG--\n" + digest.encode("ascii")


def mark_unsigned_suspect_fixture(image: bytes) -> bytes:
    """Test helper: embed known LSB suspect tag."""
    return image + _LSB_SUSPECT_TAG
