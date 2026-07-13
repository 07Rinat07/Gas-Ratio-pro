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

    @property
    def normalized_depth_range(self) -> tuple[float, float]:
        return (min(self.depth_top, self.depth_bottom), max(self.depth_top, self.depth_bottom))

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
    def _trim(cache: OrderedDict[str, Any], limit: int) -> None:
        while len(cache) > limit:
            cache.popitem(last=False)

    def prepare(
        self,
        request: ExportRequest,
        *,
        frame: Any,
        build_model: Callable[[Any, ExportRequest], Any],
        render_artifact: Callable[[Any, Any, ExportRequest], ExportArtifact],
    ) -> tuple[ExportArtifact, dict[str, float | bool]]:
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
                        cache_hit=True,
                    ),
                    {"model_cache_hit": True, "artifact_cache_hit": True, "duration_ms": 0.0},
                )

        if artifact_key in inflight:
            raise self._failure("duplicate_request", RuntimeError("Этот формат уже подготавливается."))

        inflight.add(artifact_key)
        started = perf_counter()
        try:
            model_cache_hit = model_key in model_cache
            if model_cache_hit:
                model = self._touch(model_cache, model_key)
            else:
                try:
                    model = build_model(frame, request)
                except Exception as exc:
                    raise self._failure("build_model", exc) from exc
                model_cache[model_key] = model
                registry[model_key] = request.project_id
                self._trim(model_cache, self.MODEL_CACHE_LIMIT)

            try:
                artifact = render_artifact(model, frame, request)
                artifact.validate()
            except ExportControllerError:
                raise
            except Exception as exc:
                raise self._failure(f"render_{request.format_id}", exc) from exc

            artifact_cache[artifact_key] = artifact
            registry[artifact_key] = request.project_id
            self._trim(artifact_cache, self.ARTIFACT_CACHE_LIMIT)
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
