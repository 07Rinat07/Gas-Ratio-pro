"""Persistent renderer-neutral style presets for LAS Viewer interaction overlays."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable, Mapping

from services.las_viewer_interaction_overlay import LasViewerInteractionOverlayStyle


_SCHEMA = "las.viewer.interaction-overlay-presets"
_VERSION = "1.0"
_LEGACY_VERSION = "0.9"


def _clean_name(value: object) -> str:
    name = str(value or "").strip()
    if not name:
        raise ValueError("preset name cannot be empty")
    return name


@dataclass(frozen=True, slots=True)
class LasViewerOverlayPreset:
    name: str
    style: LasViewerInteractionOverlayStyle
    description: str = ""
    builtin: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _clean_name(self.name))
        object.__setattr__(self, "description", str(self.description or "").strip())
        object.__setattr__(
            self,
            "tags",
            tuple(dict.fromkeys(str(item).strip() for item in self.tags if str(item).strip())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "builtin": self.builtin,
            "tags": list(self.tags),
            "style": self.style.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LasViewerOverlayPreset":
        style = data.get("style")
        if not isinstance(style, Mapping):
            raise ValueError("overlay preset requires style")
        return cls(
            name=_clean_name(data.get("name")),
            description=str(data.get("description") or ""),
            builtin=bool(data.get("builtin", False)),
            tags=tuple(data.get("tags") or ()),
            style=LasViewerInteractionOverlayStyle.from_dict(style),
        )


class LasViewerOverlayPresetRepository:
    """Own named overlay presets and preserve deterministic ordering."""

    def __init__(self, presets: Iterable[LasViewerOverlayPreset] = ()) -> None:
        self._presets: dict[str, LasViewerOverlayPreset] = {}
        for preset in presets:
            self.save(preset, overwrite=False)

    @classmethod
    def with_defaults(cls) -> "LasViewerOverlayPresetRepository":
        return cls(
            (
                LasViewerOverlayPreset(
                    "Default",
                    LasViewerInteractionOverlayStyle(),
                    "Balanced cursor and selection overlay",
                    True,
                    ("default",),
                ),
                LasViewerOverlayPreset(
                    "High Contrast",
                    LasViewerInteractionOverlayStyle(
                        cursor_color="#000000",
                        cursor_width=2.0,
                        selection_accent="#ff3b30",
                        selection_opacity=1.0,
                    ),
                    "High visibility for field and presentation use",
                    True,
                    ("accessibility", "contrast"),
                ),
                LasViewerOverlayPreset(
                    "Presentation",
                    LasViewerInteractionOverlayStyle(
                        cursor_color="#1f4e79",
                        cursor_width=1.5,
                        cursor_opacity=0.85,
                        selection_accent="#f4b183",
                        selection_opacity=0.75,
                    ),
                    "Reduced opacity for clean presentations",
                    True,
                    ("presentation",),
                ),
            )
        )

    def save(self, preset: LasViewerOverlayPreset, *, overwrite: bool = True) -> LasViewerOverlayPreset:
        key = preset.name.casefold()
        current = self._presets.get(key)
        if current is not None and not overwrite:
            raise ValueError(f"overlay preset already exists: {preset.name}")
        if current is not None and current.builtin and not preset.builtin:
            raise ValueError("builtin overlay preset cannot be overwritten")
        self._presets[key] = preset
        return preset

    def get(self, name: str) -> LasViewerOverlayPreset:
        key = _clean_name(name).casefold()
        try:
            return self._presets[key]
        except KeyError as exc:
            raise KeyError(f"unknown overlay preset: {name}") from exc

    def delete(self, name: str) -> bool:
        key = _clean_name(name).casefold()
        preset = self._presets.get(key)
        if preset is None:
            return False
        if preset.builtin:
            raise ValueError("builtin overlay preset cannot be deleted")
        del self._presets[key]
        return True

    def list(self) -> tuple[LasViewerOverlayPreset, ...]:
        return tuple(sorted(self._presets.values(), key=lambda item: (not item.builtin, item.name.casefold())))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": _SCHEMA,
            "version": _VERSION,
            "presets": [item.to_dict() for item in self.list()],
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LasViewerOverlayPresetRepository":
        if str(data.get("schema") or "") != _SCHEMA:
            raise ValueError("unsupported overlay preset repository schema")
        version = str(data.get("version") or "").strip()
        if version not in {_VERSION, _LEGACY_VERSION}:
            raise ValueError(f"unsupported overlay preset repository version: {version or '<missing>'}")
        raw = data.get("presets")
        if not isinstance(raw, list):
            raise ValueError("overlay preset repository requires presets list")
        return cls(LasViewerOverlayPreset.from_dict(item) for item in raw if isinstance(item, Mapping))


class LasViewerOverlayPresetFileStore:
    """Atomically persist overlay preset repositories as UTF-8 JSON."""

    def save(self, path: str | os.PathLike[str], repository: LasViewerOverlayPresetRepository) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(repository.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        temp_name: str | None = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
                temp_name = handle.name
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
        return target

    def load(self, path: str | os.PathLike[str]) -> LasViewerOverlayPresetRepository:
        target = Path(path)
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise ValueError("overlay preset file must contain an object")
        return LasViewerOverlayPresetRepository.from_dict(data)

_EXCHANGE_SCHEMA = "las.viewer.interaction-overlay-preset-exchange"
_EXCHANGE_VERSION = "1.0"
_LEGACY_VERSION = "0.9"


@dataclass(frozen=True, slots=True)
class LasViewerOverlayPresetValidationResult:
    compatible: bool
    version: str
    preset_count: int
    preset_names: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    source_version: str = _EXCHANGE_VERSION
    migrated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "compatible": self.compatible,
            "version": self.version,
            "preset_count": self.preset_count,
            "preset_names": list(self.preset_names),
            "warnings": list(self.warnings),
            "source_version": self.source_version,
            "migrated": self.migrated,
        }


@dataclass(frozen=True, slots=True)
class LasViewerOverlayPresetImportResult:
    imported: tuple[str, ...] = field(default_factory=tuple)
    skipped: tuple[str, ...] = field(default_factory=tuple)
    replaced: tuple[str, ...] = field(default_factory=tuple)

    @property
    def changed(self) -> bool:
        return bool(self.imported or self.replaced)

    def to_dict(self) -> dict[str, Any]:
        return {
            "imported": list(self.imported),
            "skipped": list(self.skipped),
            "replaced": list(self.replaced),
            "changed": self.changed,
        }


class LasViewerOverlayPresetExchange:
    """Export and import portable overlay preset packages.

    Builtin presets are excluded by default because they are part of the
    application contract. Import collision policy is explicit: ``skip``,
    ``replace`` or ``error``.
    """

    _POLICIES = frozenset({"skip", "replace", "error"})
    _SUPPORTED_VERSIONS = frozenset({_EXCHANGE_VERSION, _LEGACY_VERSION})

    def migrate_package(self, package: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
        """Return a current-schema package without mutating the caller payload."""
        source_version = str(package.get("version") or "").strip()
        if source_version == _EXCHANGE_VERSION:
            return dict(package), ()
        if source_version != _LEGACY_VERSION:
            raise ValueError(f"unsupported overlay preset exchange version: {source_version or '<missing>'}")

        raw = package.get("presets")
        if not isinstance(raw, list):
            raise ValueError("overlay preset exchange requires presets list")
        migrated_presets: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise ValueError("overlay preset exchange contains invalid preset")
            style_raw = item.get("style", item.get("overlay_style"))
            if not isinstance(style_raw, Mapping):
                raise ValueError("overlay preset requires style")
            style = dict(style_raw)
            aliases = {
                "show_cursor": "cursor_visible",
                "show_selection": "selection_visible",
                "cursor_line_color": "cursor_color",
                "cursor_line_width": "cursor_width",
                "selection_color": "selection_accent",
            }
            for old, new in aliases.items():
                if new not in style and old in style:
                    style[new] = style[old]
            migrated_presets.append({
                "name": item.get("name", item.get("title")),
                "description": item.get("description", ""),
                "builtin": False,
                "tags": item.get("tags", item.get("labels", ())),
                "style": style,
            })
        return {
            "schema": _EXCHANGE_SCHEMA,
            "version": _EXCHANGE_VERSION,
            "renderer_neutral": package.get("renderer_neutral", True),
            "presets": migrated_presets,
        }, (f"package migrated from version {source_version} to {_EXCHANGE_VERSION}",)

    def validate_package(
        self, package: Mapping[str, Any]
    ) -> tuple[LasViewerOverlayPresetValidationResult, tuple[LasViewerOverlayPreset, ...]]:
        if str(package.get("schema") or "") != _EXCHANGE_SCHEMA:
            raise ValueError("unsupported overlay preset exchange schema")
        source_version = str(package.get("version") or "").strip()
        if source_version not in self._SUPPORTED_VERSIONS:
            raise ValueError(f"unsupported overlay preset exchange version: {source_version or '<missing>'}")
        package, migration_warnings = self.migrate_package(package)
        version = str(package.get("version") or "").strip()
        if package.get("renderer_neutral") is False:
            raise ValueError("overlay preset exchange package must be renderer neutral")
        raw = package.get("presets")
        if not isinstance(raw, list):
            raise ValueError("overlay preset exchange requires presets list")

        presets: list[LasViewerOverlayPreset] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, Mapping):
                raise ValueError("overlay preset exchange contains invalid preset")
            preset = LasViewerOverlayPreset.from_dict({**item, "builtin": False})
            key = preset.name.casefold()
            if key in seen:
                raise ValueError(f"duplicate overlay preset in exchange package: {preset.name}")
            seen.add(key)
            presets.append(preset)

        warnings: list[str] = list(migration_warnings)
        if "renderer_neutral" not in package:
            warnings.append("renderer_neutral flag is missing; legacy package accepted")
        result = LasViewerOverlayPresetValidationResult(
            compatible=True,
            version=version,
            preset_count=len(presets),
            preset_names=tuple(item.name for item in presets),
            warnings=tuple(warnings),
            source_version=source_version,
            migrated=source_version != _EXCHANGE_VERSION,
        )
        return result, tuple(presets)

    def inspect_package(self, package: Mapping[str, Any]) -> LasViewerOverlayPresetValidationResult:
        result, _ = self.validate_package(package)
        return result

    def export_dict(
        self,
        repository: LasViewerOverlayPresetRepository,
        *,
        names: Iterable[str] | None = None,
        include_builtin: bool = False,
    ) -> dict[str, Any]:
        selected_names = None if names is None else {_clean_name(name).casefold() for name in names}
        presets = []
        for preset in repository.list():
            if selected_names is not None and preset.name.casefold() not in selected_names:
                continue
            if preset.builtin and not include_builtin:
                continue
            item = preset.to_dict()
            # Imported packages must never acquire builtin protection.
            item["builtin"] = False
            presets.append(item)
        return {
            "schema": _EXCHANGE_SCHEMA,
            "version": _EXCHANGE_VERSION,
            "presets": presets,
            "renderer_neutral": True,
        }

    def import_dict(
        self,
        repository: LasViewerOverlayPresetRepository,
        package: Mapping[str, Any],
        *,
        collision: str = "skip",
    ) -> LasViewerOverlayPresetImportResult:
        policy = str(collision or "").strip().lower()
        if policy not in self._POLICIES:
            raise ValueError(f"unsupported overlay preset collision policy: {collision}")
        _, presets = self.validate_package(package)

        # Preflight every collision before mutating the repository. This keeps
        # imports transactional when the selected policy is ``error``.
        if policy == "error":
            for preset in presets:
                try:
                    current = repository.get(preset.name)
                except KeyError:
                    continue
                if current.builtin:
                    raise ValueError(f"builtin overlay preset cannot be replaced: {preset.name}")
                raise ValueError(f"overlay preset already exists: {preset.name}")

        imported: list[str] = []
        skipped: list[str] = []
        replaced: list[str] = []
        for preset in presets:
            try:
                current = repository.get(preset.name)
            except KeyError:
                current = None

            if current is None:
                repository.save(preset, overwrite=False)
                imported.append(preset.name)
                continue
            if current.builtin:
                if policy == "error":
                    raise ValueError(f"builtin overlay preset cannot be replaced: {preset.name}")
                skipped.append(preset.name)
                continue
            if policy == "skip":
                skipped.append(preset.name)
            elif policy == "error":
                raise ValueError(f"overlay preset already exists: {preset.name}")
            else:
                repository.save(preset, overwrite=True)
                replaced.append(preset.name)

        return LasViewerOverlayPresetImportResult(
            imported=tuple(imported),
            skipped=tuple(skipped),
            replaced=tuple(replaced),
        )

    def export_file(
        self,
        path: str | os.PathLike[str],
        repository: LasViewerOverlayPresetRepository,
        *,
        names: Iterable[str] | None = None,
        include_builtin: bool = False,
    ) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            self.export_dict(repository, names=names, include_builtin=include_builtin),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
        temp_name: str | None = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
                temp_name = handle.name
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
        return target

    def import_file(
        self,
        path: str | os.PathLike[str],
        repository: LasViewerOverlayPresetRepository,
        *,
        collision: str = "skip",
    ) -> LasViewerOverlayPresetImportResult:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise ValueError("overlay preset exchange file must contain an object")
        return self.import_dict(repository, data, collision=collision)

from datetime import datetime, timezone
from hashlib import sha256
import tempfile
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile


@dataclass(frozen=True, slots=True)
class LasViewerOverlayPresetBackupMetadata:
    path: str
    preset_count: int
    size_bytes: int
    checksum_sha256: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.interaction-overlay-preset-backup-metadata",
            "version": "1.0",
            "path": self.path,
            "preset_count": self.preset_count,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "created_at": self.created_at,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class LasViewerOverlayPresetRestoreResult:
    source_path: str
    restored_path: str
    preset_count: int
    checksum_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.interaction-overlay-preset-backup-restore",
            "version": "1.0",
            "source_path": self.source_path,
            "restored_path": self.restored_path,
            "preset_count": self.preset_count,
            "checksum_sha256": self.checksum_sha256,
            "renderer_neutral": True,
        }


class LasViewerOverlayPresetBackupService:
    """Create, validate and restore portable preset repository backups."""

    SCHEMA = "las.viewer.interaction-overlay-preset-backup"
    VERSION = "1.0"
    MANIFEST_NAME = "manifest.json"
    PAYLOAD_NAME = "overlay-presets.json"

    def create_backup(
        self,
        repository: LasViewerOverlayPresetRepository,
        destination: str | os.PathLike[str],
    ) -> LasViewerOverlayPresetBackupMetadata:
        target = Path(destination).expanduser()
        if target.exists() and target.is_dir():
            raise ValueError("overlay preset backup path points to a directory")
        target.parent.mkdir(parents=True, exist_ok=True)

        payload = self._canonical_bytes(repository.to_dict())
        created_at = datetime.now(timezone.utc).isoformat()
        manifest = {
            "schema": self.SCHEMA,
            "version": self.VERSION,
            "created_at": created_at,
            "preset_count": len(repository.list()),
            "payload": {
                "name": self.PAYLOAD_NAME,
                "size_bytes": len(payload),
                "checksum_sha256": sha256(payload).hexdigest(),
            },
        }

        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False
            ) as temporary:
                temporary_name = temporary.name
            with ZipFile(temporary_name, "w", compression=ZIP_DEFLATED) as archive:
                archive.writestr(self.MANIFEST_NAME, self._canonical_bytes(manifest))
                archive.writestr(self.PAYLOAD_NAME, payload)
            os.replace(temporary_name, target)
            temporary_name = None
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

        archive_bytes = target.read_bytes()
        return LasViewerOverlayPresetBackupMetadata(
            path=str(target),
            preset_count=len(repository.list()),
            size_bytes=len(archive_bytes),
            checksum_sha256=sha256(archive_bytes).hexdigest(),
            created_at=created_at,
        )

    def load_backup(
        self,
        source: str | os.PathLike[str],
    ) -> LasViewerOverlayPresetRepository:
        archive_path = Path(source).expanduser()
        if not archive_path.is_file():
            raise ValueError("overlay preset backup file does not exist")
        try:
            with ZipFile(archive_path, "r") as archive:
                manifest = self._load_manifest(archive)
                payload_info = manifest["payload"]
                try:
                    payload = archive.read(self.PAYLOAD_NAME)
                except KeyError as exc:
                    raise ValueError("overlay preset backup payload is missing") from exc
                if len(payload) != int(payload_info["size_bytes"]):
                    raise ValueError("overlay preset backup payload size mismatch")
                if sha256(payload).hexdigest() != str(payload_info["checksum_sha256"]):
                    raise ValueError("overlay preset backup payload checksum mismatch")
        except BadZipFile as exc:
            raise ValueError("overlay preset backup is not a valid ZIP archive") from exc

        try:
            document = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("overlay preset backup payload is invalid") from exc
        if not isinstance(document, Mapping):
            raise ValueError("overlay preset backup payload root must be an object")
        repository = LasViewerOverlayPresetRepository.from_dict(document)
        if len(repository.list()) != int(manifest["preset_count"]):
            raise ValueError("overlay preset backup preset count mismatch")
        return repository

    def restore_backup(
        self,
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
    ) -> LasViewerOverlayPresetRestoreResult:
        repository = self.load_backup(source)
        target = LasViewerOverlayPresetFileStore().save(destination, repository)
        content = target.read_bytes()
        return LasViewerOverlayPresetRestoreResult(
            source_path=str(Path(source).expanduser()),
            restored_path=str(target),
            preset_count=len(repository.list()),
            checksum_sha256=sha256(content).hexdigest(),
        )

    def delete_with_backup(
        self,
        repository: LasViewerOverlayPresetRepository,
        name: str,
        backup_path: str | os.PathLike[str],
    ) -> LasViewerOverlayPresetBackupMetadata:
        preset = repository.get(name)
        if preset.builtin:
            raise ValueError("builtin overlay preset cannot be deleted")
        metadata = self.create_backup(repository, backup_path)
        repository.delete(name)
        return metadata

    def _load_manifest(self, archive: ZipFile) -> Mapping[str, Any]:
        try:
            raw = archive.read(self.MANIFEST_NAME)
        except KeyError as exc:
            raise ValueError("overlay preset backup manifest is missing") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("overlay preset backup manifest is invalid") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("overlay preset backup manifest root must be an object")
        if payload.get("schema") != self.SCHEMA or payload.get("version") != self.VERSION:
            raise ValueError("unsupported overlay preset backup format")
        payload_info = payload.get("payload")
        if not isinstance(payload_info, Mapping) or payload_info.get("name") != self.PAYLOAD_NAME:
            raise ValueError("overlay preset backup manifest payload is invalid")
        if int(payload.get("preset_count") or 0) < 0:
            raise ValueError("overlay preset backup preset count is invalid")
        return payload

    @staticmethod
    def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
        return (
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
