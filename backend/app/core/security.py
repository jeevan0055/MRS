from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from .config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Convert both to bytes
    password_bytes = plain_password.encode("utf-8")
    # If hashed_password is a string, convert to bytes (stored as string in DB)
    if isinstance(hashed_password, str):
        hashed_bytes = hashed_password.encode("utf-8")
    else:
        hashed_bytes = hashed_password
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    # Truncate to 72 bytes to avoid bcrypt error
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
