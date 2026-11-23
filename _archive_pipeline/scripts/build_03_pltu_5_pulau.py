"""
Tahap 4: Tarik & Gabungkan Data PLTU di 5 Pulau Indonesia + Kebutuhan Energi & Batu Bara Harian
Sumber Resmi & Terverifikasi:
1. CREA Indonesia Report (Mei 2025), Lampiran Tabel A1 (hlm. 45-49): 52 PLTU Co-Firing PLN
   (https://energyandcleanair.org/wp/wp-content/uploads/2025/05/ID-IDN-Biomass-co-firing-in-Indonesia.pdf)
2. WRI Global Power Plant Database (GitHub raw CSV): 70 PLTU Batu Bara Indonesia lengkap koordinat lat/lon
   (https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv)

Prinsip Saintis (As-Is):
- Angka RIIL publikasi (kapasitas MW, penggunaan biomassa ton/thn 2024, listrik biomassa MWh/thn 2024)
  DIPISAH TEGAS dari kolom ESTIMASI RUMUS (kebutuhan batu bara harian ton/hari & MWh/hari).
- Nilai yang memang tertulis '-' atau 'N/A' di sumber resmi dibiarkan NULL (NaN) as-is.
"""

import os
import re
import numpy as np
import pandas as pd
import pdfplumber

RAW_DIR = "raw_data"
CREA_PDF = "_archive_pipeline/raw_pdfs/crea_biomass_cofiring_indonesia_2025.pdf"
CREA_URL = "https://energyandcleanair.org/wp/wp-content/uploads/2025/05/ID-IDN-Biomass-co-firing-in-Indonesia.pdf"
WRI_URL = "https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv"

# Parameter teknis standar ketenagalistrikan PLN / ESDM (transparan & terpisah dari data riil)
DEFAULT_CF = 0.75              # Capacity Factor 75% (operasional baseload PLTU 70-80%)
NCV_BATUBARA_KCAL_KG = 4200.0  # GAR/NCV 4.200 kcal/kg (batu bara umum PLTU PLN)
NCV_BATUBARA_GJ_TON = NCV_BATUBARA_KCAL_KG * 4.184 / 1000.0  # ~17.5728 GJ/ton

# SFC (Specific Fuel Consumption, kg batu bara / kWh) berdasarkan jenis boiler (standar PLN/ESDM)
SFC_BY_BOILER = {
    "PC": 0.52,       # Pulverized Coal (unit besar/menengah, efisiensi lebih tinggi)
    "CFB": 0.58,      # Circulating Fluidized Bed (unit menengah/kecil)
    "Stoker": 0.65,   # Stoker (unit kecil <25 MW, efisiensi lebih rendah)
    "DEFAULT": 0.55,  # Rata-rata nasional PLTU PLN (0.47 - 0.65 kg/kWh)
}

# Catatan koreksi nama terjemahan PDF CREA Indonesia agar tidak membingungkan pengguna
CREA_NAME_NOTES = {
    "Pakaian 1-2": "PLTU Ropa 1-2 (terjemahan literal 'Ropa' di PDF CREA)",
    "Jadi Tanasa 1-3": "PLTU Nii Tanasa 1-3 (kendari)",
    "Angka 1-2": "PLTU Suge 1-2 (Belitung)",
    "Dia 1-2": "PLTU Berau / Lati 1-2 (Berau)",
    "Berlawanan 1-2": "PLTU Sebalang 1-2 (Lampung Selatan)",
}


def parse_id_number(val):
    """Parse angka format Indonesia di PDF CREA (titik ribuan, misal '145.302', '2.170***')."""
    if val is None:
        return np.nan
    s = str(val).strip()
    if not s or s in ("-", "N/A", "N/A**", "na"):
        return np.nan
    s = re.sub(r"\*+", "", s).strip()
    if not s or s in ("-", "N/A"):
        return np.nan
    # Jika format 145.302 -> hapus titik ribuan; jika format desimal 16.5 biarkan
    if re.match(r"^\d{1,3}(\.\d{3})+$", s):
        s = s.replace(".", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_unit_capacity_mw(unit_str):
    """Parse '2x400', '3x315', '2x16.5' menjadi (jumlah_unit, mw_per_unit, total_mw)."""
    if not unit_str:
        return np.nan, np.nan, np.nan
    s = str(unit_str).strip().lower().replace(",", ".").replace(" ", "")
    m = re.match(r"^(\d+)x(\d+(?:\.\d+)?)$", s)
    if m:
        n_unit = int(m.group(1))
        mw_unit = float(m.group(2))
        return n_unit, mw_unit, round(n_unit * mw_unit, 2)
    return np.nan, np.nan, np.nan


def map_pulau_from_lokasi(lokasi: str):
    if not isinstance(lokasi, str):
        return "Tidak Diketahui"
    low = lokasi.lower()
    if any(k in low for k in ["jawa", "banten", "jakarta", "yogyakarta", "madura"]):
        return "Jawa"
    if any(k in low for k in ["sumatra", "sumatera", "aceh", "riau", "jambi", "bengkulu", "lampung", "bangka", "belitung", "batam", "kepulauan riau"]):
        return "Sumatera"
    if any(k in low for k in ["kalimantan"]):
        return "Kalimantan"
    if any(k in low for k in ["sulawesi", "gorontalo"]):
        return "Sulawesi"
    if any(k in low for k in ["papua"]):
        return "Papua"
    if any(k in low for k in ["bali", "nusa tenggara", "lombok", "sumbawa", "ende", "kupang"]):
        return "Bali-Nusa Tenggara"
    if any(k in low for k in ["maluku", "tidore", "sofifi", "oba"]):
        return "Maluku"
    return "Lainnya"


def map_pulau_from_coords(lat: float, lon: float, name: str = ""):
    """Pemetaan akurat 5 pulau utama Indonesia dari koordinat (lat, lon) + nama PLTU."""
    low = str(name).lower()
    if any(k in low for k in ["papua", "jayapura", "holtekamp", "amamapare", "timika", "sorong", "manokwari"]):
        return "Papua"
    if any(k in low for k in ["sulawesi", "sulsel", "sulut", "sulteng", "sultra", "gorontalo", "barru", "amurang", "kendari", "jeneponto", "punagaya", "palu", "morowali", "kobe", "makassar", "bau-bau"]):
        return "Sulawesi"
    if any(k in low for k in ["kalimantan", "kaltim", "kalteng", "kalbar", "kalsel", "kaltara", "pulang pisau", "asam-asam", "asam asam", "ketapang", "sanggau", "sintang", "balikpapan", "bontang", "berau", "tarakan", "malinau", "bengkayang", "banjarmasin", "sampit", "pangkalan bun", "tabalong", "tanjung", "adaro", "kutai", "samarinda"]):
        return "Kalimantan"
    if any(k in low for k in ["sumatra", "sumatera", "aceh", "nagan raya", "pangkalan susu", "medan", "belawan", "labuhan angin", "ombilin", "teluk sirih", "tenayan", "riau", "tembilahan", "jambi", "palembang", "bukit asam", "banyuasin", "muara enim", "bengkulu", "lampung", "tarahan", "sebalang", "bangka", "air anyir", "belitung", "batam", "tanjung balai", "bintan", "simbang"]):
        return "Sumatera"
    if any(k in low for k in ["bali", "celukan bawang", "lombok", "jeranjang", "sumbawa", "batu hijau", "kupang", "bolok", "ende", "ropa", "flores", "ntb", "ntt"]):
        return "Bali-Nusa Tenggara"
    if any(k in low for k in ["maluku", "ambon", "tidore", "ternate", "halmahera", "weda", "obi", "sofifi"]):
        return "Maluku"
    if any(k in low for k in ["jawa", "java", "banten", "suralaya", "serang", "lontar", "labuan", "cilegon", "merak", "jakarta", "cikarang", "babelan", "indramayu", "cirebon", "pelabuhan ratu", "cilacap", "adipala", "rembang", "tanjung jati", "batang", "jepara", "pacitan", "paiton", "tuban", "tanjung awar", "gresik", "surabaya", "probolinggo", "karawang", "bekasi", "purwakarta"]):
        return "Jawa"

    # Fallback spasial murni berbasis kotak koordinat kepulauan Indonesia
    if pd.isna(lat) or pd.isna(lon):
        return "Tidak Diketahui"
    if lon >= 130.5:
        return "Papua"
    if lon >= 125.0 and lat > -8.5:
        return "Maluku"
    if 118.2 <= lon < 125.5 and lat > -6.5:
        return "Sulawesi"
    if 108.5 <= lon < 119.5 and lat > -4.5:
        return "Kalimantan"
    if lon < 105.6 or (lon < 108.5 and lat > -5.9):
        return "Sumatera"
    if 105.0 <= lon <= 114.6 and -9.0 <= lat <= -5.5:
        return "Jawa"
    if 114.6 < lon <= 127.5 and lat <= -7.5:
        return "Bali-Nusa Tenggara"
    return "Lainnya"


def extract_crea_52_pltu():
    """Ekstrak seluruh 52 PLTU dari Lampiran Tabel A1 CREA Mei 2025 (hlm. 45-49)."""
    raw_records = []
    current_region_pln = None
    status_group = "OPERASI_COFIRING_2024"

    with pdfplumber.open(CREA_PDF) as pdf:
        for pno in range(44, 49):
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
                        continue
                    # Baris sambungan nama lokasi (seperti "Tengah" untuk Ampana 1-2 di hlm 47)
                    if not c0 and not c1 and c2 and raw_records:
                        raw_records[-1]["lokasi_pdf"] = (raw_records[-1]["lokasi_pdf"] + " " + c2).strip()
                        continue
                    if not re.match(r"^\d+$", c0):
                        continue

                    raw_records.append({
                        "no_crea": int(c0),
                        "nama_pltu_pdf": c1,
                        "lokasi_pdf": c2,
                        "wilayah_pln": current_region_pln,
                        "status_cofiring_2024": status_group,
                        "jenis_boiler": cells[3],
                        "unit_kapasitas_raw": cells[4],
                        "jenis_biomassa_riil": cells[5],
                        "porsi_cofiring_pct_raw": cells[6],
                        "penggunaan_biomassa_2024_ton_riil": parse_id_number(cells[7]),
                        "produksi_listrik_biomassa_2024_mwh_riil": parse_id_number(cells[8]),
                        "emisi_biomassa_2024_tco2_riil": parse_id_number(cells[9]),
                    })

    rows = []
    for r in raw_records:
        pulau = map_pulau_from_lokasi(r["lokasi_pdf"])
        n_unit, mw_unit, total_mw = parse_unit_capacity_mw(r["unit_kapasitas_raw"])
        porsi_pct = parse_id_number(r["porsi_cofiring_pct_raw"])
        sfc = SFC_BY_BOILER.get(r["jenis_boiler"], SFC_BY_BOILER["DEFAULT"])

        # Estimasi kebutuhan listrik & batu bara harian (DIPISAH TEGAS dari data riil)
        est_listrik_mwh_hari = round(total_mw * DEFAULT_CF * 24.0, 2) if pd.notna(total_mw) else np.nan
        est_batubara_ton_hari = round(sfc * total_mw * DEFAULT_CF * 24.0, 2) if pd.notna(total_mw) else np.nan
        est_energi_termal_gj_hari = round(est_batubara_ton_hari * NCV_BATUBARA_GJ_TON, 2) if pd.notna(est_batubara_ton_hari) else np.nan
        riil_biomassa_ton_hari = (
            round(r["penggunaan_biomassa_2024_ton_riil"] / 365.0, 2)
            if pd.notna(r["penggunaan_biomassa_2024_ton_riil"])
            else np.nan
        )

        # Catatan fakta as-is
        notes = []
        if r["nama_pltu_pdf"] in CREA_NAME_NOTES:
            notes.append(f"Nama standar: {CREA_NAME_NOTES[r['nama_pltu_pdf']]}")
        if pd.isna(r["penggunaan_biomassa_2024_ton_riil"]):
            notes.append("Realisasi biomassa 2024 tidak tersedia / '-' di Tabel A1 CREA (NULL as-is)")
        notes.append(
            f"Konsumsi batu bara harian riil tidak dipublikasikan publik PLN; kolom est_* dihitung rumus standar (CF={DEFAULT_CF}, SFC={sfc} kg/kWh untuk boiler {r['jenis_boiler']}, NCV=4200 kcal/kg)"
        )

        rows.append({
            "no_crea": r["no_crea"],
            "nama_pltu": r["nama_pltu_pdf"],
            "nama_pltu_catatan": CREA_NAME_NOTES.get(r["nama_pltu_pdf"], r["nama_pltu_pdf"]),
            "pulau": pulau,
            "masuk_5_pulau_target": pulau in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
            "lokasi_kabkota_prov": r["lokasi_pdf"],
            "wilayah_pln": r["wilayah_pln"],
            "status_cofiring_2024": r["status_cofiring_2024"],
            "jenis_boiler": r["jenis_boiler"],
            "unit_kapasitas_raw": r["unit_kapasitas_raw"],
            "jumlah_unit": n_unit,
            "kapasitas_per_unit_mw": mw_unit,
            "kapasitas_total_mw_riil": total_mw,
            "jenis_biomassa_riil": r["jenis_biomassa_riil"],
            "porsi_cofiring_pct_riil": porsi_pct,
            "penggunaan_biomassa_2024_ton_tahun_riil": r["penggunaan_biomassa_2024_ton_riil"],
            "rata_biomassa_2024_ton_hari_riil": riil_biomassa_ton_hari,
            "listrik_biomassa_2024_mwh_tahun_riil": r["produksi_listrik_biomassa_2024_mwh_riil"],
            "emisi_biomassa_2024_tco2_tahun_riil": r["emisi_biomassa_2024_tco2_riil"],
            # Kolom konsumsi batu bara riil (NULL as-is karena tidak dipublikasikan per unit)
            "konsumsi_batubara_harian_ton_riil": np.nan,
            # Kolom ESTIMASI RUMUS (terpisah jelas)
            "param_cf_default": DEFAULT_CF,
            "param_sfc_kg_kwh": sfc,
            "param_ncv_batubara_kcal_kg": NCV_BATUBARA_KCAL_KG,
            "est_energi_listrik_harian_mwh": est_listrik_mwh_hari,
            "est_kebutuhan_batubara_harian_ton": est_batubara_ton_hari,
            "est_kebutuhan_energi_termal_harian_gj": est_energi_termal_gj_hari,
            "status_data": "TERSEDIA_RIIL_MW_DAN_BIOMASSA_CREA_2025",
            "sumber_url": CREA_URL,
            "catatan_fakta": "; ".join(notes),
        })

    return pd.DataFrame(rows)


def fetch_wri_gppd_indonesia():
    """Tarik seluruh 70 PLTU batu bara Indonesia dari WRI Global Power Plant Database (GitHub)."""
    df_all = pd.read_csv(WRI_URL, low_memory=False)
    coal = df_all[(df_all["country"] == "IDN") & (df_all["primary_fuel"] == "Coal")].copy()

    rows = []
    for _, r in coal.iterrows():
        lat = float(r["latitude"]) if pd.notna(r["latitude"]) else np.nan
        lon = float(r["longitude"]) if pd.notna(r["longitude"]) else np.nan
        mw = float(r["capacity_mw"]) if pd.notna(r["capacity_mw"]) else np.nan
        pulau = map_pulau_from_coords(lat, lon, r["name"])
        sfc = SFC_BY_BOILER["DEFAULT"]

        est_listrik_mwh_hari = round(mw * DEFAULT_CF * 24.0, 2) if pd.notna(mw) else np.nan
        est_batubara_ton_hari = round(sfc * mw * DEFAULT_CF * 24.0, 2) if pd.notna(mw) else np.nan
        est_energi_termal_gj_hari = round(est_batubara_ton_hari * NCV_BATUBARA_GJ_TON, 2) if pd.notna(est_batubara_ton_hari) else np.nan

        rows.append({
            "gppd_idnr": r["gppd_idnr"],
            "nama_pltu": r["name"],
            "pulau": pulau,
            "masuk_5_pulau_target": pulau in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
            "kapasitas_total_mw_riil": mw,
            "latitude": lat,
            "longitude": lon,
            "bahan_bakar_utama": r["primary_fuel"],
            "pemilik": r["owner"] if pd.notna(r["owner"]) else None,
            "tahun_operasi": int(r["commissioning_year"]) if pd.notna(r["commissioning_year"]) else np.nan,
            "estimasi_gwh_tahun_wri": float(r["estimated_generation_gwh_2017"]) if pd.notna(r.get("estimated_generation_gwh_2017")) else np.nan,
            "konsumsi_batubara_harian_ton_riil": np.nan,
            "param_cf_default": DEFAULT_CF,
            "param_sfc_kg_kwh": sfc,
            "param_ncv_batubara_kcal_kg": NCV_BATUBARA_KCAL_KG,
            "est_energi_listrik_harian_mwh": est_listrik_mwh_hari,
            "est_kebutuhan_batubara_harian_ton": est_batubara_ton_hari,
            "est_kebutuhan_energi_termal_harian_gj": est_energi_termal_gj_hari,
            "status_data": "TERSEDIA_WRI_GPPD_KOORDINAT_DAN_MW",
            "sumber_url": str(r["url"]) if pd.notna(r["url"]) else WRI_URL,
            "catatan_fakta": f"Sumber WRI GPPD (sumber asal: {r.get('source', 'WRI')}). Konsumsi batu bara harian riil NULL as-is; kolom est_* adalah hitungan rumus standar (CF={DEFAULT_CF}, SFC={sfc} kg/kWh, NCV=4200 kcal/kg).",
        })

    return pd.DataFrame(rows).sort_values(["pulau", "kapasitas_total_mw_riil"], ascending=[True, False]).reset_index(drop=True)


def build_island_summary(df_crea, df_wri):
    pulau_order = ["Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua", "Bali-Nusa Tenggara", "Maluku"]
    rows = []
    for p in pulau_order:
        gc = df_crea[df_crea["pulau"] == p]
        gw = df_wri[df_wri["pulau"] == p]
        rows.append({
            "pulau": p,
            "masuk_5_pulau_target": p in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
            "jumlah_pltu_crea_52": len(gc),
            "total_mw_crea_52": round(float(gc["kapasitas_total_mw_riil"].sum()), 2),
            "realisasi_biomassa_2024_ton_tahun_crea": round(float(gc["penggunaan_biomassa_2024_ton_tahun_riil"].sum()), 2),
            "est_batubara_harian_ton_crea_52": round(float(gc["est_kebutuhan_batubara_harian_ton"].sum()), 2),
            "est_listrik_harian_mwh_crea_52": round(float(gc["est_energi_listrik_harian_mwh"].sum()), 2),
            "jumlah_pltu_wri_gppd": len(gw),
            "total_mw_wri_gppd": round(float(gw["kapasitas_total_mw_riil"].sum()), 2),
            "est_batubara_harian_ton_wri_gppd": round(float(gw["est_kebutuhan_batubara_harian_ton"].sum()), 2),
            "est_listrik_harian_mwh_wri_gppd": round(float(gw["est_energi_listrik_harian_mwh"].sum()), 2),
        })
    return pd.DataFrame(rows)


def main():
    print("Mengekstrak 52 PLTU Co-Firing PLN dari PDF CREA Mei 2025...")
    df_crea = extract_crea_52_pltu()
    print(f"  CREA 52 PLTU extracted: {len(df_crea)} rows, Total MW: {df_crea['kapasitas_total_mw_riil'].sum():,.1f} MW")

    print("Mengunduh 70 PLTU Indonesia dari WRI Global Power Plant Database...")
    df_wri = fetch_wri_gppd_indonesia()
    print(f"  WRI GPPD Coal extracted: {len(df_wri)} rows, Total MW: {df_wri['kapasitas_total_mw_riil'].sum():,.1f} MW")

    df_summary = build_island_summary(df_crea, df_wri)

    out_xlsx = os.path.join(RAW_DIR, "03_data_pltu_5_pulau_batubara_harian.xlsx")
    out_csv_crea = os.path.join(RAW_DIR, "03_data_pltu_5_pulau_batubara_harian.csv")
    out_csv_wri = os.path.join(RAW_DIR, "03b_data_pltu_wri_gppd_koordinat.csv")

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="ringkasan_5_pulau", index=False)
        df_crea.to_excel(writer, sheet_name="pltu_52_cofiring_crea_2025", index=False)
        df_wri.to_excel(writer, sheet_name="pltu_70_wri_gppd_koordinat", index=False)

    df_crea.to_csv(out_csv_crea, index=False)
    df_wri.to_csv(out_csv_wri, index=False)

    print("\n=== RINGKASAN PLTU PER PULAU ===")
    print(df_summary.to_string(index=False))
    print(f"\nDisimpan ke: {out_xlsx} (3 sheets), {out_csv_crea}, {out_csv_wri}")


if __name__ == "__main__":
    main()
