-- ============================================================
-- HỆ THỐNG QUẢN LÝ PCCC V2
-- PostgreSQL 16
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. KHU VỰC
-- ============================================================
CREATE TABLE khu_vuc (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ma_khu_vuc  VARCHAR(20) UNIQUE NOT NULL,
    ten_khu_vuc VARCHAR(100) NOT NULL,
    mo_ta       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 2. VỊ TRÍ (đơn vị chính — gắn QR)
-- ============================================================
CREATE TABLE vi_tri (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    so_thu_tu    INTEGER UNIQUE NOT NULL,        -- 1, 2, 3...
    ten_vi_tri   VARCHAR(200) NOT NULL,          -- "Hành lang tầng 1"
    khu_vuc_id   UUID REFERENCES khu_vuc(id) ON DELETE SET NULL,
    mo_ta        TEXT,
    trang_thai   VARCHAR(20) NOT NULL DEFAULT 'hoat_dong'
                 CHECK (trang_thai IN ('hoat_dong', 'ngung')),
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 3. LOẠI BÌNH (có thể thêm bớt)
-- ============================================================
CREATE TABLE loai_binh (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ma_loai   VARCHAR(50) UNIQUE NOT NULL,  -- CO2_MT3, Bot_MFZ8, MFZT35, K
    ten_loai  VARCHAR(100) NOT NULL,         -- "Bình CO2 MT3"
    mo_ta     TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4. BÌNH TẠI VỊ TRÍ
-- ============================================================
CREATE TABLE binh_tai_vi_tri (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vi_tri_id    UUID NOT NULL REFERENCES vi_tri(id) ON DELETE CASCADE,
    loai_binh_id UUID NOT NULL REFERENCES loai_binh(id) ON DELETE RESTRICT,
    so_luong     INTEGER NOT NULL DEFAULT 1 CHECK (so_luong > 0),
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(vi_tri_id, loai_binh_id)
);

-- ============================================================
-- 5. TIÊU CHÍ KIỂM TRA (theo loại bình, có thể thêm bớt)
-- ============================================================
CREATE TABLE tieu_chi (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loai_binh_id UUID NOT NULL REFERENCES loai_binh(id) ON DELETE CASCADE,
    stt          INTEGER NOT NULL,
    noi_dung     VARCHAR(500) NOT NULL,   -- "Áp kế trong vùng xanh"
    is_active    BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(loai_binh_id, stt)
);

-- ============================================================
-- 6. NHÂN VIÊN
-- ============================================================
CREATE TABLE nhan_vien (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ho_ten         VARCHAR(100) NOT NULL,
    ma_nhan_vien   VARCHAR(50) UNIQUE NOT NULL,   -- mã đăng nhập
    mat_khau       TEXT NOT NULL,                  -- bcrypt hash
    quyen          VARCHAR(20) NOT NULL DEFAULT 'cap_nhat'
                   CHECK (quyen IN ('cap_nhat', 'toan_quyen')),
    is_active      BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 7. PHIẾU KIỂM TRA (1 phiếu/vị trí/tháng)
-- ============================================================
CREATE TABLE phieu_kiem_tra (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vi_tri_id      UUID NOT NULL REFERENCES vi_tri(id) ON DELETE RESTRICT,
    thang          INTEGER NOT NULL CHECK (thang BETWEEN 1 AND 12),
    nam            INTEGER NOT NULL CHECK (nam >= 2024),
    ngay_kiem_tra  DATE NOT NULL DEFAULT CURRENT_DATE,
    nhan_vien_id   UUID REFERENCES nhan_vien(id) ON DELETE SET NULL,
    -- Cache thống kê (tính lại khi cập nhật kết quả)
    tong_tieu_chi  INTEGER DEFAULT 0,
    so_dat         INTEGER DEFAULT 0,
    trang_thai     VARCHAR(20) NOT NULL DEFAULT 'chua_hoan_thanh'
                   CHECK (trang_thai IN ('dat_het', 'co_khong_dat', 'chua_hoan_thanh')),
    ghi_chu        TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(vi_tri_id, thang, nam)   -- 1 tháng 1 phiếu
);

-- ============================================================
-- 8. KẾT QUẢ TỪNG TIÊU CHÍ
-- ============================================================
CREATE TABLE ket_qua_tieu_chi (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phieu_id         UUID NOT NULL REFERENCES phieu_kiem_tra(id) ON DELETE CASCADE,
    tieu_chi_id      UUID NOT NULL REFERENCES tieu_chi(id) ON DELETE RESTRICT,
    loai_binh_id     UUID NOT NULL REFERENCES loai_binh(id) ON DELETE RESTRICT,
    ket_qua          VARCHAR(20) NOT NULL DEFAULT 'chua_kiem_tra'
                     CHECK (ket_qua IN ('dat', 'khong_dat', 'chua_kiem_tra')),
    bien_phap        TEXT,       -- chỉ điền khi không đạt
    ngay_hoan_thanh  DATE,       -- chỉ điền khi không đạt
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(phieu_id, tieu_chi_id)
);

-- ============================================================
-- 9. REFRESH TOKEN (JWT auth)
-- ============================================================
CREATE TABLE refresh_token (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nhan_vien_id UUID NOT NULL REFERENCES nhan_vien(id) ON DELETE CASCADE,
    token        TEXT UNIQUE NOT NULL,
    expires_at   TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEX
-- ============================================================
CREATE INDEX idx_vi_tri_so_thu_tu    ON vi_tri(so_thu_tu);
CREATE INDEX idx_vi_tri_khu_vuc      ON vi_tri(khu_vuc_id);
CREATE INDEX idx_binh_vi_tri         ON binh_tai_vi_tri(vi_tri_id);
CREATE INDEX idx_tieu_chi_loai_binh  ON tieu_chi(loai_binh_id);
CREATE INDEX idx_phieu_vi_tri        ON phieu_kiem_tra(vi_tri_id);
CREATE INDEX idx_phieu_thang_nam     ON phieu_kiem_tra(thang, nam);
CREATE INDEX idx_ket_qua_phieu       ON ket_qua_tieu_chi(phieu_id);
CREATE INDEX idx_ket_qua_tieu_chi    ON ket_qua_tieu_chi(tieu_chi_id);
CREATE INDEX idx_refresh_token       ON refresh_token(token);

-- ============================================================
-- TRIGGER: tự động updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vi_tri_updated_at
    BEFORE UPDATE ON vi_tri FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_nhanvien_updated_at
    BEFORE UPDATE ON nhan_vien FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_phieu_updated_at
    BEFORE UPDATE ON phieu_kiem_tra FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_ketqua_updated_at
    BEFORE UPDATE ON ket_qua_tieu_chi FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TRIGGER: tự động tính lại thống kê phiếu khi cập nhật kết quả
-- ============================================================
CREATE OR REPLACE FUNCTION recalc_phieu_stats()
RETURNS TRIGGER AS $$
DECLARE
    v_phieu_id UUID;
    v_tong INTEGER;
    v_dat INTEGER;
    v_trang_thai VARCHAR(20);
BEGIN
    v_phieu_id := COALESCE(NEW.phieu_id, OLD.phieu_id);

    SELECT COUNT(*), COUNT(*) FILTER (WHERE ket_qua = 'dat')
    INTO v_tong, v_dat
    FROM ket_qua_tieu_chi
    WHERE phieu_id = v_phieu_id;

    IF v_tong = 0 THEN
        v_trang_thai := 'chua_hoan_thanh';
    ELSIF v_dat = v_tong THEN
        v_trang_thai := 'dat_het';
    ELSE
        v_trang_thai := 'co_khong_dat';
    END IF;

    UPDATE phieu_kiem_tra
    SET tong_tieu_chi = v_tong,
        so_dat        = v_dat,
        trang_thai    = v_trang_thai,
        updated_at    = NOW()
    WHERE id = v_phieu_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_recalc_stats
    AFTER INSERT OR UPDATE OR DELETE ON ket_qua_tieu_chi
    FOR EACH ROW EXECUTE FUNCTION recalc_phieu_stats();

-- ============================================================
-- VIEW: thông tin vị trí đầy đủ
-- ============================================================
CREATE VIEW v_vi_tri_tong_hop AS
SELECT
    v.id,
    v.so_thu_tu,
    v.ten_vi_tri,
    v.trang_thai,
    k.ten_khu_vuc,
    k.ma_khu_vuc,
    -- Danh sách bình tại vị trí (JSON)
    COALESCE(
        (SELECT json_agg(json_build_object(
            'loai_binh_id', lb.id,
            'ma_loai', lb.ma_loai,
            'ten_loai', lb.ten_loai,
            'so_luong', b.so_luong
        ) ORDER BY lb.ten_loai)
        FROM binh_tai_vi_tri b
        JOIN loai_binh lb ON b.loai_binh_id = lb.id
        WHERE b.vi_tri_id = v.id),
    '[]'
    ) AS danh_sach_binh,
    -- Phiếu kiểm tra tháng này
    (SELECT json_build_object(
        'id', p.id,
        'ngay_kiem_tra', p.ngay_kiem_tra,
        'trang_thai', p.trang_thai,
        'so_dat', p.so_dat,
        'tong_tieu_chi', p.tong_tieu_chi
    )
    FROM phieu_kiem_tra p
    WHERE p.vi_tri_id = v.id
      AND p.thang = EXTRACT(MONTH FROM CURRENT_DATE)
      AND p.nam   = EXTRACT(YEAR  FROM CURRENT_DATE)
    LIMIT 1
    ) AS phieu_thang_nay
FROM vi_tri v
LEFT JOIN khu_vuc k ON v.khu_vuc_id = k.id;

-- ============================================================
-- VIEW: lịch sử theo tháng (cho calendar)
-- ============================================================
CREATE VIEW v_lich_su_kiem_tra AS
SELECT
    p.id,
    p.vi_tri_id,
    p.thang,
    p.nam,
    p.ngay_kiem_tra,
    p.trang_thai,
    p.so_dat,
    p.tong_tieu_chi,
    p.ghi_chu,
    n.ho_ten AS ten_nhan_vien
FROM phieu_kiem_tra p
LEFT JOIN nhan_vien n ON p.nhan_vien_id = n.id;

-- ============================================================
-- DỮ LIỆU MẪU
-- ============================================================

-- Khu vực
INSERT INTO khu_vuc (ma_khu_vuc, ten_khu_vuc) VALUES
    ('T1', 'Tầng 1'),
    ('T2', 'Tầng 2'),
    ('T3', 'Tầng 3'),
    ('KHO', 'Kho hàng'),
    ('HLT', 'Hầm để xe');

-- Loại bình
INSERT INTO loai_binh (ma_loai, ten_loai, mo_ta) VALUES
    ('CO2_MT3',  'Bình CO₂ MT3',       'Bình khí CO2 loại MT3'),
    ('Bot_MFZ8', 'Bình Bột MFZ8 ABC',  'Bình bột khô ABC loại MFZ8'),
    ('MFZT35',   'Bình MFZT-35',       'Bình bột xe đẩy MFZT-35'),
    ('K',        'Bình K',             'Bình chữa cháy loại K');

-- Tiêu chí kiểm tra — CO2 MT3 (8 tiêu chí)
INSERT INTO tieu_chi (loai_binh_id, stt, noi_dung)
SELECT id, stt, noi_dung FROM loai_binh, (VALUES
    (1, 'Đặt đúng vị trí, dễ lấy'),
    (2, 'Có bảng nhận diện PCCC'),
    (3, 'Chốt + niêm chì còn nguyên'),
    (4, 'Vòi/loa phun không hư hỏng'),
    (5, 'Thân bình không móp méo, rỉ sét'),
    (6, 'Không rò rỉ khí'),
    (7, 'Trọng lượng bình đạt yêu cầu'),
    (8, 'Tem kiểm định còn hiệu lực')
) AS t(stt, noi_dung)
WHERE ma_loai = 'CO2_MT3';

-- Tiêu chí kiểm tra — Bột MFZ8 (8 tiêu chí)
INSERT INTO tieu_chi (loai_binh_id, stt, noi_dung)
SELECT id, stt, noi_dung FROM loai_binh, (VALUES
    (1, 'Đặt đúng vị trí, dễ lấy'),
    (2, 'Có bảng nhận diện PCCC'),
    (3, 'Áp kế trong vùng xanh'),
    (4, 'Chốt + niêm chì còn nguyên'),
    (5, 'Vòi/loa phun không hư hỏng'),
    (6, 'Thân bình không móp méo, rỉ sét'),
    (7, 'Không rò rỉ bột/khí'),
    (8, 'Tem kiểm định còn hiệu lực')
) AS t(stt, noi_dung)
WHERE ma_loai = 'Bot_MFZ8';

-- Tiêu chí kiểm tra — MFZT-35 (7 tiêu chí)
INSERT INTO tieu_chi (loai_binh_id, stt, noi_dung)
SELECT id, stt, noi_dung FROM loai_binh, (VALUES
    (1, 'Đặt đúng vị trí, dễ di chuyển'),
    (2, 'Có bảng nhận diện PCCC'),
    (3, 'Áp kế trong vùng xanh'),
    (4, 'Chốt + niêm chì còn nguyên'),
    (5, 'Vòi/loa phun không hư hỏng'),
    (6, 'Thân bình không móp méo, rỉ sét'),
    (7, 'Tem kiểm định còn hiệu lực')
) AS t(stt, noi_dung)
WHERE ma_loai = 'MFZT35';

-- Tiêu chí kiểm tra — Bình K (6 tiêu chí)
INSERT INTO tieu_chi (loai_binh_id, stt, noi_dung)
SELECT id, stt, noi_dung FROM loai_binh, (VALUES
    (1, 'Đặt đúng vị trí, dễ lấy'),
    (2, 'Có bảng nhận diện PCCC'),
    (3, 'Áp kế trong vùng xanh'),
    (4, 'Chốt + niêm chì còn nguyên'),
    (5, 'Thân bình không móp méo, rỉ sét'),
    (6, 'Tem kiểm định còn hiệu lực')
) AS t(stt, noi_dung)
WHERE ma_loai = 'K';

-- Nhân viên mẫu
INSERT INTO nhan_vien (ho_ten, ma_nhan_vien, mat_khau, quyen) VALUES
    ('Quản trị viên', 'admin',  crypt('Admin@123', gen_salt('bf')), 'toan_quyen'),
    ('Nguyễn Văn An', 'nv001',  crypt('Nv001@123', gen_salt('bf')), 'cap_nhat'),
    ('Trần Thị Bình',  'nv002', crypt('Nv002@123', gen_salt('bf')), 'cap_nhat');

-- Vị trí mẫu
INSERT INTO vi_tri (so_thu_tu, ten_vi_tri, khu_vuc_id) VALUES
    (1, 'Hành lang tầng 1 - Cầu thang A', (SELECT id FROM khu_vuc WHERE ma_khu_vuc = 'T1')),
    (2, 'Phòng kỹ thuật tầng 1',          (SELECT id FROM khu_vuc WHERE ma_khu_vuc = 'T1')),
    (3, 'Hành lang tầng 2 - Cầu thang A', (SELECT id FROM khu_vuc WHERE ma_khu_vuc = 'T2')),
    (4, 'Hành lang tầng 2 - Cầu thang B', (SELECT id FROM khu_vuc WHERE ma_khu_vuc = 'T2')),
    (5, 'Khu vực kho chính',               (SELECT id FROM khu_vuc WHERE ma_khu_vuc = 'KHO'));

-- Bình tại vị trí mẫu (vị trí 1: CO2 + Bột, vị trí 2: Bột, ...)
INSERT INTO binh_tai_vi_tri (vi_tri_id, loai_binh_id, so_luong)
SELECT v.id, lb.id, 1
FROM vi_tri v, loai_binh lb
WHERE v.so_thu_tu = 1 AND lb.ma_loai IN ('CO2_MT3', 'Bot_MFZ8');

INSERT INTO binh_tai_vi_tri (vi_tri_id, loai_binh_id, so_luong)
SELECT v.id, lb.id, 1
FROM vi_tri v, loai_binh lb
WHERE v.so_thu_tu = 2 AND lb.ma_loai = 'Bot_MFZ8';

INSERT INTO binh_tai_vi_tri (vi_tri_id, loai_binh_id, so_luong)
SELECT v.id, lb.id, 1
FROM vi_tri v, loai_binh lb
WHERE v.so_thu_tu = 3 AND lb.ma_loai IN ('CO2_MT3', 'Bot_MFZ8');

INSERT INTO binh_tai_vi_tri (vi_tri_id, loai_binh_id, so_luong)
SELECT v.id, lb.id, 1
FROM vi_tri v, loai_binh lb
WHERE v.so_thu_tu = 4 AND lb.ma_loai = 'CO2_MT3';

INSERT INTO binh_tai_vi_tri (vi_tri_id, loai_binh_id, so_luong)
SELECT v.id, lb.id, 1
FROM vi_tri v, loai_binh lb
WHERE v.so_thu_tu = 5 AND lb.ma_loai IN ('Bot_MFZ8', 'MFZT35');

-- ============================================================
-- MIGRATION: THIẾT BỊ PCCC (Hộp vòi, Hộp phá dỡ, Trạm bơm)
-- ============================================================

-- 10. THIẾT BỊ PCCC
CREATE TABLE thiet_bi_pccc (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loai         VARCHAR(20) NOT NULL CHECK (loai IN ('hop_voi','hop_pha_do','tram_bom')),
    so_thu_tu    INT NOT NULL,
    khu_vuc_id   UUID REFERENCES khu_vuc(id) ON DELETE SET NULL,
    mo_ta        TEXT,
    qr_code      TEXT UNIQUE,
    trang_thai   VARCHAR(20) NOT NULL DEFAULT 'hoat_dong'
                 CHECK (trang_thai IN ('hoat_dong','ngung')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (loai, so_thu_tu)
);

CREATE INDEX idx_thiet_bi_loai    ON thiet_bi_pccc(loai);
CREATE INDEX idx_thiet_bi_khu_vuc ON thiet_bi_pccc(khu_vuc_id);

CREATE TRIGGER trg_thiet_bi_updated_at
    BEFORE UPDATE ON thiet_bi_pccc
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 11. TIÊU CHÍ THIẾT BỊ PCCC
CREATE TABLE tieu_chi_thiet_bi (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loai      VARCHAR(20) NOT NULL CHECK (loai IN ('hop_voi','hop_pha_do','tram_bom')),
    stt       INT NOT NULL,
    noi_dung  TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (loai, stt)
);

-- 12. PHIẾU KIỂM TRA THIẾT BỊ PCCC
CREATE TABLE phieu_kiem_tra_tb (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thiet_bi_id     UUID NOT NULL REFERENCES thiet_bi_pccc(id) ON DELETE RESTRICT,
    thang           INT NOT NULL CHECK (thang BETWEEN 1 AND 12),
    nam             INT NOT NULL,
    ngay_kiem_tra   DATE,
    nguoi_kiem_tra  UUID REFERENCES nhan_vien(id) ON DELETE SET NULL,
    trang_thai      VARCHAR(20) NOT NULL DEFAULT 'chua_hoan_thanh'
                    CHECK (trang_thai IN ('chua_hoan_thanh','dat_het','co_khong_dat')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (thiet_bi_id, thang, nam)
);

CREATE INDEX idx_phieu_tb_thiet_bi  ON phieu_kiem_tra_tb(thiet_bi_id);
CREATE INDEX idx_phieu_tb_thang_nam ON phieu_kiem_tra_tb(thang, nam);

CREATE TRIGGER trg_phieu_tb_updated_at
    BEFORE UPDATE ON phieu_kiem_tra_tb
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 13. KẾT QUẢ TIÊU CHÍ THIẾT BỊ PCCC
CREATE TABLE ket_qua_tb (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phieu_id         UUID NOT NULL REFERENCES phieu_kiem_tra_tb(id) ON DELETE CASCADE,
    tieu_chi_id      UUID NOT NULL REFERENCES tieu_chi_thiet_bi(id) ON DELETE RESTRICT,
    ket_qua          VARCHAR(20) CHECK (ket_qua IN ('dat','khong_dat')),
    bien_phap        TEXT,
    ngay_hoan_thanh  DATE,
    UNIQUE (phieu_id, tieu_chi_id)
);

CREATE INDEX idx_ket_qua_tb_phieu ON ket_qua_tb(phieu_id);

CREATE OR REPLACE FUNCTION recalc_phieu_tb_stats()
RETURNS TRIGGER AS $$
DECLARE
    v_phieu_id   UUID;
    v_tong       INTEGER;
    v_dat        INTEGER;
    v_trang_thai VARCHAR(20);
BEGIN
    v_phieu_id := COALESCE(NEW.phieu_id, OLD.phieu_id);

    SELECT COUNT(*), COUNT(*) FILTER (WHERE ket_qua = 'dat')
    INTO v_tong, v_dat
    FROM ket_qua_tb
    WHERE phieu_id = v_phieu_id;

    IF v_tong = 0 OR v_dat = 0 THEN
        v_trang_thai := 'chua_hoan_thanh';
    ELSIF v_dat = v_tong THEN
        v_trang_thai := 'dat_het';
    ELSE
        v_trang_thai := 'co_khong_dat';
    END IF;

    UPDATE phieu_kiem_tra_tb
    SET trang_thai = v_trang_thai,
        updated_at = NOW()
    WHERE id = v_phieu_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_recalc_tb_stats
    AFTER INSERT OR UPDATE OR DELETE ON ket_qua_tb
    FOR EACH ROW EXECUTE FUNCTION recalc_phieu_tb_stats();

-- INSERT tiêu chí — Hộp vòi (8 tiêu chí)
INSERT INTO tieu_chi_thiet_bi (loai, stt, noi_dung) VALUES
('hop_voi', 1, 'Hộp chữa cháy sạch sẽ, không bị che khuất'),
('hop_voi', 2, 'Kính, cửa hộp, tay khóa còn nguyên vẹn'),
('hop_voi', 3, 'Có đầy đủ lăng phun, vòi chữa cháy'),
('hop_voi', 4, 'Vòi chữa cháy xếp gọn, không rách, mục, hư hỏng'),
('hop_voi', 5, 'Van chữa cháy đóng/mở bình thường, không rò rỉ'),
('hop_voi', 6, 'Tem/biển chỉ dẫn PCCC đầy đủ, dễ nhận biết'),
('hop_voi', 7, 'Khu vực xung quanh đảm bảo lối tiếp cận ≥ 1 m'),
('hop_voi', 8, 'Thực hiện xả nước kiểm tra định kỳ (nếu có kế hoạch)');

-- INSERT tiêu chí — Hộp phá dỡ (8 tiêu chí)
INSERT INTO tieu_chi_thiet_bi (loai, stt, noi_dung) VALUES
('hop_pha_do', 1, 'Hộp đựng dụng cụ sạch sẽ, không bị che khuất'),
('hop_pha_do', 2, 'Có đầy đủ búa phá dỡ'),
('hop_pha_do', 3, 'Có đầy đủ rìu'),
('hop_pha_do', 4, 'Có đầy đủ kiềm cộng lực'),
('hop_pha_do', 5, 'Có đầy đủ xà beng'),
('hop_pha_do', 6, 'Có đầy đủ cưa cắt sắt'),
('hop_pha_do', 7, 'Có đầy đủ xà beng nhổ đinh'),
('hop_pha_do', 8, 'Dụng cụ không bị rỉ sét, cong gãy, hư hỏng');

-- INSERT tiêu chí — Trạm bơm (11 tiêu chí)
INSERT INTO tieu_chi_thiet_bi (loai, stt, noi_dung) VALUES
('tram_bom', 1,  'Khu vực trạm bơm sạch sẽ, không cản trở thao tác'),
('tram_bom', 2,  'Không có rò rỉ dầu, nước tại máy bơm và đường ống'),
('tram_bom', 3,  'Đồng hồ áp lực hoạt động bình thường'),
('tram_bom', 4,  'Tủ điện, đèn báo, CB hoạt động bình thường'),
('tram_bom', 5,  'Mức nhiên liệu máy bơm Diezel đảm bảo'),
('tram_bom', 6,  'Bình ắc quy máy Diezel hoạt động bình thường'),
('tram_bom', 7,  'Khởi động máy bơm Diezel số 1 bình thường'),
('tram_bom', 8,  'Khởi động máy bơm Diezel số 2 bình thường'),
('tram_bom', 9,  'Mô tơ bơm điện hoạt động bình thường'),
('tram_bom', 10, 'Mô tơ bơm bù áp hoạt động bình thường'),
('tram_bom', 11, 'Âm thanh, rung động khi chạy máy bình thường');

