from __future__ import annotations

from pathlib import Path
from typing import Any

from django.db.models import Q, QuerySet
from django.http import FileResponse, Http404, HttpRequest
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.artifacts.serializers import CaseArtifactSerializer
from apps.platform.authorization.access_policies import ArtifactAccessPolicy
from apps.platform.operations.audit import emit as audit_emit
from apps.platform.tenancy import scope_artifacts
from config.paths import resolve_storage_root


def _as_django_request(request: Request | HttpRequest) -> HttpRequest | None:
    if isinstance(request, HttpRequest):
        return request
    inner = getattr(request, "_request", None)
    return inner if isinstance(inner, HttpRequest) else None


class ArtifactViewSet(RetrieveModelMixin, ListModelMixin, viewsets.GenericViewSet):
    queryset: QuerySet[CaseArtifact] = CaseArtifact.objects.all()
    serializer_class = CaseArtifactSerializer
    permission_classes = [ArtifactAccessPolicy]

    def get_queryset(self) -> QuerySet[CaseArtifact]:
        qs = CaseArtifact.objects.select_related("case_fk", "case_fk__organization")
        case_id = (
            self.request.query_params.get("case") if hasattr(self.request, "query_params") else None
        )
        if case_id:
            qs = qs.filter(Q(case_id=case_id) | Q(case_fk__id=case_id))
        user = getattr(self.request, "user", None)
        return scope_artifacts(qs, user)

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        resp: Response = super().retrieve(request, *args, **kwargs)
        django_request = _as_django_request(request)
        try:
            obj = self.get_object()
            if django_request is not None:
                audit_emit(
                    django_request,
                    case_id=obj.case_id,
                    event="artifact.retrieve",
                    data={"artifact_id": obj.id, "type": obj.type},
                )
        except Exception:
            pass
        return resp

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        resp: Response = super().list(request, *args, **kwargs)
        django_request = _as_django_request(request)
        try:
            case_id = request.query_params.get("case")
            count = None
            data = getattr(resp, "data", None)
            if isinstance(data, list):
                count = len(data)
            if django_request is not None:
                audit_emit(
                    django_request,
                    case_id=case_id,
                    event="artifact.list",
                    data={"count": count},
                )
        except Exception:
            pass
        return resp

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request: Request, *args: Any, **kwargs: Any) -> FileResponse:
        artifact = self.get_object()
        path_value = artifact.path or ""
        storage_root = resolve_storage_root().resolve()
        path_obj = Path(path_value)
        if not path_obj.is_absolute():
            path_obj = storage_root / path_obj
        try:
            candidate = path_obj.resolve()
        except OSError:
            raise Http404 from None
        if not candidate.exists():
            raise Http404
        try:
            if candidate.is_dir() or not candidate.is_relative_to(storage_root):
                raise Http404
        except AttributeError:
            storage_str = str(storage_root)
            if not str(candidate).startswith(storage_str):
                raise Http404
        django_request = _as_django_request(request)
        try:
            if django_request is not None:
                audit_emit(
                    django_request,
                    case_id=artifact.case_id,
                    event="artifact.download",
                    data={"artifact_id": artifact.id, "type": artifact.type},
                )
        except Exception:
            pass
        return FileResponse(candidate.open("rb"), as_attachment=True, filename=candidate.name)
