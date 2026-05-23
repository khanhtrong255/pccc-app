from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract

from database import get_db
from models import ViTri, KhuVuc, BinhTaiViTri, LoaiBinh, PhieuKiemTra, KetQuaTieuChi, TieuChi, NhanVien

router = APIRouter()


@router.get("/vi-tri/{vi_tri_id}")
def get_vi_tri(vi_tri_id: str, db: Session = Depends(get_db)):
    """Lấy thông tin vị trí — dùng cho trang QR public"""
    vt = db.query(ViTri).filter(
        ViTri.id == vi_tri_id,
        ViTri.trang_thai == "hoat_dong"
    ).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Không tìm thấy vị trí")

    # Danh sách bình
    binh_list = db.query(BinhTaiViTri).filter(BinhTaiViTri.vi_tri_id == vt.id).all()

    return {
        "id": str(vt.id),
        "so_thu_tu": vt.so_thu_tu,
        "ten_vi_tri": vt.ten_vi_tri,
        "mo_ta": vt.mo_ta,
        "khu_vuc": {
            "ma": vt.khu_vuc.ma_khu_vuc if vt.khu_vuc else None,
            "ten": vt.khu_vuc.ten_khu_vuc if vt.khu_vuc else None,
        },
        "danh_sach_binh": [
            {
                "loai_binh_id": str(b.loai_binh_id),
                "ma_loai": b.loai_binh.ma_loai,
                "ten_loai": b.loai_binh.ten_loai,
                "so_luong": b.so_luong,
            }
            for b in binh_list
        ],
    }


@router.get("/vi-tri/{vi_tri_id}/lich-su")
def get_lich_su(vi_tri_id: str, nam: int = None, db: Session = Depends(get_db)):
    """Lấy lịch sử kiểm tra theo năm — dùng cho calendar"""
    from datetime import date
    if not nam:
        nam = date.today().year

    vt = db.query(ViTri).filter(ViTri.id == vi_tri_id).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Không tìm thấy vị trí")

    phieu_list = db.query(PhieuKiemTra).filter(
        PhieuKiemTra.vi_tri_id == vi_tri_id,
        PhieuKiemTra.nam == nam,
    ).order_by(PhieuKiemTra.thang).all()

    return {
        "nam": nam,
        "lich_su": [
            {
                "id": str(p.id),
                "thang": p.thang,
                "nam": p.nam,
                "ngay_kiem_tra": p.ngay_kiem_tra.isoformat() if p.ngay_kiem_tra else None,
                "trang_thai": p.trang_thai,
                "so_dat": p.so_dat,
                "tong_tieu_chi": p.tong_tieu_chi,
                "ten_nhan_vien": p.nhan_vien.ho_ten if p.nhan_vien else None,
            }
            for p in phieu_list
        ]
    }


@router.get("/phieu/{phieu_id}")
def get_phieu_chi_tiet(phieu_id: str, db: Session = Depends(get_db)):
    """Lấy chi tiết phiếu kiểm tra — khi click vào ngày trên calendar"""
    p = db.query(PhieuKiemTra).filter(PhieuKiemTra.id == phieu_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu")

    # Nhóm kết quả theo loại bình
    ket_qua_list = db.query(KetQuaTieuChi).filter(
        KetQuaTieuChi.phieu_id == phieu_id
    ).join(TieuChi, KetQuaTieuChi.tieu_chi_id == TieuChi.id
    ).order_by(KetQuaTieuChi.loai_binh_id, TieuChi.stt).all()
    # Group theo loại bình
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
        "id": str(p.id),
        "vi_tri_id": str(p.vi_tri_id),
        "thang": p.thang,
        "nam": p.nam,
        "ngay_kiem_tra": p.ngay_kiem_tra.isoformat() if p.ngay_kiem_tra else None,
        "trang_thai": p.trang_thai,
        "so_dat": p.so_dat,
        "tong_tieu_chi": p.tong_tieu_chi,
        "ghi_chu": p.ghi_chu,
        "ten_nhan_vien": p.nhan_vien.ho_ten if p.nhan_vien else None,
        "ket_qua_theo_loai": list(nhom.values()),
    }
