from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date
import uuid

from database import get_db
from models import ThietBiPCCC, TieuChiThietBi, PhieuKiemTraTB, KetQuaTB, KhuVuc, NhanVien
from security import get_current_user, require_quyen

router = APIRouter()

LOAI_LABEL = {
    "hop_voi":   "Hộp vòi chữa cháy",
    "hop_pha_do": "Hộp đựng dụng cụ phá dỡ",
    "tram_bom":  "Trạm bơm chữa cháy",
}

# ── HELPER: get or create phiếu tháng này ───────────────────
def get_or_create_phieu(thiet_bi_id: str, nhan_vien_id: str, db: Session):
    today = date.today()
    thang, nam = today.month, today.year

    phieu = db.query(PhieuKiemTraTB).filter_by(
        thiet_bi_id=thiet_bi_id, thang=thang, nam=nam
    ).first()

    if not phieu:
        phieu = PhieuKiemTraTB(
            thiet_bi_id=uuid.UUID(thiet_bi_id),
            thang=thang,
            nam=nam,
            ngay_kiem_tra=today,
            nguoi_kiem_tra=uuid.UUID(nhan_vien_id),
        )
        db.add(phieu)
        db.flush()

    # Auto-fill tiêu chí nếu chưa có
    thiet_bi = db.query(ThietBiPCCC).get(uuid.UUID(thiet_bi_id))
    tieu_chi_list = db.query(TieuChiThietBi).filter_by(
        loai=thiet_bi.loai, is_active=True
    ).order_by(TieuChiThietBi.stt).all()

    existing_ids = {str(k.tieu_chi_id) for k in phieu.ket_qua_list}
    for tc in tieu_chi_list:
        if str(tc.id) not in existing_ids:
            db.add(KetQuaTB(phieu_id=phieu.id, tieu_chi_id=tc.id))

    db.commit()
    db.refresh(phieu)
    return phieu


# ══════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS (scan QR)
# ══════════════════════════════════════════════════════════════

@router.get("/public/thiet-bi/{thiet_bi_id}")
def get_thiet_bi_info(thiet_bi_id: str, db: Session = Depends(get_db)):
    tb = db.query(ThietBiPCCC).filter_by(id=thiet_bi_id).first()
    if not tb:
        raise HTTPException(404, "Không tìm thấy thiết bị")

    khu_vuc = db.query(KhuVuc).get(tb.khu_vuc_id) if tb.khu_vuc_id else None

    # Lịch sử 12 tháng gần nhất
    lich_su = db.query(PhieuKiemTraTB).filter_by(
        thiet_bi_id=tb.id
    ).order_by(PhieuKiemTraTB.nam.desc(), PhieuKiemTraTB.thang.desc()).limit(12).all()

    return {
        "id": str(tb.id),
        "loai": tb.loai,
        "ten_loai": LOAI_LABEL.get(tb.loai, tb.loai),
        "so_thu_tu": tb.so_thu_tu,
        "ten_hien_thi": f"{LOAI_LABEL.get(tb.loai, tb.loai)} số {tb.so_thu_tu:02d}",
        "khu_vuc": khu_vuc.ten_khu_vuc if khu_vuc else None,
        "mo_ta": tb.mo_ta,
        "trang_thai": tb.trang_thai,
        "lich_su": [
            {
                "id": str(p.id),
                "thang": p.thang,
                "nam": p.nam,
                "ngay_kiem_tra": str(p.ngay_kiem_tra) if p.ngay_kiem_tra else None,
                "trang_thai": p.trang_thai,
            }
            for p in lich_su
        ],
    }

@router.post("/public/thiet-bi/{thiet_bi_id}/kiem-tra")
def bat_dau_kiem_tra(
    thiet_bi_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tb = db.query(ThietBiPCCC).filter_by(id=thiet_bi_id).first()
    if not tb:
        raise HTTPException(404, "Không tìm thấy thiết bị")
    if tb.trang_thai == "ngung":
        raise HTTPException(400, "Thiết bị đang ngừng hoạt động")

    phieu = get_or_create_phieu(thiet_bi_id, str(current_user.id), db)

    ket_qua_list = (
        db.query(KetQuaTB, TieuChiThietBi)
        .join(TieuChiThietBi, KetQuaTB.tieu_chi_id == TieuChiThietBi.id)
        .filter(KetQuaTB.phieu_id == phieu.id)
        .order_by(TieuChiThietBi.stt)
        .all()
    )

    return {
        "phieu_id": str(phieu.id),
        "thang": phieu.thang,
        "nam": phieu.nam,
        "trang_thai": phieu.trang_thai,
        "ten_hien_thi": f"{LOAI_LABEL.get(tb.loai, tb.loai)} số {tb.so_thu_tu:02d}",
        "khu_vuc": db.query(KhuVuc).get(tb.khu_vuc_id).ten_khu_vuc if tb.khu_vuc_id else None,
        "tieu_chi": [
            {
                "ket_qua_id": str(kq.id),
                "tieu_chi_id": str(tc.id),
                "stt": tc.stt,
                "noi_dung": tc.noi_dung,
                "ket_qua": kq.ket_qua,
                "bien_phap": kq.bien_phap,
                "ngay_hoan_thanh": str(kq.ngay_hoan_thanh) if kq.ngay_hoan_thanh else None,
            }
            for kq, tc in ket_qua_list
        ],
    }


@router.put("/public/ket-qua-tb/{ket_qua_id}")
def cap_nhat_ket_qua(
    ket_qua_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    kq = db.query(KetQuaTB).get(uuid.UUID(ket_qua_id))
    if not kq:
        raise HTTPException(404, "Không tìm thấy kết quả")

    ket_qua = body.get("ket_qua")
    if ket_qua not in ("dat", "khong_dat"):
        raise HTTPException(400, "ket_qua phải là 'dat' hoặc 'khong_dat'")

    kq.ket_qua = ket_qua
    kq.bien_phap = body.get("bien_phap") if ket_qua == "khong_dat" else None
    kq.ngay_hoan_thanh = body.get("ngay_hoan_thanh") if ket_qua == "khong_dat" else None
    db.commit()
    return {"ok": True}


@router.get("/public/phieu-tb/{phieu_id}")
def get_chi_tiet_phieu(phieu_id: str, db: Session = Depends(get_db)):
    phieu = db.query(PhieuKiemTraTB).get(uuid.UUID(phieu_id))
    if not phieu:
        raise HTTPException(404, "Không tìm thấy phiếu")

    tb = db.query(ThietBiPCCC).get(phieu.thiet_bi_id)
    nv = db.query(NhanVien).get(phieu.nguoi_kiem_tra) if phieu.nguoi_kiem_tra else None
    khu_vuc = db.query(KhuVuc).get(tb.khu_vuc_id) if tb.khu_vuc_id else None

    ket_qua_list = (
        db.query(KetQuaTB, TieuChiThietBi)
        .join(TieuChiThietBi, KetQuaTB.tieu_chi_id == TieuChiThietBi.id)
        .filter(KetQuaTB.phieu_id == phieu.id)
        .order_by(TieuChiThietBi.stt)
        .all()
    )

    return {
        "id": str(phieu.id),
        "thang": phieu.thang,
        "nam": phieu.nam,
        "ngay_kiem_tra": str(phieu.ngay_kiem_tra) if phieu.ngay_kiem_tra else None,
        "trang_thai": phieu.trang_thai,
        "ten_nhan_vien": nv.ho_ten if nv else None,
        "ten_hien_thi": f"{LOAI_LABEL.get(tb.loai, tb.loai)} số {tb.so_thu_tu:02d}",
        "khu_vuc": khu_vuc.ten_khu_vuc if khu_vuc else None,
        "tieu_chi": [
            {
                "stt": tc.stt,
                "noi_dung": tc.noi_dung,
                "ket_qua": kq.ket_qua,
                "bien_phap": kq.bien_phap,
                "ngay_hoan_thanh": str(kq.ngay_hoan_thanh) if kq.ngay_hoan_thanh else None,
            }
            for kq, tc in ket_qua_list
        ],
    }


# ══════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/admin/thiet-bi")
def list_thiet_bi(
    loai: Optional[str] = Query(None),
    khu_vuc_id: Optional[str] = Query(None),
    trang_thai: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_quyen("toan_quyen")),
):
    q = db.query(ThietBiPCCC)
    if loai:
        q = q.filter(ThietBiPCCC.loai == loai)
    if khu_vuc_id:
        q = q.filter(ThietBiPCCC.khu_vuc_id == khu_vuc_id)
    if trang_thai:
        q = q.filter(ThietBiPCCC.trang_thai == trang_thai)

    total = q.count()
    items = q.order_by(ThietBiPCCC.loai, ThietBiPCCC.so_thu_tu)\
             .offset((page - 1) * limit).limit(limit).all()

    khu_vuc_map = {
        str(k.id): k.ten_khu_vuc
        for k in db.query(KhuVuc).all()
    }

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": str(tb.id),
                "loai": tb.loai,
                "ten_loai": LOAI_LABEL.get(tb.loai, tb.loai),
                "so_thu_tu": tb.so_thu_tu,
                "khu_vuc_id": str(tb.khu_vuc_id) if tb.khu_vuc_id else None,
                "ten_khu_vuc": khu_vuc_map.get(str(tb.khu_vuc_id), "—"),
                "mo_ta": tb.mo_ta,
                "qr_code": tb.qr_code,
                "trang_thai": tb.trang_thai,
            }
            for tb in items
        ],
    }


@router.post("/admin/thiet-bi")
def create_thiet_bi(
    body: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_quyen("toan_quyen")),
):
    loai = body.get("loai")
    if loai not in LOAI_LABEL:
        raise HTTPException(400, "loai không hợp lệ")

    so_thu_tu = body.get("so_thu_tu")
    if not so_thu_tu:
        raise HTTPException(400, "Thiếu so_thu_tu")

    existing = db.query(ThietBiPCCC).filter_by(loai=loai, so_thu_tu=so_thu_tu).first()
    if existing:
        raise HTTPException(400, f"{LOAI_LABEL[loai]} số {so_thu_tu:02d} đã tồn tại")

    tb = ThietBiPCCC(
        loai=loai,
        so_thu_tu=so_thu_tu,
        khu_vuc_id=uuid.UUID(body["khu_vuc_id"]) if body.get("khu_vuc_id") else None,
        mo_ta=body.get("mo_ta"),
        qr_code=str(uuid.uuid4()),
    )
    db.add(tb)
    db.commit()
    db.refresh(tb)
    return {"id": str(tb.id), "qr_code": tb.qr_code}


@router.put("/admin/thiet-bi/{thiet_bi_id}")
def update_thiet_bi(
    thiet_bi_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_quyen("toan_quyen")),
):
    tb = db.query(ThietBiPCCC).get(uuid.UUID(thiet_bi_id))
    if not tb:
        raise HTTPException(404, "Không tìm thấy thiết bị")

    if "so_thu_tu" in body:
        tb.so_thu_tu = body["so_thu_tu"]
    if "khu_vuc_id" in body:
        tb.khu_vuc_id = uuid.UUID(body["khu_vuc_id"]) if body["khu_vuc_id"] else None
    if "mo_ta" in body:
        tb.mo_ta = body["mo_ta"]
    if "trang_thai" in body:
        tb.trang_thai = body["trang_thai"]

    db.commit()
    return {"ok": True}


@router.delete("/admin/thiet-bi/{thiet_bi_id}")
def delete_thiet_bi(
    thiet_bi_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_quyen("toan_quyen")),
):
    tb = db.query(ThietBiPCCC).get(uuid.UUID(thiet_bi_id))
    if not tb:
        raise HTTPException(404, "Không tìm thấy thiết bị")

    has_phieu = db.query(PhieuKiemTraTB).filter_by(thiet_bi_id=tb.id).first()
    if has_phieu:
        raise HTTPException(400, "Không thể xóa: đã có phiếu kiểm tra")

    db.delete(tb)
    db.commit()
    return {"ok": True}
