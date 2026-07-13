from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from time import perf_counter
from typing import Any, Callable, MutableMapping


@dataclass(frozen=True, slots=True)
class ExportRequest:
    project_id: str
    project_name: str
    source_label: str
    profile_id: str
    format_id: str
    format_label: str
    extension: str
    mime_type: str
    depth_top: float
    depth_bottom: float
    source_signature: str
    calculation_revision: int
    presentation_revision: int
    figure_height: int
    context_signature: str = ""

    @property
    def normalized_depth_range(self) -> tuple[float, float]:
        return (min(self.depth_top, self.depth_bottom), max(self.depth_top, self.depth_bottom))

    @property
    def selection_signature(self) -> str:
        """Stable signature of every user-visible export choice.

        The signature is stored together with the prepared artifact.  The UI can
        therefore detect that a profile, format or depth range has changed and
        avoid offering a stale file as if it matched the current controls.
        """
        top, bottom = self.normalized_depth_range
        payload = "|".join(
            (
                self.project_id,
                self.source_signature,
                str(self.calculation_revision),
                str(self.presentation_revision),
                self.profile_id,
                self.format_id,
                self.extension.lower().lstrip("."),
                self.mime_type.lower(),
                f"{top:.6f}",
                f"{bottom:.6f}",
                str(self.figure_height),
                self.context_signature,
            )
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    def validate(self) -> None:
        required = {
            "project_id": self.project_id,
            "profile_id": self.profile_id,
            "format_id": self.format_id,
            "extension": self.extension,
            "mime_type": self.mime_type,
            "source_signature": self.source_signature,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise ValueError(f"Не заполнены обязательные параметры экспорта: {', '.join(missing)}.")
        if not isfinite(float(self.depth_top)) or not isfinite(float(self.depth_bottom)):
            raise ValueError("Границы глубины должны быть конечными числами.")
        if self.figure_height < 400 or self.figure_height > 12000:
            raise ValueError("Высота экспортируемого графика должна быть в диапазоне 400–12000 px.")
        if self.calculation_revision < 0 or self.presentation_revision < 0:
            raise ValueError("Ревизии расчёта и представления не могут быть отрицательными.")


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    content: bytes
    file_name: str
    mime_type: str
    format_id: str
    format_label: str
    profile_id: str
    request_signature: str = ""
    cache_hit: bool = False

    def validate(self) -> None:
        if not isinstance(self.content, (bytes, bytearray)) or not self.content:
            raise ValueError("Renderer вернул пустой экспортный файл.")
        if not self.file_name.strip():
            raise ValueError("Renderer не задал имя экспортного файла.")
        if not self.mime_type.strip():
            raise ValueError("Renderer не задал MIME-тип экспортного файла.")


@dataclass(frozen=True, slots=True)
class ExportFailure:
    error_id: str
    stage: str
    exception_type: str
    message: str


class ExportControllerError(RuntimeError):
    def __init__(self, failure: ExportFailure) -> None:
        super().__init__(failure.message)
        self.failure = failure


def normalize_export_form_state(
    state: MutableMapping[str, Any],
    *,
    project_id: str,
    profile_labels: tuple[str, ...],
    format_labels: tuple[str, ...],
    print_modes: tuple[str, ...],
    depth_min: float,
    depth_max: float,
    default_top: float,
    default_bottom: float,
) -> dict[str, Any]:
    """Normalize persisted Professional Export widget values before rendering.

    Streamlit keeps widget values across reruns. After loading another LAS or
    changing the active interval, persisted depth values may fall outside the
    new widget bounds and cause the first render of the export panel to fail.
    This helper validates every dynamic field before the widgets are created.
    """
    low = min(float(depth_min), float(depth_max))
    high = max(float(depth_min), float(depth_max))

    def _choice(key: str, options: tuple[str, ...], fallback: str) -> str:
        value = state.get(key)
        if value not in options:
            value = fallback
            state[key] = value
        return str(value)

    def _bounded_number(key: str, fallback: float) -> float:
        value = state.get(key, fallback)
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = float(fallback)
        if not isfinite(value):
            value = float(fallback)
        value = max(low, min(high, value))
        state[key] = value
        return value

    profile_key = f"presentation_report_profile_{project_id}"
    format_key = f"presentation_export_format_{project_id}"
    mode_key = f"presentation_print_depth_mode_{project_id}"
    top_key = f"presentation_print_top_{project_id}"
    bottom_key = f"presentation_print_bottom_{project_id}"

    profile = _choice(profile_key, profile_labels, profile_labels[0])
    export_format = _choice(format_key, format_labels, format_labels[0])
    print_mode = _choice(mode_key, print_modes, print_modes[0])
    top = _bounded_number(top_key, default_top)
    bottom = _bounded_number(bottom_key, default_bottom)

    return {
        "profile": profile,
        "format": export_format,
        "print_mode": print_mode,
        "top": top,
        "bottom": bottom,
        "keys": {
            "profile": profile_key,
            "format": format_key,
            "print_mode": mode_key,
            "top": top_key,
            "bottom": bottom_key,
        },
    }


class ExportController:
    """Renderer-neutral, transactional export orchestration.

    The controller has no Streamlit dependency. It validates the request before
    any expensive work, isolates model building from format rendering, prevents
    duplicate concurrent submissions in one session and keeps bounded LRU
    caches so long engineering sessions do not grow memory without limit.
    """

    MODEL_CACHE_KEY = "presentation_export_model_cache_v222"
    ARTIFACT_CACHE_KEY = "presentation_export_artifact_cache_v222"
    INFLIGHT_KEY = "presentation_export_inflight_v222"
    MODEL_CACHE_LIMIT = 8
    ARTIFACT_CACHE_LIMIT = 16
    ARTIFACT_CACHE_MAX_BYTES = 64 * 1024 * 1024

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self._state = state

    def _model_cache_key(self, request: ExportRequest) -> str:
        top, bottom = request.normalized_depth_range
        payload = "|".join(
            (
                request.project_id,
                request.source_signature,
                str(request.calculation_revision),
                str(request.presentation_revision),
                request.profile_id,
                f"{top:.6f}",
                f"{bottom:.6f}",
                request.context_signature,
            )
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    def _artifact_cache_key(self, request: ExportRequest, model_key: str) -> str:
        payload = "|".join((model_key, request.format_id, str(request.figure_height)))
        return sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _failure(stage: str, exc: BaseException) -> ExportControllerError:
        digest = sha256(f"{stage}|{type(exc).__name__}|{exc}".encode("utf-8")).hexdigest()[:10]
        return ExportControllerError(
            ExportFailure(
                error_id=f"export-{digest}",
                stage=stage,
                exception_type=type(exc).__name__,
                message=str(exc) or type(exc).__name__,
            )
        )

    def _lru_cache(self, key: str) -> OrderedDict[str, Any]:
        cache = self._state.get(key)
        if not isinstance(cache, OrderedDict):
            cache = OrderedDict(cache if isinstance(cache, dict) else {})
            self._state[key] = cache
        return cache

    @staticmethod
    def _touch(cache: OrderedDict[str, Any], key: str) -> Any:
        value = cache.pop(key)
        cache[key] = value
        return value

    @staticmethod
    def _trim(cache: OrderedDict[str, Any], limit: int) -> tuple[str, ...]:
        """Trim an LRU cache and return the evicted keys."""
        evicted: list[str] = []
        while len(cache) > limit:
            key, _ = cache.popitem(last=False)
            evicted.append(key)
        return tuple(evicted)

    @staticmethod
    def _artifact_cache_bytes(cache: OrderedDict[str, Any]) -> int:
        """Return retained binary payload size without serializing artifacts."""
        total = 0
        for value in cache.values():
            if isinstance(value, ExportArtifact):
                total += len(value.content)
        return total

    @classmethod
    def _trim_artifacts(cls, cache: OrderedDict[str, Any]) -> tuple[str, ...]:
        """Bound artifact cache by entry count and actual retained bytes.

        Entry-only limits are unsafe for PDF/DOCX/PNG workloads because one
        high-resolution artifact can be much larger than many ordinary files.
        The newest artifact is kept only when it fits the configured budget.
        """
        evicted: list[str] = []
        while cache and (
            len(cache) > cls.ARTIFACT_CACHE_LIMIT
            or cls._artifact_cache_bytes(cache) > cls.ARTIFACT_CACHE_MAX_BYTES
        ):
            key, _ = cache.popitem(last=False)
            evicted.append(key)
        return tuple(evicted)

    @staticmethod
    def _validate_artifact_contract(artifact: ExportArtifact, request: ExportRequest) -> ExportArtifact:
        """Validate renderer output against the original export request."""
        artifact.validate()
        expected_extension = request.extension.lower().lstrip(".")
        actual_extension = artifact.file_name.rsplit(".", 1)[-1].lower() if "." in artifact.file_name else ""
        mismatches: list[str] = []
        if artifact.format_id != request.format_id:
            mismatches.append("format_id")
        if artifact.profile_id != request.profile_id:
            mismatches.append("profile_id")
        if artifact.mime_type.lower() != request.mime_type.lower():
            mismatches.append("mime_type")
        # The renderer contract owns format/profile/MIME.  The download name is
        # normalized centrally because legacy DOCX renderers may return a safe
        # basename without a suffix even though their bytes and MIME are valid.
        # Rejecting such a file caused repeatable first-use DOCX failures.
        if mismatches:
            raise ValueError(
                "Renderer вернул файл, не соответствующий запросу: " + ", ".join(mismatches) + "."
            )
        # Validate the binary container as well as metadata.  Renaming PDF bytes
        # to .docx (or a DOCX ZIP container to .pdf) creates a deceptively valid
        # download that fails only when the user opens it.
        content = bytes(artifact.content)
        signature_ok = True
        if request.format_id == "pdf":
            signature_ok = content.startswith(b"%PDF-")
        elif request.format_id == "docx":
            signature_ok = content.startswith(b"PK\x03\x04") and b"[Content_Types].xml" in content[:65536]
        elif request.format_id == "png":
            signature_ok = content.startswith(b"\x89PNG\r\n\x1a\n")
        elif request.format_id == "svg":
            signature_ok = content.lstrip().startswith((b"<svg", b"<?xml"))
        elif request.format_id == "xlsx":
            signature_ok = content.startswith(b"PK\x03\x04")
        if not signature_ok:
            raise ValueError("Renderer вернул бинарные данные другого формата.")

        normalized_file_name = artifact.file_name.strip()
        if actual_extension != expected_extension:
            stem = normalized_file_name.rsplit(".", 1)[0] if "." in normalized_file_name else normalized_file_name
            normalized_file_name = f"{stem}.{expected_extension}"
        return ExportArtifact(
            content=content,
            file_name=normalized_file_name,
            mime_type=artifact.mime_type,
            format_id=artifact.format_id,
            format_label=artifact.format_label,
            profile_id=artifact.profile_id,
            request_signature=request.selection_signature,
            cache_hit=artifact.cache_hit,
        )

    def prepare(
        self,
        request: ExportRequest,
        *,
        frame: Any,
        build_model: Callable[[Any, ExportRequest], Any],
        render_artifact: Callable[[Any, Any, ExportRequest], ExportArtifact],
        on_progress: Callable[[int, str], None] | None = None,
        check_cancelled: Callable[[], None] | None = None,
    ) -> tuple[ExportArtifact, dict[str, float | bool]]:
        def _progress(value: int, message: str) -> None:
            if check_cancelled is not None:
                check_cancelled()
            if on_progress is not None:
                on_progress(max(0, min(100, int(value))), message)

        _progress(2, "Проверка параметров экспорта.")
        try:
            request.validate()
        except Exception as exc:
            raise self._failure("validate_request", exc) from exc

        model_key = self._model_cache_key(request)
        artifact_key = self._artifact_cache_key(request, model_key)
        model_cache = self._lru_cache(self.MODEL_CACHE_KEY)
        artifact_cache = self._lru_cache(self.ARTIFACT_CACHE_KEY)
        registry = self._state.setdefault("presentation_export_cache_registry_v222", {})
        if not isinstance(registry, dict):
            registry = {}
            self._state["presentation_export_cache_registry_v222"] = registry
        inflight = self._state.setdefault(self.INFLIGHT_KEY, set())
        if not isinstance(inflight, set):
            inflight = set()
            self._state[self.INFLIGHT_KEY] = inflight

        if artifact_key in artifact_cache:
            _progress(95, "Используется готовый файл из кэша.")
            cached_artifact = self._touch(artifact_cache, artifact_key)
            if isinstance(cached_artifact, ExportArtifact):
                return (
                    ExportArtifact(
                        content=cached_artifact.content,
                        file_name=cached_artifact.file_name,
                        mime_type=cached_artifact.mime_type,
                        format_id=cached_artifact.format_id,
                        format_label=cached_artifact.format_label,
                        profile_id=cached_artifact.profile_id,
                        request_signature=cached_artifact.request_signature,
                        cache_hit=True,
                    ),
                    {"model_cache_hit": True, "artifact_cache_hit": True, "duration_ms": 0.0},
                )

        if artifact_key in inflight:
            raise self._failure("duplicate_request", RuntimeError("Этот формат уже подготавливается."))

        inflight.add(artifact_key)
        started = perf_counter()
        try:
            _progress(10, "Подготовка модели отчёта.")
            model_cache_hit = model_key in model_cache
            if model_cache_hit:
                model = self._touch(model_cache, model_key)
            else:
                try:
                    _progress(20, "Формируется инженерная модель отчёта.")
                    model = build_model(frame, request)
                except Exception as exc:
                    raise self._failure("build_model", exc) from exc
                model_cache[model_key] = model
                registry[model_key] = request.project_id
                for evicted_key in self._trim(model_cache, self.MODEL_CACHE_LIMIT):
                    registry.pop(evicted_key, None)

            _progress(55, f"Формируется файл {request.format_label}.")
            try:
                artifact = render_artifact(model, frame, request)
            except ExportControllerError:
                raise
            except Exception as exc:
                raise self._failure(f"render_{request.format_id}", exc) from exc

            _progress(90, "Проверяется формат готового файла.")
            try:
                artifact = self._validate_artifact_contract(artifact, request)
            except ExportControllerError:
                raise
            except Exception as exc:
                raise self._failure(f"render_{request.format_id}", exc) from exc

            artifact_cache[artifact_key] = artifact
            registry[artifact_key] = request.project_id
            _progress(100, "Экспорт завершён.")
            for evicted_key in self._trim_artifacts(artifact_cache):
                registry.pop(evicted_key, None)
            return (
                artifact,
                {
                    "model_cache_hit": model_cache_hit,
                    "artifact_cache_hit": False,
                    "duration_ms": (perf_counter() - started) * 1000.0,
                },
            )
        finally:
            inflight.discard(artifact_key)

    def clear_project_cache(self, project_id: str) -> None:
        # Cache keys are hashes, therefore project-aware invalidation uses the
        # metadata registry recorded alongside each key.
        registry = self._state.get("presentation_export_cache_registry_v222", {})
        for cache_name in (self.MODEL_CACHE_KEY, self.ARTIFACT_CACHE_KEY):
            cache = self._state.get(cache_name)
            if not isinstance(cache, MutableMapping):
                continue
            keys = [key for key, owner in registry.items() if owner == project_id and key in cache]
            for key in keys:
                cache.pop(key, None)
                registry.pop(key, None)
        self._state[self.INFLIGHT_KEY] = set()

    def cache_sizes(self) -> tuple[int, int]:
        model_cache = self._state.get(self.MODEL_CACHE_KEY, {})
        artifact_cache = self._state.get(self.ARTIFACT_CACHE_KEY, {})
        return (len(model_cache), len(artifact_cache))

    def cache_metrics(self) -> dict[str, int]:
        """Expose lightweight diagnostics for UI and performance audits."""
        model_cache = self._state.get(self.MODEL_CACHE_KEY, {})
        artifact_cache = self._state.get(self.ARTIFACT_CACHE_KEY, {})
        artifact_bytes = (
            self._artifact_cache_bytes(artifact_cache)
            if isinstance(artifact_cache, OrderedDict)
            else sum(
                len(value.content)
                for value in artifact_cache.values()
                if isinstance(value, ExportArtifact)
            )
            if isinstance(artifact_cache, dict)
            else 0
        )
        return {
            "model_entries": len(model_cache) if isinstance(model_cache, dict) else 0,
            "artifact_entries": len(artifact_cache) if isinstance(artifact_cache, dict) else 0,
            "artifact_bytes": artifact_bytes,
            "artifact_max_bytes": self.ARTIFACT_CACHE_MAX_BYTES,
        }
