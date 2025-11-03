from __future__ import annotations

from pathlib import Path

from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework import viewsets
from rest_framework.decorators import action

from config.paths import resolve_storage_root

from apps.platform.authorization.access_policies import ArtifactAccessPolicy
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.artifacts.serializers import CaseArtifactSerializer
from apps.platform.operations.audit import emit as audit_emit
from apps.platform.tenancy import scope_artifacts


class ArtifactViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CaseArtifact.objects.all()
    serializer_class = CaseArtifactSerializer
    permission_classes = [ArtifactAccessPolicy]

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset().select_related("case_fk", "case_fk__organization")
        case_id = self.request.query_params.get("case")
        if case_id:
            qs = qs.filter(Q(case_id=case_id) | Q(case_fk__id=case_id))
        user = getattr(self.request, "user", None)
        return scope_artifacts(qs, user)

    def retrieve(self, request, *args, **kwargs):  # type: ignore[override]
        resp = super().retrieve(request, *args, **kwargs)
        try:
            obj = self.get_object()
            audit_emit(request, case_id=obj.case_id, event="artifact.retrieve", data={"artifact_id": obj.id, "type": obj.type})
        except Exception:
            pass
        return resp

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        resp = super().list(request, *args, **kwargs)
        try:
            case_id = request.query_params.get("case")
            audit_emit(request, case_id=case_id, event="artifact.list", data={"count": len(resp.data) if hasattr(resp, 'data') else None})
        except Exception:
            pass
        return resp

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, *args, **kwargs):
        artifact = self.get_object()
        path_value = artifact.path or ""
        path_obj = Path(path_value)
        if not path_obj.exists():
            raise Http404
        storage_root = resolve_storage_root().resolve()
        try:
            is_relative = path_obj.resolve().is_relative_to(storage_root)
        except AttributeError:
            is_relative = str(path_obj.resolve()).startswith(str(storage_root))
        if not is_relative:
            raise Http404
        try:
            audit_emit(
                request,
                case_id=artifact.case_id,
                event="artifact.download",
                data={"artifact_id": artifact.id, "type": artifact.type},
            )
        except Exception:
            pass
        return FileResponse(path_obj.open("rb"), filename=path_obj.name, as_attachment=True)
