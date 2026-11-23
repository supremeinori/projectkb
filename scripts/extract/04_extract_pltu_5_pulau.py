"""
Step 4: Ekstraksi Folder 4 — raw_data/04_pltu_5_pulau/
Prinsip Strict Scientist / Zero-Merge:
1. Climate TRACE v6 API -> 1 tahun API = 1 CSV mentah:
   climatetrace/2021.csv .. 2025.csv (seluruh kolom asli API + estimasi pulau dari koordinat).
2. WRI Global Power Plant Database -> 1 CSV mentah:
   wri_gppd/wri_gppd_coal_idn.csv (filter country=='IDN' & primary_fuel=='Coal', seluruh kolom asli WRI).
3. CREA Mei 2025 Lampiran Tabel A1 -> 1 CSV mentah:
   crea_2025/tabel_a1_52_pltu_cofiring_2024.csv (52 PLTU PLN Co-Firing as-is, tanpa kolom estimasi rumus batu bara).
4. GEM Global Coal Plant Tracker (Opsional/Semi-Manual) -> gem_gcpt/gem_gcpt_coal_idn.csv
   jika file unduhan manual GEM ditemukan di folder gem_gcpt/; jika belum ada, dicatat jujur di audit.
5. Audit lengkap -> _audit_04_pltu_5_pulau.csv.
"""

from __future__ import annotations

import io
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils_raw import (  # noqa: E402
    ARCHIVE_PDF_DIR,
    FIVE_ISLANDS,
    RAW_DIR,
    RequestLogger,
    add_provenance_cols,
    ensure_raw_folder_tree,
    make_http_session,
    map_pulau_from_coords,
    map_pulau_from_lokasi,
    parse_id_number,
    today_iso,
    write_raw_csv,
)

FOLDER_4 = RAW_DIR / "04_pltu_5_pulau"
CT_BASE_URL = "https://api.climatetrace.org/v6/assets"
WRI_CSV_URL = (
    "https://raw.githubusercontent.com/wri/global-power-plant-database/master/"
    "output_database/global_power_plant_database.csv"
)
CREA_PDF_URL = (
    "https://energyandcleanair.org/wp/wp-content/uploads/2025/05/"
    "ID-IDN-Biomass-co-firing-in-Indonesia.pdf"
)
CREA_PDF_LOCAL = ARCHIVE_PDF_DIR / "crea_biomass_cofiring_indonesia_2025.pdf"

# Catatan klarifikasi terjemahan literal di PDF CREA edisi bahasa Indonesia (tanpa mengubah nama_pltu_pdf asli)
CREA_NAME_NOTES = {
    "Pakaian 1-2": "PLTU Ropa 1-2 (terjemahan literal 'Ropa' di PDF CREA)",
    "Jadi Tanasa 1-3": "PLTU Nii Tanasa 1-3 (Kendari)",
    "Angka 1-2": "PLTU Suge 1-2 (Belitung)",
    "Dia 1-2": "PLTU Berau / Lati 1-2 (Berau)",
    "Berlawanan 1-2": "PLTU Sebalang 1-2 (Lampung Selatan)",
}


def parse_unit_capacity_mw(unit_str: str):
    if not unit_str:
        return np.nan, np.nan, np.nan
    s = str(unit_str).strip().lower().replace(",", ".").replace(" ", "")
    m = re.match(r"^(\d+)x(\d+(?:\.\d+)?)$", s)
    if m:
        n_unit = int(m.group(1))
        mw_unit = float(m.group(2))
        return n_unit, mw_unit, round(n_unit * mw_unit, 2)
    return np.nan, np.nan, np.nan


def summarize_islands(pulau_series: pd.Series) -> dict[str, int]:
    vc = pulau_series.value_counts(dropna=False).to_dict()
    return {
        "jawa": int(vc.get("Jawa", 0)),
        "sumatera": int(vc.get("Sumatera", 0)),
        "kalimantan": int(vc.get("Kalimantan", 0)),
        "sulawesi": int(vc.get("Sulawesi", 0)),
        "papua": int(vc.get("Papua", 0)),
        "lainnya": int(sum(v for k, v in vc.items() if k not in FIVE_ISLANDS)),
    }


def extract_climatetrace(session, logger: RequestLogger, tanggal_tarik: str) -> list[dict]:
    print("\n[1/4] Menarik Climate TRACE v6 API (2021-2025, 1 tahun = 1 CSV)...", flush=True)
    audit_entries = []
    for yr in range(2021, 2026):
        url = f"{CT_BASE_URL}?countries=IDN&sectors=power&year={yr}&limit=500"
        out_path = FOLDER_4 / "climatetrace" / f"{yr}.csv"
        t0 = time.perf_counter()
        try:
            r = session.get(url, timeout=30)
            elapsed = (time.perf_counter() - t0) * 1000
            r.raise_for_status()
            payload = r.json()
            assets = payload.get("assets", [])
            coal_assets = [
                a for a in assets if "coal" in str(a.get("AssetType", "")).lower()
            ]

            rows = []
            for a in coal_assets:
                centroid = a.get("Centroid") or {}
                geom = centroid.get("Geometry") or [None, None]
                lon = geom[0] if len(geom) >= 1 else np.nan
                lat = geom[1] if len(geom) >= 2 else np.nan
                pulau = map_pulau_from_coords(lat, lon, a.get("Name", ""))

                es_list = a.get("EmissionsSummary") or []
                es0 = es_list[0] if es_list else {}
                owners = a.get("Owners") or []
                owner_names = "; ".join(
                    str(o.get("CompanyName", "")).strip()
                    for o in owners
                    if isinstance(o, dict) and o.get("CompanyName")
                )

                thumb_raw = str(a.get("Thumbnail") or "")
                thumb_clean = re.sub(r"access_token=[^&\s]+", "access_token=<REDACTED>", thumb_raw)

                rows.append(
                    {
                        "tahun_api": yr,
                        "id": a.get("Id"),
                        "name": a.get("Name"),
                        "native_id": a.get("NativeId"),
                        "country": a.get("Country"),
                        "sector": a.get("Sector"),
                        "asset_type": a.get("AssetType"),
                        "reporting_entity": a.get("ReportingEntity"),
                        "longitude": lon,
                        "latitude": lat,
                        "centroid_srid": centroid.get("SRID"),
                        "pulau_est": pulau,
                        "masuk_5_pulau": pulau in FIVE_ISLANDS,
                        "capacity_mw": es0.get("Capacity"),
                        "capacity_units": es0.get("CapacityUnits"),
                        "activity": es0.get("Activity"),
                        "activity_units": es0.get("ActivityUnits"),
                        "capacity_factor_api": es0.get("CapacityFactor"),
                        "emissions_gas": es0.get("Gas"),
                        "emissions_quantity": es0.get("EmissionsQuantity"),
                        "emissions_factor": es0.get("EmissionsFactor"),
                        "emissions_factor_units": es0.get("EmissionsFactorUnits"),
                        "emissions_summary_json": json.dumps(es_list, ensure_ascii=False) if es_list else "",
                        "owners_names": owner_names,
                        "owners_json": json.dumps(owners, ensure_ascii=False) if owners else "",
                        "confidence_json": json.dumps(a.get("Confidence"), ensure_ascii=False) if a.get("Confidence") is not None else "",
                        "sector_ranks_json": json.dumps(a.get("SectorRanks"), ensure_ascii=False) if a.get("SectorRanks") is not None else "",
                        "thumbnail": thumb_clean,
                    }
                )

            df = pd.DataFrame(rows)
            df = add_provenance_cols(
                df,
                sumber_instansi="Climate TRACE Coalition (v6 API)",
                sumber_url=url,
                satuan_asli="Capacity: MW; Activity: MWh; Emissions: t CO2e_100yr",
                level_wilayah="UNIT_PLTU",
                tanggal_tarik=tanggal_tarik,
            )
            write_raw_csv(df, out_path)

            isl = summarize_islands(df["pulau_est"]) if not df.empty else {k: 0 for k in ["jawa", "sumatera", "kalimantan", "sulawesi", "papua", "lainnya"]}
            n_coord = int((df["latitude"].notna() & df["longitude"].notna()).sum()) if not df.empty else 0
            n_mw = int(df["capacity_mw"].notna().sum()) if not df.empty else 0
            tot_mw = round(float(df["capacity_mw"].dropna().sum()), 2) if not df.empty else 0.0

            logger.log(
                f"climatetrace_{yr}", "GET", url, r.status_code, elapsed,
                rows=len(df), output_file=str(out_path.relative_to(RAW_DIR)),
            )
            print(
                f"  [CT {yr}] {len(df):3d} PLTU coal (dari {len(assets)} power assets) | Total MW={tot_mw:,.1f} | Coord={n_coord}/{len(df)}",
                flush=True,
            )
            audit_entries.append(
                {
                    "sumber": "climatetrace_v6",
                    "tahun_data": str(yr),
                    "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
                    "status_http": r.status_code,
                    "status_ekstrak": "OK",
                    "jumlah_pltu": len(df),
                    "jawa": isl["jawa"],
                    "sumatera": isl["sumatera"],
                    "kalimantan": isl["kalimantan"],
                    "sulawesi": isl["sulawesi"],
                    "papua": isl["papua"],
                    "pulau_lainnya": isl["lainnya"],
                    "kelengkapan_koordinat": f"{n_coord}/{len(df)}",
                    "kelengkapan_mw": f"{n_mw}/{len(df)}",
                    "total_kapasitas_mw": tot_mw,
                    "catatan": f"Total power assets API={len(assets)}; difilter AssetType mengandung 'coal'",
                }
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.log(f"climatetrace_{yr}", "GET", url, "ERROR", elapsed, error=str(exc))
            print(f"  [ERR CT {yr}] {exc}", flush=True)
            audit_entries.append(
                {
                    "sumber": "climatetrace_v6",
                    "tahun_data": str(yr),
                    "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
                    "status_http": "ERROR",
                    "status_ekstrak": "ERROR",
                    "jumlah_pltu": 0,
                    "jawa": 0, "sumatera": 0, "kalimantan": 0, "sulawesi": 0, "papua": 0, "pulau_lainnya": 0,
                    "kelengkapan_koordinat": "0/0",
                    "kelengkapan_mw": "0/0",
                    "total_kapasitas_mw": np.nan,
                    "catatan": str(exc),
                }
            )
        time.sleep(0.25)
    return audit_entries


def extract_wri_gppd(session, logger: RequestLogger, tanggal_tarik: str) -> dict:
    print("\n[2/4] Menarik WRI Global Power Plant Database (IDN Coal)...", flush=True)
    out_path = FOLDER_4 / "wri_gppd" / "wri_gppd_coal_idn.csv"
    t0 = time.perf_counter()
    try:
        r = session.get(WRI_CSV_URL, timeout=45)
        elapsed = (time.perf_counter() - t0) * 1000
        r.raise_for_status()
        df_all = pd.read_csv(io.StringIO(r.text), low_memory=False)
        coal = df_all[(df_all["country"] == "IDN") & (df_all["primary_fuel"] == "Coal")].copy().reset_index(drop=True)
        coal["pulau_est"] = coal.apply(
            lambda row: map_pulau_from_coords(row.get("latitude"), row.get("longitude"), row.get("name", "")),
            axis=1,
        )
        coal["masuk_5_pulau"] = coal["pulau_est"].isin(FIVE_ISLANDS)
        coal = add_provenance_cols(
            coal,
            sumber_instansi="World Resources Institute (WRI Global Power Plant Database v1.3.0)",
            sumber_url=WRI_CSV_URL,
            satuan_asli="capacity_mw: MW; generation: GWh",
            level_wilayah="UNIT_PLTU",
            tanggal_tarik=tanggal_tarik,
        )
        write_raw_csv(coal, out_path)

        isl = summarize_islands(coal["pulau_est"])
        n_coord = int((coal["latitude"].notna() & coal["longitude"].notna()).sum())
        n_mw = int(coal["capacity_mw"].notna().sum())
        tot_mw = round(float(coal["capacity_mw"].dropna().sum()), 2)
        cy = coal["commissioning_year"].dropna()
        cy_span = f"{int(cy.min())}-{int(cy.max())}" if len(cy) else ""

        logger.log(
            "wri_gppd_coal_idn", "GET", WRI_CSV_URL, r.status_code, elapsed,
            rows=len(coal), output_file=str(out_path.relative_to(RAW_DIR)),
        )
        print(
            f"  [WRI] {len(coal)} PLTU coal IDN (dari {len(df_all):,} baris global) | Total MW={tot_mw:,.1f} | Commissioning={cy_span}",
            flush=True,
        )
        return {
            "sumber": "wri_gppd",
            "tahun_data": f"commissioning {cy_span}; est_gen 2013-2017",
            "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
            "status_http": r.status_code,
            "status_ekstrak": "OK",
            "jumlah_pltu": len(coal),
            "jawa": isl["jawa"],
            "sumatera": isl["sumatera"],
            "kalimantan": isl["kalimantan"],
            "sulawesi": isl["sulawesi"],
            "papua": isl["papua"],
            "pulau_lainnya": isl["lainnya"],
            "kelengkapan_koordinat": f"{n_coord}/{len(coal)}",
            "kelengkapan_mw": f"{n_mw}/{len(coal)}",
            "total_kapasitas_mw": tot_mw,
            "catatan": f"Seluruh {len(df_all.columns)} kolom asli WRI dipertahankan as-is (filter country=='IDN' & primary_fuel=='Coal')",
        }
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        logger.log("wri_gppd_coal_idn", "GET", WRI_CSV_URL, "ERROR", elapsed, error=str(exc))
        print(f"  [ERR WRI] {exc}", flush=True)
        return {
            "sumber": "wri_gppd",
            "tahun_data": "",
            "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
            "status_http": "ERROR",
            "status_ekstrak": "ERROR",
            "jumlah_pltu": 0,
            "jawa": 0, "sumatera": 0, "kalimantan": 0, "sulawesi": 0, "papua": 0, "pulau_lainnya": 0,
            "kelengkapan_koordinat": "0/0",
            "kelengkapan_mw": "0/0",
            "total_kapasitas_mw": np.nan,
            "catatan": str(exc),
        }


def extract_crea_52_pltu(session, logger: RequestLogger, tanggal_tarik: str) -> dict:
    print("\n[3/4] Mengekstrak CREA Mei 2025 Lampiran Tabel A1 (52 PLTU PLN Co-Firing)...", flush=True)
    out_path = FOLDER_4 / "crea_2025" / "tabel_a1_52_pltu_cofiring_2024.csv"
    status_http: str | int = "LOCAL_CACHE"

    if not (CREA_PDF_LOCAL.exists() and CREA_PDF_LOCAL.stat().st_size > 100_000):
        t0 = time.perf_counter()
        r = session.get(CREA_PDF_URL, timeout=60)
        elapsed = (time.perf_counter() - t0) * 1000
        r.raise_for_status()
        status_http = r.status_code
        CREA_PDF_LOCAL.parent.mkdir(parents=True, exist_ok=True)
        CREA_PDF_LOCAL.write_bytes(r.content)
        logger.log("crea_pdf_download", "GET", CREA_PDF_URL, r.status_code, elapsed, output_file=str(CREA_PDF_LOCAL))
    else:
        print(f"  [PDF Cache] Memakai file lokal: {CREA_PDF_LOCAL.name} ({CREA_PDF_LOCAL.stat().st_size / 1e6:.2f} MB)", flush=True)

    raw_records = []
    current_region_pln = None
    status_group = "OPERASI_COFIRING_2024"
    printed_totals = []

    with pdfplumber.open(CREA_PDF_LOCAL) as pdf:
        for pno in range(44, 49):  # Halaman 45-49 (0-indexed 44..48)
            for tbl in pdf.pages[pno].extract_tables():
                for row in tbl:
                    cells = [str(c).replace("\n", " ").strip() if c else "" for c in row]
                    if len(cells) < 10:
                        continue
                    c0, c1, c2 = cells[0], cells[1], cells[2]
                    if c0 == "#":
                        continue
                    if not c0 and "wilayah" in c1.lower():
                        current_region_pln = c1
                        continue
                    if not c0 and "lima pembangkit" in c1.lower():
                        status_group = "TARGET_COFIRING_5_PLTU"
                        continue
                    if not c0 and ("total" in c1.lower() or "jumlah" in c1.lower()):
                        printed_totals.append(cells)
                        continue
                    # Baris sambungan nama lokasi (misal "Tengah" untuk Ampana 1-2 di hal 47)
                    if not c0 and not c1 and c2 and raw_records:
                        raw_records[-1]["lokasi_pdf"] = (raw_records[-1]["lokasi_pdf"] + " " + c2).strip()
                        continue
                    if not re.match(r"^\d+$", c0):
                        continue

                    raw_records.append(
                        {
                            "no_crea": int(c0),
                            "nama_pltu_pdf": c1,
                            "catatan_nama_standar": CREA_NAME_NOTES.get(c1, ""),
                            "lokasi_pdf": c2,
                            "wilayah_pln": current_region_pln,
                            "status_cofiring_2024": status_group,
                            "jenis_boiler": cells[3],
                            "unit_kapasitas_raw": cells[4],
                            "jenis_biomassa": cells[5],
                            "porsi_cofiring_pct_raw": cells[6],
                            "penggunaan_biomassa_2024_ton_raw": cells[7],
                            "produksi_listrik_biomassa_2024_mwh_raw": cells[8],
                            "emisi_biomassa_2024_tco2_raw": cells[9],
                        }
                    )

    rows = []
    for r in raw_records:
        pulau = map_pulau_from_lokasi(r["lokasi_pdf"])
        n_unit, mw_unit, total_mw = parse_unit_capacity_mw(r["unit_kapasitas_raw"])
        rows.append(
            {
                "no_crea": r["no_crea"],
                "nama_pltu_pdf": r["nama_pltu_pdf"],
                "catatan_nama_standar": r["catatan_nama_standar"],
                "lokasi_pdf": r["lokasi_pdf"],
                "pulau_est": pulau,
                "masuk_5_pulau": pulau in FIVE_ISLANDS,
                "wilayah_pln": r["wilayah_pln"],
                "status_cofiring_2024": r["status_cofiring_2024"],
                "jenis_boiler": r["jenis_boiler"],
                "unit_kapasitas_raw": r["unit_kapasitas_raw"],
                "jumlah_unit": n_unit,
                "kapasitas_per_unit_mw": mw_unit,
                "kapasitas_total_mw": total_mw,
                "jenis_biomassa": r["jenis_biomassa"],
                "porsi_cofiring_pct_raw": r["porsi_cofiring_pct_raw"],
                "porsi_cofiring_pct": parse_id_number(r["porsi_cofiring_pct_raw"], strip_footnotes=True),
                "penggunaan_biomassa_2024_ton": parse_id_number(r["penggunaan_biomassa_2024_ton_raw"], strip_footnotes=True),
                "produksi_listrik_biomassa_2024_mwh": parse_id_number(r["produksi_listrik_biomassa_2024_mwh_raw"], strip_footnotes=True),
                "emisi_biomassa_2024_tco2": parse_id_number(r["emisi_biomassa_2024_tco2_raw"], strip_footnotes=True),
            }
        )

    df = pd.DataFrame(rows)
    df = add_provenance_cols(
        df,
        sumber_instansi="Centre for Research on Energy and Clean Air (CREA, Mei 2025)",
        sumber_url=CREA_PDF_URL,
        satuan_asli="Kapasitas: MW; Biomassa: Ton/thn; Listrik: MWh/thn; Emisi: tCO2/thn",
        level_wilayah="UNIT_PLTU",
        tanggal_tarik=tanggal_tarik,
    )
    write_raw_csv(df, out_path)

    isl = summarize_islands(df["pulau_est"])
    n_mw = int(df["kapasitas_total_mw"].notna().sum())
    tot_mw = round(float(df["kapasitas_total_mw"].dropna().sum()), 2)
    tot_bio = round(float(df["penggunaan_biomassa_2024_ton"].dropna().sum()), 2)
    n_bio_null = int(df["penggunaan_biomassa_2024_ton"].isna().sum())

    print(
        f"  [CREA] {len(df)} PLTU PLN | Total MW={tot_mw:,.2f} (target ~18,342) | Biomassa 2024={tot_bio:,.0f} ton (NULL={n_bio_null})",
        flush=True,
    )
    return {
        "sumber": "crea_mei_2025_tabel_a1",
        "tahun_data": "2024",
        "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
        "status_http": status_http,
        "status_ekstrak": "OK" if len(df) == 52 else f"PERIKSA_JUMLAH_{len(df)}",
        "jumlah_pltu": len(df),
        "jawa": isl["jawa"],
        "sumatera": isl["sumatera"],
        "kalimantan": isl["kalimantan"],
        "sulawesi": isl["sulawesi"],
        "papua": isl["papua"],
        "pulau_lainnya": isl["lainnya"],
        "kelengkapan_koordinat": "0/52 (PDF tidak memuat lat/lon)",
        "kelengkapan_mw": f"{n_mw}/{len(df)}",
        "total_kapasitas_mw": tot_mw,
        "catatan": f"As-is Lampiran Tabel A1 hal. 45-49 (tanpa estimasi rumus batu bara); total biomassa 2024={tot_bio:,.0f} ton; {n_bio_null} PLTU NULL ('-'/N/A)",
    }


def check_or_extract_gem_gcpt(tanggal_tarik: str) -> dict:
    print("\n[4/4] Memeriksa slot opsional GEM Global Coal Plant Tracker (gem_gcpt/)...", flush=True)
    gem_dir = FOLDER_4 / "gem_gcpt"
    out_path = gem_dir / "gem_gcpt_coal_idn.csv"

    candidates = [
        p for p in gem_dir.iterdir()
        if p.is_file() and p.name != "gem_gcpt_coal_idn.csv" and p.suffix.lower() in {".xlsx", ".xls", ".csv"}
    ]
    if not candidates:
        print("  [GEM] Belum ada file unduhan manual GEM di raw_data/04_pltu_5_pulau/gem_gcpt/ -> dicatat jujur di audit.", flush=True)
        return {
            "sumber": "gem_gcpt_manual",
            "tahun_data": "",
            "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
            "status_http": "MANUAL_FORM_DOWNLOAD",
            "status_ekstrak": "BELUM_DIUNDUH_MANUAL",
            "jumlah_pltu": 0,
            "jawa": 0, "sumatera": 0, "kalimantan": 0, "sulawesi": 0, "papua": 0, "pulau_lainnya": 0,
            "kelengkapan_koordinat": "0/0",
            "kelengkapan_mw": "0/0",
            "total_kapasitas_mw": np.nan,
            "catatan": "Opsional/semi-manual: taruh Excel unduhan resmi GEM GCPT di raw_data/04_pltu_5_pulau/gem_gcpt/ lalu jalankan ulang skrip 04.",
        }

    src_file = sorted(candidates)[0]
    if src_file.suffix.lower() in {".xlsx", ".xls"}:
        xl = pd.ExcelFile(src_file)
        sheet = "Units" if "Units" in xl.sheet_names else xl.sheet_names[0]
        df_raw = pd.read_excel(xl, sheet_name=sheet)
    else:
        df_raw = pd.read_csv(src_file, low_memory=False)

    country_col = next((c for c in df_raw.columns if "country" in str(c).lower()), None)
    if country_col:
        df_idn = df_raw[df_raw[country_col].astype(str).str.contains("indonesia", case=False, na=False)].copy()
    else:
        df_idn = df_raw.copy()

    lat_col = next((c for c in df_idn.columns if "lat" in str(c).lower()), None)
    lon_col = next((c for c in df_idn.columns if "lon" in str(c).lower()), None)
    name_col = next((c for c in df_idn.columns if "plant" in str(c).lower() or "name" in str(c).lower()), None)
    mw_col = next((c for c in df_idn.columns if "capacity" in str(c).lower() and "mw" in str(c).lower()), None)

    if lat_col and lon_col:
        df_idn["pulau_est"] = df_idn.apply(
            lambda r: map_pulau_from_coords(r.get(lat_col), r.get(lon_col), r.get(name_col, "") if name_col else ""),
            axis=1,
        )
    else:
        df_idn["pulau_est"] = "Tidak Diketahui"
    df_idn["masuk_5_pulau"] = df_idn["pulau_est"].isin(FIVE_ISLANDS)
    df_idn = add_provenance_cols(
        df_idn,
        sumber_instansi="Global Energy Monitor (Global Coal Plant Tracker)",
        sumber_url="https://globalenergymonitor.org/projects/global-coal-plant-tracker/download-data/",
        satuan_asli="Capacity: MW",
        level_wilayah="UNIT_PLTU",
        tanggal_tarik=tanggal_tarik,
    )
    write_raw_csv(df_idn, out_path)
    isl = summarize_islands(df_idn["pulau_est"])
    tot_mw = round(float(pd.to_numeric(df_idn[mw_col], errors="coerce").dropna().sum()), 2) if mw_col else np.nan
    print(f"  [GEM] Berhasil konversi {src_file.name} -> {len(df_idn)} baris IDN", flush=True)
    return {
        "sumber": "gem_gcpt_manual",
        "tahun_data": "multi-tahun",
        "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
        "status_http": "LOCAL_MANUAL_FILE",
        "status_ekstrak": "OK",
        "jumlah_pltu": len(df_idn),
        "jawa": isl["jawa"], "sumatera": isl["sumatera"], "kalimantan": isl["kalimantan"],
        "sulawesi": isl["sulawesi"], "papua": isl["papua"], "pulau_lainnya": isl["lainnya"],
        "kelengkapan_koordinat": f"{int(df_idn[lat_col].notna().sum()) if lat_col else 0}/{len(df_idn)}",
        "kelengkapan_mw": f"{int(pd.to_numeric(df_idn[mw_col], errors='coerce').notna().sum()) if mw_col else 0}/{len(df_idn)}",
        "total_kapasitas_mw": tot_mw,
        "catatan": f"Diekspor otomatis dari {src_file.name} (filter Indonesia)",
    }


def main():
    ensure_raw_folder_tree()
    tanggal_tarik = today_iso()
    session = make_http_session(retries=3, backoff_factor=0.8)
    logger = RequestLogger("04_extract_pltu_5_pulau")

    print("=" * 72, flush=True)
    print("STEP 4: EKSTRAKSI FOLDER 4 — raw_data/04_pltu_5_pulau/", flush=True)
    print("=" * 72, flush=True)

    audit_rows = []
    audit_rows.extend(extract_climatetrace(session, logger, tanggal_tarik))
    audit_rows.append(extract_wri_gppd(session, logger, tanggal_tarik))
    audit_rows.append(extract_crea_52_pltu(session, logger, tanggal_tarik))
    audit_rows.append(check_or_extract_gem_gcpt(tanggal_tarik))

    df_audit = pd.DataFrame(audit_rows)
    audit_path = FOLDER_4 / "_audit_04_pltu_5_pulau.csv"
    write_raw_csv(df_audit, audit_path)

    print("\n" + "=" * 72, flush=True)
    print(f"SELESAI STEP 4: Audit disimpan ke {audit_path}", flush=True)
    print("=" * 72, flush=True)


if __name__ == "__main__":
    main()
