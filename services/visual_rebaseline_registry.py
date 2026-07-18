"""Controlled semantic rebaseline registry for visual regression contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = "gas-ratio-pro.visual-rebaseline"
VERSION = "1.0"


def canonical_semantic_payload(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def semantic_sha256(value: Mapping[str, Any]) -> str:
    return sha256(canonical_semantic_payload(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class VisualRebaselineContract:
    id: str
    nodeid: str
    approved_release: str
    summary: str
    semantic_contract: Mapping[str, Any] = field(default_factory=dict)
    semantic_sha256: str = ""
    status: str = ""

    @property
    def valid(self) -> bool:
        return (
            self.id.startswith("LR-")
            and "::" in self.nodeid
            and self.approved_release == "v225.7"
            and bool(self.summary)
            and bool(self.semantic_contract)
            and self.semantic_sha256 == semantic_sha256(self.semantic_contract)
            and self.status == "approved"
        )

    def assert_matches(self, actual: Mapping[str, Any]) -> None:
        actual_hash = semantic_sha256(actual)
        if actual_hash != self.semantic_sha256:
            expected_text = canonical_semantic_payload(self.semantic_contract).decode("utf-8").strip()
            actual_text = canonical_semantic_payload(actual).decode("utf-8").strip()
            raise AssertionError(
                f"visual semantic contract mismatch for {self.nodeid}\n"
                f"expected_sha256={self.semantic_sha256}\n"
                f"actual_sha256={actual_hash}\n"
                f"expected={expected_text}\n"
                f"actual={actual_text}"
            )


@dataclass(frozen=True, slots=True)
class VisualRebaselineRegistry:
    release: str
    baseline_release: str
    contracts: tuple[VisualRebaselineContract, ...]
    policy: Mapping[str, bool]
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        ids = [item.id for item in self.contracts]
        nodeids = [item.nodeid for item in self.contracts]
        return (
            self.release == "v225.7"
            and len(self.contracts) == 13
            and len(ids) == len(set(ids))
            and len(nodeids) == len(set(nodeids))
            and all(item.valid for item in self.contracts)
            and all(self.policy.get(key) is True for key in (
                "review_required",
                "semantic_assertions_required",
                "no_unreviewed_hash_update",
                "no_trace_count_only_contract",
            ))
            and not self.issues
        )

    def by_nodeid(self, nodeid: str) -> VisualRebaselineContract:
        for item in self.contracts:
            if item.nodeid == nodeid:
                return item
        raise KeyError(f"visual rebaseline contract is not registered: {nodeid}")


class VisualRebaselineRegistryService:
    def load(self, path: Path | str) -> VisualRebaselineRegistry:
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        issues: list[str] = []
        if payload.get("schema") != SCHEMA:
            issues.append("unsupported_visual_rebaseline_schema")
        if str(payload.get("version") or "") != VERSION:
            issues.append("unsupported_visual_rebaseline_version")
        contracts: list[VisualRebaselineContract] = []
        for raw in _mapping_list(payload.get("contracts")):
            contract = VisualRebaselineContract(
                id=str(raw.get("id") or ""),
                nodeid=str(raw.get("nodeid") or ""),
                approved_release=str(raw.get("approved_release") or ""),
                summary=str(raw.get("summary") or ""),
                semantic_contract=_mapping(raw.get("semantic_contract")),
                semantic_sha256=str(raw.get("semantic_sha256") or ""),
                status=str(raw.get("status") or ""),
            )
            if not contract.valid:
                issues.append(f"invalid_visual_rebaseline_contract:{contract.id or contract.nodeid}")
            contracts.append(contract)
        if len(contracts) != int(payload.get("contract_count") or 0):
            issues.append("visual_rebaseline_count_mismatch")
        return VisualRebaselineRegistry(
            release=str(payload.get("release") or ""),
            baseline_release=str(payload.get("baseline_release") or ""),
            contracts=tuple(contracts),
            policy={str(key): bool(value) for key, value in _mapping(payload.get("policy")).items()},
            issues=tuple(dict.fromkeys(issues)),
        )

    def assert_semantic(self, path: Path | str, nodeid: str, actual: Mapping[str, Any]) -> None:
        registry = self.load(path)
        if not registry.ok:
            raise AssertionError(f"visual rebaseline registry is invalid: {registry.issues}")
        registry.by_nodeid(nodeid).assert_matches(actual)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return round(value, 6)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


__all__ = [
    "VisualRebaselineContract",
    "VisualRebaselineRegistry",
    "VisualRebaselineRegistryService",
    "canonical_semantic_payload",
    "semantic_sha256",
]
