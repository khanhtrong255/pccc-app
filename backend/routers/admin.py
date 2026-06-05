import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    KhuVuc, ViTri, LoaiBinh, BinhTaiViTri,
    TieuChi, NhanVien, PhieuKiemTra
)
from security import require_toan_quyen, require_xem_hoac_toan_quyen, hash_password

router = APIRouter()


# ── KHU VỰC ─────────────────────────────────────────────────

@router.get("/khu-vuc")
def list_khu_vuc(db: Session = Depends(get_db), _=Depends(require_xem_hoac_toan_quyen)):
    return db.query(KhuVuc).order_by(KhuVuc.ma_khu_vuc).all()


class KhuVucBody(BaseModel):
    ma_khu_vuc: str
    ten_khu_vuc: str
    mo_ta: Optional[str] = None


@router.post("/khu-vuc", status_code=201)
def create_khu_vuc(body: KhuVucBody, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    kv = KhuVuc(**body.model_dump())
    db.add(kv)
    db.commit()
    db.refresh(kv)
    return kv


@router.put("/khu-vuc/{kv_id}")
def update_khu_vuc(kv_id: str, body: KhuVucBody, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    kv = db.query(KhuVuc).filter(KhuVuc.id == kv_id).first()
    if not kv:
        raise HTTPException(status_code=404, detail="Không tìm thấy khu vực")
    for k, v in body.model_dump().items():
        setattr(kv, k, v)
    db.commit()
    return kv


@router.delete("/khu-vuc/{kv_id}")
def delete_khu_vuc(kv_id: str, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    kv = db.query(KhuVuc).filter(KhuVuc.id == kv_id).first()
    if not kv:
        raise HTTPException(status_code=404, detail="Không tìm thấy khu vực")
    if db.query(ViTri).filter(ViTri.khu_vuc_id == kv_id).count() > 0:
        raise HTTPException(status_code=400, detail="Không thể xóa khu vực đã được gán vào vị trí. Hãy gỡ các vị trí khỏi khu vực này trước.")
    db.delete(kv)
    db.commit()
    return {"message": "Đã xóa"}


# ── VỊ TRÍ ──────────────────────────────────────────────────

@router.get("/vi-tri")
def list_vi_tri(db: Session = Depends(get_db), _=Depends(require_xem_hoac_toan_quyen)):
    from datetime import date
    today = date.today()
    thang = today.month
    nam   = today.year

    vt_list = db.query(ViTri).order_by(ViTri.so_thu_tu).all()

    # Lấy tất cả phiếu tháng này 1 lần — tránh N+1 query
    phieu_thang = {
        str(p.vi_tri_id): p
        for p in db.query(PhieuKiemTra).filter(
            PhieuKiemTra.thang == thang,
            PhieuKiemTra.nam   == nam,
        ).all()
    }

    result = []
    for vt in vt_list:
        phieu = phieu_thang.get(str(vt.id))
        result.append({
            "id": str(vt.id),
            "so_thu_tu": vt.so_thu_tu,
            "ten_vi_tri": vt.ten_vi_tri,
            "trang_thai": vt.trang_thai,
            "mo_ta": vt.mo_ta,
            "khu_vuc": {
                "id": str(vt.khu_vuc.id) if vt.khu_vuc else None,
                "ten": vt.khu_vuc.ten_khu_vuc if vt.khu_vuc else None,
            },
            "so_loai_binh": len(vt.binh_list),
            "kiem_tra_thang_nay": {
                "trang_thai": phieu.trang_thai if phieu else None,
                "ngay_kiem_tra": phieu.ngay_kiem_tra.isoformat() if phieu and phieu.ngay_kiem_tra else None,
            }
        })
    return result


class ViTriBody(BaseModel):
    so_thu_tu: int
    ten_vi_tri: str
    khu_vuc_id: Optional[str] = None
    mo_ta: Optional[str] = None
    trang_thai: str = "hoat_dong"


@router.post("/vi-tri", status_code=201)
def create_vi_tri(body: ViTriBody, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    vt = ViTri(
        so_thu_tu=body.so_thu_tu,
        ten_vi_tri=body.ten_vi_tri,
        khu_vuc_id=uuid.UUID(body.khu_vuc_id) if body.khu_vuc_id else None,
        mo_ta=body.mo_ta,
        trang_thai=body.trang_thai,
    )
    db.add(vt)
    db.commit()
    db.refresh(vt)
    return {"id": str(vt.id), "so_thu_tu": vt.so_thu_tu, "ten_vi_tri": vt.ten_vi_tri}


@router.put("/vi-tri/{vt_id}")
def update_vi_tri(vt_id: str, body: ViTriBody, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    vt = db.query(ViTri).filter(ViTri.id == vt_id).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Không tìm thấy vị trí")
    vt.so_thu_tu  = body.so_thu_tu
    vt.ten_vi_tri = body.ten_vi_tri
    vt.khu_vuc_id = uuid.UUID(body.khu_vuc_id) if body.khu_vuc_id else None
    vt.mo_ta      = body.mo_ta
    vt.trang_thai = body.trang_thai
    db.commit()
    return {"message": "Đã cập nhật"}


@router.delete("/vi-tri/{vt_id}")
def delete_vi_tri(vt_id: str, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    vt = db.query(ViTri).filter(ViTri.id == vt_id).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Không tìm thấy vị trí")
    # Kiểm tra có phiếu kiểm tra không
    if db.query(PhieuKiemTra).filter(PhieuKiemTra.vi_tri_id == vt_id).count() > 0:
        raise HTTPException(status_code=400, detail="Không thể xóa vị trí đã có phiếu kiểm tra. Hãy đổi trạng thái sang 'ngưng' thay vì xóa.")
    db.delete(vt)
    db.commit()
    return {"message": "Đã xóa"}


# ── BÌNH TẠI VỊ TRÍ ─────────────────────────────────────────

class BinhViTriBody(BaseModel):
    loai_binh_id: str
    so_luong: int = 1


@router.get("/vi-tri/{vt_id}/binh")
def list_binh_vi_tri(vt_id: str, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    return db.query(BinhTaiViTri).filter(BinhTaiViTri.vi_tri_id == vt_id).all()


@router.post("/vi-tri/{vt_id}/binh", status_code=201)
def add_binh_vi_tri(vt_id: str, body: BinhViTriBody, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    b = BinhTaiViTri(
        vi_tri_id=uuid.UUID(vt_id),
        loai_binh_id=uuid.UUID(body.loai_binh_id),
        so_luong=body.so_luong,
    )
    db.add(b)
    db.commit()
    return {"message": "Đã thêm"}


@router.delete("/vi-tri/{vt_id}/binh/{binh_id}")
def remove_binh_vi_tri(vt_id: str, binh_id: str, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    b = db.query(BinhTaiViTri).filter(
        BinhTaiViTri.vi_tri_id == vt_id,
        BinhTaiViTri.id == binh_id,
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="Không tìm thấy")
    db.delete(b)
    db.commit()
    return {"message": "Đã xóa"}


# ── LOẠI BÌNH & TIÊU CHÍ ────────────────────────────────────

@router.get("/loai-binh")
def list_loai_binh(db: Session = Depends(get_db), _=Depends(require_xem_hoac_toan_quyen)):
    return db.query(LoaiBinh).order_by(LoaiBinh.ten_loai).all()


@router.get("/loai-binh/{lb_id}/tieu-chi")
def list_tieu_chi(lb_id: str, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    return db.query(TieuChi).filter(
        TieuChi.loai_binh_id == lb_id
    ).order_by(TieuChi.stt).all()


class TieuChiBody(BaseModel):
    stt: int
    noi_dung: str
    is_active: bool = True


@router.post("/loai-binh/{lb_id}/tieu-chi", status_code=201)
def create_tieu_chi(lb_id: str, body: TieuChiBody, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    tc = TieuChi(loai_binh_id=uuid.UUID(lb_id), **body.model_dump())
    db.add(tc)
    db.commit()
    return {"message": "Đã thêm"}


@router.put("/tieu-chi/{tc_id}")
def update_tieu_chi(tc_id: str, body: TieuChiBody, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    tc = db.query(TieuChi).filter(TieuChi.id == tc_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tiêu chí")
    tc.stt       = body.stt
    tc.noi_dung  = body.noi_dung
    tc.is_active = body.is_active
    db.commit()
    return {"message": "Đã cập nhật"}


@router.delete("/tieu-chi/{tc_id}")
def delete_tieu_chi(tc_id: str, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    tc = db.query(TieuChi).filter(TieuChi.id == tc_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tiêu chí")
    db.delete(tc)
    db.commit()
    return {"message": "Đã xóa"}


# ── NHÂN VIÊN ────────────────────────────────────────────────

@router.get("/nhan-vien")
def list_nhan_vien(db: Session = Depends(get_db), _=Depends(require_xem_hoac_toan_quyen)):
    nv_list = db.query(NhanVien).order_by(NhanVien.ho_ten).all()
    return [
        {
            "id": str(nv.id),
            "ho_ten": nv.ho_ten,
            "ma_nhan_vien": nv.ma_nhan_vien,
            "quyen": nv.quyen,
            "is_active": nv.is_active,
        }
        for nv in nv_list
    ]


class NhanVienBody(BaseModel):
    ho_ten: str
    ma_nhan_vien: str
    mat_khau: Optional[str] = None   # None khi update, không đổi password
    quyen: str = "cap_nhat"
    is_active: bool = True


@router.post("/nhan-vien", status_code=201)
def create_nhan_vien(body: NhanVienBody, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    if not body.mat_khau:
        raise HTTPException(status_code=400, detail="Mật khẩu không được để trống")
    nv = NhanVien(
        ho_ten=body.ho_ten,
        ma_nhan_vien=body.ma_nhan_vien,
        mat_khau=hash_password(body.mat_khau),
        quyen=body.quyen,
        is_active=body.is_active,
    )
    db.add(nv)
    db.commit()
    return {"message": "Đã tạo nhân viên"}


@router.put("/nhan-vien/{nv_id}")
def update_nhan_vien(nv_id: str, body: NhanVienBody, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    nv = db.query(NhanVien).filter(NhanVien.id == nv_id).first()
    if not nv:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")
    nv.ho_ten       = body.ho_ten
    nv.ma_nhan_vien = body.ma_nhan_vien
    nv.quyen        = body.quyen
    nv.is_active    = body.is_active
    if body.mat_khau:
        nv.mat_khau = hash_password(body.mat_khau)
    db.commit()
    return {"message": "Đã cập nhật"}


@router.delete("/nhan-vien/{nv_id}")
def delete_nhan_vien(nv_id: str, db: Session = Depends(get_db), _=Depends(require_toan_quyen)):
    nv = db.query(NhanVien).filter(NhanVien.id == nv_id).first()
    if not nv:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")
    # Soft delete — không xóa hẳn
    nv.is_active = False
    db.commit()
    return {"message": "Đã khóa tài khoản"}


# ── THỐNG KÊ DASHBOARD ──────────────────────────────────────

@router.get("/thong-ke")
def thong_ke(db: Session = Depends(get_db), _=Depends(require_xem_hoac_toan_quyen)):
    from datetime import date
    today = date.today()

    tong_vi_tri   = db.query(ViTri).filter(ViTri.trang_thai == "hoat_dong").count()
    tong_nhan_vien = db.query(NhanVien).filter(NhanVien.is_active == True).count()

    # Phiếu tháng này
    phieu_thang = db.query(PhieuKiemTra).filter(
        PhieuKiemTra.thang == today.month,
        PhieuKiemTra.nam == today.year,
    ).count()

    # Vị trí chưa kiểm tra tháng này
    da_kiem_tra_ids = db.query(PhieuKiemTra.vi_tri_id).filter(
        PhieuKiemTra.thang == today.month,
        PhieuKiemTra.nam == today.year,
    ).subquery()
    chua_kiem_tra = db.query(ViTri).filter(
        ViTri.trang_thai == "hoat_dong",
        ~ViTri.id.in_(da_kiem_tra_ids)
    ).count()

    return {
        "tong_vi_tri": tong_vi_tri,
        "tong_nhan_vien": tong_nhan_vien,
        "phieu_thang_nay": phieu_thang,
        "chua_kiem_tra_thang_nay": chua_kiem_tra,
        "thang": today.month,
        "nam": today.year,
    }
