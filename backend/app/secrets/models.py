"""Encrypted secret storage backing table (plan open-decision D4).

We never store plaintext secrets. The application stores a secret_reference
elsewhere (e.g. git_connections.secret_reference) and the actual value lives
here encrypted at rest with a Fernet key.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at_column, uuid_str


class SecretEntry(Base):
    __tablename__ = "secrets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = created_at_column()
