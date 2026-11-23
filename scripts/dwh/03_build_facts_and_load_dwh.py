"""
Step 3 DWH ETL: Membangun 3 Fact Tables Produksi/Energi/PLTU & Load Seluruh Star Schema ke SQLite DWH
Output:
  - warehouse/tables/fact_commodity_production.csv
  - warehouse/tables/fact_biomass_energy_potential.csv
  - warehouse/tables/fact_pltu_operations.csv
  - warehouse/biomass_dwh.sqlite  (5 Dimensi + 4 Fact Tables + 4 Analytic Views, PRAGMA foreign_keys = ON)
"""

import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path
import numpy as np
import pandas as pd

TABLES_DIR = Path("warehouse/tables")
WAREHOUSE_DIR = Path("warehouse")
DDL_PATH = WAREHOUSE_DIR / "ddl_star_schema.sql"
DB_PATH = WAREHOUSE_DIR / "biomass_dwh.sqlite"

# Import langsung dari 01_build_dimensions via importlib (nama file diawali angka)
import importlib.util
_spec = importlib.util.spec_from_file_location("dim_mod", Path(__file__).resolve().parent / "01_build_dimensions.py")
dim_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dim_mod)

PROVINCES_38 = dim_mod.PROVINCES_38
norm_prov_name = dim_mod.norm_prov_name
norm_kab_compact = dim_mod.norm_kab_compact

COAL_REF_HHV_MJ_KG = 19.0        # Acuan batu bara sub-bituminous PLTU Indonesia (~4.540 kcal/kg)
COAL_EF_TCO2_PER_TON = 2.15      # Faktor emisi IPCC batu bara sub-bituminous (tCO2 / ton batu bara)
EFF_CONSERVATIVE = 0.2545        # Efisiensi konversi bioenergi konservatif (KTH 2026 di memori proyek)
EFF_COFIRING_DIRECT = 0.3300     # Efisiensi termal langsung boiler PLTU PC/CFB


def load_lookups():
    dim_time = pd.read_csv(TABLES_DIR / "dim_time.csv")
    dim_loc = pd.read_csv(TABLES_DIR / "dim_location.csv")
    dim_fs = pd.read_csv(TABLES_DIR / "dim_feedstock.csv")
    dim_src = pd.read_csv(TABLES_DIR / "dim_data_source.csv")
    dim_pltu = pd.read_csv(TABLES_DIR / "dim_power_plant.csv")
    pltu_map = pd.read_csv(WAREHOUSE_DIR / "pltu_entity_resolution_map.csv")

    time_keys = set(dim_time["time_key"].astype(int))
    loc_by_code = dict(zip(dim_loc["location_code"], dim_loc["location_key"].astype(int)))
    prov_name_to_kd2 = {norm_prov_name(n): kd2 for kd2, n, _, _, _ in PROVINCES_38}
    src_by_code = dict(zip(dim_src["kode_sumber"], dim_src["source_key"].astype(int)))
    fs_by_code = dict(zip(dim_fs["kode_feedstock"], dim_fs["feedstock_key"].astype(int)))

    # Lookup pulau -> location_code
    pulau_to_loc_key = {}
    for _, r in dim_loc[dim_loc["level_wilayah"] == "PULAU"].iterrows():
        pulau_to_loc_key[str(r["pulau"]).upper().strip()] = int(r["location_key"])

    # Lookup kabkota (kd_prov, compact_name) -> location_key
    kab_compact_to_key = {}
    for _, r in dim_loc[dim_loc["level_wilayah"] == "KABKOTA"].iterrows():
        kp = str(int(r["kode_bps_prov"])).zfill(2) if pd.notna(r["kode_bps_prov"]) else ""
        kab_compact_to_key[(kp, norm_kab_compact(r["nama_kabkota"]))] = int(r["location_key"])

    return {
        "dim_time": dim_time, "dim_loc": dim_loc, "dim_fs": dim_fs,
        "dim_src": dim_src, "dim_pltu": dim_pltu, "pltu_map": pltu_map,
        "time_keys": time_keys, "loc_by_code": loc_by_code,
        "prov_name_to_kd2": prov_name_to_kd2, "src_by_code": src_by_code,
        "fs_by_code": fs_by_code, "pulau_to_loc_key": pulau_to_loc_key,
        "kab_compact_to_key": kab_compact_to_key,
    }


def resolve_kabkota_key(lk, kd_prov: str, raw_kab_name: str) -> int:
    kc = norm_kab_compact(raw_kab_name)
    exact = lk["kab_compact_to_key"].get((kd_prov, kc))
    if exact:
        return exact
    best_key, best_r = None, 0.0
    for (ep, ek), lkey in lk["kab_compact_to_key"].items():
        if ep == kd_prov:
            if kc in ek or ek in kc:
                return lkey
            r = SequenceMatcher(None, kc, ek).ratio()
            if r >= 0.80 and r > best_r:
                best_r, best_key = r, lkey
    if best_key:
        return best_key
    return lk["loc_by_code"][f"PROV_{kd_prov}"]


def build_fact_commodity_production(lk):
    print("\n[1/4] Membangun fact_commodity_production...")
    rows = []
    fid = 1
    src = lk["src_by_code"]
    loc = lk["loc_by_code"]
    fs = lk["fs_by_code"]

    kom_to_fs = {
        "padi": fs["SEKAM_PADI"],
        "jagung": fs["TONGKOL_JAGUNG"],
        "kelapa_sawit": fs["CANGKANG_SAWIT"],
        "tebu": fs["AMPAS_TEBU"],
    }

    # --- A. BDSP KAB/KOTA (152 file CSV: 4 komoditas x 38 provinsi, 2010-2026) ---
    for kom in ["padi", "jagung", "kelapa_sawit", "tebu"]:
        fkey = kom_to_fs[kom]
        for csv_path in sorted(Path(f"raw_data/01_bdsp_kementan/{kom}/kabkota").glob("*.csv")):
            df = pd.read_csv(csv_path)
            yr_cols = [c for c in df.columns if str(c).isdigit() and 2010 <= int(c) <= 2026]
            for _, r in df.iterrows():
                kd_kab = str(r["kode_kabkota"]).zfill(4)
                lkey = loc[f"KAB_{kd_kab}"]
                for yc in yr_cols:
                    yr = int(yc)
                    val = float(r[yc]) if pd.notna(r[yc]) else None
                    # Tagging cakupan & kualitas berdasarkan temuan AUDIT_RAW_DATA.md
                    if kom == "kelapa_sawit" and yr >= 2018:
                        skey = src["BDSP_KABKOTA_PR"]
                        basis = "CPO_PERKEBUNAN_RAKYAT"
                        qflag = "UNPUBLISHED_YEAR_2026" if yr == 2026 else "PR_SCOPE_ONLY"
                        is_prim = 0 if yr == 2026 else 1
                    elif kom == "tebu" and yr >= 2023:
                        skey = src["BDSP_KABKOTA_PR"]
                        basis = "GULA_HABLUR_PERKEBUNAN_RAKYAT"
                        qflag = "UNPUBLISHED_YEAR_2026" if yr == 2026 else "PR_SCOPE_ONLY"
                        is_prim = 0 if yr == 2026 else 1
                    elif kom == "jagung" and yr >= 2018:
                        skey = src["BDSP_KABKOTA"]
                        basis = "PIPILAN_KERING"
                        qflag = "UNPUBLISHED_YEAR_2026" if yr == 2026 else "JAGUNG_KABKOTA_INCOMPLETE_POST_KSA"
                        is_prim = 0
                    else:
                        skey = src["BDSP_KABKOTA"]
                        basis = {"padi": "GKG", "jagung": "PIPILAN_KERING", "kelapa_sawit": "CPO", "tebu": "GULA_HABLUR"}[kom]
                        qflag = "UNPUBLISHED_YEAR_2026" if yr == 2026 else "OK_KABKOTA"
                        is_prim = 0 if yr == 2026 else 1

                    rows.append({
                        "prod_fact_id": fid, "time_key": yr, "location_key": lkey,
                        "feedstock_key": fkey, "source_key": skey,
                        "level_wilayah_fakta": "KABKOTA",
                        "produksi_nilai_asli": val, "satuan_asli": "Ton",
                        "produksi_ton_std": val, "produksi_m3_std": None,
                        "luas_panen_atau_tanam_ha": None, "produktivitas_nilai": None,
                        "basis_pelaporan": basis, "is_primary_analysis_row": is_prim,
                        "quality_flag": qflag,
                    })
                    fid += 1

    # --- B. BDSP PROVINSI (4 file CSV: 38 provinsi x 2010-2026) ---
    for kom in ["padi", "jagung", "kelapa_sawit", "tebu"]:
        fkey = kom_to_fs[kom]
        csv_path = Path(f"raw_data/01_bdsp_kementan/{kom}/provinsi/bdsp_{kom}_38_provinsi.csv")
        df = pd.read_csv(csv_path)
        yr_cols = [c for c in df.columns if str(c).isdigit() and 2010 <= int(c) <= 2026]
        for _, r in df.iterrows():
            kd_prov = str(r["kode_prov"]).zfill(2)
            lkey = loc[f"PROV_{kd_prov}"]
            for yc in yr_cols:
                yr = int(yc)
                val = float(r[yc]) if pd.notna(r[yc]) else None
                if yr == 2026:
                    is_prim, qflag, basis = 0, "UNPUBLISHED_YEAR_2026", "BELUM_RILIS"
                elif kom == "padi":
                    # BPS 1498#2 primary untuk 2018-2024; BDSP primary untuk 2010-2017 & 2025
                    is_prim = 0 if (2018 <= yr <= 2024) else 1
                    qflag = "SECONDARY_COVERED_BY_BPS_1498" if is_prim == 0 else "OK_PROVINSI"
                    basis = "GKG"
                elif kom == "jagung":
                    # BPS 2204#2 primary untuk 2020-2024; BDSP primary untuk 2010-2019 & 2025
                    is_prim = 0 if (2020 <= yr <= 2024) else 1
                    qflag = "SECONDARY_COVERED_BY_BPS_2204" if is_prim == 0 else "OK_PROVINSI"
                    basis = "PIPILAN_KERING"
                elif kom == "kelapa_sawit":
                    # BPS 132#2 (2008-2023) & BPS 2566#2 (2024) primary; 2025 anomali 4.8x ditandai jelas!
                    if yr == 2025:
                        is_prim, qflag, basis = 0, "ANOMALY_2025_SCALE_4_8X", "SUSPECT_TBS_VS_CPO"
                    else:
                        is_prim = 0
                        qflag = "SECONDARY_COVERED_BY_BPS_PERKEBUNAN"
                        basis = "CPO_ALL_OWNERSHIP"
                else:  # tebu
                    is_prim = 1 if yr == 2025 else 0
                    qflag = "OK_PROVINSI" if yr == 2025 else "SECONDARY_COVERED_BY_BPS_PERKEBUNAN"
                    basis = "GULA_HABLUR_ALL_OWNERSHIP"

                rows.append({
                    "prod_fact_id": fid, "time_key": yr, "location_key": lkey,
                    "feedstock_key": fkey, "source_key": src["BDSP_PROVINSI"],
                    "level_wilayah_fakta": "PROVINSI",
                    "produksi_nilai_asli": val, "satuan_asli": "Ton",
                    "produksi_ton_std": val, "produksi_m3_std": None,
                    "luas_panen_atau_tanam_ha": None, "produktivitas_nilai": None,
                    "basis_pelaporan": basis, "is_primary_analysis_row": is_prim,
                    "quality_flag": qflag,
                })
                fid += 1

    # --- C. SATU DATA KEMENTAN SAWIT KAB/KOTA 2023 (514 baris) ---
    sd = pd.read_csv("raw_data/01_bdsp_kementan/satudata_kementan/sawit_kabkota_2023.csv")
    for _, r in sd[sd["tipe_baris"] == "KABKOTA"].iterrows():
        kd_prov = lk["prov_name_to_kd2"].get(norm_prov_name(r["provinsi_konteks"]))
        if not kd_prov:
            continue
        lkey = resolve_kabkota_key(lk, kd_prov, r["kabupaten_kota_raw"])
        val = float(r["produksi_ton"]) if pd.notna(r["produksi_ton"]) else None
        rows.append({
            "prod_fact_id": fid, "time_key": 2023, "location_key": lkey,
            "feedstock_key": fs["CANGKANG_SAWIT"], "source_key": src["SATUDATA_SAWIT_2023"],
            "level_wilayah_fakta": "KABKOTA",
            "produksi_nilai_asli": val, "satuan_asli": "Ton",
            "produksi_ton_std": val, "produksi_m3_std": None,
            "luas_panen_atau_tanam_ha": float(r["luas_jumlah_ha"]) if pd.notna(r["luas_jumlah_ha"]) else None,
            "produktivitas_nilai": float(r["produktivitas_kg_ha"]) if pd.notna(r["produktivitas_kg_ha"]) else None,
            "basis_pelaporan": "CPO_PERKEBUNAN_RAKYAT", "is_primary_analysis_row": 0,
            "quality_flag": "CROSSCHECK_SATUDATA_2023",
        })
        fid += 1

    # --- D. BPS RI 1498 PADI (2018-2024) & 2204 JAGUNG (2020-2024) ---
    for folder, kom, sk_code, basis in [
        ("1498_padi", "padi", "BPS_RI_1498_PADI", "GKG_KSA"),
        ("2204_jagung", "jagung", "BPS_RI_2204_JAGUNG", "PIPILAN_KERING_KSA"),
    ]:
        fkey = kom_to_fs[kom]
        for csv_path in sorted(Path(f"raw_data/02_bps/bps_ri/{folder}").glob("*.csv")):
            df = pd.read_csv(csv_path)
            for _, r in df.iterrows():
                yr = int(r["tahun"])
                kb = str(int(r["kode_baris"])) if pd.notna(r["kode_baris"]) else ""
                if kb == "9999" or str(r["label_baris"]).upper().strip() == "INDONESIA":
                    lkey, lvl, is_prim, qflag = loc["IDN_00"], "NASIONAL", 0, "SUMMARY_ROW_NASIONAL"
                else:
                    kd2 = kb[:2].zfill(2)
                    lkey = loc.get(f"PROV_{kd2}")
                    if lkey is None:
                        continue
                    lvl, is_prim, qflag = "PROVINSI", 1, "OK_BPS_PRIMARY"
                val = float(r["Produksi (ton)"]) if pd.notna(r["Produksi (ton)"]) else None
                rows.append({
                    "prod_fact_id": fid, "time_key": yr, "location_key": lkey,
                    "feedstock_key": fkey, "source_key": src[sk_code],
                    "level_wilayah_fakta": lvl,
                    "produksi_nilai_asli": val, "satuan_asli": "Ton",
                    "produksi_ton_std": val, "produksi_m3_std": None,
                    "luas_panen_atau_tanam_ha": float(r["Luas Panen (ha)"]) if pd.notna(r["Luas Panen (ha)"]) else None,
                    "produktivitas_nilai": float(r["Produktivitas (ku/ha)"]) if pd.notna(r["Produktivitas (ku/ha)"]) else None,
                    "basis_pelaporan": basis, "is_primary_analysis_row": is_prim,
                    "quality_flag": qflag,
                })
                fid += 1

    # --- E. BPS RI 2566 PERKEBUNAN (2024) & 132 PERKEBUNAN HISTORIS (2008-2023) ---
    for folder, sk_code in [
        ("2566_perkebunan", "BPS_RI_2566_PERKEBUNAN"),
        ("132_perkebunan_historis", "BPS_RI_132_PERKEBUNAN_HIST"),
    ]:
        for csv_path in sorted(Path(f"raw_data/02_bps/bps_ri/{folder}").glob("*.csv")):
            df = pd.read_csv(csv_path)
            for _, r in df.iterrows():
                yr = int(r["tahun"])
                kb = str(int(r["kode_baris"])) if pd.notna(r["kode_baris"]) else ""
                if kb == "9999" or str(r["label_baris"]).upper().strip() == "INDONESIA":
                    lkey, lvl, is_prim_base, qflag = loc["IDN_00"], "NASIONAL", 0, "SUMMARY_ROW_NASIONAL"
                else:
                    kd2 = kb[:2].zfill(2)
                    lkey = loc.get(f"PROV_{kd2}")
                    if lkey is None:
                        continue
                    lvl, is_prim_base, qflag = "PROVINSI", 1, "OK_BPS_PRIMARY"
                for col_bps, fcode, basis in [
                    ("Kelapa Sawit", "CANGKANG_SAWIT", "CPO_ALL_OWNERSHIP"),
                    ("Tebu", "AMPAS_TEBU", "GULA_HABLUR_ALL_OWNERSHIP"),
                ]:
                    if col_bps not in df.columns:
                        continue
                    val_rt = float(r[col_bps]) if pd.notna(r[col_bps]) else None
                    val_ton = (val_rt * 1000.0) if val_rt is not None else None
                    rows.append({
                        "prod_fact_id": fid, "time_key": yr, "location_key": lkey,
                        "feedstock_key": fs[fcode], "source_key": src[sk_code],
                        "level_wilayah_fakta": lvl,
                        "produksi_nilai_asli": val_rt, "satuan_asli": "Ribu Ton",
                        "produksi_ton_std": val_ton, "produksi_m3_std": None,
                        "luas_panen_atau_tanam_ha": None, "produktivitas_nilai": None,
                        "basis_pelaporan": basis, "is_primary_analysis_row": is_prim_base,
                        "quality_flag": qflag,
                    })
                    fid += 1

    # --- F. BPS RI 2512 KAYU JENIS POHON (2020-2023) & 1973 KAYU HPH PULAU (2019-2022) ---
    for csv_path in sorted(Path("raw_data/02_bps/bps_ri/2512_kayu_jenis_pohon").glob("*.csv")):
        df = pd.read_csv(csv_path)
        for _, r in df.iterrows():
            yr = int(r["tahun"])
            lbl = str(r["label_baris"]).strip()
            val = float(r["nilai"]) if pd.notna(r["nilai"]) else None
            if lbl.startswith("A. JUMLAH KAYU BULAT"):
                fkey, sat, m3_v, basis = fs["LIMBAH_KAYU_SERBUK"], "m3", val, "HTI_TOTAL_KAYU_BULAT"
            elif lbl.startswith("B. KAYU BAKAR"):
                fkey, sat, m3_v, basis = fs["KAYU_BAKAR_BPS"], "SM", None, "HTI_KAYU_BAKAR"
            elif re.match(r"^\d+\.\s+", lbl):
                fkey, sat, m3_v, basis = fs["LIMBAH_KAYU_SERBUK"], "m3", val, f"HTI_SPECIES:{lbl}"
            else:
                continue  # Getah/Resin & Daun Kayu Putih di luar biomassa kayu
            rows.append({
                "prod_fact_id": fid, "time_key": yr, "location_key": loc["IDN_00"],
                "feedstock_key": fkey, "source_key": src["BPS_RI_2512_KAYU_JENIS"],
                "level_wilayah_fakta": "NASIONAL",
                "produksi_nilai_asli": val, "satuan_asli": sat,
                "produksi_ton_std": None, "produksi_m3_std": m3_v,
                "luas_panen_atau_tanam_ha": None, "produktivitas_nilai": None,
                "basis_pelaporan": basis, "is_primary_analysis_row": 0,
                "quality_flag": "REFERENCE_BPS_NASIONAL",
            })
            fid += 1

    for csv_path in sorted(Path("raw_data/02_bps/bps_ri/1973_kayu_hph_pulau").glob("*.csv")):
        df = pd.read_csv(csv_path)
        for _, r in df.iterrows():
            yr = int(r["tahun"])
            lbl = str(r["label_baris"]).upper().strip()
            val = float(r["nilai"]) if pd.notna(r["nilai"]) else None
            if lbl == "INDONESIA":
                lkey, lvl = loc["IDN_00"], "NASIONAL"
            else:
                lkey = lk["pulau_to_loc_key"].get(lbl)
                if lkey is None:
                    continue
                lvl = "PULAU"
            rows.append({
                "prod_fact_id": fid, "time_key": yr, "location_key": lkey,
                "feedstock_key": fs["LIMBAH_KAYU_SERBUK"], "source_key": src["BPS_RI_1973_KAYU_HPH"],
                "level_wilayah_fakta": lvl,
                "produksi_nilai_asli": val, "satuan_asli": "m3",
                "produksi_ton_std": None, "produksi_m3_std": val,
                "luas_panen_atau_tanam_ha": None, "produktivitas_nilai": None,
                "basis_pelaporan": "HPH_HUTAN_ALAM", "is_primary_analysis_row": 0,
                "quality_flag": "REFERENCE_BPS_PULAU",
            })
            fid += 1

    # --- G. KLHK PHL KAYU BULAT (BUKU 2024: 2020-2024 & BUKU 2022: 2018-2022) ---
    phl_specs = [
        ("raw_data/03_klhk_phl_kayu/buku_2024/tabel_3_9_pbph_provinsi_2020_2024.csv", "KLHK_PHL_2024_PBPH", "PBPH", True),
        ("raw_data/03_klhk_phl_kayu/buku_2024/tabel_3_12_perhutani_provinsi_2020_2024.csv", "KLHK_PHL_2024_PERHUTANI", "PERHUTANI", True),
        ("raw_data/03_klhk_phl_kayu/buku_2022/tabel_pbph_provinsi_2018_2022.csv", "KLHK_PHL_2022_PBPH", "PBPH", False),
        ("raw_data/03_klhk_phl_kayu/buku_2022/tabel_perhutani_provinsi_2018_2022.csv", "KLHK_PHL_2022_PERHUTANI", "PERHUTANI", False),
    ]
    for path_str, sk_code, basis, is_buku_2024 in phl_specs:
        df = pd.read_csv(path_str)
        yr_cols = [c for c in df.columns if str(c).isdigit()]
        for _, r in df.iterrows():
            kd2 = lk["prov_name_to_kd2"].get(norm_prov_name(r["provinsi_pdf"]))
            if not kd2:
                continue
            lkey = loc[f"PROV_{kd2}"]
            for yc in yr_cols:
                yr = int(yc)
                val = float(r[yc]) if pd.notna(r[yc]) else None
                if is_buku_2024:
                    is_prim, qflag = 1, "OK_KLHK_PRIMARY"
                else:
                    # Buku 2022 hanya primary untuk 2018-2019 (2020-2022 sudah identik di Buku 2024)
                    is_prim = 1 if yr < 2020 else 0
                    qflag = "OK_KLHK_PRIMARY" if yr < 2020 else "SUPERSEDED_BY_BUKU_2024"
                rows.append({
                    "prod_fact_id": fid, "time_key": yr, "location_key": lkey,
                    "feedstock_key": fs["LIMBAH_KAYU_SERBUK"], "source_key": src[sk_code],
                    "level_wilayah_fakta": "PROVINSI",
                    "produksi_nilai_asli": val, "satuan_asli": "m3",
                    "produksi_ton_std": None, "produksi_m3_std": val,
                    "luas_panen_atau_tanam_ha": None, "produktivitas_nilai": None,
                    "basis_pelaporan": basis, "is_primary_analysis_row": is_prim,
                    "quality_flag": qflag,
                })
                fid += 1

    df_prod = pd.DataFrame(rows)
    df_prod.to_csv(TABLES_DIR / "fact_commodity_production.csv", index=False, encoding="utf-8-sig")
    print(f"[fact_commodity_production] {len(df_prod):,} baris total | primary rows={int(df_prod['is_primary_analysis_row'].sum()):,}")
    return df_prod


def build_fact_biomass_energy_potential(lk, df_prod):
    print("\n[2/4] Membangun fact_biomass_energy_potential (2 skenario x PROVINSI & KABKOTA)...")
    fs_meta = lk["dim_fs"].set_index("feedstock_key").to_dict(orient="index")

    # Ambil hanya baris primary (bebas double-count & bebas anomali Sawit 2025 / 2026 kosong) pada level PROVINSI & KABKOTA
    prim = df_prod[
        (df_prod["is_primary_analysis_row"] == 1)
        & (df_prod["level_wilayah_fakta"].isin(["PROVINSI", "KABKOTA"]))
    ].copy()

    # Agregasikan PBPH + Perhutani per (time_key, location_key, feedstock_key, source_key) tetap per source_key agar FK terjaga!
    rows = []
    eid = 1
    scenarios = [
        ("BASE_CONSERVATIVE", EFF_CONSERVATIVE),
        ("PLTU_COFIRING_DIRECT_33PCT", EFF_COFIRING_DIRECT),
    ]

    for _, r in prim.iterrows():
        fk = int(r["feedstock_key"])
        meta = fs_meta.get(fk)
        if not meta or pd.isna(meta["rpr_ratio_default"]):
            continue

        # Tentukan tonase komoditas (konversi m3 -> ton hanya untuk Kayu Bulat via wood_density terdokumentasi)
        if pd.notna(r["produksi_ton_std"]) and r["produksi_ton_std"] > 0:
            comm_ton = float(r["produksi_ton_std"])
        elif pd.notna(r["produksi_m3_std"]) and r["produksi_m3_std"] > 0 and pd.notna(meta["wood_density_ton_per_m3"]):
            comm_ton = float(r["produksi_m3_std"]) * float(meta["wood_density_ton_per_m3"])
        else:
            continue

        rpr = float(meta["rpr_ratio_default"])
        moist = float(meta["moisture_pct_default"]) if pd.notna(meta["moisture_pct_default"]) else 12.0
        hhv = float(meta["avg_hhv_mj_kg"]) if pd.notna(meta["avg_hhv_mj_kg"]) else float(meta["ml_predicted_hhv_mj_kg"])
        ash_pct = float(meta["avg_ash_pct_db"]) if pd.notna(meta["avg_ash_pct_db"]) else 5.0

        wet_ton = comm_ton * rpr
        dry_ton = wet_ton * (1.0 - moist / 100.0)
        energy_gj = dry_ton * hhv          # 1 ton * 1 MJ/kg = 1 GJ
        coal_eq = energy_gj / COAL_REF_HHV_MJ_KG
        co2_off = coal_eq * COAL_EF_TCO2_PER_TON
        ash_ton = dry_ton * (ash_pct / 100.0)

        for scen_code, eff in scenarios:
            elec_mwh = (energy_gj / 3.6) * eff
            rows.append({
                "energy_fact_id": eid,
                "time_key": int(r["time_key"]),
                "location_key": int(r["location_key"]),
                "feedstock_key": fk,
                "source_key": int(r["source_key"]),
                "level_wilayah_fakta": r["level_wilayah_fakta"],
                "scenario_code": scen_code,
                "commodity_production_ton": round(comm_ton, 2),
                "rpr_ratio_used": rpr,
                "estimated_residue_wet_ton": round(wet_ton, 2),
                "estimated_residue_dry_ton": round(dry_ton, 2),
                "hhv_used_mj_kg": round(hhv, 3),
                "total_energy_potential_gj": round(energy_gj, 2),
                "convertible_electricity_mwh": round(elec_mwh, 2),
                "coal_equivalent_ton": round(coal_eq, 2),
                "estimated_co2_offset_ton": round(co2_off, 2),
                "ash_load_ton": round(ash_ton, 2),
            })
            eid += 1

    df_ener = pd.DataFrame(rows)
    df_ener.to_csv(TABLES_DIR / "fact_biomass_energy_potential.csv", index=False, encoding="utf-8-sig")
    print(f"[fact_biomass_energy_potential] {len(df_ener):,} baris -> {df_ener['level_wilayah_fakta'].value_counts().to_dict()}")
    return df_ener


def map_crea_biomass_to_fs(jenis_str, fs_map):
    s = str(jenis_str or "").lower()
    if "gergaji" in s or "kayu" in s or "serpihan" in s:
        return fs_map["LIMBAH_KAYU_SERBUK"]
    if "sawit" in s or "cangkang" in s:
        return fs_map["CANGKANG_SAWIT"]
    if "jagung" in s or "tongkol" in s:
        return fs_map["TONGKOL_JAGUNG"]
    if "padi" in s or "sekam" in s:
        return fs_map["SEKAM_PADI"]
    if "tebu" in s or "ampas" in s:
        return fs_map["AMPAS_TEBU"]
    if "rdf" in s:
        return fs_map["PELET_RDF"]
    return fs_map["NON_COFIRING_COAL"]


def resolve_crea_location(lk, lokasi_pdf: str, pulau_est: str) -> int:
    # Format lokasi_pdf umumnya "Kab/Kota, Provinsi"
    parts = [p.strip() for p in str(lokasi_pdf or "").split(",") if p.strip()]
    if len(parts) >= 2:
        prov_txt = parts[-1]
        kd2 = lk["prov_name_to_kd2"].get(norm_prov_name(prov_txt))
        if kd2:
            return lk["loc_by_code"][f"PROV_{kd2}"]
    # Fallback jika hanya nama provinsi atau format berbeda
    for p in reversed(parts):
        kd2 = lk["prov_name_to_kd2"].get(norm_prov_name(p))
        if kd2:
            return lk["loc_by_code"][f"PROV_{kd2}"]
    return lk["pulau_to_loc_key"].get(str(pulau_est).upper().strip(), lk["loc_by_code"]["PULAU_LAINNYA"])


def build_fact_pltu_operations(lk):
    print("\n[3/4] Membangun fact_pltu_operations (Climate TRACE 2021-2025 + WRI + CREA 2024)...")
    src = lk["src_by_code"]
    fs = lk["fs_by_code"]
    pmap = lk["pltu_map"]
    id_to_pltu_key = {
        (r["source_code"], str(r["source_plant_id"])): int(r["pltu_key"])
        for _, r in pmap.iterrows()
    }

    rows = []
    oid = 1

    # 1. Climate TRACE v6 (2021..2025 -> 500 rows)
    for yr in range(2021, 2026):
        df = pd.read_csv(f"raw_data/04_pltu_5_pulau/climatetrace/{yr}.csv")
        for _, r in df.iterrows():
            pkey = id_to_pltu_key[("CLIMATETRACE_V6", str(int(r["id"])))]
            pulau = str(r["pulau_est"]).upper().strip()
            lkey = lk["pulau_to_loc_key"].get(pulau, lk["loc_by_code"]["PULAU_LAINNYA"])
            # Climate TRACE capacity_factor_api = full-load operating hours / year (dibagi 8760 jam -> %)
            cf_pct = round((float(r["capacity_factor_api"]) / 8760.0) * 100.0, 2) if pd.notna(r["capacity_factor_api"]) else None
            rows.append({
                "pltu_fact_id": oid,
                "time_key": yr,
                "location_key": lkey,
                "pltu_key": pkey,
                "feedstock_key": fs["NON_COFIRING_COAL"],
                "source_key": src["CLIMATETRACE_V6"],
                "capacity_mw": round(float(r["capacity_mw"]), 2) if pd.notna(r["capacity_mw"]) else None,
                "jumlah_unit": None,
                "activity_generation_mwh": round(float(r["activity"]), 2) if pd.notna(r["activity"]) else None,
                "capacity_factor_pct": cf_pct,
                "emissions_co2e_ton": round(float(r["emissions_quantity"]), 2) if pd.notna(r["emissions_quantity"]) else None,
                "emissions_factor_t_per_mwh": round(float(r["emissions_factor"]), 4) if pd.notna(r["emissions_factor"]) else None,
                "cofiring_share_pct": None,
                "biomass_used_ton": None,
                "biomass_electricity_mwh": None,
                "biomass_emissions_tco2": None,
                "is_primary_analysis_row": 1,
            })
            oid += 1

    # 2. WRI GPPD (70 rows, acuan generasi 2017)
    wri = pd.read_csv("raw_data/04_pltu_5_pulau/wri_gppd/wri_gppd_coal_idn.csv")
    for _, r in wri.iterrows():
        pkey = id_to_pltu_key[("WRI_GPPD_V130", str(r["gppd_idnr"]).strip())]
        pulau = str(r["pulau_est"]).upper().strip()
        lkey = lk["pulau_to_loc_key"].get(pulau, lk["loc_by_code"]["PULAU_LAINNYA"])
        gen_mwh = round(float(r["estimated_generation_gwh_2017"]) * 1000.0, 2) if pd.notna(r["estimated_generation_gwh_2017"]) else None
        cap_mw = round(float(r["capacity_mw"]), 2) if pd.notna(r["capacity_mw"]) else None
        cf_pct = round((gen_mwh / (cap_mw * 8760.0)) * 100.0, 2) if (gen_mwh and cap_mw and cap_mw > 0) else None
        rows.append({
            "pltu_fact_id": oid,
            "time_key": 2017,
            "location_key": lkey,
            "pltu_key": pkey,
            "feedstock_key": fs["NON_COFIRING_COAL"],
            "source_key": src["WRI_GPPD_V130"],
            "capacity_mw": cap_mw,
            "jumlah_unit": None,
            "activity_generation_mwh": gen_mwh,
            "capacity_factor_pct": cf_pct,
            "emissions_co2e_ton": None,
            "emissions_factor_t_per_mwh": None,
            "cofiring_share_pct": None,
            "biomass_used_ton": None,
            "biomass_electricity_mwh": None,
            "biomass_emissions_tco2": None,
            "is_primary_analysis_row": 0,
        })
        oid += 1

    # 3. CREA Mei 2025 Tabel A1 (52 PLTU PLN Co-Firing, tahun realisasi 2024)
    crea = pd.read_csv("raw_data/04_pltu_5_pulau/crea_2025/tabel_a1_52_pltu_cofiring_2024.csv")
    for _, r in crea.iterrows():
        c_id = f"CREA_{int(r['no_crea']):02d}"
        pkey = id_to_pltu_key[("CREA_MEI_2025", c_id)]
        lkey = resolve_crea_location(lk, r["lokasi_pdf"], r["pulau_est"])
        fkey = map_crea_biomass_to_fs(r["jenis_biomassa"], fs)
        rows.append({
            "pltu_fact_id": oid,
            "time_key": 2024,
            "location_key": lkey,
            "pltu_key": pkey,
            "feedstock_key": fkey,
            "source_key": src["CREA_MEI_2025"],
            "capacity_mw": round(float(r["kapasitas_total_mw"]), 2) if pd.notna(r["kapasitas_total_mw"]) else None,
            "jumlah_unit": int(r["jumlah_unit"]) if pd.notna(r["jumlah_unit"]) else None,
            "activity_generation_mwh": None,
            "capacity_factor_pct": None,
            "emissions_co2e_ton": None,
            "emissions_factor_t_per_mwh": None,
            "cofiring_share_pct": round(float(r["porsi_cofiring_pct"]), 3) if pd.notna(r["porsi_cofiring_pct"]) else None,
            "biomass_used_ton": round(float(r["penggunaan_biomassa_2024_ton"]), 2) if pd.notna(r["penggunaan_biomassa_2024_ton"]) else None,
            "biomass_electricity_mwh": round(float(r["produksi_listrik_biomassa_2024_mwh"]), 2) if pd.notna(r["produksi_listrik_biomassa_2024_mwh"]) else None,
            "biomass_emissions_tco2": round(float(r["emisi_biomassa_2024_tco2"]), 2) if pd.notna(r["emisi_biomassa_2024_tco2"]) else None,
            "is_primary_analysis_row": 1,
        })
        oid += 1

    df_pltu = pd.DataFrame(rows)
    df_pltu["jumlah_unit"] = df_pltu["jumlah_unit"].astype("Int64")
    df_pltu.to_csv(TABLES_DIR / "fact_pltu_operations.csv", index=False, encoding="utf-8-sig")
    print(f"[fact_pltu_operations] {len(df_pltu)} baris (CT=500, WRI=70, CREA=52)")
    return df_pltu


def load_to_sqlite():
    print(f"\n[4/4] Memuat seluruh Star Schema ke {DB_PATH} (PRAGMA foreign_keys = ON)...")
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DDL_PATH.read_text(encoding="utf-8"))

    # Urutan muat wajib: Dimensi dulu -> Fact Tables
    load_order = [
        "dim_time",
        "dim_location",
        "dim_feedstock",
        "dim_power_plant",
        "dim_data_source",
        "fact_commodity_production",
        "fact_biomass_chemistry",
        "fact_biomass_energy_potential",
        "fact_pltu_operations",
    ]
    for tbl in load_order:
        df = pd.read_csv(TABLES_DIR / f"{tbl}.csv")
        df.to_sql(tbl, conn, if_exists="append", index=False)
        cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  Loaded {tbl:<32} : {cnt:>7,} baris")

    # Foreign key integrity verification
    fk_errors = conn.execute("PRAGMA foreign_key_check;").fetchall()
    conn.commit()
    conn.close()
    if fk_errors:
        raise RuntimeError(f"FOREIGN KEY VIOLATIONS FOUND: {len(fk_errors)} -> {fk_errors[:5]}")
    print("  PRAGMA foreign_key_check : 0 pelanggaran (100% Referential Integrity PASS!)")


if __name__ == "__main__":
    lk = load_lookups()
    df_prod = build_fact_commodity_production(lk)
    build_fact_biomass_energy_potential(lk, df_prod)
    build_fact_pltu_operations(lk)
    load_to_sqlite()
    print("\nSelesai membangun & memuat Star Schema Data Warehouse!")
