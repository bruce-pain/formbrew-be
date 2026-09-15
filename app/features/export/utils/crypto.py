from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    raw = settings.GOOGLE_SHEETS_TOKEN_ENCRYPTION_KEY
    if not raw:
        raise ValueError(
            "GOOGLE_SHEETS_TOKEN_ENCRYPTION_KEY must be set (Fernet.generate_key())"
        )
    try:
        return Fernet(raw.encode("utf-8"))
    except Exception as exc:
        raise ValueError(
            "GOOGLE_SHEETS_TOKEN_ENCRYPTION_KEY must be a valid Fernet key"
        ) from exc


def encrypt_token(token: str) -> str:
    """Encrypt a refresh token for storage."""
    return _fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored refresh token. Raises InvalidToken if the key changed."""
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
