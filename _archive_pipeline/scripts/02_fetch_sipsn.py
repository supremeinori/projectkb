"""
Script 02: Fetch and Standardize SIPSN KemenLH (Timbulan & Komposisi Sampah Nasional)
Sources:
1. Timbulan: https://sampahnasional.kemenlh.go.id/indikatif/api/v2/tbl_timbulan
2. Komposisi: https://sampahnasional.kemenlh.go.id/indikatif/api/v2/tbl_komposisi
Output:
- Raw JSON files in data/raw/sipsn/
- Clean standardized table: data/interim/sipsn_clean.csv
"""

import os
import sys
import time
import json
import urllib3
import requests
import pandas as pd

urllib3.disable_warnings()

RAW_SIPSN_DIR = os.path.join("biomass-feedstock-finder", "data", "raw", "sipsn")
INTERIM_DIR = os.path.join("biomass-feedstock-finder", "data", "interim")
DOCS_DIR = os.path.join("biomass-feedstock-finder", "docs")

os.makedirs(RAW_SIPSN_DIR, exist_ok=True)
os.makedirs(INTERIM_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

BASE_URL = "https://sampahnasional.kemenlh.go.id/indikatif/api/v2"
API_KEY = "80kkc8kw88w40cg8osc84c4ocg4kgks840ck8s4g"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
PERIODS = [1, 2]

def fetch_sipsn_endpoint(endpoint_name, year, period):
    raw_filename = f"{endpoint_name}_{year}_p{period}.json"
    raw_path = os.path.join(RAW_SIPSN_DIR, raw_filename)
    
    # Check if already cached locally
    if os.path.exists(raw_path):
        with open(raw_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data.get("data", [])
            except Exception:
                pass

    url = f"{BASE_URL}/{endpoint_name}"
    params = {
        "key": API_KEY,
        "t": year,
        "p": period,
        "lmt": 1000,
        "pg": 1
    }
    
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=25, verify=False)
        r.raise_for_status()
        resp_json = r.json()
        
        # Save raw response
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(resp_json, f, ensure_ascii=False, indent=2)
            
        time.sleep(1.5) # Polite delay
        return resp_json.get("data", [])
    except Exception as e:
        print(f"  [Warning] Failed fetching {endpoint_name} {year} p{period}: {e}")
        return []

def main():
    print("=" * 60)
    print("STARTING 02_FETCH_SIPSN.PY")
    print("=" * 60)
    
    all_timbulan_records = []
    all_komposisi_records = []
    
    for y in YEARS:
        for p in PERIODS:
            print(f"Fetching SIPSN year {y} period {p}...")
            # 1. Timbulan
            timb_data = fetch_sipsn_endpoint("tbl_timbulan", y, p)
            if timb_data:
                for row in timb_data:
                    all_timbulan_records.append({
                        "tahun": int(row.get("tahun", y)),
                        "periode": int(row.get("periode", p)),
                        "provinsi": str(row.get("nama_provinsi", "")).strip(),
                        "kabkota": str(row.get("nama_kabkota", "")).strip(),
                        "timbulan_harian_ton": pd.to_numeric(row.get("jml_timbulan_harian", None), errors="coerce"),
                        "timbulan_tahunan_ton": pd.to_numeric(row.get("jml_timbulan_tahun", None), errors="coerce")
                    })
            
            # 2. Komposisi
            komp_data = fetch_sipsn_endpoint("tbl_komposisi", y, p)
            if komp_data:
                for row in komp_data:
                    all_komposisi_records.append({
                        "tahun": int(row.get("tahun", y)),
                        "periode": int(row.get("periode", p)),
                        "provinsi": str(row.get("provinsi", "")).strip(),
                        "kabkota": str(row.get("kabkota", "")).strip(),
                        "pct_sisa_makanan": pd.to_numeric(row.get("Sisa Makanan", None), errors="coerce"),
                        "pct_kayu_ranting": pd.to_numeric(row.get("Kayu Ranting", None), errors="coerce"),
                        "pct_kertas_karton": pd.to_numeric(row.get("Kertas/Karton", None), errors="coerce"),
                        "pct_plastik": pd.to_numeric(row.get("Plastik", None), errors="coerce"),
                        "pct_logam": pd.to_numeric(row.get("Logam", None), errors="coerce"),
                        "pct_kain": pd.to_numeric(row.get("Kain", None), errors="coerce"),
                        "pct_karet_kulit": pd.to_numeric(row.get("Karet/Kulit", None), errors="coerce"),
                        "pct_kaca": pd.to_numeric(row.get("Kaca", None), errors="coerce"),
                        "pct_lainnya": pd.to_numeric(row.get("Lainnya", None), errors="coerce")
                    })

    df_timb = pd.DataFrame(all_timbulan_records)
    df_komp = pd.DataFrame(all_komposisi_records)
    
    print(f"\nRaw Timbulan extracted: {len(df_timb)} rows")
    print(f"Raw Komposisi extracted: {len(df_komp)} rows")
    
    # Merge timbulan and komposisi
    if not df_timb.empty and not df_komp.empty:
        df_merged = pd.merge(
            df_timb,
            df_komp,
            on=["tahun", "periode", "provinsi", "kabkota"],
            how="outer"
        )
    elif not df_timb.empty:
        df_merged = df_timb
    else:
        df_merged = df_komp
        
    df_merged["source_dataset"] = "sipsn_kemenlh"
    
    # Sort and clean
    df_merged = df_merged.sort_values(by=["tahun", "periode", "provinsi", "kabkota"]).reset_index(drop=True)
    
    out_csv = os.path.join(INTERIM_DIR, "sipsn_clean.csv")
    df_merged.to_csv(out_csv, index=False)
    
    print(f"\nSuccessfully wrote cleaned SIPSN dataset to: {out_csv}")
    print(f"Total rows: {len(df_merged):,}")
    print(f"Total columns: {len(df_merged.columns)}")
    
    print("\n--- Missing Value Audit ---")
    missing = df_merged.isnull().mean() * 100
    for col, pct in missing.items():
        print(f"  {col:<25}: {pct:>6.2f}% missing ({df_merged[col].isnull().sum()} rows)")
        
    print("\nSummary Rows by Year:")
    print(df_merged["tahun"].value_counts().sort_index().to_string())
    print("\nDone 02_fetch_sipsn.py successfully!\n")

if __name__ == "__main__":
    main()
