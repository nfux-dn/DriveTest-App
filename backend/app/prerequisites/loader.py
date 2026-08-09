"""Resolve a prerequisite template for a (suite, platform, system_type).

Layering (each layer optional, sections concatenated, later fields override
earlier fields with the same id), per spec section 9/14 directory model:

    prerequisites/<suite_id>/common.yaml
    prerequisites/<suite_id>/<platform>/default.yaml
    prerequisites/<suite_id>/<platform>/<system_type>.yaml
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from app.core.errors import ApiError
from app.prerequisites.schemas import (
    PrerequisiteField,
    PrerequisiteSection,
    PrerequisiteTemplate,
)

logger = logging.getLogger("drivetest.prerequisites.loader")


def _read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _candidate_files(definitions_dir: Path, suite_id: str, platform: str | None, system_type: str | None) -> list[Path]:
    base = definitions_dir / "prerequisites" / suite_id
    candidates = [base / "common.yaml"]
    if platform:
        candidates.append(base / platform / "default.yaml")
        if system_type:
            candidates.append(base / platform / f"{system_type}.yaml")
    return candidates


def resolve_template(
    definitions_dir: Path,
    suite_id: str,
    platform: str | None,
    system_type: str | None,
) -> PrerequisiteTemplate:
    files = [p for p in _candidate_files(definitions_dir, suite_id, platform, system_type) if p.exists()]
    if not files:
        raise ApiError(
            code="PREREQUISITE_TEMPLATE_NOT_FOUND",
            message=f"No prerequisite template found for suite '{suite_id}'.",
            status_code=404,
        )

    merged_sections: dict[str, PrerequisiteSection] = {}
    version = 1
    template_id = suite_id

    for path in files:
        data = _read_yaml(path)
        version = max(version, int(data.get("version", 1) or 1))
        template_id = data.get("id", template_id)
        for raw_section in data.get("sections", []) or []:
            section = _parse_section(raw_section, path)
            existing = merged_sections.get(section.id)
            if existing is None:
                merged_sections[section.id] = section
            else:
                _merge_fields(existing, section)

    template = PrerequisiteTemplate(
        id=template_id,
        version=version,
        suite_id=suite_id,
        sections=list(merged_sections.values()),
    )
    logger.info(
        "prerequisite_template_resolved suite=%s platform=%s system=%s sections=%d",
        suite_id,
        platform,
        system_type,
        len(template.sections),
    )
    return template


def _parse_section(raw: dict, path: Path) -> PrerequisiteSection:
    try:
        return PrerequisiteSection(
            id=raw["id"],
            title=raw.get("title", raw["id"]),
            fields=[PrerequisiteField(**f) for f in raw.get("fields", []) or []],
        )
    except (KeyError, TypeError) as exc:
        raise ApiError(
            code="PREREQUISITE_TEMPLATE_INVALID",
            message=f"Invalid prerequisite section in {path.name}: {exc}",
            status_code=500,
        ) from exc


def _merge_fields(existing: PrerequisiteSection, incoming: PrerequisiteSection) -> None:
    by_id = {f.id: f for f in existing.fields}
    for field in incoming.fields:
        by_id[field.id] = field  # later layer overrides
    existing.fields = list(by_id.values())
