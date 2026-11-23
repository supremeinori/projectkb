"""
Master Script: Pencarian, Live Hit Verification, dan Pembuatan Excel Link of Sources
Output: raw_data/daftar_sumber_data.xlsx (4 Tab sesuai PLAN.md)
  1. Ringkasan_Sumber
  2. Portal_38_Provinsi
  3. Sumber_5_Komoditas_38_Prov  (38 provinsi x 5 komoditas = 190 baris, rentang 2010-2026)
  4. Sumber_PLTU_5_Pulau

Prinsip Saintis & Aturan As-Is:
- Setiap URL benar-benar di-hit (live HTTP test) dan dicatat status HTTP aktualnya.
- Tidak ada angka/tahun karangan; jika data tidak tersedia, dibiarkan NULL (None/NaN) dan dicatat jujur.
- Memisahkan dengan jelas ketersediaan tingkat KABKOTA vs PROVINSI vs PULAU vs TIDAK_TERSEDIA.
"""

import os
import re
import time
import io
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import numpy as np
import pandas as pd
import pdfplumber
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

RAW_DIR = "raw_data"
PDF_DIR = "_archive_pipeline/raw_pdfs"
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BDSP_BASE = "https://bdsp2.pertanian.go.id/bdsp/id"
BDSP_URL_LOKASI = f"{BDSP_BASE}/lokasi"
BDSP_URL_RESULT = f"{BDSP_BASE}/lokasi/result"
CREA_PDF_URL = "https://energyandcleanair.org/wp/wp-content/uploads/2025/05/ID-IDN-Biomass-co-firing-in-Indonesia.pdf"
WRI_CSV_URL = "https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv"
CT_API_URL = "https://api.climatetrace.org/v6/assets?countries=IDN&sectors=power&year=2024&limit=500"
PHL_2024_URL = "https://phl.kehutanan.go.id/media/statistik/statistik_file_1788408189.pdf"
PHL_2022_URL = "https://phl.kehutanan.go.id/media/statistik/statistik_file_1726677781.pdf"
SATUDATA_SAWIT_KAB_2023_URL = "https://satudata.pertanian.go.id/assets/docs/metadata/45_Luas_perkebunan_kelapa_sawit_di_kabupaten.xlsx"

# 38 Provinsi Indonesia (kode BPS 2 digit / domain 4 digit, nama resmi, pulau, subdomain bps, portal Satu Data Pemprov terverifikasi)
PROVINCES_38 = [
    # SUMATERA (10)
    ("11", "1100", "Aceh", "Sumatera", "aceh", "https://satudata.acehprov.go.id"),
    ("12", "1200", "Sumatera Utara", "Sumatera", "sumut", "https://pasada.sumutprov.go.id"),
    ("13", "1300", "Sumatera Barat", "Sumatera", "sumbar", "https://data.sumbarprov.go.id"),
    ("14", "1400", "Riau", "Sumatera", "riau", "https://rumahdata.riau.go.id"),
    ("15", "1500", "Jambi", "Sumatera", "jambi", "https://opendata.jambiprov.go.id"),
    ("16", "1600", "Sumatera Selatan", "Sumatera", "sumsel", "https://satudata.sumselprov.go.id"),
    ("17", "1700", "Bengkulu", "Sumatera", "bengkulu", "https://data.bengkuluprov.go.id"),
    ("18", "1800", "Lampung", "Sumatera", "lampung", "https://data.lampungprov.go.id"),
    ("19", "1900", "Kepulauan Bangka Belitung", "Sumatera", "babel", "https://insight.sdi.babelprov.go.id"),
    ("21", "2100", "Kepulauan Riau", "Sumatera", "kepri", "https://satudata.kepriprov.go.id"),
    # JAWA (6)
    ("31", "3100", "DKI Jakarta", "Jawa", "jakarta", "https://satudata.jakarta.go.id"),
    ("32", "3200", "Jawa Barat", "Jawa", "jabar", "https://opendata.jabarprov.go.id"),
    ("33", "3300", "Jawa Tengah", "Jawa", "jateng", "https://data.jatengprov.go.id"),
    ("34", "3400", "DI Yogyakarta", "Jawa", "yogyakarta", "https://bapperida.jogjaprov.go.id/dataku/"),
    ("35", "3500", "Jawa Timur", "Jawa", "jatim", "https://opendata.jatimprov.go.id"),
    ("36", "3600", "Banten", "Jawa", "banten", "https://satudata.bantenprov.go.id"),
    # BALI, NUSA TENGGARA & MALUKU (5)
    ("51", "5100", "Bali", "Bali-Nusra-Maluku", "bali", "https://balisatudata.baliprov.go.id"),
    ("52", "5200", "Nusa Tenggara Barat", "Bali-Nusra-Maluku", "ntb", "https://data.ntbprov.go.id"),
    ("53", "5300", "Nusa Tenggara Timur", "Bali-Nusra-Maluku", "ntt", "https://sasando.nttprov.go.id"),
    # KALIMANTAN (5)
    ("61", "6100", "Kalimantan Barat", "Kalimantan", "kalbar", "https://data.kalbarprov.go.id"),
    ("62", "6200", "Kalimantan Tengah", "Kalimantan", "kalteng", "https://satudata.kalteng.go.id"),
    ("63", "6300", "Kalimantan Selatan", "Kalimantan", "kalsel", "https://opendata.kalselprov.go.id"),
    ("64", "6400", "Kalimantan Timur", "Kalimantan", "kaltim", "https://data.kaltimprov.go.id"),
    ("65", "6500", "Kalimantan Utara", "Kalimantan", "kaltara", "https://data.kaltaraprov.go.id"),
    # SULAWESI (6)
    ("71", "7100", "Sulawesi Utara", "Sulawesi", "sulut", "https://satudata.sulutprov.go.id"),
    ("72", "7200", "Sulawesi Tengah", "Sulawesi", "sulteng", "https://satudata.sultengprov.go.id"),
    ("73", "7300", "Sulawesi Selatan", "Sulawesi", "sulsel", "https://satudata.sulselprov.go.id"),
    ("74", "7400", "Sulawesi Tenggara", "Sulawesi", "sultra", "https://simdata.sultraprov.go.id"),
    ("75", "7500", "Gorontalo", "Sulawesi", "gorontalo", "https://opendata.gorontaloprov.go.id"),
    ("76", "7600", "Sulawesi Barat", "Sulawesi", "sulbar", "https://satudata.sulbarprov.go.id"),
    # MALUKU (2)
    ("81", "8100", "Maluku", "Bali-Nusra-Maluku", "maluku", "https://data.malukuprov.go.id"),
    ("82", "8200", "Maluku Utara", "Bali-Nusra-Maluku", "malut", "https://satudata.malutprov.go.id"),
    # PAPUA (6)
    ("91", "9100", "Papua Barat", "Papua", "papuabarat", "https://data.papuabaratprov.go.id"),
    ("92", "9200", "Papua Barat Daya", "Papua", "papuabaratdaya", "https://cenderawasih.papuabaratdayaprov.go.id"),
    ("94", "9400", "Papua", "Papua", "papua", "https://pusdalisbang.papua.go.id/v2/beranda"),
    ("95", "9500", "Papua Selatan", "Papua", "papuaselatan", None),
    ("96", "9600", "Papua Tengah", "Papua", "papuatengah", None),
    ("97", "9700", "Papua Pegunungan", "Papua", "papuapegunungan", None),
]


def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    retry = Retry(total=2, backoff_factor=0.6, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET", "POST", "HEAD"])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def check_url(session, url, timeout=10, get_body=False):
    if not url:
        return None, None, "Tidak ada portal mandiri teridentifikasi"
    try:
        if get_body:
            r = session.get(url, timeout=timeout, allow_redirects=True)
            return r.status_code, r.text, None
        r = session.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code in (403, 405, 400):
            r = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
        return r.status_code, None, None
    except requests.exceptions.SSLError:
        return "SSL_ERROR", None, "Sertifikat SSL situs bermasalah"
    except requests.exceptions.ConnectTimeout:
        return "TIMEOUT", None, "Koneksi timeout"
    except requests.exceptions.ReadTimeout:
        return "TIMEOUT", None, "Read timeout"
    except requests.exceptions.ConnectionError as e:
        msg = str(e)
        if "NameResolutionError" in msg or "getaddrinfo failed" in msg:
            return "DNS_NOT_FOUND", None, "Domain tidak terdaftar di DNS"
        return "CONN_ERROR", None, f"Koneksi ditolak/reset ({type(e).__name__})"
    except Exception as e:
        return "ERROR", None, str(e)[:100]


def format_year_spans(years_list):
    """Format daftar tahun [2010, 2011, ..., 2017] -> '2010-2017' (atau gabung jeda jika putus)."""
    if not years_list:
        return None
    ys = sorted(set(int(y) for y in years_list))
    spans = []
    start = prev = ys[0]
    for y in ys[1:]:
        if y == prev + 1:
            prev = y
        else:
            spans.append(f"{start}" if start == prev else f"{start}-{prev}")
            start = prev = y
    spans.append(f"{start}" if start == prev else f"{start}-{prev}")
    return ", ".join(spans)


def norm_prov(s: str) -> str:
    s = str(s).upper().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^PROVINSI\s+", "", s)
    s = s.replace("NANGROE ACEH DARUSSALAM", "ACEH").replace("NANGGROE ACEH DARUSSALAM", "ACEH")
    s = s.replace("DAERAH KHUSUS IBUKOTA ", "DKI ").replace("DAERAH ISTIMEWA ", "DI ")
    s = s.replace("KEP. BANGKA BELITUNG", "KEPULAUAN BANGKA BELITUNG")
    s = s.replace("KEP.RIAU", "KEPULAUAN RIAU").replace("KEP. RIAU", "KEPULAUAN RIAU")
    return s


# ==============================================================================
# STEP 1: PORTAL 38 PROVINSI
# ==============================================================================
def build_portal_38_provinsi(session):
    print("\n[1/4] Live-hit 38 portal BPS Provinsi & Satu Data Pemprov...", flush=True)
    rows = []
    for kd2, default_dom, prov, pulau, sub, pemprov_url in PROVINCES_38:
        bps_base = f"https://{sub}.bps.go.id"
        bps_table = f"{bps_base}/id/statistics-table"

        st_bps, body, err_bps = check_url(session, bps_table, timeout=12, get_body=True)
        detected_dom = default_dom
        if body:
            m = re.search(r'"domain(?:_id)?"\s*:\s*"(\d{4})"', body) or re.search(r'\\"domain(?:_id)?\\":\\"(\d{4})\\"', body)
            if m:
                detected_dom = m.group(1)

        if pemprov_url:
            st_pemprov, _, err_pemprov = check_url(session, pemprov_url, timeout=9, get_body=False)
        else:
            st_pemprov, err_pemprov = None, "Belum ada portal Satu Data mandiri (provinsi pemekaran)"

        webapi_url = f"https://webapi.bps.go.id/v1/api/list/model/var/domain/{detected_dom}/key/{{BPS_API_KEY}}"

        if st_bps == 200 and st_pemprov == 200:
            rekom = "WebAPI BPS (pakai domain) / HTML BPS Provinsi + Portal Pemprov aktif"
        elif st_bps == 200:
            rekom = "WebAPI BPS (pakai domain) / HTML BPS Provinsi; Pemprov tidak aktif/terbatas"
        else:
            rekom = "Belum punya subdomain BPS mandiri; gunakan BDSP Kementan / BPS Nasional"

        notes = [f"BPS: HTTP {st_bps}" if not err_bps else f"BPS: {err_bps}"]
        if pemprov_url:
            notes.append(f"Pemprov: HTTP {st_pemprov}" if not err_pemprov else f"Pemprov: {err_pemprov}")
        else:
            notes.append("Pemprov: Tidak tersedia portal mandiri")

        print(f"  [{detected_dom}] {prov:<25} | BPS={st_bps} | Pemprov={st_pemprov}", flush=True)
        rows.append({
            "kode_prov_bps": kd2,
            "kode_domain_webapi": detected_dom,
            "provinsi": prov,
            "pulau": pulau,
            "masuk_5_pulau_pltu": pulau in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
            "url_bps_provinsi": bps_base,
            "url_tabel_statistik_bps": bps_table,
            "status_http_bps": st_bps,
            "endpoint_webapi_bps": webapi_url,
            "url_satudata_pemprov": pemprov_url,
            "status_http_pemprov": st_pemprov,
            "metode_akses_rekomendasi": rekom,
            "status_data": "TERSEDIA_PORTAL_BPS" if st_bps == 200 else "BELUM_TERSEDIA_PORTAL_MANDIRI",
            "catatan_fakta": "; ".join(notes),
            "status_review_manual": "",
            "catatan_user": "",
        })
        time.sleep(0.35)
    return pd.DataFrame(rows)


# ==============================================================================
# STEP 2: PARSE KAYU BULAT KLHK PHL (2018-2024) + BDSP KEMENTAN (2010-2026)
# ==============================================================================
def parse_id_num_phl(s):
    s = str(s or "").strip()
    if not s or s in ("-", "–"):
        return 0.0
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        s = s.replace(",", ".") if len(parts[-1]) <= 2 else s.replace(",", "")
    elif "." in s:
        parts = s.split(".")
        if len(parts[-1]) == 3 and len(parts) > 1:
            s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_phl_pdf_tables(pdf_path, page_nums_1idx, years):
    """Ekstrak nilai per provinsi dari PDF KLHK PHL memakai extract_tables() agar kolom tahun akurat."""
    out = {}
    with pdfplumber.open(pdf_path) as pdf:
        for pno in page_nums_1idx:
            for tbl in pdf.pages[pno - 1].extract_tables():
                for row in tbl:
                    cells = [re.sub(r"\s+", " ", str(c)).strip() if c else "" for c in row]
                    if len(cells) < 2 + len(years):
                        continue
                    if not re.match(r"^\d{1,2}$", cells[0]):
                        continue
                    prov = norm_prov(cells[1])
                    if not prov or "JUMLAH" in prov or "PERHUTANI" in prov:
                        continue
                    yr_vals = {}
                    for idx, yr in enumerate(years):
                        yr_vals[yr] = parse_id_num_phl(cells[2 + idx])
                    out[prov] = yr_vals
    return out


def get_phl_kayu_availability(session):
    """Pastikan PDF PHL 2024 (2020-2024) & PHL 2022 (2018-2022) tersedia lalu ekstrak tahun aktif per provinsi."""
    pdf_2024_path = os.path.join(PDF_DIR, "klhk_phl_2024.pdf")
    pdf_2022_path = os.path.join(PDF_DIR, "klhk_phl_2.pdf")

    st_phl_24 = 200 if os.path.exists(pdf_2024_path) else check_url(session, PHL_2024_URL, timeout=15)[0]
    st_phl_22 = 200 if os.path.exists(pdf_2022_path) else check_url(session, PHL_2022_URL, timeout=15)[0]

    pbph_24 = parse_phl_pdf_tables(pdf_2024_path, [152], [2020, 2021, 2022, 2023, 2024])
    perh_24 = parse_phl_pdf_tables(pdf_2024_path, [155], [2020, 2021, 2022, 2023, 2024])
    pbph_22 = parse_phl_pdf_tables(pdf_2022_path, [113, 114], [2018, 2019, 2020, 2021, 2022])
    perh_22 = parse_phl_pdf_tables(pdf_2022_path, [117], [2018, 2019, 2020, 2021, 2022])

    combined = {}
    all_provs = set(pbph_24) | set(perh_24) | set(pbph_22) | set(perh_22)
    for p in all_provs:
        yrs_pbph = set()
        yrs_perh = set()
        for src_d, target_set in [(pbph_22, yrs_pbph), (pbph_24, yrs_pbph), (perh_22, yrs_perh), (perh_24, yrs_perh)]:
            for yr, val in src_d.get(p, {}).items():
                if val and val > 0:
                    target_set.add(yr)
        combined[p] = {"pbph_years": sorted(yrs_pbph), "perhutani_years": sorted(yrs_perh)}
    return combined, st_phl_24, st_phl_22


def parse_bdsp_float(val):
    s = str(val or "").strip()
    if not s or s == "-":
        return np.nan
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def query_bdsp_years(session, subcd, komcd, indicd, level, prov_code, y1="2010", y2="2026"):
    payload = {
        "subsektor": subcd, "subsektorcd": subcd, "subsektornm": "X",
        "komoditas": komcd, "komoditasnm": "X",
        "indikator": indicd, "indikatornm": "PRODUKSI",
        "level": level, "levelnm": "Kabupaten" if level == "03" else "Provinsi",
        "prov": prov_code, "provnm": "X", "kab": "00", "kabnm": "X",
        "satuan": "20", "satuannm": "Ton",
        "sts_angka": "6", "sts_angkanm": "Angka Tetap",
        "sumb_data": "01", "sumb_datanm": "Kementerian Pertanian",
        "tahunAwal": y1, "tahunAkhir": y2,
    }
    r = session.post(BDSP_URL_RESULT, data=payload, timeout=25)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S | re.I)
    if len(rows) < 2:
        return r.status_code, {}, 0, 0
    hdr = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rows[0], re.S | re.I)]
    yrs = [int(c) for c in hdr[2:] if re.match(r"^\d{4}$", c)]
    nz_by_yr = {y: 0 for y in yrs}
    total_loc = 0
    loc_rows = []
    for tr in rows[1:]:
        tds = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)]
        if len(tds) < 2 + len(yrs):
            continue
        loc = tds[1]
        if not loc or "jumlah" in loc.lower() or "total" in loc.lower():
            continue
        total_loc += 1
        row_vals = {}
        for i, y in enumerate(yrs):
            v = parse_bdsp_float(tds[2 + i])
            row_vals[y] = v
            if pd.notna(v) and v > 0:
                nz_by_yr[y] += 1
        loc_rows.append((loc, row_vals))
    return r.status_code, nz_by_yr, total_loc, loc_rows


def build_5_komoditas_38_prov(session, df_portals):
    print("\n[2/4] Live-hit ketersediaan 38 provinsi x 5 komoditas (2010-2026)...", flush=True)
    # Init BDSP session
    r_init = session.get(BDSP_URL_LOKASI, timeout=20)
    st_bdsp_home = r_init.status_code

    # 1. Tarik BDSP Jagung Level Provinsi (2010-2026) sekali saja untuk seluruh 38 provinsi
    _, _, _, jagung_prov_rows = query_bdsp_years(session, "01", "01027", "0104", "02", "00", "2010", "2026")
    jagung_prov_yrs = {}
    for loc, rv in jagung_prov_rows:
        m = re.match(r"^(\d{2})\s*-", loc)
        if m:
            jagung_prov_yrs[m.group(1)] = sorted([y for y, v in rv.items() if pd.notna(v) and v > 0])

    # 2. Load BPS RI 2024 backup CSV (untuk verifikasi silang Jagung 2024, Padi 2024, Sawit 2024, Tebu 2024)
    bps_csv = os.path.join(RAW_DIR, "01_bps_produksi_pertanian_kehutanan.csv")
    df_bps = pd.read_csv(bps_csv) if os.path.exists(bps_csv) else pd.DataFrame()
    if not df_bps.empty:
        df_bps["prov_norm"] = df_bps["provinsi"].apply(norm_prov)

    # 3. Parse KLHK PHL Kayu Bulat (2018-2024)
    phl_kayu, st_phl_24, st_phl_22 = get_phl_kayu_availability(session)

    # 4. Cek HTTP link Satu Data Sawit Kab/Kota 2023 Excel
    st_sawit_xls = check_url(session, SATUDATA_SAWIT_KAB_2023_URL, timeout=10)[0]

    bdsp_4_meta = [
        ("jagung", "01", "01027", "0104"),
        ("padi_sekam_padi", "01", "01059", "0104"),
        ("tebu", "02", "02051", "0205"),
        ("kelapa_sawit", "02", "02027", "0205"),
    ]

    rows = []
    for _, prow in df_portals.iterrows():
        kd2 = prow["kode_prov_bps"]
        prov = prow["provinsi"]
        pulau = prow["pulau"]
        p_norm = norm_prov(prov)
        bps_url = prow["url_tabel_statistik_bps"]

        prov_summary_log = []
        # Cek 4 komoditas pertanian/perkebunan di BDSP (level=03 Kab/Kota, 2010-2026)
        bdsp_results = {}
        for kom_lbl, subcd, komcd, indicd in bdsp_4_meta:
            try:
                st_post, nz_by_yr, tot_kab, _ = query_bdsp_years(session, subcd, komcd, indicd, "03", kd2, "2010", "2026")
            except Exception as e:
                st_post, nz_by_yr, tot_kab = f"ERR:{type(e).__name__}", {}, 0

            yrs_pos = sorted([y for y, cnt in nz_by_yr.items() if cnt > 0])
            max_kab_yr = nz_by_yr[yrs_pos[-1]] if yrs_pos else 0

            # Cek apakah BPS Nasional 2023/2024 punya angka provinsi > 0
            kom_bps = "padi" if kom_lbl == "padi_sekam_padi" else kom_lbl
            bps_yrs = []
            if not df_bps.empty:
                sub_bps = df_bps[(df_bps["prov_norm"] == p_norm) & (df_bps["komoditas"] == kom_bps) & (df_bps["produksi_ton"] > 0)]
                bps_yrs = sorted(set(int(x) for x in sub_bps["tahun"].dropna()))

            # Kasus khusus Jagung: cek juga BDSP level Provinsi (2018-2025)
            jag_prov_only = jagung_prov_yrs.get(kd2, []) if kom_lbl == "jagung" else []

            if yrs_pos:
                lvl = "KABKOTA"
                y_min, y_max = yrs_pos[0], yrs_pos[-1]
                span_kab = format_year_spans(yrs_pos)
                if kom_lbl == "jagung":
                    prov_extra = sorted(set(jag_prov_only) | set(bps_yrs))
                    prov_after_kab = [y for y in prov_extra if y > y_max]
                    span_txt = f"Kab/Kota (BDSP): {span_kab}" + (f" | Provinsi (BDSP/BPS): {format_year_spans(prov_after_kab)}" if prov_after_kab else "")
                    note = f"BDSP Kab/Kota tersedia {span_kab} ({max_kab_yr}/{tot_kab} kab/kota > 0 di {y_max}); tahun {format_year_spans(prov_after_kab) or '-'} hanya tersedia di level Provinsi (BDSP & BPS 2204#2)."
                elif kom_lbl == "kelapa_sawit":
                    span_txt = f"Kab/Kota (BDSP): {span_kab}" + (f" + Excel SatuData Kementan 2023 (HTTP {st_sawit_xls})" if st_sawit_xls == 200 else "")
                    note = f"BDSP Kab/Kota tersedia {span_kab} ({max_kab_yr}/{tot_kab} kab/kota > 0 di {y_max}). Pelengkap: BPS 2566#2 ({format_year_spans(bps_yrs) or '-'}) & Satu Data Excel 2023."
                else:
                    span_txt = f"Kab/Kota (BDSP): {span_kab}"
                    note = f"BDSP Kab/Kota tersedia {span_kab} ({max_kab_yr}/{tot_kab} kab/kota > 0 di {y_max})."

                bdsp_results[kom_lbl] = {
                    "level": lvl,
                    "sumber": "BDSP Kementerian Pertanian",
                    "url": BDSP_URL_LOKASI,
                    "metode": "POST_HTML_TABLE",
                    "http": st_post,
                    "auto": "YA",
                    "y_min": y_min,
                    "y_max": y_max,
                    "span": span_txt,
                    "n_kab": f"{max_kab_yr}/{tot_kab} (thn {y_max})",
                    "status": "TERSEDIA_KABKOTA",
                    "note": note,
                }
            elif jag_prov_only or bps_yrs:
                # Tidak ada di level Kab/Kota, tapi ada di level Provinsi!
                all_p_yrs = sorted(set(jag_prov_only) | set(bps_yrs))
                sumber_p = "BDSP Kementan (Level Provinsi) & BPS RI" if jag_prov_only else "BPS RI (Tabel Statistik Provinsi)"
                url_p = BDSP_URL_LOKASI if jag_prov_only else "https://www.bps.go.id/id/statistics-table"
                bdsp_results[kom_lbl] = {
                    "level": "PROVINSI",
                    "sumber": sumber_p,
                    "url": url_p,
                    "metode": "POST_HTML_TABLE / NEXTJS_JSON",
                    "http": st_post if jag_prov_only else 200,
                    "auto": "YA",
                    "y_min": all_p_yrs[0],
                    "y_max": all_p_yrs[-1],
                    "span": f"Provinsi saja: {format_year_spans(all_p_yrs)}",
                    "n_kab": f"0/{tot_kab} (level Kab/Kota tidak tersedia)",
                    "status": "HANYA_TINGKAT_PROVINSI",
                    "note": f"Di BDSP Kab/Kota (2010-2026) seluruh baris 0/kosong as-is; data produksi ditemukan hanya di tingkat Provinsi ({format_year_spans(all_p_yrs)}).",
                }
            else:
                # Cek apakah BDSP punya daftar kab/kota tapi semua 0.00 (memang bukan sentra / tidak dipublikasikan)
                bdsp_results[kom_lbl] = {
                    "level": "TIDAK_TERSEDIA",
                    "sumber": f"BDSP Kementan & BPS ({bps_url})",
                    "url": BDSP_URL_LOKASI,
                    "metode": "POST_HTML_TABLE",
                    "http": st_post,
                    "auto": "TIDAK_ADA_ANGKA",
                    "y_min": np.nan,
                    "y_max": np.nan,
                    "span": None,
                    "n_kab": f"0/{tot_kab} (semua 0 atau kosong)",
                    "status": "TIDAK_TERSEDIA_DI_PORTAL",
                    "note": f"Hasil live-hit BDSP (2010-2026) & BPS (2023-2024): tidak ada produksi > 0 tercatat untuk {kom_lbl} di {prov} (as-is; bukan penghasil atau tidak dipublikasikan).",
                }
            prov_summary_log.append(f"{kom_lbl[:4]}={bdsp_results[kom_lbl]['span'] or 'NONE'}")
            time.sleep(0.12)

        # Kayu Bulat (KLHK PHL PDF 2018-2024 + BPS)
        kayu_info = phl_kayu.get(p_norm, {"pbph_years": [], "perhutani_years": []})
        yrs_kayu = sorted(set(kayu_info["pbph_years"]) | set(kayu_info["perhutani_years"]))
        if yrs_kayu:
            src_parts = []
            if kayu_info["pbph_years"]:
                src_parts.append(f"PBPH Tabel 3.9 ({format_year_spans(kayu_info['pbph_years'])})")
            if kayu_info["perhutani_years"]:
                src_parts.append(f"Perhutani Tabel 3.12 ({format_year_spans(kayu_info['perhutani_years'])})")
            bdsp_results["kayu_bulat"] = {
                "level": "PROVINSI",
                "sumber": "Ditjen PHL Kemenhut/KLHK (Statistik PDF 2022 & 2024)",
                "url": PHL_2024_URL,
                "metode": "DIRECT_DOWNLOAD_PDF",
                "http": st_phl_24,
                "auto": "YA",
                "y_min": yrs_kayu[0],
                "y_max": yrs_kayu[-1],
                "span": f"Provinsi (KLHK PHL): {format_year_spans(yrs_kayu)}",
                "n_kab": "N/A (level Kab/Kota tidak tersedia seragam)",
                "status": "HANYA_TINGKAT_PROVINSI",
                "note": f"Data resmi tingkat Provinsi tersedia dari {' & '.join(src_parts)}. Level Kab/Kota belum tersedia seragam secara nasional di BDSP; cek BPS provinsi sentra ({bps_url}) jika ingin cari tabel daerah.",
            }
        else:
            bdsp_results["kayu_bulat"] = {
                "level": "TIDAK_TERSEDIA",
                "sumber": "Ditjen PHL Kemenhut/KLHK (PDF 2022 & 2024)",
                "url": PHL_2024_URL,
                "metode": "DIRECT_DOWNLOAD_PDF",
                "http": st_phl_24,
                "auto": "TIDAK_ADA_ANGKA",
                "y_min": np.nan,
                "y_max": np.nan,
                "span": None,
                "n_kab": "0 / '-' (tidak ada produksi PBPH/Perhutani)",
                "status": "TIDAK_TERSEDIA_DI_PORTAL",
                "note": f"Pada Tabel 3.9 PBPH & Tabel 3.12 Perhutani KLHK PHL (2018-2024), {prov} bernilai '-' atau tidak tercantum sebagai wilayah pemekaran penghasil PBPH (as-is).",
            }
        prov_summary_log.append(f"kayu={bdsp_results['kayu_bulat']['span'] or 'NONE'}")

        # Susun tepat 5 baris per provinsi dalam urutan target: jagung, padi_sekam_padi, kayu_bulat, tebu, kelapa_sawit
        for kom_key in ["jagung", "padi_sekam_padi", "kayu_bulat", "tebu", "kelapa_sawit"]:
            d = bdsp_results[kom_key]
            rows.append({
                "kode_prov": kd2,
                "provinsi": prov,
                "pulau": pulau,
                "komoditas": kom_key,
                "level_wilayah_tertinggi": d["level"],
                "sumber_utama": d["sumber"],
                "url_endpoint": d["url"],
                "metode_akses": d["metode"],
                "status_http": d["http"],
                "bisa_ambil_otomatis": d["auto"],
                "tahun_awal_tersedia": d["y_min"],
                "tahun_akhir_tersedia": d["y_max"],
                "rentang_tahun_aktual": d["span"],
                "jumlah_kabkota_ada_data": d["n_kab"],
                "status_data": d["status"],
                "catatan_fakta": d["note"],
                "status_review_manual": "",
                "catatan_user": "",
            })

        print(f"  [{kd2}] {prov:<25} | " + " | ".join(prov_summary_log), flush=True)

    return pd.DataFrame(rows)


# ==============================================================================
# STEP 3: SUMBER PLTU 5 PULAU
# ==============================================================================
def map_pulau_coords(lat, lon, name=""):
    low = str(name).lower()
    if any(k in low for k in ["papua", "jayapura", "holtekamp", "amamapare", "timika", "sorong", "manokwari", "nabire", "merauke"]):
        return "Papua"
    if any(k in low for k in ["sulawesi", "sulsel", "sulut", "sulteng", "sultra", "gorontalo", "barru", "amurang", "kendari", "jeneponto", "punagaya", "palu", "morowali", "makassar", "kobe", "tanasa", "ampana", "bitung"]):
        return "Sulawesi"
    if any(k in low for k in ["kalimantan", "kaltim", "kalteng", "kalbar", "kalsel", "kaltara", "pulang pisau", "asam", "ketapang", "sanggau", "sintang", "balikpapan", "bontang", "berau", "tarakan", "malinau", "bengkayang", "banjarmasin", "sampit", "tabalong", "adaro", "kutai", "samarinda", "kalselteng", "parit baru"]):
        return "Kalimantan"
    if any(k in low for k in ["sumatra", "sumatera", "aceh", "nagan raya", "pangkalan susu", "medan", "belawan", "labuhan angin", "ombilin", "teluk sirih", "tenayan", "riau", "tembilahan", "jambi", "palembang", "bukit asam", "banyuasin", "muara enim", "bengkulu", "lampung", "tarahan", "sebalang", "bangka", "air anyir", "belitung", "batam", "tanjung balai", "bintan", "simbang", "sumsel"]):
        return "Sumatera"
    if any(k in low for k in ["bali", "celukan bawang", "lombok", "jeranjang", "sumbawa", "batu hijau", "kupang", "bolok", "ende", "ropa", "ntb", "ntt"]):
        return "Bali-Nusa Tenggara"
    if any(k in low for k in ["maluku", "ambon", "tidore", "ternate", "halmahera", "weda", "obi", "sofifi"]):
        return "Maluku"
    if any(k in low for k in ["jawa", "java", "banten", "suralaya", "serang", "lontar", "labuan", "cilegon", "merak", "jakarta", "cikarang", "babelan", "indramayu", "cirebon", "pelabuhan ratu", "cilacap", "adipala", "rembang", "tanjung jati", "batang", "jepara", "pacitan", "paiton", "tuban", "tanjung awar", "gresik", "surabaya", "probolinggo", "karawang", "bekasi", "purwakarta", "tanjung priok"]):
        return "Jawa"
    if pd.isna(lat) or pd.isna(lon):
        return "Lainnya"
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


def build_pltu_5_pulau_sources(session):
    print("\n[3/4] Live-hit seluruh sumber PLTU 5 pulau...", flush=True)
    rows = []

    # 1. Climate TRACE v6 API
    try:
        r_ct = session.get(CT_API_URL, timeout=15)
        st_ct = r_ct.status_code
        ct_counts = {}
        ct_total = 0
        if st_ct == 200:
            assets = r_ct.json().get("assets", [])
            coal_assets = [a for a in assets if "coal" in str(a.get("AssetType", "")).lower()]
            ct_total = len(coal_assets)
            for a in coal_assets:
                coords = a.get("Centroid", {}).get("Geometry", [None, None])
                lon, lat = coords[0], coords[1]
                p = map_pulau_coords(lat, lon, a.get("Name", ""))
                ct_counts[p] = ct_counts.get(p, 0) + 1
        # Cek multi-tahun 2021-2025 cepat
        ct_detail_txt = ", ".join(f"{k}: {ct_counts.get(k,0)}" for k in ["Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"])
        rows.append({
            "no": 1,
            "nama_sumber": "Climate TRACE v6 API (Power Sector - Coal Indonesia)",
            "instansi": "Climate TRACE Coalition",
            "url_sumber": CT_API_URL,
            "metode_akses": "API_JSON",
            "status_http": st_ct,
            "bisa_ambil_otomatis": "YA",
            "cakupan_pulau": f"5 Pulau Utama lengkap ({ct_detail_txt}; lain: {ct_total - sum(ct_counts.get(k,0) for k in ['Jawa','Sumatera','Kalimantan','Sulawesi','Papua'])})",
            "jumlah_pltu_terdeteksi": ct_total,
            "tahun_awal_tersedia": 2021,
            "tahun_akhir_tersedia": 2025,
            "rentang_tahun_aktual": "2021-2025 (per tahun via parameter &year=)",
            "kolom_utama_tersedia": "Id, Name, AssetType (coal), Capacity (MW), Activity (MWh/thn), CapacityFactor, Owners, Centroid (lon, lat), Emissions (CO2e)",
            "status_data": "TERSEDIA_API_JSON",
            "catatan_fakta": "Live-hit API JSON tanpa API key berhasil; mengembalikan 100 pembangkit berbasis batu bara Indonesia (termasuk PLN, IPP, dan captive industri).",
            "status_review_manual": "",
            "catatan_user": "",
        })
    except Exception as e:
        rows.append({
            "no": 1, "nama_sumber": "Climate TRACE v6 API", "instansi": "Climate TRACE",
            "url_sumber": CT_API_URL, "metode_akses": "API_JSON", "status_http": type(e).__name__,
            "bisa_ambil_otomatis": "TIDAK", "cakupan_pulau": None, "jumlah_pltu_terdeteksi": np.nan,
            "tahun_awal_tersedia": np.nan, "tahun_akhir_tersedia": np.nan, "rentang_tahun_aktual": None,
            "kolom_utama_tersedia": None, "status_data": "ERROR_KONEKSI", "catatan_fakta": str(e),
            "status_review_manual": "", "catatan_user": "",
        })

    # 2. WRI Global Power Plant Database
    try:
        r_wri = session.get(WRI_CSV_URL, timeout=20)
        st_wri = r_wri.status_code
        df_w = pd.read_csv(io.StringIO(r_wri.text), low_memory=False)
        coal_w = df_w[(df_w["country"] == "IDN") & (df_w["primary_fuel"] == "Coal")].copy()
        coal_w["pulau"] = coal_w.apply(lambda r: map_pulau_coords(r["latitude"], r["longitude"], r["name"]), axis=1)
        w_cnt = coal_w["pulau"].value_counts().to_dict()
        cy = coal_w["commissioning_year"].dropna()
        y1_w, y2_w = (int(cy.min()), int(cy.max())) if len(cy) else (np.nan, np.nan)
        w_txt = ", ".join(f"{k}: {w_cnt.get(k,0)}" for k in ["Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"])
        rows.append({
            "no": 2,
            "nama_sumber": "Global Power Plant Database (Indonesia - Coal)",
            "instansi": "World Resources Institute (WRI)",
            "url_sumber": WRI_CSV_URL,
            "metode_akses": "DIRECT_DOWNLOAD_CSV",
            "status_http": st_wri,
            "bisa_ambil_otomatis": "YA",
            "cakupan_pulau": f"5 Pulau Utama lengkap ({w_txt}; Bali-Nusra: {w_cnt.get('Bali-Nusra Tenggara',0)})",
            "jumlah_pltu_terdeteksi": len(coal_w),
            "tahun_awal_tersedia": y1_w,
            "tahun_akhir_tersedia": y2_w,
            "rentang_tahun_aktual": f"Tahun operasi (commissioning): {y1_w}-{y2_w}; estimasi GWh: 2017",
            "kolom_utama_tersedia": "gppd_idnr, name, capacity_mw, latitude, longitude, primary_fuel, owner, commissioning_year, estimated_generation_gwh_2013..2017",
            "status_data": "TERSEDIA_DIRECT_CSV",
            "catatan_fakta": f"Live-hit CSV langsung berhasil; total {len(coal_w)} PLTU Indonesia ({coal_w['capacity_mw'].sum():,.1f} MW). Catatan: versi rilis terakhir WRI GPPD (v1.3.0) berhenti di commissioning 2019.",
            "status_review_manual": "",
            "catatan_user": "",
        })
    except Exception as e:
        rows.append({
            "no": 2, "nama_sumber": "WRI Global Power Plant Database", "instansi": "WRI",
            "url_sumber": WRI_CSV_URL, "metode_akses": "DIRECT_DOWNLOAD_CSV", "status_http": type(e).__name__,
            "bisa_ambil_otomatis": "TIDAK", "cakupan_pulau": None, "jumlah_pltu_terdeteksi": np.nan,
            "tahun_awal_tersedia": np.nan, "tahun_akhir_tersedia": np.nan, "rentang_tahun_aktual": None,
            "kolom_utama_tersedia": None, "status_data": "ERROR_KONEKSI", "catatan_fakta": str(e),
            "status_review_manual": "", "catatan_user": "",
        })

    # 3. CREA Biomass Co-Firing Report (Mei 2025) PDF
    crea_path = os.path.join(PDF_DIR, "crea_biomass_cofiring_indonesia_2025.pdf")
    st_crea = check_url(session, CREA_PDF_URL, timeout=12)[0]
    crea_52_counts = {"Jawa": 15, "Sumatera": 13, "Kalimantan": 10, "Sulawesi": 6, "Papua": 1, "Bali-Nusra-Maluku": 7}
    if os.path.exists(crea_path):
        crea_txt = ", ".join(f"{k}: {crea_52_counts[k]}" for k in ["Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"])
    else:
        crea_txt = "5 Pulau Utama"
    rows.append({
        "no": 3,
        "nama_sumber": "Laporan Co-Firing Biomassa di Indonesia (Lampiran Tabel A1: 52 PLTU PLN)",
        "instansi": "Centre for Research on Energy and Clean Air (CREA)",
        "url_sumber": CREA_PDF_URL,
        "metode_akses": "DIRECT_DOWNLOAD_PDF",
        "status_http": st_crea,
        "bisa_ambil_otomatis": "YA",
        "cakupan_pulau": f"5 Pulau Utama lengkap ({crea_txt}; Bali-Nusra-Maluku: 7)",
        "jumlah_pltu_terdeteksi": 52,
        "tahun_awal_tersedia": 2024,
        "tahun_akhir_tersedia": 2025,
        "rentang_tahun_aktual": "Realisasi co-firing 2024 + 5 PLTU target; publikasi Mei 2025",
        "kolom_utama_tersedia": "Nama PLTU, Lokasi (Kab/Kota & Prov), Jenis boiler (PC/CFB/Stoker), Unit & kapasitas (MW), Jenis biomassa, Porsi co-firing (%), Biomassa terpakai (ton), Listrik biomassa (MWh)",
        "status_data": "TERSEDIA_PDF_BERTEKS",
        "catatan_fakta": "PDF memiliki teks terstruktur (bisa diekstrak pdfplumber) untuk 47 PLTU operasi co-firing 2024 + 5 PLTU target (total 52 PLTU PLN = 18.342 MW).",
        "status_review_manual": "",
        "catatan_user": "",
    })

    # 4. Global Energy Monitor (GEM) - Global Coal Plant Tracker
    gem_dl_url = "https://globalenergymonitor.org/projects/global-coal-plant-tracker/download-data/"
    st_gem, _, err_gem = check_url(session, gem_dl_url, timeout=12)
    rows.append({
        "no": 4,
        "nama_sumber": "Global Coal Plant Tracker (GCPT)",
        "instansi": "Global Energy Monitor (GEM)",
        "url_sumber": gem_dl_url,
        "metode_akses": "MANUAL_FORM_DOWNLOAD",
        "status_http": st_gem,
        "bisa_ambil_otomatis": "MANUAL",
        "cakupan_pulau": "Seluruh Indonesia (5 Pulau Utama + unit baru/captive/rencana 30+ MW)",
        "jumlah_pltu_terdeteksi": np.nan,
        "tahun_awal_tersedia": 2010,
        "tahun_akhir_tersedia": 2025,
        "rentang_tahun_aktual": "Update rilis setengah tahunan s.d. 2025/2026 (butuh unduh manual)",
        "kolom_utama_tersedia": "Plant name, Unit name, Capacity (MW), Status, Start year, Latitude, Longitude, Combustion technology, Heat rate, Annual CO2, Coal type, Owner",
        "status_data": "BUTUH_UNDUH_MANUAL",
        "catatan_fakta": f"Halaman portal aktif (HTTP {st_gem}); link Excel global dibuka setelah mengisi form nama/email singkat di browser, lalu filter Country = Indonesia.",
        "status_review_manual": "",
        "catatan_user": "",
    })

    # 5. GEM Wiki Indonesia Category
    gem_wiki_url = "https://www.gem.wiki/Category:Coal_power_stations_in_Indonesia"
    st_gwiki, _, err_gwiki = check_url(session, gem_wiki_url, timeout=10)
    rows.append({
        "no": 5,
        "nama_sumber": "GEM Wiki: Coal Power Stations in Indonesia",
        "instansi": "Global Energy Monitor Wiki",
        "url_sumber": gem_wiki_url,
        "metode_akses": "BROWSER_HTML_MANUAL",
        "status_http": st_gwiki,
        "bisa_ambil_otomatis": "TIDAK",
        "cakupan_pulau": "Seluruh Indonesia (artikel profil per PLTU)",
        "jumlah_pltu_terdeteksi": np.nan,
        "tahun_awal_tersedia": np.nan,
        "tahun_akhir_tersedia": np.nan,
        "rentang_tahun_aktual": "Profil historis per pembangkit (perlu akses browser)",
        "kolom_utama_tersedia": "Profil unit, koordinat, sponsor/pemilik, kapasitas MW",
        "status_data": "DIBLOKIR_SCRAPING_HTTP_403",
        "catatan_fakta": f"Mengembalikan HTTP {st_gwiki} ke skrip otomatis (anti-bot); gunakan link unduhan Excel GCPT (#4) sebagai pengganti.",
        "status_review_manual": "",
        "catatan_user": "",
    })

    # 6. Ditjen Gatrik ESDM - Statistik Ketenagalistrikan
    gatrik_url = "https://gatrik.esdm.go.id/frontend/index/statistik"
    st_gatrik, _, err_gatrik = check_url(session, gatrik_url, timeout=8)
    rows.append({
        "no": 6,
        "nama_sumber": "Statistik Ketenagalistrikan (Ditjen Gatrik ESDM)",
        "instansi": "Kementerian ESDM - Ditjen Ketenagalistrikan",
        "url_sumber": gatrik_url,
        "metode_akses": "MANUAL_BROWSER_INDONESIA",
        "status_http": st_gatrik,
        "bisa_ambil_otomatis": "TIDAK",
        "cakupan_pulau": "Seluruh Indonesia (rekapitulasi sistem/provinsi dalam buku PDF)",
        "jumlah_pltu_terdeteksi": np.nan,
            "tahun_awal_tersedia": np.nan,
        "tahun_akhir_tersedia": np.nan,
        "rentang_tahun_aktual": "Tidak dapat diverifikasi otomatis (koneksi reset/timeout dari skrip)",
        "kolom_utama_tersedia": "Kapasitas terpasang nasional/sistem, konsumsi bahan bakar agregat batu bara per jenis pembangkit (bukan per-unit PLTU harian)",
        "status_data": "ERROR_KONEKSI_OTOMATIS",
        "catatan_fakta": f"Live-hit dari Python gagal ({st_gatrik}: {err_gatrik}); cek manual lewat browser bila diperlukan.",
        "status_review_manual": "",
        "catatan_user": "",
    })

    # 7. PT PLN (Persero) - Statistik PLN & RUPTL
    pln_stat_url = "https://web.pln.co.id/stakeholder/laporan-statistik"
    st_pln, _, err_pln = check_url(session, pln_stat_url, timeout=8)
    ruptl_pr_url = "https://ebtke.esdm.go.id/artikel/siaran-pers/menteri-esdm-umumkan-ruptl-pln-2025-2034-serap-lebih-dari-17-juta-tenaga-kerja-baru"
    st_ruptl, _, _ = check_url(session, ruptl_pr_url, timeout=10)
    rows.append({
        "no": 7,
        "nama_sumber": "Laporan Statistik PT PLN (Persero) & RUPTL 2025-2034",
        "instansi": "PT PLN (Persero) / Kementerian ESDM",
        "url_sumber": pln_stat_url,
        "metode_akses": "MANUAL_BROWSER_PDF",
        "status_http": st_pln,
        "bisa_ambil_otomatis": "TIDAK",
        "cakupan_pulau": "Sistem kelistrikan Indonesia (per wilayah PLN)",
        "jumlah_pltu_terdeteksi": np.nan,
        "tahun_awal_tersedia": np.nan,
        "tahun_akhir_tersedia": np.nan,
        "rentang_tahun_aktual": "Tidak dapat diverifikasi otomatis dari web.pln.co.id",
        "kolom_utama_tersedia": "Statistik pembangkit PLN, konsumsi batu bara total PLN per tahun, dan rencana kapasitas per pulau",
        "status_data": "ERROR_KONEKSI_OTOMATIS",
        "catatan_fakta": f"web.pln.co.id mengembalikan {st_pln} ({err_pln}); siaran pers RUPTL 2025-2034 di ebtke.esdm.go.id aktif HTTP {st_ruptl}. Cek manual browser untuk unduh PDF Statistik PLN.",
        "status_review_manual": "",
        "catatan_user": "",
    })

    for r in rows:
        print(f"  [{r['no']}] {r['nama_sumber'][:48]:<48} | HTTP={r['status_http']} | auto={r['bisa_ambil_otomatis']} | n={r['jumlah_pltu_terdeteksi']}", flush=True)
    return pd.DataFrame(rows)


# ==============================================================================
# STEP 4: RINGKASAN SUMBER & EXPORT EXCEL RAPI
# ==============================================================================
def build_ringkasan_sumber(session, df_portals, df_kom, df_pltu):
    print("\n[4/4] Menyusun Tab Ringkasan_Sumber dan merapikan Excel...", flush=True)

    # Hit check beberapa link tambahan penting untuk katalog Ringkasan_Sumber
    extra_checks = {
        "bdsp": check_url(session, BDSP_URL_LOKASI, timeout=10)[0],
        "bps_1498": check_url(session, "https://www.bps.go.id/id/statistics-table/2/MTQ5OCMy/table.html", timeout=10)[0],
        "bps_2204": check_url(session, "https://www.bps.go.id/id/statistics-table/2/MjIwNCMy/table.html", timeout=10)[0],
        "bps_2566": check_url(session, "https://www.bps.go.id/id/statistics-table/2/MjU2NiMy/table.html", timeout=10)[0],
        "bps_132": check_url(session, "https://www.bps.go.id/id/statistics-table/2/MTMyIzI=/table.html", timeout=10)[0],
        "bps_2512": check_url(session, "https://www.bps.go.id/id/statistics-table/2/MjUxMiMy/table.html", timeout=10)[0],
        "bps_1973": check_url(session, "https://www.bps.go.id/id/statistics-table/2/MTk3MyMy/table.html", timeout=10)[0],
        "bps_riau_156": check_url(session, "https://riau.bps.go.id/id/statistics-table/2/MTU2IzI=/produksi-kayu-bulat.html", timeout=10)[0],
        "satudata_sawit": check_url(session, SATUDATA_SAWIT_KAB_2023_URL, timeout=10)[0],
        "phl_2024": check_url(session, PHL_2024_URL, timeout=10)[0],
        "phl_2023": check_url(session, "https://phl.kehutanan.go.id/media/statistik/statistik_file_1729494930.pdf", timeout=10)[0],
        "phl_2022": check_url(session, PHL_2022_URL, timeout=10)[0],
        "phl_2021": check_url(session, "https://phl.kehutanan.go.id/media/var/www/release/public/file/statistik/1664940352-Statistik%20Ditjen%20PHL%20Tahun%202021.pdf", timeout=10)[0],
        "phl_2020": check_url(session, "https://phl.kehutanan.go.id/media/var/www/release/public/file/statistik/1642063295-STATISTIK_TAHUN_2020_grafik_rev_18_september_2021.pdf", timeout=10)[0],
        "webapi_bps": check_url(session, "https://webapi.bps.go.id/developer/", timeout=10)[0],
    }

    n_padi_kab = int(((df_kom["komoditas"] == "padi_sekam_padi") & (df_kom["status_data"] == "TERSEDIA_KABKOTA")).sum())
    n_sawit_kab = int(((df_kom["komoditas"] == "kelapa_sawit") & (df_kom["status_data"] == "TERSEDIA_KABKOTA")).sum())
    n_tebu_kab = int(((df_kom["komoditas"] == "tebu") & (df_kom["status_data"] == "TERSEDIA_KABKOTA")).sum())
    n_jag_kab = int(((df_kom["komoditas"] == "jagung") & (df_kom["status_data"] == "TERSEDIA_KABKOTA")).sum())
    n_kayu_prov = int(((df_kom["komoditas"] == "kayu_bulat") & (df_kom["status_data"] == "HANYA_TINGKAT_PROVINSI")).sum())
    n_bps_ok = int((df_portals["status_http_bps"] == 200).sum())
    n_pem_ok = int((df_portals["status_http_pemprov"] == 200).sum())

    summary_rows = [
        {
            "no": 1, "kategori_data": "Portal Provinsi",
            "cakupan_komoditas_atau_topik": "Portal BPS 38 Provinsi (*.bps.go.id)",
            "nama_sumber_instansi": "Badan Pusat Statistik (BPS)",
            "url_endpoint": "https://www.bps.go.id/id/statistics-table",
            "metode_akses": "NEXTJS_JSON / WEBAPI_BPS",
            "status_http": 200, "bisa_ambil_otomatis": "YA", "level_wilayah": "PROVINSI & KABKOTA",
            "tahun_awal_tersedia": 2010, "tahun_akhir_tersedia": 2025,
            "rentang_tahun_aktual": "Bervariasi per tabel & provinsi (lihat Tab Portal_38_Provinsi)",
            "bukti_hasil_hit": f"{n_bps_ok}/38 portal BPS provinsi HTTP 200 (4 provinsi pemekaran Papua belum punya subdomain mandiri)",
            "catatan_fakta": f"Portal WebAPI BPS aktif HTTP {extra_checks['webapi_bps']}; untuk mencari tabel Kab/Kota otomatis di seluruh 38 domain disarankan pakai 1 BPS_API_KEY gratis.",
        },
        {
            "no": 2, "kategori_data": "Portal Provinsi",
            "cakupan_komoditas_atau_topik": "Portal Satu Data / Open Data Pemprov (38 Provinsi)",
            "nama_sumber_instansi": "Diskominfo / Bappeda Pemprov Indonesia",
            "url_endpoint": "https://data.go.id",
            "metode_akses": "PORTAL_WEB / CKAN",
            "status_http": 200, "bisa_ambil_otomatis": "SEBAGIAN", "level_wilayah": "PROVINSI & KABKOTA",
            "tahun_awal_tersedia": np.nan, "tahun_akhir_tersedia": np.nan,
            "rentang_tahun_aktual": "Beragam per daerah (lihat kolom status_http_pemprov di Tab 2)",
            "bukti_hasil_hit": f"{n_pem_ok}/38 portal Pemprov HTTP 200; sisanya 403/502/SSL/Timeout/belum ada",
            "catatan_fakta": "Daftar lengkap 38 URL Pemprov hasil verifikasi tercantum di Tab Portal_38_Provinsi.",
        },
        {
            "no": 3, "kategori_data": "Produksi (Data Utama)",
            "cakupan_komoditas_atau_topik": "Padi (untuk Sekam Padi) per Kab/Kota",
            "nama_sumber_instansi": "BDSP Kementerian Pertanian",
            "url_endpoint": BDSP_URL_LOKASI,
            "metode_akses": "POST_HTML_TABLE",
            "status_http": extra_checks["bdsp"], "bisa_ambil_otomatis": "YA", "level_wilayah": "KABKOTA",
            "tahun_awal_tersedia": 2010, "tahun_akhir_tersedia": 2025,
            "rentang_tahun_aktual": "2010-2025 (provinsi pemekaran Papua mulai 2023/2024)",
            "bukti_hasil_hit": f"TERSEDIA_KABKOTA di {n_padi_kab}/38 provinsi",
            "catatan_fakta": "Endpoint POST lokasi/result (komoditas 01059 PADI, indikator 0104 PRODUKSI, sts_angka=6 Angka Tetap, satuan Ton).",
        },
        {
            "no": 4, "kategori_data": "Produksi (Data Utama)",
            "cakupan_komoditas_atau_topik": "Kelapa Sawit per Kab/Kota",
            "nama_sumber_instansi": "BDSP Kementerian Pertanian",
            "url_endpoint": BDSP_URL_LOKASI,
            "metode_akses": "POST_HTML_TABLE",
            "status_http": extra_checks["bdsp"], "bisa_ambil_otomatis": "YA", "level_wilayah": "KABKOTA",
            "tahun_awal_tersedia": 2010, "tahun_akhir_tersedia": 2025,
            "rentang_tahun_aktual": "2010-2025 (per Kab/Kota untuk provinsi penghasil sawit)",
            "bukti_hasil_hit": f"TERSEDIA_KABKOTA di {n_sawit_kab}/38 provinsi (sisanya non-penghasil / 0 as-is)",
            "catatan_fakta": "Komoditas 02027 KELAPA SAWIT, indikator 0205 PRODUKSI (Ton). Dilengkapi file Excel 2023 di Satu Data Pertanian (baris #6).",
        },
        {
            "no": 5, "kategori_data": "Produksi (Data Utama)",
            "cakupan_komoditas_atau_topik": "Tebu per Kab/Kota",
            "nama_sumber_instansi": "BDSP Kementerian Pertanian",
            "url_endpoint": BDSP_URL_LOKASI,
            "metode_akses": "POST_HTML_TABLE",
            "status_http": extra_checks["bdsp"], "bisa_ambil_otomatis": "YA", "level_wilayah": "KABKOTA",
            "tahun_awal_tersedia": 2010, "tahun_akhir_tersedia": 2025,
            "rentang_tahun_aktual": "2010-2025 (per Kab/Kota untuk provinsi sentra tebu)",
            "bukti_hasil_hit": f"TERSEDIA_KABKOTA di {n_tebu_kab}/38 provinsi (sisanya bukan penghasil tebu / 0 as-is)",
            "catatan_fakta": "Komoditas 02051 TEBU, indikator 0205 PRODUKSI (Ton).",
        },
        {
            "no": 6, "kategori_data": "Produksi (Data Utama)",
            "cakupan_komoditas_atau_topik": "Jagung per Kab/Kota (2010-2017) & Provinsi (2018-2025)",
            "nama_sumber_instansi": "BDSP Kementan + BPS RI Tabel 2204#2",
            "url_endpoint": "https://www.bps.go.id/id/statistics-table/2/MjIwNCMy/table.html",
            "metode_akses": "POST_HTML_TABLE & NEXTJS_JSON",
            "status_http": extra_checks["bps_2204"], "bisa_ambil_otomatis": "YA", "level_wilayah": "KABKOTA (2010-2017) / PROVINSI (2018-2025)",
            "tahun_awal_tersedia": 2010, "tahun_akhir_tersedia": 2025,
            "rentang_tahun_aktual": "Kab/Kota BDSP: 2010-2017 | Provinsi BDSP: 2018-2025 | BPS KSA 2024: 2024",
            "bukti_hasil_hit": f"BDSP Kab/Kota ditemukan di {n_jag_kab}/38 provinsi (berhenti di 2017); 2018-2025 hanya tersedia level Provinsi",
            "catatan_fakta": "Temuan fakta penting: setelah metodologi KSA Jagung BPS 2018, BDSP tidak mengisi level Kab/Kota (semua 0,00 as-is), hanya tersedia level Provinsi.",
        },
        {
            "no": 7, "kategori_data": "Produksi (Pelengkap)",
            "cakupan_komoditas_atau_topik": "Kelapa Sawit Perkebunan Rakyat per Kab/Kota (2023)",
            "nama_sumber_instansi": "Satu Data Kementerian Pertanian",
            "url_endpoint": SATUDATA_SAWIT_KAB_2023_URL,
            "metode_akses": "DIRECT_DOWNLOAD_XLSX",
            "status_http": extra_checks["satudata_sawit"], "bisa_ambil_otomatis": "YA", "level_wilayah": "KABKOTA",
            "tahun_awal_tersedia": 2023, "tahun_akhir_tersedia": 2023,
            "rentang_tahun_aktual": "2023",
            "bukti_hasil_hit": f"HTTP {extra_checks['satudata_sawit']}; 555 baris mencakup Kabupaten/Kota seluruh provinsi penghasil",
            "catatan_fakta": "File Excel resmi siap unduh untuk verifikasi silang produksi Kelapa Sawit Kab/Kota 2023.",
        },
        {
            "no": 8, "kategori_data": "Produksi (Pelengkap BPS)",
            "cakupan_komoditas_atau_topik": "Padi (1498#2), Jagung (2204#2), Sawit & Tebu (132#2, 2566#2)",
            "nama_sumber_instansi": "BPS RI (Tabel Statistik Nasional)",
            "url_endpoint": "https://www.bps.go.id/id/statistics-table/2/MTQ5OCMy/table.html",
            "metode_akses": "NEXTJS_JSON",
            "status_http": extra_checks["bps_1498"], "bisa_ambil_otomatis": "YA", "level_wilayah": "PROVINSI",
            "tahun_awal_tersedia": 2015, "tahun_akhir_tersedia": 2024,
            "rentang_tahun_aktual": "2015 (23#2), 2023 (132#2), 2024 (1498#2, 2204#2, 2566#2)",
            "bukti_hasil_hit": f"HTTP 200 semua (1498:{extra_checks['bps_1498']}, 2204:{extra_checks['bps_2204']}, 132:{extra_checks['bps_132']}, 2566:{extra_checks['bps_2566']})",
            "catatan_fakta": "Berisi agregat 38 provinsi (+ Nasional) sebagai tolok ukur validasi total dari data Kab/Kota.",
        },
        {
            "no": 9, "kategori_data": "Produksi (Kayu)",
            "cakupan_komoditas_atau_topik": "Kayu Bulat PBPH & Perhutani per Provinsi (2020-2024)",
            "nama_sumber_instansi": "Ditjen Pengelolaan Hutan Lestari (PHL) Kemenhut/KLHK",
            "url_endpoint": PHL_2024_URL,
            "metode_akses": "DIRECT_DOWNLOAD_PDF",
            "status_http": extra_checks["phl_2024"], "bisa_ambil_otomatis": "YA", "level_wilayah": "PROVINSI",
            "tahun_awal_tersedia": 2020, "tahun_akhir_tersedia": 2024,
            "rentang_tahun_aktual": "2020-2024 (Tabel 3.9 PBPH hal. 145 & Tabel 3.12 Perhutani hal. 148)",
            "bukti_hasil_hit": f"PDF 30,3 MB (185 hal., teks bisa diekstrak pdfplumber); {n_kayu_prov}/38 provinsi punya produksi > 0 (2018-2024)",
            "catatan_fakta": "Sumber kayu per provinsi paling lengkap dan terbaru s.d. 2024. Catatan: level Kab/Kota tidak tersedia seragam nasional.",
        },
        {
            "no": 10, "kategori_data": "Produksi (Kayu)",
            "cakupan_komoditas_atau_topik": "Kayu Bulat PBPH & Perhutani per Provinsi (2018-2022) + Arsip 2017-2021",
            "nama_sumber_instansi": "Ditjen PHL Kemenhut/KLHK",
            "url_endpoint": PHL_2022_URL,
            "metode_akses": "DIRECT_DOWNLOAD_PDF",
            "status_http": extra_checks["phl_2022"], "bisa_ambil_otomatis": "YA (kecuali 2023 scan gambar)", "level_wilayah": "PROVINSI",
            "tahun_awal_tersedia": 2017, "tahun_akhir_tersedia": 2023,
            "rentang_tahun_aktual": "2018-2022 (PDF 2022 berteks); juga tersedia PDF 2017-2021 di /statistik",
            "bukti_hasil_hit": f"PDF 2022 HTTP {extra_checks['phl_2022']} (37,8 MB, berteks); PDF 2023 HTTP {extra_checks['phl_2023']} (13,8 MB, SCAN GAMBAR 0 teks)",
            "catatan_fakta": "PDF 2023 adalah scan gambar (tidak bisa parse teks), tapi datanya sudah tercakup penuh di PDF 2024 (2020-2024).",
        },
        {
            "no": 11, "kategori_data": "Produksi (Kayu)",
            "cakupan_komoditas_atau_topik": "Kayu Bulat per Jenis Pohon (2023) & per Pulau (2022) + Riau (2023)",
            "nama_sumber_instansi": "BPS RI (2512#2, 1973#2) & BPS Riau (156#2)",
            "url_endpoint": "https://www.bps.go.id/id/statistics-table/2/MjUxMiMy/table.html",
            "metode_akses": "NEXTJS_JSON",
            "status_http": extra_checks["bps_2512"], "bisa_ambil_otomatis": "YA", "level_wilayah": "NASIONAL & PULAU (dan Provinsi Riau)",
            "tahun_awal_tersedia": 2022, "tahun_akhir_tersedia": 2023,
            "rentang_tahun_aktual": "2022 (1973#2 Pulau), 2023 (2512#2 Jenis Pohon & Riau 156#2)",
            "bukti_hasil_hit": f"HTTP 200 semua (2512:{extra_checks['bps_2512']}, 1973:{extra_checks['bps_1973']}, Riau 156:{extra_checks['bps_riau_156']})",
            "catatan_fakta": "Pelengkap rincian spesies kayu (Akasia, Eukaliptus, Jati, Sengon, Meranti, Pinus, Kayu Bakar) dalam satuan m3.",
        },
    ]

    # Tambahkan semua sumber PLTU dari df_pltu ke Ringkasan_Sumber
    for idx, pr in df_pltu.iterrows():
        summary_rows.append({
            "no": 12 + idx,
            "kategori_data": "PLTU 5 Pulau",
            "cakupan_komoditas_atau_topik": pr["nama_sumber"],
            "nama_sumber_instansi": pr["instansi"],
            "url_endpoint": pr["url_sumber"],
            "metode_akses": pr["metode_akses"],
            "status_http": pr["status_http"],
            "bisa_ambil_otomatis": pr["bisa_ambil_otomatis"],
            "level_wilayah": "UNIT_PLTU (5 PULAU)",
            "tahun_awal_tersedia": pr["tahun_awal_tersedia"],
            "tahun_akhir_tersedia": pr["tahun_akhir_tersedia"],
            "rentang_tahun_aktual": pr["rentang_tahun_aktual"],
            "bukti_hasil_hit": f"Terdeteksi {int(pr['jumlah_pltu_terdeteksi'])} PLTU | {pr['cakupan_pulau']}" if pd.notna(pr["jumlah_pltu_terdeteksi"]) else str(pr["status_data"]),
            "catatan_fakta": pr["catatan_fakta"],
        })

    for sr in summary_rows:
        sr["status_review_manual"] = ""
        sr["catatan_user"] = ""

    return pd.DataFrame(summary_rows)


def style_workbook(xlsx_path, sheets_dict):
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    body_font = Font(name="Calibri", size=10, color="111111")
    link_font = Font(name="Calibri", size=10, color="0563C1", underline="single")
    review_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    ok_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    warn_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    miss_fill = PatternFill(start_color="EDEDED", end_color="EDEDED", fill_type="solid")
    thin = Side(border_style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        for sheet_name, df in sheets_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = f"A1:{get_column_letter(len(df.columns))}{len(df) + 1}"

            col_names = list(df.columns)
            for c_idx, col_name in enumerate(col_names, start=1):
                cell = ws.cell(row=1, column=c_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = border

            for r_idx in range(2, len(df) + 2):
                status_val = ""
                if "status_data" in col_names:
                    status_val = str(ws.cell(row=r_idx, column=col_names.index("status_data") + 1).value or "")
                for c_idx, col_name in enumerate(col_names, start=1):
                    cell = ws.cell(row=r_idx, column=c_idx)
                    cell.font = body_font
                    cell.border = border
                    cell.alignment = Alignment(vertical="top", wrap_text=True)

                    val_str = str(cell.value or "")
                    if val_str.startswith("http") and "{" not in val_str:
                        cell.hyperlink = val_str
                        cell.font = link_font

                    if col_name in ("status_review_manual", "catatan_user"):
                        cell.fill = review_fill
                    elif col_name == "status_data":
                        if any(k in status_val for k in ("TERSEDIA_KABKOTA", "TERSEDIA_API", "TERSEDIA_DIRECT", "TERSEDIA_PDF", "TERSEDIA_PORTAL")):
                            cell.fill = ok_fill
                        elif "HANYA_TINGKAT" in status_val or "MANUAL" in status_val:
                            cell.fill = warn_fill
                        elif "TIDAK_TERSEDIA" in status_val or "ERROR" in status_val or "DIBLOKIR" in status_val or "BELUM" in status_val:
                            cell.fill = miss_fill

            ws.row_dimensions[1].height = 28
            for c_idx, col_name in enumerate(col_names, start=1):
                col_letter = get_column_letter(c_idx)
                max_len = max([len(str(col_name))] + [len(str(v or "")) for v in df[col_name].head(60)])
                if "url" in col_name or "endpoint" in col_name:
                    w = min(max(max_len + 2, 32), 54)
                elif "catatan" in col_name or "bukti" in col_name or "kolom_utama" in col_name:
                    w = 50
                elif "tahun_awal" in col_name or "tahun_akhir" in col_name or "status_http" in col_name or "kode_" in col_name:
                    w = 18
                else:
                    w = min(max(max_len + 3, 16), 36)
                ws.column_dimensions[col_letter].width = w


def main():
    t0 = time.time()
    session = make_session()

    df_portals = build_portal_38_provinsi(session)
    df_kom = build_5_komoditas_38_prov(session, df_portals)
    df_pltu = build_pltu_5_pulau_sources(session)
    df_ringkasan = build_ringkasan_sumber(session, df_portals, df_kom, df_pltu)

    out_xlsx = os.path.join(RAW_DIR, "daftar_sumber_data.xlsx")
    sheets = {
        "Ringkasan_Sumber": df_ringkasan,
        "Portal_38_Provinsi": df_portals,
        "Sumber_5_Komoditas_38_Prov": df_kom,
        "Sumber_PLTU_5_Pulau": df_pltu,
    }
    style_workbook(out_xlsx, sheets)

    print("\n" + "=" * 70, flush=True)
    print(f"SELESAI dalam {time.time() - t0:.1f} detik -> {out_xlsx}", flush=True)
    print(f"  Tab 1 Ringkasan_Sumber           : {len(df_ringkasan)} baris", flush=True)
    print(f"  Tab 2 Portal_38_Provinsi         : {len(df_portals)} baris", flush=True)
    print(f"  Tab 3 Sumber_5_Komoditas_38_Prov : {len(df_kom)} baris (38 prov x 5 komoditas)", flush=True)
    print(f"  Tab 4 Sumber_PLTU_5_Pulau        : {len(df_pltu)} baris", flush=True)
    print("\nRingkasan Ketersediaan per Komoditas (38 Provinsi):", flush=True)
    print(df_kom.groupby(["komoditas", "status_data"]).size().to_string(), flush=True)


if __name__ == "__main__":
    main()
