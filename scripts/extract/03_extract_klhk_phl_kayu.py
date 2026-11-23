"""
Step 3: Ekstraksi Folder 3 — raw_data/03_klhk_phl_kayu/
Prinsip Strict Scientist / Zero-Merge:
- 1 tabel PDF = 1 file CSV mentah (tidak digabung antar buku atau antar PBPH vs Perhutani).
  1. buku_2024/tabel_3_9_pbph_provinsi_2020_2024.csv       (Statistik PHL 2024, hal. 152, pdfplumber, m3)
  2. buku_2024/tabel_3_12_perhutani_provinsi_2020_2024.csv (Statistik PHL 2024, hal. 155, pdfplumber, m3)
  3. buku_2022/tabel_pbph_provinsi_2018_2022.csv           (Statistik PHL 2022, hal. 113-114, PyMuPDF, m3)
  4. buku_2022/tabel_perhutani_provinsi_2018_2022.csv      (Statistik PHL 2022, hal. 117, PyMuPDF, m3)
- Tanda '-' atau sel kosong di PDF disimpan sebagai NULL (kosong di CSV), TIDAK dijadikan 0.
- Reconciliation check wajib: SUM(provinsi) vs baris JUMLAH tercetak di PDF untuk setiap tahun (2018-2024)
  disimpan ke _audit_03_klhk_phl_reconciliation.csv.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pdfplumber
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils_raw import (  # noqa: E402
    ARCHIVE_PDF_DIR,
    RAW_DIR,
    RequestLogger,
    add_provenance_cols,
    ensure_raw_folder_tree,
    make_http_session,
    today_iso,
    write_raw_csv,
)

FOLDER_3 = RAW_DIR / "03_klhk_phl_kayu"
PHL_2024_URL = "https://phl.kehutanan.go.id/media/statistik/statistik_file_1788408189.pdf"
PHL_2022_URL = "https://phl.kehutanan.go.id/media/statistik/statistik_file_1726677781.pdf"

PHL_2024_LOCAL = ARCHIVE_PDF_DIR / "klhk_phl_2024.pdf"
PHL_2022_LOCAL = ARCHIVE_PDF_DIR / "klhk_phl_2.pdf"


def parse_num_strict(val: str | None, style: str) -> float:
    """
    Parse angka PDF secara ketat:
    - style='id' (Buku PHL 2024): titik = ribuan, koma = desimal (misal '1.513,12', '832')
    - style='en' (Buku PHL 2022): koma = ribuan, titik = desimal (misal '1,513.12', '387.56')
    - Tanda '-' atau kosong -> np.nan (NULL).
    - Angka '0' / '0,00' / '0.00' -> 0.0.
    """
    if val is None:
        return np.nan
    s = str(val).replace("\u00a0", " ").strip()
    if not s or s in {"-", "–", "—", "...", "n/a", "N/A"}:
        return np.nan
    s = re.sub(r"\s+", "", s)
    if style == "id":
        s = s.replace(".", "").replace(",", ".")
    elif style == "en":
        s = s.replace(",", "")
    else:
        raise ValueError(f"Unknown style: {style}")
    try:
        return float(s)
    except ValueError:
        return np.nan


def ensure_pdf(local_path: Path, url: str, session, logger: RequestLogger, tag: str) -> Path:
    if local_path.exists() and local_path.stat().st_size > 100_000:
        print(f"  [PDF Cache] Memakai file lokal terverifikasi: {local_path.name} ({local_path.stat().st_size / 1e6:.2f} MB)", flush=True)
        return local_path
    print(f"  [PDF Download] Mengunduh {url} ...", flush=True)
    t0 = time.perf_counter()
    r = session.get(url, timeout=60)
    elapsed = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(r.content)
    logger.log(tag, "GET", url, r.status_code, elapsed, output_file=str(local_path))
    return local_path


def extract_phl_2024_table(pdf_path: Path, page_1idx: int, years: list[str], jenis_izin: str):
    """Ekstrak tabel berbatas garis di PDF PHL 2024 via pdfplumber (format angka Indonesia)."""
    rows = []
    printed_total = {}
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_1idx - 1]
        for tbl in page.extract_tables():
            for raw_row in tbl:
                cells = [
                    re.sub(r"\s+", " ", str(c)).strip() if c is not None else ""
                    for c in raw_row
                ]
                if len(cells) < 2 + len(years):
                    continue
                c0, c1 = cells[0], cells[1]
                # Cek baris JUMLAH
                if c0.upper() == "JUMLAH" or c1.upper() == "JUMLAH":
                    val_cells = cells[2 : 2 + len(years)]
                    for yr, vc in zip(years, val_cells):
                        printed_total[yr] = parse_num_strict(vc, style="id")
                    continue
                if not re.match(r"^\d{1,2}$", c0):
                    continue
                rec = {
                    "no_tabel": int(c0),
                    "provinsi_pdf": c1,
                    "sumber_kayu": jenis_izin,
                    "edisi_buku": "Statistik PHL 2024",
                    "halaman_pdf": page_1idx,
                }
                for idx, yr in enumerate(years):
                    rec[yr] = parse_num_strict(cells[2 + idx], style="id")
                rows.append(rec)
    return pd.DataFrame(rows), printed_total


def extract_phl_2022_text_table(pdf_path: Path, pages_1idx: list[int], years: list[str], jenis_izin: str):
    """Ekstrak tabel tanpa garis vertikal di PDF PHL 2022 via PyMuPDF (format angka Inggris)."""
    doc = pymupdf.open(pdf_path)
    lines = []
    for pno in pages_1idx:
        for ln in doc[pno - 1].get_text("text").splitlines():
            s = re.sub(r"\s+", " ", ln).strip()
            if s:
                lines.append(s)

    num_pat = re.compile(r"^(?:-|–|\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)$")

    # Ambil baris JUMLAH tercetak: di PDF 2022, 5 angka tepat sebelum token "JUMLAH"
    printed_total = {}
    for idx, ln in enumerate(lines):
        if ln.upper() == "JUMLAH" and idx >= len(years):
            cand = lines[idx - len(years) : idx]
            if all(num_pat.match(c) for c in cand):
                for yr, vc in zip(years, cand):
                    printed_total[yr] = parse_num_strict(vc, style="en")
                break

    # Ekstrak baris 1..N secara berurutan
    rows = []
    expected_no = 1
    i = 0
    while i < len(lines):
        ln = lines[i]
        # Cocokkan nomor baris persis expected_no (bisa sendiri "1" atau "10 Kep. Bangka Belitung")
        m = re.match(rf"^{expected_no}(?:\s+(.+))?$", ln)
        if m:
            rest = (m.group(1) or "").strip()
            # Jangan salah tangkap header halaman/tahun
            if rest and num_pat.match(rest):
                i += 1
                continue
            name_parts = [rest] if rest else []
            vals = []
            j = i + 1
            while j < len(lines) and len(vals) < len(years):
                cur = lines[j]
                if cur.upper() == "JUMLAH":
                    break
                if num_pat.match(cur):
                    vals.append(parse_num_strict(cur, style="en"))
                elif not vals:
                    name_parts.append(cur)
                else:
                    break
                j += 1

            prov_name = re.sub(r"\s+", " ", " ".join(name_parts)).strip()
            if prov_name and len(vals) == len(years):
                rec = {
                    "no_tabel": expected_no,
                    "provinsi_pdf": prov_name,
                    "sumber_kayu": jenis_izin,
                    "edisi_buku": "Statistik PHL 2022",
                    "halaman_pdf": ",".join(str(p) for p in pages_1idx),
                }
                for yr, v in zip(years, vals):
                    rec[yr] = v
                rows.append(rec)
                expected_no += 1
                i = j
                continue
        i += 1

    return pd.DataFrame(rows), printed_total


def reconcile(df: pd.DataFrame, printed_total: dict[str, float], years: list[str], buku: str, tabel: str, file_rel: str):
    rec_rows = []
    for yr in years:
        calc_sum = float(df[yr].dropna().sum()) if yr in df.columns else np.nan
        pdf_tot = printed_total.get(yr, np.nan)
        diff = round(calc_sum - pdf_tot, 4) if pd.notna(calc_sum) and pd.notna(pdf_tot) else np.nan
        pct_diff = round((abs(diff) / pdf_tot) * 100.0, 6) if pd.notna(diff) and pdf_tot else np.nan
        n_pos = int((df[yr].dropna() > 0).sum()) if yr in df.columns else 0
        n_zero = int((df[yr].dropna() == 0).sum()) if yr in df.columns else 0
        n_null = int(df[yr].isna().sum()) if yr in df.columns else 0
        status = "MATCH" if pd.notna(diff) and abs(diff) <= 0.05 else "MISMATCH"
        rec_rows.append(
            {
                "buku": buku,
                "tabel": tabel,
                "file_relatif": file_rel,
                "tahun": int(yr),
                "jumlah_baris_provinsi": len(df),
                "provinsi_positif": n_pos,
                "provinsi_nol_eksplisit": n_zero,
                "provinsi_null_dash": n_null,
                "sum_ekstrak_m3": round(calc_sum, 2),
                "jumlah_cetak_pdf_m3": round(pdf_tot, 2) if pd.notna(pdf_tot) else np.nan,
                "selisih_m3": diff,
                "selisih_pct": pct_diff,
                "status_rekonsiliasi": status,
            }
        )
    return rec_rows


def main():
    ensure_raw_folder_tree()
    tanggal_tarik = today_iso()
    session = make_http_session(retries=3, backoff_factor=0.8)
    logger = RequestLogger("03_extract_klhk_phl_kayu")

    print("=" * 72, flush=True)
    print("STEP 3: EKSTRAKSI FOLDER 3 — raw_data/03_klhk_phl_kayu/", flush=True)
    print("=" * 72, flush=True)

    pdf_2024 = ensure_pdf(PHL_2024_LOCAL, PHL_2024_URL, session, logger, "klhk_phl_2024")
    pdf_2022 = ensure_pdf(PHL_2022_LOCAL, PHL_2022_URL, session, logger, "klhk_phl_2022")

    specs = [
        {
            "buku": "buku_2024",
            "tabel": "Tabel 3.9 PBPH (2020-2024)",
            "out_path": FOLDER_3 / "buku_2024" / "tabel_3_9_pbph_provinsi_2020_2024.csv",
            "url": PHL_2024_URL,
            "extractor": lambda: extract_phl_2024_table(pdf_2024, 152, ["2020", "2021", "2022", "2023", "2024"], "PBPH"),
            "years": ["2020", "2021", "2022", "2023", "2024"],
        },
        {
            "buku": "buku_2024",
            "tabel": "Tabel 3.12 Perhutani (2020-2024)",
            "out_path": FOLDER_3 / "buku_2024" / "tabel_3_12_perhutani_provinsi_2020_2024.csv",
            "url": PHL_2024_URL,
            "extractor": lambda: extract_phl_2024_table(pdf_2024, 155, ["2020", "2021", "2022", "2023", "2024"], "Perum Perhutani"),
            "years": ["2020", "2021", "2022", "2023", "2024"],
        },
        {
            "buku": "buku_2022",
            "tabel": "Tabel 3.9 PBPH (2018-2022)",
            "out_path": FOLDER_3 / "buku_2022" / "tabel_pbph_provinsi_2018_2022.csv",
            "url": PHL_2022_URL,
            "extractor": lambda: extract_phl_2022_text_table(pdf_2022, [113, 114], ["2018", "2019", "2020", "2021", "2022"], "PBPH"),
            "years": ["2018", "2019", "2020", "2021", "2022"],
        },
        {
            "buku": "buku_2022",
            "tabel": "Tabel 3.12 Perhutani (2018-2022)",
            "out_path": FOLDER_3 / "buku_2022" / "tabel_perhutani_provinsi_2018_2022.csv",
            "url": PHL_2022_URL,
            "extractor": lambda: extract_phl_2022_text_table(pdf_2022, [117], ["2018", "2019", "2020", "2021", "2022"], "Perum Perhutani"),
            "years": ["2018", "2019", "2020", "2021", "2022"],
        },
    ]

    all_recon = []
    for sp in specs:
        df, printed_tot = sp["extractor"]()
        df = add_provenance_cols(
            df,
            sumber_instansi="Ditjen Pengelolaan Hutan Lestari (PHL) Kemenhut/KLHK",
            sumber_url=sp["url"],
            satuan_asli="m3",
            level_wilayah="PROVINSI",
            tanggal_tarik=tanggal_tarik,
        )
        write_raw_csv(df, sp["out_path"])
        rel = str(sp["out_path"].relative_to(RAW_DIR)).replace("\\", "/")
        recon = reconcile(df, printed_tot, sp["years"], sp["buku"], sp["tabel"], rel)
        all_recon.extend(recon)

        mismatches = [r for r in recon if r["status_rekonsiliasi"] != "MATCH"]
        print(
            f"  [OK] {rel:<64} | rows={len(df):2d} | recon_match={len(recon)-len(mismatches)}/{len(recon)}",
            flush=True,
        )
        for m in mismatches:
            print(
                f"       [MISMATCH] {m['tahun']}: sum={m['sum_ekstrak_m3']:,.2f} vs pdf={m['jumlah_cetak_pdf_m3']:,.2f} (diff={m['selisih_m3']:,.2f})",
                flush=True,
            )

    df_recon = pd.DataFrame(all_recon)
    recon_path = FOLDER_3 / "_audit_03_klhk_phl_reconciliation.csv"
    write_raw_csv(df_recon, recon_path)

    n_match = int((df_recon["status_rekonsiliasi"] == "MATCH").sum())
    print("\n" + "=" * 72, flush=True)
    print(f"SELESAI STEP 3: 4 tabel PDF diekstrak | Rekonsiliasi MATCH: {n_match}/{len(df_recon)}", flush=True)
    print(f"Audit rekonsiliasi disimpan ke: {recon_path}", flush=True)
    print("=" * 72, flush=True)


if __name__ == "__main__":
    main()
