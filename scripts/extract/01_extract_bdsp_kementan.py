"""
Step 1: Ekstraksi Folder 1 — raw_data/01_bdsp_kementan/
Prinsip Strict Scientist / Zero-Merge:
- 1 request POST BDSP Kab/Kota (per komoditas x per provinsi) = 1 file CSV sendiri.
  (4 komoditas x 38 provinsi = 152 file di {komoditas}/kabkota/{kode}_{slug}.csv)
- 1 request POST BDSP Provinsi (per komoditas) = 1 file CSV sendiri.
  (4 file di {komoditas}/provinsi/bdsp_{komoditas}_38_provinsi.csv)
- 1 konversi mentah 1:1 Excel Satu Data Kementan (Kelapa Sawit 2023) = 1 file CSV sendiri.
  (satudata_kementan/sawit_kabkota_2023.csv)
- Audit lengkap ke _audit_01_bdsp_kementan.csv.

Tidak ada penggabungan antar-provinsi atau antar-komoditas, tidak ada perhitungan RPR/limbah.
"""

from __future__ import annotations

import io
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils_raw import (  # noqa: E402
    PROVINCES_38,
    RAW_DIR,
    RequestLogger,
    add_provenance_cols,
    ensure_raw_folder_tree,
    make_http_session,
    parse_bdsp_number,
    today_iso,
    write_raw_csv,
)

BDSP_BASE = "https://bdsp2.pertanian.go.id/bdsp/id"
BDSP_URL_LOKASI = f"{BDSP_BASE}/lokasi"
BDSP_URL_RESULT = f"{BDSP_BASE}/lokasi/result"
SATUDATA_SAWIT_URL = (
    "https://satudata.pertanian.go.id/assets/docs/metadata/"
    "45_Luas_perkebunan_kelapa_sawit_di_kabupaten.xlsx"
)

FOLDER_1 = RAW_DIR / "01_bdsp_kementan"

BDSP_COMMODITIES = [
    {
        "slug": "padi",
        "subsektorcd": "01",
        "subsektornm": "Tanaman Pangan",
        "komcd": "01059",
        "komnm": "PADI",
        "indicd": "0104",
    },
    {
        "slug": "kelapa_sawit",
        "subsektorcd": "02",
        "subsektornm": "Perkebunan",
        "komcd": "02027",
        "komnm": "KELAPA SAWIT",
        "indicd": "0205",
    },
    {
        "slug": "tebu",
        "subsektorcd": "02",
        "subsektornm": "Perkebunan",
        "komcd": "02051",
        "komnm": "TEBU",
        "indicd": "0205",
    },
    {
        "slug": "jagung",
        "subsektorcd": "01",
        "subsektornm": "Tanaman Pangan",
        "komcd": "01027",
        "komnm": "JAGUNG",
        "indicd": "0104",
    },
]


def _clean_html_cell(cell_html: str) -> str:
    txt = re.sub(r"<[^>]+>", "", cell_html)
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", txt).strip()


def parse_bdsp_table_html(html: str):
    """
    Parse tabel HTML keluaran POST /lokasi/result.
    Mengembalikan:
      years: list[str] (misal ['2010', ..., '2026'])
      rows: list[dict] (baris wilayah asli tanpa baris TOTAL)
      printed_totals: dict[str, float] (baris TOTAL tercetak di HTML jika ada)
      raw_cell_stats: dict (n_explicit_zero, n_null, n_positive)
    """
    tr_list = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    if len(tr_list) < 2:
        return [], [], {}, {"n_explicit_zero": 0, "n_null": 0, "n_positive": 0}

    header_cells = [
        _clean_html_cell(c)
        for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr_list[0], re.S | re.I)
    ]
    years = [c for c in header_cells[2:] if re.match(r"^\d{4}$", c)]
    if not years:
        return [], [], {}, {"n_explicit_zero": 0, "n_null": 0, "n_positive": 0}

    rows = []
    printed_totals = {}
    stats = {"n_explicit_zero": 0, "n_null": 0, "n_positive": 0}

    for tr in tr_list[1:]:
        tds = [
            _clean_html_cell(c)
            for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)
        ]
        if not tds:
            continue

        # Deteksi baris TOTAL / JUMLAH (sering colspan=2 sehingga jumlah sel = 1 + len(years))
        first_two = " ".join(tds[:2]).lower()
        if tds[0].lower() in {"total", "jumlah"} or (
            len(tds) >= 2 and tds[1].lower() in {"total", "jumlah"}
        ):
            offset = 1 if tds[0].lower() in {"total", "jumlah"} else 2
            if len(tds) >= offset + len(years):
                for idx, yr in enumerate(years):
                    printed_totals[yr] = parse_bdsp_number(tds[offset + idx])
            continue

        if len(tds) < 2 + len(years):
            continue

        no_str = tds[0]
        loc_raw = tds[1]
        if not loc_raw or "jumlah" in first_two or "total" in first_two:
            continue

        m = re.match(r"^(\d+)\s*-\s*(.+)$", loc_raw)
        if m:
            kode_wilayah, nama_wilayah = m.group(1).strip(), m.group(2).strip()
        else:
            kode_wilayah, nama_wilayah = "", loc_raw

        rec = {
            "no_urut": no_str,
            "kode_wilayah": kode_wilayah,
            "nama_wilayah": nama_wilayah,
            "lokasi_raw": loc_raw,
        }
        for idx, yr in enumerate(years):
            val = parse_bdsp_number(tds[2 + idx])
            rec[yr] = val
            if pd.isna(val):
                stats["n_null"] += 1
            elif val == 0.0:
                stats["n_explicit_zero"] += 1
            else:
                stats["n_positive"] += 1
        rows.append(rec)

    return years, rows, printed_totals, stats


def post_bdsp(session, comm: dict, level: str, prov_code: str, prov_name: str, y1="2010", y2="2026", max_attempts: int = 5):
    payload = {
        "subsektor": comm["subsektorcd"],
        "subsektorcd": comm["subsektorcd"],
        "subsektornm": comm["subsektornm"],
        "komoditas": comm["komcd"],
        "komoditasnm": comm["komnm"],
        "indikator": comm["indicd"],
        "indikatornm": "PRODUKSI",
        "level": level,
        "levelnm": "Kabupaten" if level == "03" else "Provinsi",
        "prov": prov_code,
        "provnm": prov_name,
        "kab": "00",
        "kabnm": "-- Pilih Kabupaten --",
        "satuan": "20",
        "satuannm": "Ton",
        "sts_angka": "6",
        "sts_angkanm": "Angka Tetap",
        "sumb_data": "01",
        "sumb_datanm": "Kementerian Pertanian",
        "tahunAwal": y1,
        "tahunAkhir": y2,
    }
    last_resp = None
    for attempt in range(1, max_attempts + 1):
        resp = session.post(BDSP_URL_RESULT, data=payload, timeout=30)
        last_resp = resp
        if resp.status_code == 200 and "<tr" in resp.text.lower():
            return resp
        # Refresh cookie sesi bila kena Cloudflare 520/5xx atau respons kosong
        wait_sec = 1.2 * attempt
        print(f"    [Retry {attempt}/{max_attempts}] HTTP {resp.status_code} untuk {comm['slug']} lvl={level} prov={prov_code}; tunggu {wait_sec:.1f}s...", flush=True)
        time.sleep(wait_sec)
        try:
            session.get(BDSP_URL_LOKASI, timeout=20)
        except Exception:
            pass
    return last_resp


def compute_year_range_and_nonzero_locs(rows: list[dict], years: list[str]):
    """Hitung rentang tahun aktual yang memiliki nilai > 0 dan jumlah wilayah non-nol."""
    active_years = []
    nonzero_loc_count = 0
    for r in rows:
        has_pos = any(pd.notna(r.get(y)) and r.get(y) > 0 for y in years)
        if has_pos:
            nonzero_loc_count += 1
    for y in years:
        if any(pd.notna(r.get(y)) and r.get(y) > 0 for r in rows):
            active_years.append(int(y))
    if active_years:
        span = f"{min(active_years)}-{max(active_years)}"
        return min(active_years), max(active_years), span, nonzero_loc_count
    return np.nan, np.nan, "", nonzero_loc_count


def extract_satudata_sawit_2023(session, logger: RequestLogger, tanggal_tarik: str):
    """Konversi mentah 1:1 Excel Satu Data Kementan Kelapa Sawit Kab/Kota 2023 ke CSV."""
    out_path = FOLDER_1 / "satudata_kementan" / "sawit_kabkota_2023.csv"
    t0 = time.perf_counter()
    try:
        resp = session.get(SATUDATA_SAWIT_URL, timeout=30)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        status = resp.status_code
        resp.raise_for_status()

        raw_df = pd.read_excel(io.BytesIO(resp.content), sheet_name=0, header=None)
        # Baris 0: judul; Baris 1: kosong; Baris 2-3: merged header; Baris 4..akhir: isi data
        # Pertahankan 1:1 seluruh baris isi (row 4..akhir), beri konteks provinsi & tipe_baris tanpa menghapus baris
        current_prov = ""
        records = []
        n_zero = 0
        n_null = 0
        n_pos = 0
        n_kab_non_nol = 0

        for excel_row_idx in range(4, len(raw_df)):
            row = raw_df.iloc[excel_row_idx]
            wilayah_raw = "" if pd.isna(row.iloc[0]) else str(row.iloc[0]).strip()
            nums_raw = [row.iloc[i] if i < len(row) else np.nan for i in range(1, 8)]
            all_nums_empty = all(pd.isna(x) or str(x).strip() == "" for x in nums_raw)

            if not wilayah_raw and all_nums_empty:
                continue

            if all_nums_empty:
                current_prov = wilayah_raw
                tipe_baris = "PROVINSI_HEADER"
            elif wilayah_raw.upper().startswith(("KAB.", "KOTA", "KAB ")):
                tipe_baris = "KABKOTA"
            elif "JUMLAH" in wilayah_raw.upper() or "TOTAL" in wilayah_raw.upper() or "INDONESIA" in wilayah_raw.upper():
                tipe_baris = "TOTAL"
            else:
                tipe_baris = "KABKOTA"

            parsed_nums = [parse_bdsp_number(x) for x in nums_raw]
            for v in parsed_nums:
                if pd.isna(v):
                    n_null += 1
                elif v == 0.0:
                    n_zero += 1
                else:
                    n_pos += 1

            prod_val = parsed_nums[4]
            if tipe_baris == "KABKOTA" and pd.notna(prod_val) and prod_val > 0:
                n_kab_non_nol += 1

            records.append(
                {
                    "baris_excel": excel_row_idx + 1,
                    "tipe_baris": tipe_baris,
                    "provinsi_konteks": current_prov,
                    "kabupaten_kota_raw": wilayah_raw,
                    "luas_tbm_ha": parsed_nums[0],
                    "luas_tm_ha": parsed_nums[1],
                    "luas_ttm_tr_ha": parsed_nums[2],
                    "luas_jumlah_ha": parsed_nums[3],
                    "produksi_ton": parsed_nums[4],
                    "produktivitas_kg_ha": parsed_nums[5],
                    "jumlah_petani_kk": parsed_nums[6],
                    "tahun": 2023,
                }
            )

        df_out = pd.DataFrame(records)
        df_out = add_provenance_cols(
            df_out,
            sumber_instansi="Satu Data Kementerian Pertanian",
            sumber_url=SATUDATA_SAWIT_URL,
            satuan_asli="Luas: Ha; Produksi: Ton; Produktivitas: Kg/Ha; Petani: KK",
            level_wilayah="KABKOTA",
            tanggal_tarik=tanggal_tarik,
        )
        write_raw_csv(df_out, out_path)
        logger.log(
            target_id="satudata_sawit_2023",
            method="GET",
            url=SATUDATA_SAWIT_URL,
            status=status,
            duration_ms=elapsed_ms,
            rows=len(df_out),
            output_file=str(out_path.relative_to(RAW_DIR)),
        )
        return {
            "sumber": "satudata_kementan",
            "komoditas": "kelapa_sawit",
            "level_wilayah": "KABKOTA",
            "kode_prov": "00",
            "provinsi": "INDONESIA (38 PROVINSI)",
            "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
            "status_http": status,
            "status_ekstrak": "OK",
            "jumlah_baris": len(df_out),
            "jumlah_wilayah_non_nol": n_kab_non_nol,
            "tahun_awal_aktual": 2023,
            "tahun_akhir_aktual": 2023,
            "rentang_tahun_aktual": "2023",
            "sel_positif": n_pos,
            "sel_nol_eksplisit": n_zero,
            "sel_null": n_null,
            "max_selisih_vs_total_html": np.nan,
            "catatan": f"Konversi mentah 1:1 Excel resmi (baris 5..556 = {len(df_out)} baris, termasuk 38 PROVINSI_HEADER + {sum(df_out['tipe_baris']=='KABKOTA')} KABKOTA)",
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.log(
            target_id="satudata_sawit_2023",
            method="GET",
            url=SATUDATA_SAWIT_URL,
            status="ERROR",
            duration_ms=elapsed_ms,
            error=str(exc),
        )
        return {
            "sumber": "satudata_kementan",
            "komoditas": "kelapa_sawit",
            "level_wilayah": "KABKOTA",
            "kode_prov": "00",
            "provinsi": "INDONESIA",
            "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
            "status_http": "ERROR",
            "status_ekstrak": "ERROR",
            "jumlah_baris": 0,
            "jumlah_wilayah_non_nol": 0,
            "tahun_awal_aktual": np.nan,
            "tahun_akhir_aktual": np.nan,
            "rentang_tahun_aktual": "",
            "sel_positif": 0,
            "sel_nol_eksplisit": 0,
            "sel_null": 0,
            "max_selisih_vs_total_html": np.nan,
            "catatan": str(exc),
        }


def max_total_diff(rows: list[dict], years: list[str], printed_totals: dict[str, float]) -> float:
    if not rows or not printed_totals:
        return np.nan
    diffs = []
    for y in years:
        if y in printed_totals and pd.notna(printed_totals[y]):
            s = sum(r[y] for r in rows if pd.notna(r.get(y)))
            diffs.append(abs(s - printed_totals[y]))
    return round(max(diffs), 4) if diffs else np.nan


def main():
    resume_mode = "--resume" in sys.argv
    ensure_raw_folder_tree()
    tanggal_tarik = today_iso()
    session = make_http_session(retries=3, backoff_factor=0.8)
    logger = RequestLogger("01_extract_bdsp_kementan")

    existing_audit = {}
    audit_path = FOLDER_1 / "_audit_01_bdsp_kementan.csv"
    if resume_mode and audit_path.exists():
        df_prev = pd.read_csv(audit_path)
        for _, r in df_prev.iterrows():
            if str(r.get("status_ekstrak")) == "OK" and int(r.get("jumlah_baris", 0) or 0) > 0:
                existing_audit[str(r["file_relatif"])] = r.to_dict()

    print("=" * 72, flush=True)
    print(f"STEP 1: EKSTRAKSI FOLDER 1 — raw_data/01_bdsp_kementan/ (resume={resume_mode}, skip_ok={len(existing_audit)})", flush=True)
    print("=" * 72, flush=True)

    # 1. Inisialisasi sesi BDSP
    t0 = time.perf_counter()
    r_init = session.get(BDSP_URL_LOKASI, timeout=25)
    logger.log("bdsp_init_session", "GET", BDSP_URL_LOKASI, r_init.status_code, (time.perf_counter() - t0) * 1000)
    print(f"[Init] GET {BDSP_URL_LOKASI} -> HTTP {r_init.status_code}", flush=True)

    audit_rows = []

    # 2. Tarik Level Provinsi (level=02) -> 4 file (1 per komoditas)
    print("\n[1/3] Menarik BDSP Level Provinsi (level=02, 2010-2026)...", flush=True)
    for comm in BDSP_COMMODITIES:
        slug = comm["slug"]
        out_path = FOLDER_1 / slug / "provinsi" / f"bdsp_{slug}_38_provinsi.csv"
        rel_key = str(out_path.relative_to(RAW_DIR)).replace("\\", "/")
        if resume_mode and rel_key in existing_audit and out_path.exists():
            audit_rows.append(existing_audit[rel_key])
            print(f"  [SKIP OK] {rel_key}", flush=True)
            continue
        t0 = time.perf_counter()
        try:
            resp = post_bdsp(session, comm, level="02", prov_code="00", prov_name="-- Pilih Provinsi --")
            elapsed = (time.perf_counter() - t0) * 1000
            years, rows, printed_tot, stats = parse_bdsp_table_html(resp.text)

            # Bangun DataFrame persis struktur tabel BDSP
            df_rows = []
            for r in rows:
                entry = {
                    "no_urut": r["no_urut"],
                    "kode_prov": r["kode_wilayah"],
                    "provinsi": r["nama_wilayah"],
                    "lokasi_raw": r["lokasi_raw"],
                    "komoditas": slug,
                    "kode_komoditas_bdsp": comm["komcd"],
                    "status_angka": "Angka Tetap",
                }
                for y in years:
                    entry[y] = r[y]
                df_rows.append(entry)

            df = pd.DataFrame(df_rows)
            df = add_provenance_cols(
                df,
                sumber_instansi="BDSP Kementerian Pertanian",
                sumber_url=BDSP_URL_LOKASI,
                satuan_asli="Ton",
                level_wilayah="PROVINSI",
                tanggal_tarik=tanggal_tarik,
            )
            write_raw_csv(df, out_path)
            y_min, y_max, span, nz_cnt = compute_year_range_and_nonzero_locs(rows, years)
            mdiff = max_total_diff(rows, years, printed_tot)

            logger.log(
                f"bdsp_prov_{slug}", "POST", BDSP_URL_RESULT, resp.status_code,
                elapsed, rows=len(df), output_file=str(out_path.relative_to(RAW_DIR)),
            )
            print(f"  [PROV] {slug:<13} -> {len(df):2d} baris | non-nol={nz_cnt:2d} | tahun={span or 'KOSONG'} | max_diff_total={mdiff}", flush=True)
            audit_rows.append(
                {
                    "sumber": "bdsp_kementan",
                    "komoditas": slug,
                    "level_wilayah": "PROVINSI",
                    "kode_prov": "00",
                    "provinsi": "38 PROVINSI",
                    "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
                    "status_http": resp.status_code,
                    "status_ekstrak": "OK" if len(df) > 0 else "KOSONG",
                    "jumlah_baris": len(df),
                    "jumlah_wilayah_non_nol": nz_cnt,
                    "tahun_awal_aktual": y_min,
                    "tahun_akhir_aktual": y_max,
                    "rentang_tahun_aktual": span,
                    "sel_positif": stats["n_positive"],
                    "sel_nol_eksplisit": stats["n_explicit_zero"],
                    "sel_null": stats["n_null"],
                    "max_selisih_vs_total_html": mdiff,
                    "catatan": "Tabel provinsi 2010-2026 as-is (sts_angka=6 Angka Tetap)",
                }
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.log(f"bdsp_prov_{slug}", "POST", BDSP_URL_RESULT, "ERROR", elapsed, error=str(exc))
            print(f"  [ERR PROV] {slug}: {exc}", flush=True)
            audit_rows.append(
                {
                    "sumber": "bdsp_kementan",
                    "komoditas": slug,
                    "level_wilayah": "PROVINSI",
                    "kode_prov": "00",
                    "provinsi": "38 PROVINSI",
                    "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
                    "status_http": "ERROR",
                    "status_ekstrak": "ERROR",
                    "jumlah_baris": 0,
                    "jumlah_wilayah_non_nol": 0,
                    "tahun_awal_aktual": np.nan,
                    "tahun_akhir_aktual": np.nan,
                    "rentang_tahun_aktual": "",
                    "sel_positif": 0,
                    "sel_nol_eksplisit": 0,
                    "sel_null": 0,
                    "max_selisih_vs_total_html": np.nan,
                    "catatan": str(exc),
                }
            )
        time.sleep(0.2)

    # 3. Tarik Level Kab/Kota (level=03) -> 4 komoditas x 38 provinsi = 152 file CSV terpisah
    print("\n[2/3] Menarik BDSP Level Kab/Kota (4 komoditas x 38 provinsi = 152 CSV)...", flush=True)
    for comm in BDSP_COMMODITIES:
        slug = comm["slug"]
        ok_cnt = 0
        nonempty_cnt = 0
        for kd2, _dom, prov_name, prov_slug, pulau, _sub in PROVINCES_38:
            out_path = FOLDER_1 / slug / "kabkota" / f"{kd2}_{prov_slug}.csv"
            rel_key = str(out_path.relative_to(RAW_DIR)).replace("\\", "/")
            if resume_mode and rel_key in existing_audit and out_path.exists():
                audit_rows.append(existing_audit[rel_key])
                ok_cnt += 1
                if int(existing_audit[rel_key].get("jumlah_wilayah_non_nol", 0) or 0) > 0:
                    nonempty_cnt += 1
                continue
            t0 = time.perf_counter()
            try:
                resp = post_bdsp(session, comm, level="03", prov_code=kd2, prov_name=prov_name)
                elapsed = (time.perf_counter() - t0) * 1000
                years, rows, printed_tot, stats = parse_bdsp_table_html(resp.text)

                df_rows = []
                for r in rows:
                    entry = {
                        "no_urut": r["no_urut"],
                        "kode_prov": kd2,
                        "provinsi": prov_name,
                        "pulau": pulau,
                        "kode_kabkota": r["kode_wilayah"],
                        "kabupaten_kota": r["nama_wilayah"],
                        "lokasi_raw": r["lokasi_raw"],
                        "komoditas": slug,
                        "kode_komoditas_bdsp": comm["komcd"],
                        "status_angka": "Angka Tetap",
                    }
                    for y in years:
                        entry[y] = r[y]
                    df_rows.append(entry)

                if df_rows:
                    df = pd.DataFrame(df_rows)
                else:
                    cols = [
                        "no_urut", "kode_prov", "provinsi", "pulau", "kode_kabkota",
                        "kabupaten_kota", "lokasi_raw", "komoditas", "kode_komoditas_bdsp",
                        "status_angka",
                    ] + years
                    df = pd.DataFrame(columns=cols)

                df = add_provenance_cols(
                    df,
                    sumber_instansi="BDSP Kementerian Pertanian",
                    sumber_url=BDSP_URL_LOKASI,
                    satuan_asli="Ton",
                    level_wilayah="KABKOTA",
                    tanggal_tarik=tanggal_tarik,
                )
                write_raw_csv(df, out_path)

                y_min, y_max, span, nz_cnt = compute_year_range_and_nonzero_locs(rows, years)
                mdiff = max_total_diff(rows, years, printed_tot)
                ok_cnt += 1
                if nz_cnt > 0:
                    nonempty_cnt += 1

                logger.log(
                    f"bdsp_kab_{slug}_{kd2}", "POST", BDSP_URL_RESULT, resp.status_code,
                    elapsed, rows=len(df), output_file=str(out_path.relative_to(RAW_DIR)),
                )
                note = (
                    "As-is BDSP Kab/Kota"
                    if nz_cnt > 0
                    else "Seluruh kab/kota bernilai 0 atau kosong di BDSP (as-is)"
                )
                audit_rows.append(
                    {
                        "sumber": "bdsp_kementan",
                        "komoditas": slug,
                        "level_wilayah": "KABKOTA",
                        "kode_prov": kd2,
                        "provinsi": prov_name,
                        "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
                        "status_http": resp.status_code,
                        "status_ekstrak": "OK" if len(df) > 0 else "KOSONG",
                        "jumlah_baris": len(df),
                        "jumlah_wilayah_non_nol": nz_cnt,
                        "tahun_awal_aktual": y_min,
                        "tahun_akhir_aktual": y_max,
                        "rentang_tahun_aktual": span,
                        "sel_positif": stats["n_positive"],
                        "sel_nol_eksplisit": stats["n_explicit_zero"],
                        "sel_null": stats["n_null"],
                        "max_selisih_vs_total_html": mdiff,
                        "catatan": note,
                    }
                )
            except Exception as exc:
                elapsed = (time.perf_counter() - t0) * 1000
                logger.log(f"bdsp_kab_{slug}_{kd2}", "POST", BDSP_URL_RESULT, "ERROR", elapsed, error=str(exc))
                print(f"  [ERR] {slug} {kd2}_{prov_slug}: {exc}", flush=True)
                audit_rows.append(
                    {
                        "sumber": "bdsp_kementan",
                        "komoditas": slug,
                        "level_wilayah": "KABKOTA",
                        "kode_prov": kd2,
                        "provinsi": prov_name,
                        "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
                        "status_http": "ERROR",
                        "status_ekstrak": "ERROR",
                        "jumlah_baris": 0,
                        "jumlah_wilayah_non_nol": 0,
                        "tahun_awal_aktual": np.nan,
                        "tahun_akhir_aktual": np.nan,
                        "rentang_tahun_aktual": "",
                        "sel_positif": 0,
                        "sel_nol_eksplisit": 0,
                        "sel_null": 0,
                        "max_selisih_vs_total_html": np.nan,
                        "catatan": str(exc),
                    }
                )
            time.sleep(0.12)
        print(f"  [KABKOTA] {slug:<13} -> {ok_cnt}/38 file tersimpan ({nonempty_cnt} provinsi memiliki produksi > 0)", flush=True)

    # 4. Tarik Excel Satu Data Sawit 2023
    print("\n[3/3] Konversi Direct Excel Satu Data Kementan (Sawit Kab/Kota 2023)...", flush=True)
    sd_rel = "01_bdsp_kementan/satudata_kementan/sawit_kabkota_2023.csv"
    if resume_mode and sd_rel in existing_audit and (RAW_DIR / sd_rel).exists():
        sd_audit = existing_audit[sd_rel]
        print(f"  [SKIP OK] {sd_rel}", flush=True)
    else:
        sd_audit = extract_satudata_sawit_2023(session, logger, tanggal_tarik)
    audit_rows.append(sd_audit)
    print(f"  [SATUDATA] sawit_kabkota_2023.csv -> {sd_audit['jumlah_baris']} baris ({sd_audit['jumlah_wilayah_non_nol']} kab/kota produksi > 0)", flush=True)

    # 5. Tulis Audit Folder 1
    df_audit = pd.DataFrame(audit_rows)
    audit_path = FOLDER_1 / "_audit_01_bdsp_kementan.csv"
    write_raw_csv(df_audit, audit_path)

    n_err = int((df_audit["status_ekstrak"] == "ERROR").sum())
    print("\n" + "=" * 72, flush=True)
    print(f"SELESAI STEP 1: Total {len(df_audit)} file raw diekstrak | Error: {n_err}", flush=True)
    print(f"Audit disimpan ke: {audit_path}", flush=True)
    print("=" * 72, flush=True)


if __name__ == "__main__":
    main()
