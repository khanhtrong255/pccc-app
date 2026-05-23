import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import NhanVien, RefreshToken

# ── Password hashing ────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ── JWT ─────────────────────────────────────────────────────
ALGORITHM = "HS256"
bearer_scheme = HTTPBearer()

def create_access_token(nhan_vien_id: str, quyen: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": nhan_vien_id,
        "quyen": quyen,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)

def create_refresh_token() -> str:
    return secrets.token_hex(32)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
        )

# ── Dependencies ────────────────────────────────────────────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> NhanVien:
    payload = decode_access_token(credentials.credentials)
    nv_id   = payload.get("sub")
    if not nv_id:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

    nv = db.query(NhanVien).filter(
        NhanVien.id == nv_id,
        NhanVien.is_active == True
    ).first()
    if not nv:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại hoặc đã bị khóa")
    return nv

def require_toan_quyen(nv: NhanVien = Depends(get_current_user)) -> NhanVien:
    if nv.quyen != "toan_quyen":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thực hiện thao tác này"
        )
    return nv
