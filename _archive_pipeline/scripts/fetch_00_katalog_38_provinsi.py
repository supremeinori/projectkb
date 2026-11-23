"""
Tahap 1: Membangun & memverifikasi katalog endpoint 38 portal provinsi Indonesia
(BPS Provinsi *.bps.go.id + WebAPI BPS + Portal Satu Data Pemprov yang terverifikasi).
Prinsip Saintis: Semua status HTTP & kode domain diverifikasi langsung (as-is).
"""

import os
import re
import time
import requests
import pandas as pd

RAW_DIR = "raw_data"
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Daftar resmi 38 Provinsi Indonesia (34 + 4 pemekaran Papua)
# Kode BPS mengikuti Permendagri / Master File Desa BPS terbaru:
# 91=Papua Barat, 92=Papua Barat Daya (cek aktual di portal), 94=Papua, 95=Papua Selatan, 96=Papua Tengah, 97=Papua Pegunungan
# Skrip ini akan otomatis mendeteksi domain code aktual dari HTML portal masing-masing jika tersedia!
PROVINCES = [
    # SUMATERA (10)
    ("1100", "Aceh", "Sumatera", "aceh", "https://data.acehprov.go.id"),
    ("1200", "Sumatera Utara", "Sumatera", "sumut", "https://satudata.sumutprov.go.id"),
    ("1300", "Sumatera Barat", "Sumatera", "sumbar", "https://data.sumbarprov.go.id"),
    ("1400", "Riau", "Sumatera", "riau", "https://satudata.riau.go.id"),
    ("1500", "Jambi", "Sumatera", "jambi", "https://data.jambiprov.go.id"),
    ("1600", "Sumatera Selatan", "Sumatera", "sumsel", "https://satudata.sumselprov.go.id"),
    ("1700", "Bengkulu", "Sumatera", "bengkulu", "https://satudata.bengkuluprov.go.id"),
    ("1800", "Lampung", "Sumatera", "lampung", "https://data.lampungprov.go.id"),
    ("1900", "Kepulauan Bangka Belitung", "Sumatera", "babel", "https://satudata.babelprov.go.id"),
    ("2100", "Kepulauan Riau", "Sumatera", "kepri", "https://satudata.kepriprov.go.id"),
    # JAWA (6)
    ("3100", "DKI Jakarta", "Jawa", "jakarta", "https://satudata.jakarta.go.id"),
    ("3200", "Jawa Barat", "Jawa", "jabar", "https://opendata.jabarprov.go.id"),
    ("3300", "Jawa Tengah", "Jawa", "jateng", "https://data.jatengprov.go.id"),
    ("3400", "DI Yogyakarta", "Jawa", "yogyakarta", "https://satudata.jogjaprov.go.id"),
    ("3500", "Jawa Timur", "Jawa", "jatim", "https://opendata.jatimprov.go.id"),
    ("3600", "Banten", "Jawa", "banten", "https://satudata.bantenprov.go.id"),
    # BALI, NUSA TENGGARA & MALUKU (5)
    ("5100", "Bali", "Bali-Nusra-Maluku", "bali", "https://satudata.baliprov.go.id"),
    ("5200", "Nusa Tenggara Barat", "Bali-Nusra-Maluku", "ntb", "https://data.ntbprov.go.id"),
    ("5300", "Nusa Tenggara Timur", "Bali-Nusra-Maluku", "ntt", "https://satudata.nttprov.go.id"),
    # KALIMANTAN (5)
    ("6100", "Kalimantan Barat", "Kalimantan", "kalbar", "https://data.kalbarprov.go.id"),
    ("6200", "Kalimantan Tengah", "Kalimantan", "kalteng", "https://satudata.kalteng.go.id"),
    ("6300", "Kalimantan Selatan", "Kalimantan", "kalsel", "https://data.kalselprov.go.id"),
    ("6400", "Kalimantan Timur", "Kalimantan", "kaltim", "https://data.kaltimprov.go.id"),
    ("6500", "Kalimantan Utara", "Kalimantan", "kaltara", "https://satudata.kaltaraprov.go.id"),
    # SULAWESI (6)
    ("7100", "Sulawesi Utara", "Sulawesi", "sulut", "https://satudata.sulutprov.go.id"),
    ("7200", "Sulawesi Tengah", "Sulawesi", "sulteng", "https://satudata.sultengprov.go.id"),
    ("7300", "Sulawesi Selatan", "Sulawesi", "sulsel", "https://satudata.sulselprov.go.id"),
    ("7400", "Sulawesi Tenggara", "Sulawesi", "sultra", "https://satudata.sultraprov.go.id"),
    ("7500", "Gorontalo", "Sulawesi", "gorontalo", "https://satudata.gorontaloprov.go.id"),
    ("7600", "Sulawesi Barat", "Sulawesi", "sulbar", "https://satudata.sulbarprov.go.id"),
    # MALUKU (2)
    ("8100", "Maluku", "Bali-Nusra-Maluku", "maluku", "https://satudata.malukuprov.go.id"),
    ("8200", "Maluku Utara", "Bali-Nusra-Maluku", "malut", "https://satudata.malutprov.go.id"),
    # PAPUA (6)
    ("9100", "Papua Barat", "Papua", "papuabarat", "https://satudata.papuabaratprov.go.id"),
    ("9200", "Papua Barat Daya", "Papua", "papuabaratdaya", None),
    ("9400", "Papua", "Papua", "papua", "https://satudata.papua.go.id"),
    ("9500", "Papua Selatan", "Papua", "papuaselatan", None),
    ("9600", "Papua Tengah", "Papua", "papuatengah", None),
    ("9700", "Papua Pegunungan", "Papua", "papuapegunungan", None),
]


def check_url(url, timeout=10, get_body=False):
    if not url:
        return None, None, "Tidak ada URL terdata"
    try:
        if get_body:
            r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            return r.status_code, r.text, None
        else:
            r = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if r.status_code in (405, 403):
                r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True, stream=True)
            return r.status_code, None, None
    except requests.exceptions.SSLError:
        return "SSL_ERROR", None, "Sertifikat SSL bermasalah"
    except requests.exceptions.ConnectTimeout:
        return "TIMEOUT", None, "Koneksi timeout"
    except requests.exceptions.ReadTimeout:
        return "TIMEOUT", None, "Read timeout"
    except requests.exceptions.ConnectionError as e:
        msg = str(e)
        if "NameResolutionError" in msg or "getaddrinfo failed" in msg:
            return "DNS_NOT_FOUND", None, "Domain tidak terdaftar di DNS"
        return "CONN_ERROR", None, f"Koneksi ditolak/reset: {type(e).__name__}"
    except Exception as e:
        return "ERROR", None, str(e)[:120]


def main():
    print("Memverifikasi endpoint 38 portal BPS Provinsi + Satu Data Pemprov...")
    rows = []
    for default_domain, prov, pulau, sub, pemprov_url in PROVINCES:
        bps_base = f"https://{sub}.bps.go.id"
        bps_table = f"{bps_base}/id/statistics-table"

        # Cek portal BPS (GET untuk sekaligus ekstrak domain code aktual dari HTML jika ada)
        status_bps, body, err_bps = check_url(bps_table, timeout=12, get_body=True)
        detected_domain = default_domain
        note_bps = ""
        if body:
            # Cari domain code 4 digit di HTML/Next.js props seperti "domain":"3500" atau "domain_id":"3500"
            m = re.search(r'"domain(?:_id)?"\s*:\s*"(\d{4})"', body)
            if m:
                detected_domain = m.group(1)
            elif re.search(r'\\"domain(?:_id)?\\":\\"(\d{4})\\"', body):
                detected_domain = re.search(r'\\"domain(?:_id)?\\":\\"(\d{4})\\"', body).group(1)
            note_bps = f"Aktif (HTTP {status_bps})"
        else:
            note_bps = err_bps or f"HTTP {status_bps}"

        # Cek portal Pemprov (jika ada)
        if pemprov_url:
            status_pemprov, _, err_pemprov = check_url(pemprov_url, timeout=8, get_body=False)
            note_pemprov = f"HTTP {status_pemprov}" if not err_pemprov else err_pemprov
        else:
            status_pemprov = None
            note_pemprov = "Belum terdata portal Satu Data mandiri (provinsi pemekaran)"

        status_data = "TERSEDIA_PORTAL_BPS" if status_bps == 200 else "TIDAK_TERSEDIA_DI_PORTAL"
        catatan = f"BPS: {note_bps}; Pemprov: {note_pemprov}"
        if detected_domain != default_domain:
            catatan += f" [Domain aktual terdeteksi: {detected_domain}]"

        webapi_endpoint = f"https://webapi.bps.go.id/v1/api/list/model/var/domain/{detected_domain}/key/{{BPS_API_KEY}}"

        print(f"  [{detected_domain}] {prov:<26} | {pulau:<17} | BPS: {str(status_bps):<13} | Pemprov: {str(status_pemprov)}")
        rows.append({
            "kode_domain_bps": detected_domain,
            "provinsi": prov,
            "pulau": pulau,
            "masuk_5_pulau_pltu": pulau in {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"},
            "url_bps_provinsi": bps_base,
            "url_tabel_statistik_bps": bps_table,
            "status_http_bps": status_bps,
            "endpoint_webapi_bps": webapi_endpoint,
            "url_satudata_pemprov": pemprov_url,
            "status_http_pemprov": status_pemprov,
            "status_data": status_data,
            "sumber_url": bps_table,
            "catatan_fakta": catatan,
        })
        time.sleep(0.4)

    df = pd.DataFrame(rows)
    out_csv = os.path.join(RAW_DIR, "00_katalog_endpoint_38_provinsi.csv")
    out_xlsx = os.path.join(RAW_DIR, "00_katalog_endpoint_38_provinsi.xlsx")
    df.to_csv(out_csv, index=False)
    df.to_excel(out_xlsx, index=False)

    print("\n=== RINGKASAN KATALOG 38 PROVINSI ===")
    print("Total provinsi:", len(df))
    print("BPS HTTP 200  :", (df["status_http_bps"] == 200).sum())
    print("Pemprov 200   :", (df["status_http_pemprov"] == 200).sum())
    print(f"Disimpan ke: {out_xlsx} & {out_csv}")


if __name__ == "__main__":
    main()
