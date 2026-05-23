from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid

from database import get_db
from models import (
    ViTri, PhieuKiemTra, KetQuaTieuChi,
    TieuChi, BinhTaiViTri, NhanVien
)
from security import get_current_user

router = APIRouter()


class KetQuaItem(BaseModel):
    tieu_chi_id: str
    loai_binh_id: str
    ket_qua: str                      # dat / khong_dat / chua_kiem_tra
    bien_phap: Optional[str] = None
    ngay_hoan_thanh: Optional[str] = None


class TaoPhieuRequest(BaseModel):
    vi_tri_id: str
    ngay_kiem_tra: Optional[str] = None
    ghi_chu: Optional[str] = None


class CapNhatKetQuaRequest(BaseModel):
    ket_qua_list: List[KetQuaItem]
    ghi_chu: Optional[str] = None


@router.get("/vi-tri/{vi_tri_id}/phieu-thang-nay")
def get_or_create_phieu(
    vi_tri_id: str,
    nv: NhanVien = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lấy phiếu tháng hiện tại, nếu chưa có thì tạo mới.
    Trả về phiếu kèm toàn bộ tiêu chí cần điền.
    """
    today = date.today()
    thang = today.month
    nam   = today.year

    vt = db.query(ViTri).filter(
        ViTri.id == vi_tri_id,
        ViTri.trang_thai == "hoat_dong"
    ).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Không tìm thấy vị trí")

    # Tìm phiếu tháng này
    phieu = db.query(PhieuKiemTra).filter(
        PhieuKiemTra.vi_tri_id == vi_tri_id,
        PhieuKiemTra.thang == thang,
        PhieuKiemTra.nam == nam,
    ).first()

    if not phieu:
        # Tạo phiếu mới
        phieu = PhieuKiemTra(
            vi_tri_id=uuid.UUID(vi_tri_id),
            thang=thang,
            nam=nam,
            ngay_kiem_tra=today,
            nhan_vien_id=nv.id,
        )
        db.add(phieu)
        db.flush()  # lấy id trước khi commit

        # Tạo các dòng kết quả cho từng tiêu chí
        binh_list = db.query(BinhTaiViTri).filter(
            BinhTaiViTri.vi_tri_id == vi_tri_id
        ).all()

        for binh in binh_list:
            tieu_chi_list = db.query(TieuChi).filter(
                TieuChi.loai_binh_id == binh.loai_binh_id,
                TieuChi.is_active == True
            ).order_by(TieuChi.stt).all()

            for tc in tieu_chi_list:
                kq = KetQuaTieuChi(
                    phieu_id=phieu.id,
                    tieu_chi_id=tc.id,
                    loai_binh_id=binh.loai_binh_id,
                    ket_qua="chua_kiem_tra",
                )
                db.add(kq)

        db.commit()
        db.refresh(phieu)

    # Trả về phiếu + kết quả nhóm theo loại bình
    ket_qua_list = db.query(KetQuaTieuChi).filter(
        KetQuaTieuChi.phieu_id == phieu.id
    ).join(TieuChi, KetQuaTieuChi.tieu_chi_id == TieuChi.id
    ).order_by(KetQuaTieuChi.loai_binh_id, TieuChi.stt).all()

    nhom = {}
    for kq in ket_qua_list:
        lb_id = str(kq.loai_binh_id)
        if lb_id not in nhom:
            nhom[lb_id] = {
                "loai_binh_id": lb_id,
                "ma_loai": kq.loai_binh.ma_loai,
                "ten_loai": kq.loai_binh.ten_loai,
                "tieu_chi": []
            }
        nhom[lb_id]["tieu_chi"].append({
            "id": str(kq.id),
            "tieu_chi_id": str(kq.tieu_chi_id),
            "stt": kq.tieu_chi.stt,
            "noi_dung": kq.tieu_chi.noi_dung,
            "ket_qua": kq.ket_qua,
            "bien_phap": kq.bien_phap,
            "ngay_hoan_thanh": kq.ngay_hoan_thanh.isoformat() if kq.ngay_hoan_thanh else None,
        })

    return {
        "id": str(phieu.id),
        "thang": phieu.thang,
        "nam": phieu.nam,
        "ngay_kiem_tra": phieu.ngay_kiem_tra.isoformat(),
        "trang_thai": phieu.trang_thai,
        "so_dat": phieu.so_dat,
        "tong_tieu_chi": phieu.tong_tieu_chi,
        "ghi_chu": phieu.ghi_chu,
        "la_phieu_moi": phieu.created_at == phieu.updated_at,
        "ket_qua_theo_loai": list(nhom.values()),
    }


@router.put("/phieu/{phieu_id}")
def cap_nhat_ket_qua(
    phieu_id: str,
    body: CapNhatKetQuaRequest,
    nv: NhanVien = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cập nhật kết quả từng tiêu chí trong phiếu"""
    phieu = db.query(PhieuKiemTra).filter(PhieuKiemTra.id == phieu_id).first()
    if not phieu:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu")

    # Cập nhật từng kết quả
    for item in body.ket_qua_list:
        kq = db.query(KetQuaTieuChi).filter(
            KetQuaTieuChi.phieu_id == phieu_id,
            KetQuaTieuChi.tieu_chi_id == item.tieu_chi_id,
        ).first()

        if not kq:
            continue

        kq.ket_qua = item.ket_qua

        if item.ket_qua == "khong_dat":
            kq.bien_phap       = item.bien_phap
            kq.ngay_hoan_thanh = date.fromisoformat(item.ngay_hoan_thanh) if item.ngay_hoan_thanh else None
        else:
            # Xóa biện pháp nếu đổi sang đạt
            kq.bien_phap       = None
            kq.ngay_hoan_thanh = None

    if body.ghi_chu is not None:
        phieu.ghi_chu = body.ghi_chu

    # Cập nhật người kiểm tra và ngày
    phieu.nhan_vien_id   = nv.id
    phieu.ngay_kiem_tra  = date.today()

    db.commit()

    return {"success": True, "message": "Cập nhật thành công"}
