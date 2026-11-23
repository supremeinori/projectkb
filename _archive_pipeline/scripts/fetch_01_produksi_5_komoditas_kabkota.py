"""
Tahap 2: Tarik Data Produksi 5 Komoditas per Kabupaten/Kota (38 Provinsi Indonesia)
Sumber Resmi & Terverifikasi:
1. BDSP Kementerian Pertanian (https://bdsp2.pertanian.go.id/bdsp/id/lokasi)
   - Padi (01059): Level Kabupaten/Kota, 2020-2024 (Angka Tetap sts_angka=6)
   - Kelapa Sawit (02027): Level Kabupaten/Kota, 2020-2024 (Angka Tetap sts_angka=6)
   - Tebu (02051): Level Kabupaten/Kota, 2020-2024 (Angka Tetap sts_angka=6)
   - Jagung (01027): Level Kabupaten/Kota, 2015-2017 (Angka Tetap sts_angka=6; 2018-2024 tidak tersedia di BDSP as-is)
2. BPS RI (raw_data/01_bps_produksi_pertanian_kehutanan.csv — hasil scrape resmi tabel BPS 1498#2, 2204#2, 2566#2, 2512#2, 1973#2)
   - Pelengkap resmi level Provinsi 2024 (termasuk Jagung KSA 2024 & 4 provinsi pemekaran Papua)
   - Data Kayu Bulat Nasional 2023 (Tabel 2512#2) & per Pulau 2022 (Tabel 1973#2)

Prinsip Saintis (As-Is):
- Tidak ada angka dummy atau pemecahan buatan dari provinsi ke Kab/Kota.
- Setiap provinsi x komoditas yang tidak ditemukan di level Kab/Kota dicatat jujur pada sheet
  `status_ketersediaan_38_provinsi` dan kolom `status_data`, `sumber_url`, `catatan_fakta`.
- Kolom `produksi_utama_ton_riil` dipisah tegas dari `est_potensi_limbah_ton` (hitung RPR resmi).
"""

import os
import re
import time
import numpy as np
import pandas as pd
import requests

RAW_DIR = "raw_data"
BDSP_BASE = "https://bdsp2.pertanian.go.id/bdsp/id"
BDSP_URL_LOKASI = f"{BDSP_BASE}/lokasi"
BDSP_URL_RESULT = f"{BDSP_BASE}/lokasi/result"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Mapping kode provinsi BDSP (2 digit) -> Pulau
PROV_TO_PULAU = {
    "11": "Sumatera", "12": "Sumatera", "13": "Sumatera", "14": "Sumatera", "15": "Sumatera",
    "16": "Sumatera", "17": "Sumatera", "18": "Sumatera", "19": "Sumatera", "21": "Sumatera",
    "31": "Jawa", "32": "Jawa", "33": "Jawa", "34": "Jawa", "35": "Jawa", "36": "Jawa",
    "51": "Bali-Nusra-Maluku", "52": "Bali-Nusra-Maluku", "53": "Bali-Nusra-Maluku",
    "61": "Kalimantan", "62": "Kalimantan", "63": "Kalimantan", "64": "Kalimantan", "65": "Kalimantan",
    "71": "Sulawesi", "72": "Sulawesi", "73": "Sulawesi", "74": "Sulawesi", "75": "Sulawesi", "76": "Sulawesi",
    "81": "Bali-Nusra-Maluku", "82": "Bali-Nusra-Maluku",
    "91": "Papua", "92": "Papua", "94": "Papua", "95": "Papua", "96": "Papua", "97": "Papua",
}

# Target komoditas BDSP
BDSP_TARGETS = [
    {
        "komoditas_std": "padi",
        "limbah_target": "sekam_padi",
        "rpr": 0.20,
        "subsektorcd": "01",
        "subsektornm": "Tanaman Pangan",
        "komcd": "01059",
        "komnm": "PADI",
        "indicd": "0104",
        "tahun_awal": "2020",
        "tahun_akhir": "2024",
    },
    {
        "komoditas_std": "kelapa_sawit",
        "limbah_target": "limbah_sawit_cangkang_serat_tkks",
        "rpr": 0.42,  # 0.065 cangkang + 0.135 serat + 0.22 TKKS
        "subsektorcd": "02",
        "subsektornm": "Perkebunan",
        "komcd": "02027",
        "komnm": "KELAPA SAWIT",
        "indicd": "0205",
        "tahun_awal": "2020",
        "tahun_akhir": "2024",
    },
    {
        "komoditas_std": "tebu",
        "limbah_target": "ampas_tebu",
        "rpr": 0.30,
        "subsektorcd": "02",
        "subsektornm": "Perkebunan",
        "komcd": "02051",
        "komnm": "TEBU",
        "indicd": "0205",
        "tahun_awal": "2020",
        "tahun_akhir": "2024",
    },
    {
        "komoditas_std": "jagung",
        "limbah_target": "bonggol_jagung",
        "rpr": 0.28,
        "subsektorcd": "01",
        "subsektornm": "Tanaman Pangan",
        "komcd": "01027",
        "komnm": "JAGUNG",
        "indicd": "0104",
        "tahun_awal": "2015",
        "tahun_akhir": "2017",
    },
]


def parse_bdsp_float(val: str):
    if val is None:
        return np.nan
    s = str(val).strip()
    if not s or s == "-":
        return np.nan
    # BDSP format: '379244,91' (comma decimal, no thousand separator) or '1.234,56'
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_bdsp_html_table(html: str):
    """Parse HTML table dari lokasi/result -> (years_list, list of (kode_kab, nama_kab, {year: float}))."""
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    if len(rows) < 2:
        return [], []

    header_cells = [
        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
        for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rows[0], re.S | re.I)
    ]
    years = [int(c) for c in header_cells[2:] if re.match(r"^\d{4}$", c)]
    if not years:
        return [], []

    data = []
    for tr in rows[1:]:
        cells = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
            for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)
        ]
        if len(cells) < 2 + len(years):
            continue
        loc = cells[1]
        if not loc or "jumlah" in loc.lower() or "total" in loc.lower():
            continue
        m = re.match(r"^(\d+)\s*-\s*(.+)$", loc)
        if m:
            kode_kab, nama_kab = m.group(1).strip(), m.group(2).strip()
        else:
            kode_kab, nama_kab = "", loc
        vals = {}
        for idx, yr in enumerate(years):
            vals[yr] = parse_bdsp_float(cells[2 + idx])
        data.append((kode_kab, nama_kab, vals))
    return years, data


def normalize_prov_name(s: str) -> str:
    s = str(s).strip().upper()
    s = re.sub(r"^PROVINSI\s+", "", s)
    s = s.replace("KEP. ", "KEPULAUAN ").replace("D.I. ", "DI ").replace("DKI ", "DKI ")
    return s


def main():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get(BDSP_URL_LOKASI, timeout=20)

    provs = s.get(f"{BDSP_BASE}/lokasi/getProv", timeout=20).json()
    print(f"Mengambil data Kab/Kota dari BDSP Kementan untuk {len(provs)} provinsi x {len(BDSP_TARGETS)} komoditas...")

    # Load BPS provincial 2024 backup (for Jagung 2024, Kayu, and cross-check of 4 new Papua provinces)
    bps_prov_path = os.path.join(RAW_DIR, "01_bps_produksi_pertanian_kehutanan.csv")
    df_bps_prov = pd.read_csv(bps_prov_path) if os.path.exists(bps_prov_path) else pd.DataFrame()
    if not df_bps_prov.empty:
        df_bps_prov["prov_norm"] = df_bps_prov["provinsi"].apply(normalize_prov_name)

    all_kabkota_rows = []
    availability_rows = []

    for p in provs:
        p_code = str(p["fkode_prop"]).strip()
        p_name = str(p["nama_prop"]).strip()
        p_norm = normalize_prov_name(p_name)
        pulau = PROV_TO_PULAU.get(p_code, "Lainnya")

        avail_entry = {
            "kode_prov": p_code,
            "provinsi": p_name,
            "pulau": pulau,
            "masuk_5_pulau_target": pulau in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
        }

        for tgt in BDSP_TARGETS:
            kom_std = tgt["komoditas_std"]
            payload = {
                "subsektor": tgt["subsektorcd"],
                "subsektorcd": tgt["subsektorcd"],
                "subsektornm": tgt["subsektornm"],
                "komoditas": tgt["komcd"],
                "komoditasnm": tgt["komnm"],
                "indikator": tgt["indicd"],
                "indikatornm": "PRODUKSI",
                "level": "03",
                "levelnm": "Kabupaten",
                "prov": p_code,
                "provnm": p_name,
                "kab": "00",
                "kabnm": "-- Pilih Kabupaten --",
                "satuan": "20",
                "satuannm": "Ton",
                "sts_angka": "6",  # Angka Tetap
                "sts_angkanm": "Angka Tetap",
                "sumb_data": "01",
                "sumb_datanm": "Kementerian Pertanian",
                "tahunAwal": tgt["tahun_awal"],
                "tahunAkhir": tgt["tahun_akhir"],
            }
            try:
                rr = s.post(BDSP_URL_RESULT, data=payload, timeout=25)
                years, table_data = parse_bdsp_html_table(rr.text)
            except Exception as e:
                years, table_data = [], []
                print(f"  [ERR] {p_name} - {kom_std}: {e}")

            # Check latest year with non-zero production in this province
            nonzero_years = []
            for yr in years:
                tot_yr = sum(v.get(yr, 0.0) for _, _, v in table_data if pd.notna(v.get(yr)) and v.get(yr) > 0)
                if tot_yr > 0:
                    nonzero_years.append(yr)

            if nonzero_years:
                latest_yr = max(nonzero_years)
                n_kab_total = len(table_data)
                n_kab_pos = sum(1 for _, _, v in table_data if pd.notna(v.get(latest_yr)) and v.get(latest_yr) > 0)

                for kode_kab, nama_kab, v_dict in table_data:
                    for yr in nonzero_years:
                        val = v_dict.get(yr, np.nan)
                        # Simpan as-is (jika 0.00 di tahun aktif provinsi, tetap tampil 0.00 sesuai BDSP)
                        est_limbah = round(val * tgt["rpr"], 2) if pd.notna(val) else np.nan
                        note = (
                            f"BDSP Kementan (Angka Tetap, kode {tgt['komcd']}); "
                            + (
                                "Catatan: data Jagung Kab/Kota di BDSP berhenti di 2017 (2018-2024 tidak tersedia di BDSP as-is; lihat baris BPS Provinsi 2024)"
                                if kom_std == "jagung"
                                else "Data resmi tingkat Kabupaten/Kota"
                            )
                        )
                        all_kabkota_rows.append({
                            "kode_prov": p_code,
                            "provinsi": p_name,
                            "pulau": pulau,
                            "masuk_5_pulau_target": pulau in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
                            "kode_kabkota": kode_kab,
                            "kabupaten_kota": nama_kab,
                            "level_wilayah": "KABKOTA",
                            "tahun": yr,
                            "is_tahun_terbaru_kabkota": (yr == latest_yr),
                            "komoditas": kom_std,
                            "limbah_target": tgt["limbah_target"],
                            "produksi_utama_ton_riil": val,
                            "rpr_resmi": tgt["rpr"],
                            "est_potensi_limbah_ton": est_limbah,
                            "status_data": "TERSEDIA_KABKOTA",
                            "sumber_data": "BDSP Kementerian Pertanian (Angka Tetap)",
                            "sumber_url": BDSP_URL_LOKASI,
                            "catatan_fakta": note,
                        })

                avail_entry[f"{kom_std}_status"] = f"TERSEDIA_KABKOTA ({min(nonzero_years)}-{latest_yr}, {n_kab_pos}/{n_kab_total} kab/kota > 0)"
            else:
                # Tidak ada data Kab/Kota non-nol di BDSP -> cek apakah ada di BPS Provinsi 2024
                bps_match = pd.DataFrame()
                if not df_bps_prov.empty:
                    bps_match = df_bps_prov[
                        (df_bps_prov["prov_norm"] == p_norm)
                        & (df_bps_prov["komoditas"] == kom_std)
                        & (df_bps_prov["produksi_ton"] > 0)
                    ].sort_values("tahun", ascending=False)

                if not bps_match.empty:
                    r_bps = bps_match.iloc[0]
                    val_bps = float(r_bps["produksi_ton"])
                    yr_bps = int(r_bps["tahun"])
                    all_kabkota_rows.append({
                        "kode_prov": p_code,
                        "provinsi": p_name,
                        "pulau": pulau,
                        "masuk_5_pulau_target": pulau in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
                        "kode_kabkota": None,
                        "kabupaten_kota": None,
                        "level_wilayah": "PROVINSI",
                        "tahun": yr_bps,
                        "is_tahun_terbaru_kabkota": False,
                        "komoditas": kom_std,
                        "limbah_target": tgt["limbah_target"],
                        "produksi_utama_ton_riil": val_bps,
                        "rpr_resmi": tgt["rpr"],
                        "est_potensi_limbah_ton": round(val_bps * tgt["rpr"], 2),
                        "status_data": "HANYA_TINGKAT_PROVINSI",
                        "sumber_data": f"BPS RI ({r_bps['sumber_bps']})",
                        "sumber_url": "https://www.bps.go.id/id/statistics-table",
                        "catatan_fakta": f"Tidak tersedia per Kab/Kota di BDSP Kementan ({tgt['tahun_awal']}-{tgt['tahun_akhir']} bernilai 0,00 as-is); ditampilkan agregat tingkat PROVINSI resmi BPS tahun {yr_bps} tanpa dipecah buatan.",
                    })
                    avail_entry[f"{kom_std}_status"] = f"HANYA_TINGKAT_PROVINSI (BPS {yr_bps}; BDSP Kab/Kota kosong)"
                else:
                    # Benar-benar tidak tersedia / tidak ada produksi di kedua sumber -> catat NULL as-is!
                    all_kabkota_rows.append({
                        "kode_prov": p_code,
                        "provinsi": p_name,
                        "pulau": pulau,
                        "masuk_5_pulau_target": pulau in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
                        "kode_kabkota": None,
                        "kabupaten_kota": None,
                        "level_wilayah": "TIDAK_TERSEDIA",
                        "tahun": np.nan,
                        "is_tahun_terbaru_kabkota": False,
                        "komoditas": kom_std,
                        "limbah_target": tgt["limbah_target"],
                        "produksi_utama_ton_riil": np.nan,
                        "rpr_resmi": tgt["rpr"],
                        "est_potensi_limbah_ton": np.nan,
                        "status_data": "TIDAK_TERSEDIA_DI_PORTAL",
                        "sumber_data": "BDSP Kementan & BPS RI",
                        "sumber_url": BDSP_URL_LOKASI,
                        "catatan_fakta": f"Tidak ditemukan data produksi > 0 untuk {kom_std} di BDSP Kementan ({tgt['tahun_awal']}-{tgt['tahun_akhir']}) maupun BPS Provinsi (kemungkinan memang bukan penghasil komoditas ini atau tidak dipublikasikan; NULL as-is).",
                    })
                    avail_entry[f"{kom_std}_status"] = "TIDAK_TERSEDIA_DI_PORTAL (NULL as-is)"

            time.sleep(0.15)  # Polite delay

        # Tambahan: untuk JAGUNG, tambahkan pula baris referensi resmi BPS Provinsi 2024 (karena BDSP Kab/Kota terakhir 2017)
        if not df_bps_prov.empty:
            jag_2024 = df_bps_prov[
                (df_bps_prov["prov_norm"] == p_norm)
                & (df_bps_prov["komoditas"] == "jagung")
                & (df_bps_prov["tahun"] == 2024)
            ]
            if not jag_2024.empty and avail_entry["jagung_status"].startswith("TERSEDIA_KABKOTA"):
                val_j = float(jag_2024.iloc[0]["produksi_ton"])
                all_kabkota_rows.append({
                    "kode_prov": p_code,
                    "provinsi": p_name,
                    "pulau": pulau,
                    "masuk_5_pulau_target": pulau in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
                    "kode_kabkota": None,
                    "kabupaten_kota": None,
                    "level_wilayah": "PROVINSI",
                    "tahun": 2024,
                    "is_tahun_terbaru_kabkota": False,
                    "komoditas": "jagung",
                    "limbah_target": "bonggol_jagung",
                    "produksi_utama_ton_riil": val_j,
                    "rpr_resmi": 0.28,
                    "est_potensi_limbah_ton": round(val_j * 0.28, 2),
                    "status_data": "HANYA_TINGKAT_PROVINSI",
                    "sumber_data": "BPS RI (bps_table_2204 KSA Jagung 2024)",
                    "sumber_url": "https://www.bps.go.id/id/statistics-table/2/MjIwNCMy/table.html",
                    "catatan_fakta": "Referensi resmi Jagung KSA 2024 tingkat Provinsi dari BPS Pusat (data Kab/Kota 2024 belum tersedia di BDSP Kementan; tidak dipecah buatan).",
                })

        # KAYU BULAT: belum tersedia per Kab/Kota nasional seragam -> catat jujur as-is di matriks 38 provinsi
        avail_entry["kayu_bulat_status"] = "HANYA_TINGKAT_PULAU_DAN_NASIONAL (BPS 1973#2 & 2512#2; tidak tersedia seragam per Kab/Kota)"

        availability_rows.append(avail_entry)
        print(
            f"  [{p_code}] {p_name:<25} | Padi: {avail_entry['padi_status'][:22]:<22} | "
            f"Sawit: {avail_entry['kelapa_sawit_status'][:22]:<22} | "
            f"Tebu: {avail_entry['tebu_status'][:22]:<22} | "
            f"Jagung: {avail_entry['jagung_status'][:22]}"
        )

    # Tambahkan baris resmi KAYU BULAT (Nasional 2023 & Pulau 2022) dari BPS Tabel 2512#2 & 1973#2 (as-is, tanpa pecah buatan)
    if not df_bps_prov.empty:
        kayu_df = df_bps_prov[df_bps_prov["komoditas"].isin(["kayu_bulat", "kayu_bakar"])]
        for _, r in kayu_df.iterrows():
            prov_lbl = str(r["provinsi"])
            pulau_k = (
                "Sumatera" if "SUMATERA" in prov_lbl else
                "Jawa" if "JAWA" in prov_lbl else
                "Kalimantan" if "KALIMANTAN" in prov_lbl else
                "Papua" if "PAPUA" in prov_lbl else
                "Sulawesi" if "SULAWESI" in prov_lbl else
                "Nasional"
            )
            rpr_k = 0.25 if r["komoditas"] == "kayu_bulat" else 1.0
            val_k = float(r["produksi_ton"])
            url_k = (
                "https://www.bps.go.id/id/statistics-table/2/MjUxMiMy/table.html"
                if "2512" in str(r["sumber_bps"])
                else "https://www.bps.go.id/id/statistics-table/2/MTk3MyMy/table.html"
            )
            all_kabkota_rows.append({
                "kode_prov": None,
                "provinsi": prov_lbl,
                "pulau": pulau_k,
                "masuk_5_pulau_target": pulau_k in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
                "kode_kabkota": None,
                "kabupaten_kota": None,
                "level_wilayah": "PULAU" if str(r["wilayah"]) == "ISLAND_TOTAL" else "NASIONAL",
                "tahun": int(r["tahun"]),
                "is_tahun_terbaru_kabkota": False,
                "komoditas": r["komoditas"],
                "limbah_target": "serpihan_kayu_bulat" if r["komoditas"] == "kayu_bulat" else "kayu_bakar",
                "produksi_utama_ton_riil": val_k,
                "rpr_resmi": rpr_k,
                "est_potensi_limbah_ton": round(val_k * rpr_k, 2),
                "status_data": "HANYA_TINGKAT_PULAU_ATAU_NASIONAL",
                "sumber_data": f"BPS RI ({r['sumber_bps']})",
                "sumber_url": url_k,
                "catatan_fakta": "Produksi kayu bulat resmi BPS (konversi m3 x 0,70 ton/m3; kayu bakar SM x 0,50). Data kayu bulat tidak dipublikasikan seragam per Kab/Kota di BDSP; ditampilkan as-is di level Pulau/Nasional tanpa dipecah buatan.",
            })

    df_all = pd.DataFrame(all_kabkota_rows)
    df_avail = pd.DataFrame(availability_rows)

    # Ringkasan tahun terbaru per Kab/Kota (agar langsung enak dipakai di tabel/Power BI tanpa duplikasi multi-tahun)
    df_latest_kabkota = df_all[
        (df_all["level_wilayah"] == "KABKOTA") & (df_all["is_tahun_terbaru_kabkota"] == True)
    ].copy()

    out_xlsx = os.path.join(RAW_DIR, "01_produksi_5_komoditas_per_kabkota.xlsx")
    out_csv = os.path.join(RAW_DIR, "01_produksi_5_komoditas_per_kabkota.csv")
    out_avail_csv = os.path.join(RAW_DIR, "01b_status_ketersediaan_38_provinsi.csv")

    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df_avail.to_excel(writer, sheet_name="status_ketersediaan_38_prov", index=False)
        df_latest_kabkota.to_excel(writer, sheet_name="kabkota_tahun_terbaru", index=False)
        df_all.to_excel(writer, sheet_name="semua_data_multi_tahun_as_is", index=False)

    df_all.to_csv(out_csv, index=False)
    df_avail.to_csv(out_avail_csv, index=False)

    print("\n=== TAHAP 2 SELESAI ===")
    print(f"Total baris semua_data_multi_tahun_as_is : {len(df_all):,}")
    print(f"Total baris kabkota_tahun_terbaru        : {len(df_latest_kabkota):,}")
    print("\nBreakdown by komoditas & level_wilayah:")
    print(df_all.groupby(["komoditas", "level_wilayah", "status_data"]).size().to_string())
    print(f"\nDisimpan ke: {out_xlsx} (3 sheets), {out_csv}, {out_avail_csv}")


if __name__ == "__main__":
    main()
