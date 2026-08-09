"""SecretStore: encrypt secrets at rest, expose only opaque references.

Plan open-decision D4. Tokens are encrypted with a Fernet key and stored in the
`secrets` table. Callers receive/keep only the reference (the row id). The raw
plaintext is never logged, returned to the frontend, or stored unencrypted.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError
from app.secrets.models import SecretEntry


class SecretStore:
    def __init__(self, db: Session) -> None:
        self._db = db
        key = get_settings().secret_encryption_key
        if not key:
            self._fernet: Fernet | None = None
        else:
            self._fernet = Fernet(key.encode("utf-8"))

    def _require_fernet(self) -> Fernet:
        if self._fernet is None:
            raise ApiError(
                code="SECRET_STORE_UNCONFIGURED",
                message="Secret storage is not configured. Set DRIVETEST_SECRET_ENCRYPTION_KEY.",
                status_code=500,
            )
        return self._fernet

    def store(self, plaintext: str) -> str:
        """Encrypt and persist a secret. Returns an opaque reference."""
        fernet = self._require_fernet()
        entry = SecretEntry(ciphertext=fernet.encrypt(plaintext.encode("utf-8")))
        self._db.add(entry)
        self._db.flush()
        return entry.id

    def reveal(self, reference: str) -> str:
        """Decrypt a secret by reference. Only used inside the backend, never exposed."""
        fernet = self._require_fernet()
        entry = self._db.get(SecretEntry, reference)
        if entry is None:
            raise ApiError(code="SECRET_NOT_FOUND", message="Secret reference not found.", status_code=404)
        try:
            return fernet.decrypt(entry.ciphertext).decode("utf-8")
        except InvalidToken as exc:  # pragma: no cover - indicates key mismatch
            raise ApiError(
                code="SECRET_DECRYPT_FAILED",
                message="Secret could not be decrypted.",
                status_code=500,
            ) from exc

    def delete(self, reference: str) -> None:
        entry = self._db.get(SecretEntry, reference)
        if entry is not None:
            self._db.delete(entry)
            self._db.flush()

    @staticmethod
    def generate_key() -> str:
        """Helper to mint a new Fernet key for .env setup."""
        return Fernet.generate_key().decode("utf-8")
