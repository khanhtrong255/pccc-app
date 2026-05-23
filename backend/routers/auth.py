from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import NhanVien, RefreshToken
from security import (
    verify_password, hash_password, create_access_token,
    create_refresh_token, get_current_user
)
from config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    ma_nhan_vien: str
    mat_khau: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    ho_ten: str
    quyen: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    nv = db.query(NhanVien).filter(
        NhanVien.ma_nhan_vien == body.ma_nhan_vien,
        NhanVien.is_active == True
    ).first()

    if not nv or not verify_password(body.mat_khau, nv.mat_khau):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mã nhân viên hoặc mật khẩu không đúng"
        )

    access_token  = create_access_token(str(nv.id), nv.quyen)
    refresh_token = create_refresh_token()

    # Lưu refresh token
    rt = RefreshToken(
        nhan_vien_id=nv.id,
        token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(rt)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        ho_ten=nv.ho_ten,
        quyen=nv.quyen,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    rt = db.query(RefreshToken).filter(
        RefreshToken.token == body.refresh_token,
        RefreshToken.expires_at > datetime.now(timezone.utc)
    ).first()

    if not rt:
        raise HTTPException(status_code=401, detail="Refresh token không hợp lệ hoặc đã hết hạn")

    nv = db.query(NhanVien).filter(
        NhanVien.id == rt.nhan_vien_id,
        NhanVien.is_active == True
    ).first()
    if not nv:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại")

    # Xoá token cũ, tạo mới
    db.delete(rt)
    new_rt = RefreshToken(
        nhan_vien_id=nv.id,
        token=create_refresh_token(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_rt)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(str(nv.id), nv.quyen),
        refresh_token=new_rt.token,
        ho_ten=nv.ho_ten,
        quyen=nv.quyen,
    )


@router.post("/logout")
def logout(
    nv: NhanVien = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Xoá tất cả refresh token của user
    db.query(RefreshToken).filter(RefreshToken.nhan_vien_id == nv.id).delete()
    db.commit()
    return {"message": "Đăng xuất thành công"}


@router.get("/me")
def me(nv: NhanVien = Depends(get_current_user)):
    return {
        "id": str(nv.id),
        "ho_ten": nv.ho_ten,
        "ma_nhan_vien": nv.ma_nhan_vien,
        "quyen": nv.quyen,
    }


class DoiMatKhauRequest(BaseModel):
    mat_khau_cu: str
    mat_khau_moi: str


@router.put("/doi-mat-khau")
def doi_mat_khau(
    body: DoiMatKhauRequest,
    nv: NhanVien = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.mat_khau_cu, nv.mat_khau):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu cũ không đúng"
        )
    if len(body.mat_khau_moi) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải có ít nhất 6 ký tự"
        )
    nv.mat_khau = hash_password(body.mat_khau_moi)
    db.commit()
    return {"message": "Đổi mật khẩu thành công"}
