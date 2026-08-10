"""Import all ORM models so Base.metadata is fully populated.

Alembic's env.py and any create_all call must import this module.
"""

from __future__ import annotations

from app.auth.models import User  # noqa: F401
from app.git.models import GitConnection  # noqa: F401
from app.prerequisites.models import PrerequisiteInstance  # noqa: F401
from app.results.models import AiEvaluation, Artifact, TestRun  # noqa: F401
from app.runs.models import Run  # noqa: F401
from app.secrets.models import SecretEntry  # noqa: F401
from app.suites.models import Suite  # noqa: F401
