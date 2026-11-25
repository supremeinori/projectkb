"""
Utilitas bersama untuk Fase 2: Penarikan Raw Data (Strict Scientist / Zero-Merge).
- Parser angka format Indonesia (ketat membedakan NULL vs 0).
- Writer CSV standar UTF-8 with BOM (utf-8-sig), delimiter koma, desimal titik.
- HTTP session dengan retry otomatis + logger per request (JSONL).
- Pembuatan hierarki 4 folder raw_data/ sesuai PLAN_TARIK_RAW_DATA.md.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "raw_data"
ARCHIVE_PDF_DIR = PROJECT_ROOT / "_archive_pipeline" / "raw_pdfs"
LOG_DIR = PROJECT_ROOT / "scripts" / "extract" / "_logs"

FIVE_ISLANDS = {"Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Papua"}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

# 38 Provinsi Indonesia (kode BPS 2 digit, domain WebAPI 4 digit, nama resmi, slug file, pulau, subdomain BPS)
PROVINCES_38 = [
    ("11", "1100", "Aceh", "aceh", "Sumatera", "aceh"),
    ("12", "1200", "Sumatera Utara", "sumatera_utara", "Sumatera", "sumut"),
    ("13", "1300", "Sumatera Barat", "sumatera_barat", "Sumatera", "sumbar"),
    ("14", "1400", "Riau", "riau", "Sumatera", "riau"),
    ("15", "1500", "Jambi", "jambi", "Sumatera", "jambi"),
    ("16", "1600", "Sumatera Selatan", "sumatera_selatan", "Sumatera", "sumsel"),
    ("17", "1700", "Bengkulu", "bengkulu", "Sumatera", "bengkulu"),
    ("18", "1800", "Lampung", "lampung", "Sumatera", "lampung"),
    ("19", "1900", "Kepulauan Bangka Belitung", "kepulauan_bangka_belitung", "Sumatera", "babel"),
    ("21", "2100", "Kepulauan Riau", "kepulauan_riau", "Sumatera", "kepri"),
    ("31", "3100", "DKI Jakarta", "dki_jakarta", "Jawa", "jakarta"),
    ("32", "3200", "Jawa Barat", "jawa_barat", "Jawa", "jabar"),
    ("33", "3300", "Jawa Tengah", "jawa_tengah", "Jawa", "jateng"),
    ("34", "3400", "DI Yogyakarta", "di_yogyakarta", "Jawa", "yogyakarta"),
    ("35", "3500", "Jawa Timur", "jawa_timur", "Jawa", "jatim"),
    ("36", "3600", "Banten", "banten", "Jawa", "banten"),
    ("51", "5100", "Bali", "bali", "Bali-Nusra-Maluku", "bali"),
    ("52", "5200", "Nusa Tenggara Barat", "nusa_tenggara_barat", "Bali-Nusra-Maluku", "ntb"),
    ("53", "5300", "Nusa Tenggara Timur", "nusa_tenggara_timur", "Bali-Nusra-Maluku", "ntt"),
    ("61", "6100", "Kalimantan Barat", "kalimantan_barat", "Kalimantan", "kalbar"),
    ("62", "6200", "Kalimantan Tengah", "kalimantan_tengah", "Kalimantan", "kalteng"),
    ("63", "6300", "Kalimantan Selatan", "kalimantan_selatan", "Kalimantan", "kalsel"),
    ("64", "6400", "Kalimantan Timur", "kalimantan_timur", "Kalimantan", "kaltim"),
    ("65", "6500", "Kalimantan Utara", "kalimantan_utara", "Kalimantan", "kaltara"),
    ("71", "7100", "Sulawesi Utara", "sulawesi_utara", "Sulawesi", "sulut"),
    ("72", "7200", "Sulawesi Tengah", "sulawesi_tengah", "Sulawesi", "sulteng"),
    ("73", "7300", "Sulawesi Selatan", "sulawesi_selatan", "Sulawesi", "sulsel"),
    ("74", "7400", "Sulawesi Tenggara", "sulawesi_tenggara", "Sulawesi", "sultra"),
    ("75", "7500", "Gorontalo", "gorontalo", "Sulawesi", "gorontalo"),
    ("76", "7600", "Sulawesi Barat", "sulawesi_barat", "Sulawesi", "sulbar"),
    ("81", "8100", "Maluku", "maluku", "Bali-Nusra-Maluku", "maluku"),
    ("82", "8200", "Maluku Utara", "maluku_utara", "Bali-Nusra-Maluku", "malut"),
    ("91", "9100", "Papua Barat", "papua_barat", "Papua", "papuabarat"),
    ("92", "9200", "Papua Barat Daya", "papua_barat_daya", "Papua", "papuabaratdaya"),
    ("94", "9400", "Papua", "papua", "Papua", "papua"),
    ("95", "9500", "Papua Selatan", "papua_selatan", "Papua", "papuaselatan"),
    ("96", "9600", "Papua Tengah", "papua_tengah", "Papua", "papuatengah"),
    ("97", "9700", "Papua Pegunungan", "papua_pegunungan", "Papua", "papuapegunungan"),
]

PROV_BY_CODE = {p[0]: p for p in PROVINCES_38}


def ensure_raw_folder_tree() -> list[Path]:
    """Buat seluruh hierarki 4 folder raw_data/ dan folder log ekstraksi."""
    dirs = [
        LOG_DIR,
        # Folder 1: BDSP & Satu Data Kementan
        RAW_DIR / "01_bdsp_kementan" / "padi" / "kabkota",
        RAW_DIR / "01_bdsp_kementan" / "padi" / "provinsi",
        RAW_DIR / "01_bdsp_kementan" / "kelapa_sawit" / "kabkota",
        RAW_DIR / "01_bdsp_kementan" / "kelapa_sawit" / "provinsi",
        RAW_DIR / "01_bdsp_kementan" / "tebu" / "kabkota",
        RAW_DIR / "01_bdsp_kementan" / "tebu" / "provinsi",
        RAW_DIR / "01_bdsp_kementan" / "jagung" / "kabkota",
        RAW_DIR / "01_bdsp_kementan" / "jagung" / "provinsi",
        RAW_DIR / "01_bdsp_kementan" / "satudata_kementan",
        # Folder 2: BPS RI & slot BPS Provinsi
        RAW_DIR / "02_bps" / "bps_ri" / "1498_padi",
        RAW_DIR / "02_bps" / "bps_ri" / "2204_jagung",
        RAW_DIR / "02_bps" / "bps_ri" / "2566_perkebunan",
        RAW_DIR / "02_bps" / "bps_ri" / "132_perkebunan_historis",
        RAW_DIR / "02_bps" / "bps_ri" / "2512_kayu_jenis_pohon",
        RAW_DIR / "02_bps" / "bps_ri" / "1973_kayu_hph_pulau",
        RAW_DIR / "02_bps" / "bps_provinsi",
        # Folder 3: KLHK PHL Kayu Bulat
        RAW_DIR / "03_klhk_phl_kayu" / "buku_2024",
        RAW_DIR / "03_klhk_phl_kayu" / "buku_2022",
        # Folder 4: PLTU 5 Pulau
        RAW_DIR / "04_pltu_5_pulau" / "climatetrace",
        RAW_DIR / "04_pltu_5_pulau" / "wri_gppd",
        RAW_DIR / "04_pltu_5_pulau" / "crea_2025",
        RAW_DIR / "04_pltu_5_pulau" / "gem_gcpt",
        # Folder 5: Data Komplementer Karakteristik & HHV Biomassa (315 sampel + referensi)
        RAW_DIR / "05_biomassa_komplementer",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def today_iso() -> str:
    return dt.date.today().isoformat()


def slugify(text: str) -> str:
    s = str(text or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def normalize_prov_name(s: str) -> str:
    """Standarisasi nama provinsi hanya untuk pencocokan audit (tidak mengubah raw CSV)."""
    t = str(s or "").upper().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"^PROVINSI\s+", "", t)
    t = t.replace("NANGGROE ACEH DARUSSALAM", "ACEH").replace("NANGROE ACEH DARUSSALAM", "ACEH")
    t = t.replace("DAERAH KHUSUS IBUKOTA ", "DKI ").replace("D.K.I. ", "DKI ")
    t = t.replace("DAERAH ISTIMEWA ", "DI ").replace("D.I. ", "DI ")
    t = t.replace("KEP. BANGKA BELITUNG", "KEPULAUAN BANGKA BELITUNG")
    t = t.replace("KEP.BANGKA BELITUNG", "KEPULAUAN BANGKA BELITUNG")
    t = t.replace("BANGKA BELITUNG", "KEPULAUAN BANGKA BELITUNG")
    t = t.replace("KEPULAUAN KEPULAUAN ", "KEPULAUAN ")
    t = t.replace("KEP. RIAU", "KEPULAUAN RIAU").replace("KEP.RIAU", "KEPULAUAN RIAU")
    t = t.replace("SUMATRA", "SUMATERA")
    return t


def parse_id_number(val: Any, strip_footnotes: bool = False) -> float:
    """
    Parser angka format Indonesia (1.234.567,89 -> 1234567.89).
    Ketat membedakan NULL vs 0:
    - None, '', '-', '–', '—', '...', 'N/A', 'na', 'null' -> np.nan (NULL)
    - '0', '0,00', '0.00' -> 0.0
    """
    if val is None:
        return np.nan
    if isinstance(val, (int, float, np.number)):
        return float(val) if not pd.isna(val) else np.nan
    s = str(val).strip()
    if strip_footnotes:
        s = re.sub(r"\*+", "", s).strip()
    # Normalisasi spasi dalam angka (kadang muncul di PDF)
    s = s.replace("\u00a0", " ").strip()
    if not s or s.lower() in {"-", "–", "—", "...", "..", "n/a", "na", "null", "none", "nan"}:
        return np.nan

    # Hilangkan spasi di antara angka
    s = re.sub(r"(?<=\d)\s+(?=\d)", "", s)

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # Format Indonesia: 1.234.567,89
            s = s.replace(".", "").replace(",", ".")
        else:
            # Format Inggris: 1,234,567.89
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        # Jika ada >1 koma (1,234,567) atau tepat 3 digit di belakang koma dengan ribuan Inggris
        if len(parts) > 2:
            s = s.replace(",", "")
        elif len(parts[-1]) == 3 and len(parts[0]) <= 3 and not parts[0].startswith("0"):
            # Hati-hati: bisa ribuan Inggris (1,234) atau 3 desimal Indonesia (12,345).
            # Di sumber Indonesia (BDSP/KLHK/BPS), koma adalah desimal (misal 1,250 ton atau 379244,91).
            s = s.replace(",", ".")
        else:
            s = s.replace(",", ".")
    elif "." in s:
        parts = s.split(".")
        # Format ribuan Indonesia murni: 1.234 atau 1.234.567 (semua segmen setelah pertama 3 digit)
        if len(parts) > 1 and all(len(p) == 3 and p.isdigit() for p in parts[1:]) and parts[0].lstrip("-").isdigit() and len(parts[0].lstrip("-")) <= 3:
            s = s.replace(".", "")
        # else: biarkan sebagai desimal titik (misal 16.5 atau 1234.56)

    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_bdsp_number(val: Any) -> float:
    """
    Parser khusus keluaran BDSP Kementan:
    - '-' atau kosong -> np.nan (NULL)
    - '0' atau '0,00' -> 0.0
    - '379244,91' atau '1.234.567,89' -> float
    """
    if val is None:
        return np.nan
    s = str(val).strip().replace("\u00a0", "")
    if not s or s in {"-", "–", "—", "..."}:
        return np.nan
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_phl_number(val: Any) -> float:
    """
    Parser khusus PDF Statistik Ditjen PHL KLHK (angka Indonesia: titik ribuan, koma desimal 2 digit).
    Tanda '-' / kosong -> np.nan (NULL).
    """
    if val is None:
        return np.nan
    s = str(val).strip().replace("\u00a0", " ")
    if not s or s in {"-", "–", "—", "...", "n/a", "N/A"}:
        return np.nan
    # Hapus spasi antar digit akibat layout PDF
    s = re.sub(r"(?<=\d)\s+(?=\d)", "", s)
    s = re.sub(r"(?<=\d)\s*([.,])\s*(?=\d)", r"\1", s)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) > 2:
            s = s.replace(",", "")
        elif len(parts[-1]) <= 2:
            s = s.replace(",", ".")
        else:
            # Di PHL 2022/2024 kadang titik ribuan terbaca koma? Cek: PDF 2024 pakai koma ribuan & titik desimal (Inggris) atau sebaliknya!
            s = s.replace(",", "")
    elif "." in s:
        parts = s.split(".")
        if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
            s = s.replace(".", "")
        elif len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def make_http_session(retries: int = 3, backoff_factor: float = 0.8) -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
        allowed_methods=["GET", "POST", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class RequestLogger:
    """Pencatat log per HTTP request ke JSONL agar kegagalan parsial mudah dilacak & diulang."""

    def __init__(self, script_name: str):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.log_path = LOG_DIR / f"{script_name}.jsonl"

    def log(
        self,
        target_id: str,
        method: str,
        url: str,
        status: Any,
        duration_ms: float,
        rows: Optional[int] = None,
        output_file: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        entry = {
            "ts": dt.datetime.now().isoformat(timespec="seconds"),
            "target_id": target_id,
            "method": method,
            "url": url,
            "status": status,
            "duration_ms": round(duration_ms, 1),
            "rows": rows,
            "output_file": output_file,
            "error": error,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def add_provenance_cols(
    df: pd.DataFrame,
    sumber_instansi: str,
    sumber_url: str,
    satuan_asli: str,
    level_wilayah: str,
    tanggal_tarik: Optional[str] = None,
) -> pd.DataFrame:
    """Tambahkan kolom metadata asal standar tanpa mengubah nilai angka aslinya."""
    out = df.copy()
    out["sumber_instansi"] = sumber_instansi
    out["sumber_url"] = sumber_url
    out["satuan_asli"] = satuan_asli
    out["level_wilayah"] = level_wilayah
    out["tanggal_tarik"] = tanggal_tarik or today_iso()
    return out


def write_raw_csv(df: pd.DataFrame, path: Path | str) -> Path:
    """Simpan CSV mentah sesuai standar Fase 2: UTF-8 with BOM, delimiter koma, desimal titik, NULL kosong."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(
        p,
        index=False,
        encoding="utf-8-sig",
        sep=",",
        na_rep="",
        lineterminator="\n",
    )
    return p


def map_pulau_from_lokasi(lokasi: str) -> str:
    if not isinstance(lokasi, str) or not lokasi.strip():
        return "Tidak Diketahui"
    low = lokasi.lower()
    if any(k in low for k in ["jawa", "banten", "jakarta", "yogyakarta", "madura"]):
        return "Jawa"
    if any(
        k in low
        for k in [
            "sumatra", "sumatera", "aceh", "riau", "jambi", "bengkulu",
            "lampung", "bangka", "belitung", "batam", "kepulauan riau",
        ]
    ):
        return "Sumatera"
    if "kalimantan" in low:
        return "Kalimantan"
    if any(k in low for k in ["sulawesi", "gorontalo"]):
        return "Sulawesi"
    if "papua" in low:
        return "Papua"
    if any(k in low for k in ["bali", "nusa tenggara", "lombok", "sumbawa", "ende", "kupang"]):
        return "Bali-Nusa Tenggara"
    if any(k in low for k in ["maluku", "tidore", "sofifi", "oba"]):
        return "Maluku"
    return "Lainnya"


def map_pulau_from_coords(lat: Any, lon: Any, name: str = "") -> str:
    """Pemetaan 5 pulau utama Indonesia (plus Bali-Nusra & Maluku) dari nama & koordinat."""
    low = str(name or "").lower()
    if any(k in low for k in ["papua", "jayapura", "holtekamp", "amamapare", "timika", "sorong", "manokwari", "nabire", "merauke"]):
        return "Papua"
    if any(k in low for k in ["sulawesi", "sulsel", "sulut", "sulteng", "sultra", "gorontalo", "barru", "amurang", "kendari", "jeneponto", "punagaya", "palu", "morowali", "kobe", "makassar", "bau-bau", "tanasa", "ampana", "bitung"]):
        return "Sulawesi"
    if any(k in low for k in ["kalimantan", "kaltim", "kalteng", "kalbar", "kalsel", "kaltara", "pulang pisau", "asam-asam", "asam asam", "ketapang", "sanggau", "sintang", "balikpapan", "bontang", "berau", "tarakan", "malinau", "bengkayang", "banjarmasin", "sampit", "pangkalan bun", "tabalong", "adaro", "kutai", "samarinda", "kalselteng", "parit baru"]):
        return "Kalimantan"
    if any(k in low for k in ["sumatra", "sumatera", "aceh", "nagan raya", "pangkalan susu", "medan", "belawan", "labuhan angin", "ombilin", "teluk sirih", "tenayan", "riau", "tembilahan", "jambi", "palembang", "bukit asam", "banyuasin", "muara enim", "bengkulu", "lampung", "tarahan", "sebalang", "bangka", "air anyir", "belitung", "batam", "tanjung balai", "bintan", "simbang", "sumsel"]):
        return "Sumatera"
    if any(k in low for k in ["bali", "celukan bawang", "lombok", "jeranjang", "sumbawa", "batu hijau", "kupang", "bolok", "ende", "ropa", "flores", "ntb", "ntt"]):
        return "Bali-Nusa Tenggara"
    if any(k in low for k in ["maluku", "ambon", "tidore", "ternate", "halmahera", "weda", "obi", "sofifi"]):
        return "Maluku"
    if any(k in low for k in ["jawa", "java", "banten", "suralaya", "serang", "lontar", "labuan", "cilegon", "merak", "jakarta", "cikarang", "babelan", "indramayu", "cirebon", "pelabuhan ratu", "cilacap", "adipala", "rembang", "tanjung jati", "batang", "jepara", "pacitan", "paiton", "tuban", "tanjung awar", "gresik", "surabaya", "probolinggo", "karawang", "bekasi", "purwakarta", "tanjung priok"]):
        return "Jawa"

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return "Tidak Diketahui"
    if pd.isna(lat_f) or pd.isna(lon_f):
        return "Tidak Diketahui"
    if lon_f >= 130.5:
        return "Papua"
    if lon_f >= 125.0 and lat_f > -8.5:
        return "Maluku"
    if 118.2 <= lon_f < 125.5 and lat_f > -6.5:
        return "Sulawesi"
    if 108.5 <= lon_f < 119.5 and lat_f > -4.5:
        return "Kalimantan"
    if lon_f < 105.6 or (lon_f < 108.5 and lat_f > -5.9):
        return "Sumatera"
    if 105.0 <= lon_f <= 114.6 and -9.0 <= lat_f <= -5.5:
        return "Jawa"
    if 114.6 < lon_f <= 127.5 and lat_f <= -7.5:
        return "Bali-Nusa Tenggara"
    return "Lainnya"


def load_bps_api_key() -> str:
    key = os.environ.get("BPS_API_KEY", "").strip()
    if key:
        return key
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("BPS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


if __name__ == "__main__":
    created = ensure_raw_folder_tree()
    print(f"Created/verified {len(created)} directories under {RAW_DIR} and {LOG_DIR}.")
