import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, Text,
    ForeignKey, DateTime, Date, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class KhuVuc(Base):
    __tablename__ = "khu_vuc"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ma_khu_vuc  = Column(String(20), unique=True, nullable=False)
    ten_khu_vuc = Column(String(100), nullable=False)
    mo_ta       = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    vi_tri_list = relationship("ViTri", back_populates="khu_vuc")


class ViTri(Base):
    __tablename__ = "vi_tri"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    so_thu_tu   = Column(Integer, unique=True, nullable=False)
    ten_vi_tri  = Column(String(200), nullable=False)
    khu_vuc_id  = Column(UUID(as_uuid=True), ForeignKey("khu_vuc.id", ondelete="SET NULL"))
    mo_ta       = Column(Text)
    trang_thai  = Column(String(20), nullable=False, default="hoat_dong")
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now())

    khu_vuc      = relationship("KhuVuc", back_populates="vi_tri_list")
    binh_list    = relationship("BinhTaiViTri", back_populates="vi_tri", cascade="all, delete-orphan")
    phieu_list   = relationship("PhieuKiemTra", back_populates="vi_tri")


class LoaiBinh(Base):
    __tablename__ = "loai_binh"
    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ma_loai   = Column(String(50), unique=True, nullable=False)
    ten_loai  = Column(String(100), nullable=False)
    mo_ta     = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tieu_chi_list  = relationship("TieuChi", back_populates="loai_binh")
    binh_list      = relationship("BinhTaiViTri", back_populates="loai_binh")


class BinhTaiViTri(Base):
    __tablename__ = "binh_tai_vi_tri"
    __table_args__ = (UniqueConstraint("vi_tri_id", "loai_binh_id"),)
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vi_tri_id    = Column(UUID(as_uuid=True), ForeignKey("vi_tri.id", ondelete="CASCADE"), nullable=False)
    loai_binh_id = Column(UUID(as_uuid=True), ForeignKey("loai_binh.id", ondelete="RESTRICT"), nullable=False)
    so_luong     = Column(Integer, nullable=False, default=1)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    vi_tri    = relationship("ViTri", back_populates="binh_list")
    loai_binh = relationship("LoaiBinh", back_populates="binh_list")


class TieuChi(Base):
    __tablename__ = "tieu_chi"
    __table_args__ = (UniqueConstraint("loai_binh_id", "stt"),)
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loai_binh_id = Column(UUID(as_uuid=True), ForeignKey("loai_binh.id", ondelete="CASCADE"), nullable=False)
    stt          = Column(Integer, nullable=False)
    noi_dung     = Column(String(500), nullable=False)
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    loai_binh  = relationship("LoaiBinh", back_populates="tieu_chi_list")
    ket_qua    = relationship("KetQuaTieuChi", back_populates="tieu_chi")


class NhanVien(Base):
    __tablename__ = "nhan_vien"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ho_ten         = Column(String(100), nullable=False)
    ma_nhan_vien   = Column(String(50), unique=True, nullable=False)
    mat_khau       = Column(Text, nullable=False)
    quyen          = Column(String(20), nullable=False, default="cap_nhat")
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), server_default=func.now())

    phieu_list     = relationship("PhieuKiemTra", back_populates="nhan_vien")
    refresh_tokens = relationship("RefreshToken", back_populates="nhan_vien", cascade="all, delete-orphan")


class PhieuKiemTra(Base):
    __tablename__ = "phieu_kiem_tra"
    __table_args__ = (UniqueConstraint("vi_tri_id", "thang", "nam"),)
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vi_tri_id      = Column(UUID(as_uuid=True), ForeignKey("vi_tri.id", ondelete="RESTRICT"), nullable=False)
    thang          = Column(Integer, nullable=False)
    nam            = Column(Integer, nullable=False)
    ngay_kiem_tra  = Column(Date, nullable=False)
    nhan_vien_id   = Column(UUID(as_uuid=True), ForeignKey("nhan_vien.id", ondelete="SET NULL"))
    tong_tieu_chi  = Column(Integer, default=0)
    so_dat         = Column(Integer, default=0)
    trang_thai     = Column(String(20), nullable=False, default="chua_hoan_thanh")
    ghi_chu        = Column(Text)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), server_default=func.now())

    vi_tri       = relationship("ViTri", back_populates="phieu_list")
    nhan_vien    = relationship("NhanVien", back_populates="phieu_list")
    ket_qua_list = relationship("KetQuaTieuChi", back_populates="phieu", cascade="all, delete-orphan")


class KetQuaTieuChi(Base):
    __tablename__ = "ket_qua_tieu_chi"
    __table_args__ = (UniqueConstraint("phieu_id", "tieu_chi_id"),)
    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phieu_id         = Column(UUID(as_uuid=True), ForeignKey("phieu_kiem_tra.id", ondelete="CASCADE"), nullable=False)
    tieu_chi_id      = Column(UUID(as_uuid=True), ForeignKey("tieu_chi.id", ondelete="RESTRICT"), nullable=False)
    loai_binh_id     = Column(UUID(as_uuid=True), ForeignKey("loai_binh.id", ondelete="RESTRICT"), nullable=False)
    ket_qua          = Column(String(20), nullable=False, default="chua_kiem_tra")
    bien_phap        = Column(Text)
    ngay_hoan_thanh  = Column(Date)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now())

    phieu     = relationship("PhieuKiemTra", back_populates="ket_qua_list")
    tieu_chi  = relationship("TieuChi", back_populates="ket_qua")
    loai_binh = relationship("LoaiBinh")


class RefreshToken(Base):
    __tablename__ = "refresh_token"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nhan_vien_id = Column(UUID(as_uuid=True), ForeignKey("nhan_vien.id", ondelete="CASCADE"), nullable=False)
    token        = Column(Text, unique=True, nullable=False)
    expires_at   = Column(DateTime(timezone=True), nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    nhan_vien = relationship("NhanVien", back_populates="refresh_tokens")