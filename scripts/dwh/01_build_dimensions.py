"""
Step 1 DWH ETL: Membangun 5 Conformed Dimensions Star Schema
Output ke warehouse/tables/:
  1. dim_time.csv
  2. dim_location.csv
  3. dim_data_source.csv
  4. dim_feedstock.csv        (baseline; diperkaya ML pada 02_ml_biomass_hhv_cluster.py)
  5. dim_power_plant.csv      (Master PLTU 5 Pulau hasil entity resolution ClimateTRACE + WRI + CREA)
  + warehouse/pltu_entity_resolution_map.csv (bridge audit pemetaan raw PLTU -> pltu_key)
"""

import math
import os
import re
from pathlib import Path
import numpy as np
import pandas as pd

OUT_DIR = Path("warehouse/tables")
OUT_DIR.mkdir(parents=True, exist_ok=True)
WAREHOUSE_DIR = Path("warehouse")

# 38 Provinsi Resmi Indonesia (kode BPS 2 digit, nama baku, pulau, masuk_5_pulau, wilayah_pln)
PROVINCES_38 = [
    ("11", "Aceh", "Sumatera", 1, "Sumatera"),
    ("12", "Sumatera Utara", "Sumatera", 1, "Sumatera"),
    ("13", "Sumatera Barat", "Sumatera", 1, "Sumatera"),
    ("14", "Riau", "Sumatera", 1, "Sumatera"),
    ("15", "Jambi", "Sumatera", 1, "Sumatera"),
    ("16", "Sumatera Selatan", "Sumatera", 1, "Sumatera"),
    ("17", "Bengkulu", "Sumatera", 1, "Sumatera"),
    ("18", "Lampung", "Sumatera", 1, "Sumatera"),
    ("19", "Kepulauan Bangka Belitung", "Sumatera", 1, "Sumatera"),
    ("21", "Kepulauan Riau", "Sumatera", 1, "Sumatera"),
    ("31", "DKI Jakarta", "Jawa", 1, "JAMALI"),
    ("32", "Jawa Barat", "Jawa", 1, "JAMALI"),
    ("33", "Jawa Tengah", "Jawa", 1, "JAMALI"),
    ("34", "DI Yogyakarta", "Jawa", 1, "JAMALI"),
    ("35", "Jawa Timur", "Jawa", 1, "JAMALI"),
    ("36", "Banten", "Jawa", 1, "JAMALI"),
    ("51", "Bali", "Bali-Nusa Tenggara", 0, "JAMALI"),
    ("52", "Nusa Tenggara Barat", "Bali-Nusa Tenggara", 0, "Nusa Tenggara"),
    ("53", "Nusa Tenggara Timur", "Bali-Nusa Tenggara", 0, "Nusa Tenggara"),
    ("61", "Kalimantan Barat", "Kalimantan", 1, "Kalimantan"),
    ("62", "Kalimantan Tengah", "Kalimantan", 1, "Kalimantan"),
    ("63", "Kalimantan Selatan", "Kalimantan", 1, "Kalimantan"),
    ("64", "Kalimantan Timur", "Kalimantan", 1, "Kalimantan"),
    ("65", "Kalimantan Utara", "Kalimantan", 1, "Kalimantan"),
    ("71", "Sulawesi Utara", "Sulawesi", 1, "Sulawesi"),
    ("72", "Sulawesi Tengah", "Sulawesi", 1, "Sulawesi"),
    ("73", "Sulawesi Selatan", "Sulawesi", 1, "Sulawesi"),
    ("74", "Sulawesi Tenggara", "Sulawesi", 1, "Sulawesi"),
    ("75", "Gorontalo", "Sulawesi", 1, "Sulawesi"),
    ("76", "Sulawesi Barat", "Sulawesi", 1, "Sulawesi"),
    ("81", "Maluku", "Maluku", 0, "Maluku-Papua"),
    ("82", "Maluku Utara", "Maluku", 0, "Maluku-Papua"),
    ("91", "Papua Barat", "Papua", 1, "Maluku-Papua"),
    ("92", "Papua Barat Daya", "Papua", 1, "Maluku-Papua"),
    ("94", "Papua", "Papua", 1, "Maluku-Papua"),
    ("95", "Papua Selatan", "Papua", 1, "Maluku-Papua"),
    ("96", "Papua Tengah", "Papua", 1, "Maluku-Papua"),
    ("97", "Papua Pegunungan", "Papua", 1, "Maluku-Papua"),
]

# Approksimasi koordinat centroid ibu kota provinsi (untuk pemetaan spasial di Power BI)
PROV_COORDS = {
    "11": (5.5483, 95.3238), "12": (3.5952, 98.6722), "13": (-0.9471, 100.4172),
    "14": (0.5071, 101.4478), "15": (-1.6101, 103.6131), "16": (-2.9761, 104.7754),
    "17": (-3.7928, 102.2608), "18": (-5.4292, 105.2610), "19": (-2.1316, 106.1169),
    "21": (0.9186, 104.4665), "31": (-6.2088, 106.8456), "32": (-6.9175, 107.6191),
    "33": (-6.9667, 110.4167), "34": (-7.7956, 110.3695), "35": (-7.2575, 112.7521),
    "36": (-6.1200, 106.1503), "51": (-8.6705, 115.2126), "52": (-8.5833, 116.1167),
    "53": (-10.1772, 123.6070), "61": (-0.0263, 109.3425), "62": (-2.2136, 113.9108),
    "63": (-3.3194, 114.5908), "64": (-0.5022, 117.1536), "65": (2.8375, 117.3653),
    "71": (1.4748, 124.8421), "72": (-0.8917, 119.8707), "73": (-5.1477, 119.4327),
    "74": (-3.9985, 122.5129), "75": (0.5435, 123.0568), "76": (-2.6775, 118.8861),
    "81": (-3.6954, 128.1814), "82": (0.7893, 127.3878), "91": (-0.8615, 134.0620),
    "92": (-0.8762, 131.2558), "94": (-2.5916, 140.6690), "95": (-8.4932, 140.4018),
    "96": (-3.3667, 135.4960), "97": (-4.0928, 138.9438),
}


def norm_text(s: str) -> str:
    s = str(s or "").upper().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def norm_prov_name(s: str) -> str:
    s = norm_text(s)
    s = re.sub(r"^PROVINSI\s+", "", s)
    repl = {
        "NANGROE ACEH DARUSSALAM": "ACEH",
        "NANGGROE ACEH DARUSSALAM": "ACEH",
        "DAERAH KHUSUS IBUKOTA JAKARTA": "DKI JAKARTA",
        "DAERAH ISTIMEWA YOGYAKARTA": "DI YOGYAKARTA",
        "KEP. BANGKA BELITUNG": "KEPULAUAN BANGKA BELITUNG",
        "KEP.RIAU": "KEPULAUAN RIAU",
        "KEP. RIAU": "KEPULAUAN RIAU",
        "BANGKA BELITUNG": "KEPULAUAN BANGKA BELITUNG",
    }
    return repl.get(s, s)


KAB_ALIAS_EXACT = {
    "BIREUEN": "BIREUN",
    "DHARMASRAYA": "DHARMASRAYA",
    "PAHUWATO": "POHUWATO",
    "KEPULAUANTANIMBAR": "MALUKUTENGGARABARAT",
    "PANGKAJENEKEPULAUAN": "PANGKAJENEDANKEPULAUAN",
    "KEPSERIBU": "KEPULAUANSERIBU",
    "ADMKEPSERIBU": "KEPULAUANSERIBU",
    "KUTAIKARTANEGARA": "KUTAIKERTANEGARA",
    "MAHAKAMULU": "MAHAKAMHULU",
}


def norm_kab_name(s: str) -> str:
    s = norm_text(s)
    s = re.sub(r"^(KABUPATEN|KAB\.?|KOTA ADM\.?|KOTA)\s+", "", s)
    s = re.sub(r"^ADM\.?\s+", "", s)
    s = re.sub(r"[^A-Z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_kab_compact(s: str) -> str:
    c = re.sub(r"[^A-Z0-9]", "", norm_kab_name(s))
    return KAB_ALIAS_EXACT.get(c, c)


def haversine_km(lat1, lon1, lat2, lon2):
    if any(pd.isna(v) for v in (lat1, lon1, lat2, lon2)):
        return 99999.0
    r = 6371.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


GENERIC_GEO_WORDS = {
    "banten", "jawa", "java", "sumatera", "sumatra", "kalimantan",
    "sulawesi", "papua", "barat", "timur", "utara", "selatan", "tengah",
    "kalsel", "kaltim", "kalteng", "kalbar", "sulsel", "sulut", "sulteng", "sultra", "sumsel", "sumut",
}


def clean_pltu_stem(name: str) -> str:
    s = str(name or "").lower().strip()
    s = re.sub(r"\b(pltu|pln|power\s*station|power\s*plant|steam|coal|station|plant|unit|units|expansi|ekspansi|ext|extension|ipp|ftpp|ftp|baru|new|captive)\b", " ", s)
    s = re.sub(r"\b\d+\s*[-–&+x]\s*\d+\b", " ", s)
    s = re.sub(r"\b\d+\b", " ", s)
    s = re.sub(r"[^a-z\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def pltu_specific_tokens(stem: str) -> set:
    toks = set(stem.split())
    spec = toks - GENERIC_GEO_WORDS
    return spec if spec else toks


def build_dim_time():
    rows = []
    for y in range(1998, 2027):
        rows.append({
            "time_key": y,
            "year": y,
            "decade": (y // 10) * 10,
            "is_post_papua_split": 1 if y >= 2023 else 0,
            "is_bps_ksa_era": 1 if y >= 2018 else 0,
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "dim_time.csv", index=False, encoding="utf-8-sig")
    print(f"[dim_time] {len(df)} baris (1998..2026)")
    return df


def build_dim_location():
    rows = []
    key = 1

    # 1. NASIONAL
    rows.append({
        "location_key": key, "location_code": "IDN_00", "level_wilayah": "NASIONAL",
        "kode_bps_prov": None, "nama_provinsi": "INDONESIA",
        "kode_bps_kabkota": None, "nama_kabkota": None,
        "pulau": "Indonesia", "masuk_5_pulau_pltu": 0, "wilayah_pln": "Nasional",
        "latitude_centroid": -2.5489, "longitude_centroid": 118.0149,
    })
    key += 1

    # 2. PULAU (5 pulau utama + wilayah agregat BPS 1973#2 + lainnya)
    pulau_defs = [
        ("PULAU_JAWA", "Jawa", 1, "JAMALI", -7.25, 110.0),
        ("PULAU_SUMATERA", "Sumatera", 1, "Sumatera", -0.50, 101.5),
        ("PULAU_KALIMANTAN", "Kalimantan", 1, "Kalimantan", -0.50, 114.5),
        ("PULAU_SULAWESI", "Sulawesi", 1, "Sulawesi", -2.00, 120.5),
        ("PULAU_PAPUA", "Papua", 1, "Maluku-Papua", -4.00, 138.0),
        ("PULAU_BALI_NUSRA", "Bali-Nusa Tenggara", 0, "Nusa Tenggara", -8.65, 118.5),
        ("PULAU_MALUKU", "Maluku", 0, "Maluku-Papua", -1.50, 128.0),
        ("PULAU_BALI_NUSRA_SULAWESI", "Bali, Nusa Tenggara, dan Sulawesi", 0, "Sulawesi-Nusra", -5.00, 120.0),
        ("PULAU_MALUKU_PAPUA", "Maluku dan Papua", 0, "Maluku-Papua", -3.50, 134.0),
        ("PULAU_LAINNYA", "Lainnya", 0, "Lainnya", None, None),
    ]
    for code, nama, in5, pln, lat, lon in pulau_defs:
        rows.append({
            "location_key": key, "location_code": code, "level_wilayah": "PULAU",
            "kode_bps_prov": None, "nama_provinsi": None,
            "kode_bps_kabkota": None, "nama_kabkota": None,
            "pulau": nama, "masuk_5_pulau_pltu": in5, "wilayah_pln": pln,
            "latitude_centroid": lat, "longitude_centroid": lon,
        })
        key += 1

    # 3. PROVINSI (38 resmi)
    prov_lookup = {}
    for kd2, nama, pulau, in5, pln in PROVINCES_38:
        lat, lon = PROV_COORDS[kd2]
        rows.append({
            "location_key": key, "location_code": f"PROV_{kd2}", "level_wilayah": "PROVINSI",
            "kode_bps_prov": kd2, "nama_provinsi": nama,
            "kode_bps_kabkota": None, "nama_kabkota": None,
            "pulau": pulau, "masuk_5_pulau_pltu": in5, "wilayah_pln": pln,
            "latitude_centroid": lat, "longitude_centroid": lon,
        })
        prov_lookup[kd2] = (nama, pulau, in5, pln)
        key += 1

    # 4. KABKOTA (union seluruh 4 komoditas BDSP -> 541 kode unik)
    kab_map = {}
    for kom in ["padi", "jagung", "kelapa_sawit", "tebu"]:
        for f in sorted(Path(f"raw_data/01_bdsp_kementan/{kom}/kabkota").glob("*.csv")):
            d = pd.read_csv(f, usecols=["kode_prov", "kode_kabkota", "kabupaten_kota"])
            for _, r in d.iterrows():
                kd_prov = str(r["kode_prov"]).zfill(2)
                kd_kab = str(r["kode_kabkota"]).zfill(4)
                nm_kab = str(r["kabupaten_kota"]).strip()
                if kd_kab not in kab_map:
                    kab_map[kd_kab] = (kd_prov, nm_kab)

    for kd_kab in sorted(kab_map):
        kd_prov, nm_kab = kab_map[kd_kab]
        p_nama, pulau, in5, pln = prov_lookup[kd_prov]
        rows.append({
            "location_key": key, "location_code": f"KAB_{kd_kab}", "level_wilayah": "KABKOTA",
            "kode_bps_prov": kd_prov, "nama_provinsi": p_nama,
            "kode_bps_kabkota": kd_kab, "nama_kabkota": nm_kab,
            "pulau": pulau, "masuk_5_pulau_pltu": in5, "wilayah_pln": pln,
            "latitude_centroid": None, "longitude_centroid": None,
        })
        key += 1

    # 5. Cek apakah ada Kab/Kota dari Satu Data Sawit 2023 yang belum match di kab_map (pakai compact + alias resmi)
    from difflib import SequenceMatcher
    sd = pd.read_csv("raw_data/01_bdsp_kementan/satudata_kementan/sawit_kabkota_2023.csv")
    sd_kab = sd[sd["tipe_baris"] == "KABKOTA"].copy()
    prov_name_to_kd2 = {norm_prov_name(n): kd2 for kd2, n, _, _, _ in PROVINCES_38}
    existing_kab_compact = {(kd_prov, norm_kab_compact(nm)): kd_kab for kd_kab, (kd_prov, nm) in kab_map.items()}
    extra_idx = 1
    for _, r in sd_kab.iterrows():
        p_norm = norm_prov_name(r["provinsi_konteks"])
        kd_prov = prov_name_to_kd2.get(p_norm)
        k_comp = norm_kab_compact(r["kabupaten_kota_raw"])
        if kd_prov and (kd_prov, k_comp) not in existing_kab_compact:
            matched = None
            best_ratio = 0.0
            for (ep, ek), ek_code in existing_kab_compact.items():
                if ep == kd_prov:
                    if k_comp in ek or ek in k_comp:
                        matched = ek_code
                        break
                    ratio = SequenceMatcher(None, k_comp, ek).ratio()
                    if ratio >= 0.85 and ratio > best_ratio:
                        best_ratio = ratio
                        matched = ek_code
            if not matched:
                syn_code = f"{kd_prov}X{extra_idx:02d}"
                extra_idx += 1
                p_nama, pulau, in5, pln = prov_lookup[kd_prov]
                rows.append({
                    "location_key": key, "location_code": f"KAB_{syn_code}", "level_wilayah": "KABKOTA",
                    "kode_bps_prov": kd_prov, "nama_provinsi": p_nama,
                    "kode_bps_kabkota": syn_code, "nama_kabkota": str(r["kabupaten_kota_raw"]).strip(),
                    "pulau": pulau, "masuk_5_pulau_pltu": in5, "wilayah_pln": pln,
                    "latitude_centroid": None, "longitude_centroid": None,
                })
                existing_kab_compact[(kd_prov, k_comp)] = syn_code
                key += 1

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "dim_location.csv", index=False, encoding="utf-8-sig")
    print(f"[dim_location] {len(df)} baris -> {df['level_wilayah'].value_counts().to_dict()}")
    return df


def build_dim_data_source():
    sources = [
        (1, "BDSP_KABKOTA", "BDSP Kementerian Pertanian", "Produksi Komoditas Level Kab/Kota (2010-2026)", "KABKOTA", "KABKOTA_BDSP_STANDARD", "Ton", "https://bdsp2.pertanian.go.id/bdsp/id/lokasi"),
        (2, "BDSP_KABKOTA_PR", "BDSP Kementerian Pertanian", "Produksi Kelapa Sawit & Tebu Kab/Kota (Cakupan Perkebunan Rakyat 2018+/2023+)", "KABKOTA", "PERKEBUNAN_RAKYAT_ONLY", "Ton", "https://bdsp2.pertanian.go.id/bdsp/id/lokasi"),
        (3, "BDSP_PROVINSI", "BDSP Kementerian Pertanian", "Produksi Komoditas Level 38 Provinsi (2010-2026)", "PROVINSI", "ALL_OWNERSHIP", "Ton", "https://bdsp2.pertanian.go.id/bdsp/id/lokasi"),
        (4, "SATUDATA_SAWIT_2023", "Satu Data Kementerian Pertanian", "Luas & Produksi Kelapa Sawit Perkebunan Rakyat per Kab/Kota (2023)", "KABKOTA", "PERKEBUNAN_RAKYAT_ONLY", "Ton", "https://satudata.pertanian.go.id/assets/docs/metadata/45_Luas_perkebunan_kelapa_sawit_di_kabupaten.xlsx"),
        (5, "BPS_RI_1498_PADI", "Badan Pusat Statistik (BPS RI)", "Tabel 1498#2: Luas Panen, Produksi, Produktivitas Padi Menurut Provinsi (2018-2024)", "PROVINSI", "ALL_OWNERSHIP", "Ton", "https://www.bps.go.id/id/statistics-table/2/MTQ5OCMy/table.html"),
        (6, "BPS_RI_2204_JAGUNG", "Badan Pusat Statistik (BPS RI)", "Tabel 2204#2: Luas Panen, Produksi, Produktivitas Jagung Menurut Provinsi (2020-2024)", "PROVINSI", "ALL_OWNERSHIP", "Ton", "https://www.bps.go.id/id/statistics-table/2/MjIwNCMy/table.html"),
        (7, "BPS_RI_2566_PERKEBUNAN", "Badan Pusat Statistik (BPS RI)", "Tabel 2566#2: Produksi Tanaman Perkebunan Menurut Provinsi (2024)", "PROVINSI", "ALL_OWNERSHIP_PR_PBN_PBS", "Ribu Ton", "https://www.bps.go.id/id/statistics-table/2/MjU2NiMy/table.html"),
        (8, "BPS_RI_132_PERKEBUNAN_HIST", "Badan Pusat Statistik (BPS RI)", "Tabel 132#2: Produksi Tanaman Perkebunan Historis Menurut Provinsi (2008-2023)", "PROVINSI", "ALL_OWNERSHIP_PR_PBN_PBS", "Ribu Ton", "https://www.bps.go.id/id/statistics-table/2/MTMyIzI=/table.html"),
        (9, "BPS_RI_2512_KAYU_JENIS", "Badan Pusat Statistik (BPS RI)", "Tabel 2512#2: Produksi Perusahaan Pembudidaya Tanaman Kehutanan per Jenis (2020-2023)", "NASIONAL", "HTI_PEMBUDIDAYA", "m3 / SM", "https://www.bps.go.id/id/statistics-table/2/MjUxMiMy/table.html"),
        (10, "BPS_RI_1973_KAYU_HPH", "Badan Pusat Statistik (BPS RI)", "Tabel 1973#2: Produksi Kayu Bulat Perusahaan HPH Menurut Pulau (2019-2022)", "PULAU", "HPH_HUTAN_ALAM", "m3", "https://www.bps.go.id/id/statistics-table/2/MTk3MyMy/table.html"),
        (11, "KLHK_PHL_2024_PBPH", "Ditjen PHL Kemenhut/KLHK", "Statistik PHL 2024 Tabel 3.9: Produksi Kayu Bulat PBPH per Provinsi (2020-2024)", "PROVINSI", "PBPH", "m3", "https://phl.kehutanan.go.id/media/statistik/statistik_file_1788408189.pdf"),
        (12, "KLHK_PHL_2024_PERHUTANI", "Ditjen PHL Kemenhut/KLHK", "Statistik PHL 2024 Tabel 3.12: Produksi Kayu Bulat Perum Perhutani (2020-2024)", "PROVINSI", "PERHUTANI", "m3", "https://phl.kehutanan.go.id/media/statistik/statistik_file_1788408189.pdf"),
        (13, "KLHK_PHL_2022_PBPH", "Ditjen PHL Kemenhut/KLHK", "Statistik PHL 2022 Tabel 3.9: Produksi Kayu Bulat PBPH per Provinsi (2018-2022)", "PROVINSI", "PBPH", "m3", "https://phl.kehutanan.go.id/media/statistik/statistik_file_1726677781.pdf"),
        (14, "KLHK_PHL_2022_PERHUTANI", "Ditjen PHL Kemenhut/KLHK", "Statistik PHL 2022 Tabel 3.12: Produksi Kayu Bulat Perum Perhutani (2018-2022)", "PROVINSI", "PERHUTANI", "m3", "https://phl.kehutanan.go.id/media/statistik/statistik_file_1726677781.pdf"),
        (15, "MENDELEY_5XSWR8YP34", "Mendeley Data (Biomass HHV)", "Biomass Dataset for HHV Prediction (315 Sampel Proximate + Ultimate + HHV)", "SAMPEL_LAB", "LITERATURE_LAB", "wt% db / MJ/kg", "https://data.mendeley.com/datasets/5xswr8yp34"),
        (16, "GITHUB_DURAN_UA", "Biomass Ultimate Analysis DB", "Biomass Ultimate Analysis Dataset (1.023 Sampel C/H/O/N/S)", "SAMPEL_LAB", "LITERATURE_LAB", "wt% db", "https://github.com/duran-biomass-dataset"),
        (17, "GITHUB_DURAN_PA", "Biomass Proximate Analysis DB", "Biomass Proximate Analysis Dataset (891 Sampel Ash/VM/FC)", "SAMPEL_LAB", "LITERATURE_LAB", "wt% db", "https://github.com/duran-biomass-dataset"),
        (18, "CLIMATETRACE_V6", "Climate TRACE Coalition", "Climate TRACE v6 Power Sector Assets - Coal Indonesia (2021-2025)", "UNIT_PLTU", "PLN_IPP_CAPTIVE", "MW / MWh / tCO2e", "https://api.climatetrace.org/v6/assets?countries=IDN&sectors=power&year=2024&limit=500"),
        (19, "WRI_GPPD_V130", "World Resources Institute (WRI)", "Global Power Plant Database v1.3.0 - Coal Indonesia (70 PLTU)", "UNIT_PLTU", "PLN_IPP_CAPTIVE", "MW / GWh", "https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv"),
        (20, "CREA_MEI_2025", "Centre for Research on Energy and Clean Air (CREA)", "Laporan Co-Firing Biomassa Indonesia Mei 2025 - Tabel A1 (52 PLTU PLN)", "UNIT_PLTU", "PLN_COFIRING", "MW / Ton / MWh / tCO2", "https://energyandcleanair.org/wp/wp-content/uploads/2025/05/ID-IDN-Biomass-co-firing-in-Indonesia.pdf"),
    ]
    cols = [
        "source_key", "kode_sumber", "nama_instansi", "nama_dataset",
        "level_granularity_asli", "ownership_coverage_scope", "satuan_asli", "url_sumber"
    ]
    df = pd.DataFrame(sources, columns=cols)
    df.to_csv(OUT_DIR / "dim_data_source.csv", index=False, encoding="utf-8-sig")
    print(f"[dim_data_source] {len(df)} baris")
    return df


def build_dim_feedstock():
    # Parameter RPR konservatif & transparan mengacu Buku Saku Bioenergi Ditjen EBTKE ESDM & literatur biomassa Indonesia.
    # Nilai avg_hhv_mj_kg, ml_predicted_hhv_mj_kg, avg_ash_pct_db, avg_sulfur_pct_db & grade akan diisi/diperkaya
    # langsung dari data empiris + ML pada 02_ml_biomass_hhv_cluster.py.
    feedstocks = [
        {
            "feedstock_key": 1, "kode_komoditas": "PADI", "nama_komoditas": "Padi",
            "subsektor": "Tanaman Pangan", "kode_feedstock": "SEKAM_PADI",
            "nama_limbah_biomassa": "Sekam Padi (Rice Husk)", "phyllis_category": "husk/shell/pit",
            "rpr_ratio_default": 0.20, "wood_density_ton_per_m3": None, "moisture_pct_default": 10.0,
            "rpr_reference_note": "RPR = 0.20 ton sekam / ton GKG (Buku Saku Bioenergi ESDM; kisaran 0.20-0.23).",
        },
        {
            "feedstock_key": 2, "kode_komoditas": "JAGUNG", "nama_komoditas": "Jagung",
            "subsektor": "Tanaman Pangan", "kode_feedstock": "TONGKOL_JAGUNG",
            "nama_limbah_biomassa": "Tongkol Jagung (Corn Cob)", "phyllis_category": "straw (stalk/cob/ear)",
            "rpr_ratio_default": 0.273, "wood_density_ton_per_m3": None, "moisture_pct_default": 15.0,
            "rpr_reference_note": "RPR = 0.273 ton tongkol / ton jagung pipilan kering (ESDM / Koopmans & Koppejan).",
        },
        {
            "feedstock_key": 3, "kode_komoditas": "KELAPA_SAWIT", "nama_komoditas": "Kelapa Sawit",
            "subsektor": "Perkebunan", "kode_feedstock": "CANGKANG_SAWIT",
            "nama_limbah_biomassa": "Cangkang Sawit (Palm Kernel Shell / PKS)", "phyllis_category": "husk/shell/pit",
            "rpr_ratio_default": 0.295, "wood_density_ton_per_m3": None, "moisture_pct_default": 12.0,
            "rpr_reference_note": "Basis BPS/BDSP = ton CPO. 1 ton CPO / 0.22 OER = 4.545 ton TBS; PKS = 6.5% TBS -> 0.295 ton PKS / ton CPO (konservatif, hanya PKS; belum termasuk EFB/serat).",
        },
        {
            "feedstock_key": 4, "kode_komoditas": "TEBU", "nama_komoditas": "Tebu",
            "subsektor": "Perkebunan", "kode_feedstock": "AMPAS_TEBU",
            "nama_limbah_biomassa": "Ampas Tebu (Sugarcane Bagasse)", "phyllis_category": "grass/plant",
            "rpr_ratio_default": 4.00, "wood_density_ton_per_m3": None, "moisture_pct_default": 50.0,
            "rpr_reference_note": "Basis BPS/BDSP = ton Gula Hablur/GKP (~2.46 jt ton/thn). 1 ton GKP / 0.075 rendemen = 13.33 ton tebu giling x 0.30 bagasse basah = 4.0 ton bagasse basah (2.0 ton kering @ 50% moisture).",
        },
        {
            "feedstock_key": 5, "kode_komoditas": "KAYU_BULAT", "nama_komoditas": "Kayu Bulat",
            "subsektor": "Kehutanan", "kode_feedstock": "LIMBAH_KAYU_SERBUK",
            "nama_limbah_biomassa": "Serbuk Gergaji & Serpihan Kayu (Sawdust / Woodchips)", "phyllis_category": "untreated wood",
            "rpr_ratio_default": 0.25, "wood_density_ton_per_m3": 0.60, "moisture_pct_default": 15.0,
            "rpr_reference_note": "Basis KLHK PHL = m3 kayu bulat. Konversi konservatif 0.60 ton/m3 (rata-rata HTI Akasia/Eukaliptus/Rimba) x RPR limbah industri/pemanenan 0.25.",
        },
        {
            "feedstock_key": 6, "kode_komoditas": "KAYU_BAKAR", "nama_komoditas": "Kayu Bakar",
            "subsektor": "Kehutanan", "kode_feedstock": "KAYU_BAKAR_BPS",
            "nama_limbah_biomassa": "Kayu Bakar (Fuelwood - BPS 2512#2)", "phyllis_category": "untreated wood",
            "rpr_ratio_default": 1.00, "wood_density_ton_per_m3": 0.50, "moisture_pct_default": 20.0,
            "rpr_reference_note": "Khusus catatan BPS 2512#2 baris B. KAYU BAKAR (SM); tidak digabungkan ke total Kayu Bulat.",
        },
        {
            "feedstock_key": 7, "kode_komoditas": "SAMPAH_RDF", "nama_komoditas": "Sampah Perkotaan (RDF)",
            "subsektor": "Waste-to-Energy", "kode_feedstock": "PELET_RDF",
            "nama_limbah_biomassa": "Pelet RDF / Limbah Padat (Referensi CREA)", "phyllis_category": "organic residue/product",
            "rpr_ratio_default": None, "wood_density_ton_per_m3": None, "moisture_pct_default": 15.0,
            "rpr_reference_note": "Entri referensi khusus PLTU co-firing CREA yang memakai Pelet RDF.",
        },
        {
            "feedstock_key": 8, "kode_komoditas": "LAINNYA_BIOMASSA", "nama_komoditas": "Biomassa Lainnya (Lab)",
            "subsektor": "Referensi Kimia Lab", "kode_feedstock": "OTHER_BIOMASS",
            "nama_limbah_biomassa": "Kandidat Biomassa Lain (Mendeley/Duran Lab)", "phyllis_category": "unclassified_biomass",
            "rpr_ratio_default": None, "wood_density_ton_per_m3": None, "moisture_pct_default": None,
            "rpr_reference_note": "Sampel lab kimia di luar 5 komoditas utama (misal jerami, kotoran ternak, rumput energi, dll.).",
        },
        {
            "feedstock_key": 9, "kode_komoditas": "BATU_BARA_ONLY", "nama_komoditas": "Batu Bara (Belum Tercatat Co-Firing)",
            "subsektor": "PLTU Referensi", "kode_feedstock": "NON_COFIRING_COAL",
            "nama_limbah_biomassa": "Tidak Ada Biomassa / Belum Dilaporkan", "phyllis_category": "none",
            "rpr_ratio_default": None, "wood_density_ton_per_m3": None, "moisture_pct_default": None,
            "rpr_reference_note": "Placeholder FK agar fact_pltu_operations (ClimateTRACE / WRI / target CREA) bebas NULL FK.",
        },
    ]
    for f in feedstocks:
        f.update({
            "avg_hhv_mj_kg": None,
            "ml_predicted_hhv_mj_kg": None,
            "avg_ash_pct_db": None,
            "avg_sulfur_pct_db": None,
            "boiler_suitability_grade": None,
            "slagging_risk_level": None,
        })
    cols = [
        "feedstock_key", "kode_komoditas", "nama_komoditas", "subsektor", "kode_feedstock",
        "nama_limbah_biomassa", "phyllis_category", "rpr_ratio_default", "wood_density_ton_per_m3",
        "moisture_pct_default", "avg_hhv_mj_kg", "ml_predicted_hhv_mj_kg", "avg_ash_pct_db",
        "avg_sulfur_pct_db", "boiler_suitability_grade", "slagging_risk_level", "rpr_reference_note"
    ]
    df = pd.DataFrame(feedstocks)[cols]
    df.to_csv(OUT_DIR / "dim_feedstock.csv", index=False, encoding="utf-8-sig")
    print(f"[dim_feedstock] {len(df)} baris (baseline siap diperkaya ML)")
    return df


def token_jaccard(a: str, b: str) -> float:
    ta = pltu_specific_tokens(a)
    tb = pltu_specific_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def build_dim_power_plant():
    ct24 = pd.read_csv("raw_data/04_pltu_5_pulau/climatetrace/2024.csv")
    wri = pd.read_csv("raw_data/04_pltu_5_pulau/wri_gppd/wri_gppd_coal_idn.csv")
    crea = pd.read_csv("raw_data/04_pltu_5_pulau/crea_2025/tabel_a1_52_pltu_cofiring_2024.csv")

    masters = []
    bridge_rows = []
    pltu_key = 1

    # 1. Anchor: 100 Climate TRACE coal plants (lengkap lat/lon + 2021-2025 activity)
    for _, r in ct24.sort_values("id").iterrows():
        ct_id = int(r["id"])
        pulau = str(r["pulau_est"])
        masters.append({
            "pltu_key": pltu_key,
            "pltu_master_id": f"PLTU_M{pltu_key:03d}",
            "nama_pltu_standar": str(r["name"]).strip(),
            "nama_climatetrace": str(r["name"]).strip(),
            "nama_wri_gppd": None,
            "nama_crea_2025": None,
            "owner_operator": str(r["owners_names"]).strip() if pd.notna(r["owners_names"]) else None,
            "jenis_boiler": None,
            "status_cofiring_2024": "BELUM_TERCATAT_DI_CREA",
            "commissioning_year": None,
            "latitude": float(r["latitude"]) if pd.notna(r["latitude"]) else None,
            "longitude": float(r["longitude"]) if pd.notna(r["longitude"]) else None,
            "pulau": pulau,
            "masuk_5_pulau_pltu": 1 if bool(r["masuk_5_pulau"]) else 0,
            "wilayah_pln": None,
            "entity_match_method": "ANCHOR_CLIMATETRACE",
            "_stem": clean_pltu_stem(r["name"]),
        })
        bridge_rows.append({
            "source_code": "CLIMATETRACE_V6", "source_plant_id": str(ct_id),
            "source_plant_name": str(r["name"]).strip(), "pltu_key": pltu_key,
            "match_method": "ANCHOR_CT", "match_score": 1.0, "dist_km": 0.0,
        })
        pltu_key += 1

    # 2. Match 70 WRI GPPD plants HANYA ke 100 Climate TRACE anchor (mencegah beberapa WRI dengan koordinat
    #    centroid default identik saling menelan satu sama lain!)
    ct_anchors = list(masters)
    wri_matched = 0
    for _, r in wri.sort_values("gppd_idnr").iterrows():
        w_id = str(r["gppd_idnr"]).strip()
        w_name = str(r["name"]).strip()
        w_stem = clean_pltu_stem(w_name)
        w_lat, w_lon = r["latitude"], r["longitude"]
        best_m, best_dist, best_sim = None, 99999.0, 0.0
        for m in ct_anchors:
            d = haversine_km(w_lat, w_lon, m["latitude"], m["longitude"])
            sim = token_jaccard(w_stem, m["_stem"])
            if (d <= 4.0 and sim >= 0.25) or (d <= 15.0 and sim >= 0.45) or (sim >= 0.65 and m["pulau"] == str(r["pulau_est"])):
                score_d = d - sim * 20.0
                if best_m is None or score_d < (best_dist - best_sim * 20.0):
                    best_m, best_dist, best_sim = m, d, sim
        if best_m is not None:
            wri_matched += 1
            best_m["nama_wri_gppd"] = w_name if not best_m["nama_wri_gppd"] else f"{best_m['nama_wri_gppd']} | {w_name}"
            if pd.notna(r["commissioning_year"]) and best_m["commissioning_year"] is None:
                best_m["commissioning_year"] = int(r["commissioning_year"])
            if not best_m["owner_operator"] and pd.notna(r["owner"]):
                best_m["owner_operator"] = str(r["owner"]).strip()
            if "+WRI" not in best_m["entity_match_method"]:
                best_m["entity_match_method"] += "+WRI"
            bridge_rows.append({
                "source_code": "WRI_GPPD_V130", "source_plant_id": w_id,
                "source_plant_name": w_name, "pltu_key": best_m["pltu_key"],
                "match_method": "GEO_NAME_MATCH", "match_score": round(best_sim, 3),
                "dist_km": round(best_dist, 2),
            })
        else:
            masters.append({
                "pltu_key": pltu_key,
                "pltu_master_id": f"PLTU_M{pltu_key:03d}",
                "nama_pltu_standar": w_name,
                "nama_climatetrace": None,
                "nama_wri_gppd": w_name,
                "nama_crea_2025": None,
                "owner_operator": str(r["owner"]).strip() if pd.notna(r["owner"]) else None,
                "jenis_boiler": None,
                "status_cofiring_2024": "BELUM_TERCATAT_DI_CREA",
                "commissioning_year": int(r["commissioning_year"]) if pd.notna(r["commissioning_year"]) else None,
                "latitude": float(w_lat) if pd.notna(w_lat) else None,
                "longitude": float(w_lon) if pd.notna(w_lon) else None,
                "pulau": str(r["pulau_est"]),
                "masuk_5_pulau_pltu": 1 if bool(r["masuk_5_pulau"]) else 0,
                "wilayah_pln": None,
                "entity_match_method": "WRI_ONLY",
                "_stem": w_stem,
            })
            bridge_rows.append({
                "source_code": "WRI_GPPD_V130", "source_plant_id": w_id,
                "source_plant_name": w_name, "pltu_key": pltu_key,
                "match_method": "NEW_WRI_ONLY", "match_score": 0.0, "dist_km": None,
            })
            pltu_key += 1

    # 3. Match 52 CREA 2025 PLTU PLN Co-Firing ke master CT/WRI memakai token spesifik + pulau
    pre_crea_masters = list(masters)
    crea_matched = 0
    for _, r in crea.sort_values("no_crea").iterrows():
        c_id = f"CREA_{int(r['no_crea']):02d}"
        c_name = str(r["nama_pltu_pdf"]).strip()
        c_stem = clean_pltu_stem(c_name)
        c_spec = " ".join(sorted(pltu_specific_tokens(c_stem)))
        c_pulau = str(r["pulau_est"]).strip()
        c_boiler = str(r["jenis_boiler"]).strip() if pd.notna(r["jenis_boiler"]) else None
        c_status = str(r["status_cofiring_2024"]).strip() if pd.notna(r["status_cofiring_2024"]) else None
        c_wil = str(r["wilayah_pln"]).replace("Wilayah:", "").strip() if pd.notna(r["wilayah_pln"]) else None

        best_m, best_sim = None, 0.0
        for m in pre_crea_masters:
            if m["pulau"] != c_pulau:
                continue
            sim = token_jaccard(c_stem, m["_stem"])
            m_spec = " ".join(sorted(pltu_specific_tokens(m["_stem"])))
            if c_spec and m_spec and (c_spec == m_spec):
                sim = 1.0
            if sim >= 0.50 and sim > best_sim:
                best_m, best_sim = m, sim

        if best_m is not None:
            crea_matched += 1
            best_m["nama_crea_2025"] = c_name if not best_m["nama_crea_2025"] else f"{best_m['nama_crea_2025']} | {c_name}"
            if c_boiler:
                best_m["jenis_boiler"] = c_boiler if not best_m["jenis_boiler"] else (
                    best_m["jenis_boiler"] if c_boiler in best_m["jenis_boiler"] else f"{best_m['jenis_boiler']}/{c_boiler}"
                )
            if c_status == "OPERASI_COFIRING_2024" or best_m["status_cofiring_2024"] == "BELUM_TERCATAT_DI_CREA":
                best_m["status_cofiring_2024"] = c_status
            if c_wil and not best_m["wilayah_pln"]:
                best_m["wilayah_pln"] = c_wil
            if "+CREA" not in best_m["entity_match_method"]:
                best_m["entity_match_method"] += "+CREA"
            bridge_rows.append({
                "source_code": "CREA_MEI_2025", "source_plant_id": c_id,
                "source_plant_name": c_name, "pltu_key": best_m["pltu_key"],
                "match_method": "NAME_PULAU_MATCH", "match_score": round(best_sim, 3),
                "dist_km": None,
            })
        else:
            masters.append({
                "pltu_key": pltu_key,
                "pltu_master_id": f"PLTU_M{pltu_key:03d}",
                "nama_pltu_standar": f"PLTU {c_name}",
                "nama_climatetrace": None,
                "nama_wri_gppd": None,
                "nama_crea_2025": c_name,
                "owner_operator": "PT PLN (Persero)",
                "jenis_boiler": c_boiler,
                "status_cofiring_2024": c_status,
                "commissioning_year": None,
                "latitude": None,
                "longitude": None,
                "pulau": c_pulau,
                "masuk_5_pulau_pltu": 1 if bool(r["masuk_5_pulau"]) else 0,
                "wilayah_pln": c_wil,
                "entity_match_method": "CREA_ONLY",
                "_stem": c_stem,
            })
            bridge_rows.append({
                "source_code": "CREA_MEI_2025", "source_plant_id": c_id,
                "source_plant_name": c_name, "pltu_key": pltu_key,
                "match_method": "NEW_CREA_ONLY", "match_score": 0.0, "dist_km": None,
            })
            pltu_key += 1

    df_m = pd.DataFrame(masters).drop(columns=["_stem"])
    df_m["commissioning_year"] = df_m["commissioning_year"].astype("Int64")
    df_m.to_csv(OUT_DIR / "dim_power_plant.csv", index=False, encoding="utf-8-sig")

    df_b = pd.DataFrame(bridge_rows)
    df_b.to_csv(WAREHOUSE_DIR / "pltu_entity_resolution_map.csv", index=False, encoding="utf-8-sig")
    print(f"[dim_power_plant] {len(df_m)} master PLTU (WRI matched={wri_matched}/70, CREA matched={crea_matched}/52)")
    print("  Breakdown match_method:", df_m["entity_match_method"].value_counts().to_dict())
    return df_m, df_b


if __name__ == "__main__":
    build_dim_time()
    build_dim_location()
    build_dim_data_source()
    build_dim_feedstock()
    build_dim_power_plant()
    print("\nSelesai membangun 5 Conformed Dimensions -> warehouse/tables/")
