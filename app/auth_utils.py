import secrets
from typing import Dict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from . import models

# token -> user_id
TOKENS: Dict[str, int] = {}


def create_token_for_user(user: models.Usuario) -> str:
    """Genera un token aleatorio y lo asocia al usuario en memoria."""
    token = secrets.token_hex(32)
    TOKENS[token] = user.id
    return token


def get_user_by_token(db: Session, token: str) -> models.Usuario:
    """Obtiene el usuario asociado a un token o lanza 401."""
    user_id = TOKENS.get(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )

    user = db.get(models.Usuario, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )

    return user
