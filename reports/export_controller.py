from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
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


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    content: bytes
    file_name: str
    mime_type: str
    format_id: str
    format_label: str
    profile_id: str
    cache_hit: bool = False


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
    """Renderer-neutral export orchestration with model/artifact caching.

    The controller deliberately has no Streamlit dependency. It isolates the
    expensive report model build from format rendering, so switching PDF/DOCX/
    XLSX does not rebuild the engineering interpretation model.
    """

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

    def prepare(
        self,
        request: ExportRequest,
        *,
        frame: Any,
        build_model: Callable[[Any, ExportRequest], Any],
        render_artifact: Callable[[Any, Any, ExportRequest], ExportArtifact],
    ) -> tuple[ExportArtifact, dict[str, float | bool]]:
        model_key = self._model_cache_key(request)
        artifact_key = self._artifact_cache_key(request, model_key)
        model_cache = self._state.setdefault("presentation_export_model_cache_v222", {})
        artifact_cache = self._state.setdefault("presentation_export_artifact_cache_v222", {})

        cached_artifact = artifact_cache.get(artifact_key)
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

        started = perf_counter()
        model_cache_hit = model_key in model_cache
        if model_cache_hit:
            model = model_cache[model_key]
        else:
            try:
                model = build_model(frame, request)
            except Exception as exc:  # pragma: no cover - exercised via integration tests
                raise self._failure("build_model", exc) from exc
            model_cache[model_key] = model

        try:
            artifact = render_artifact(model, frame, request)
        except Exception as exc:  # pragma: no cover - exercised via integration tests
            raise self._failure(f"render_{request.format_id}", exc) from exc

        artifact_cache[artifact_key] = artifact
        return (
            artifact,
            {
                "model_cache_hit": model_cache_hit,
                "artifact_cache_hit": False,
                "duration_ms": (perf_counter() - started) * 1000.0,
            },
        )

    def clear_project_cache(self, project_id: str) -> None:
        # Cache keys are hashed, so a full export-cache reset is safer and cheap.
        self._state.pop("presentation_export_model_cache_v222", None)
        self._state.pop("presentation_export_artifact_cache_v222", None)
