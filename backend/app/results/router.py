"""Test-run result routes (spec section 29)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.db.session import get_db
from app.results import service
from app.results.schemas import ArtifactOut, TestRunDetailOut

router = APIRouter(prefix="/api/test-runs", tags=["results"])


@router.get("/{test_run_id}", response_model=TestRunDetailOut)
def get_test_run(
    test_run_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> TestRunDetailOut:
    return service.get_test_run(db, test_run_id)


@router.get("/{test_run_id}/artifacts", response_model=list[ArtifactOut])
def list_artifacts(
    test_run_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[ArtifactOut]:
    return service.list_artifacts(db, test_run_id)


@router.get("/{test_run_id}/artifacts/download")
def download_all_artifacts(
    test_run_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> Response:
    """Download all files gathered for a test as a single zip."""
    data, filename = service.bundle_artifacts(db, test_run_id)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{test_run_id}/artifacts/{artifact_id}/download")
def download_artifact(
    test_run_id: str,
    artifact_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> FileResponse:
    """Download a single artifact file."""
    path, filename = service.get_artifact_download(db, test_run_id, artifact_id)
    return FileResponse(path=str(path), filename=filename, media_type="application/octet-stream")
