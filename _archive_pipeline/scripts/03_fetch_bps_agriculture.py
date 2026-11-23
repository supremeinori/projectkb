"""
Script 03: Fetch and Standardize BPS Agriculture & Plantation Data
Commodities: Padi, Kelapa Sawit, Jagung, Tebu
Output:
- Raw JSON files in data/raw/bps/
- Clean standardized long-table: data/interim/bps_agriculture_clean.csv
"""

import os
import sys
import time
import json
import base64
import requests
import pandas as pd

RAW_BPS_DIR = os.path.join("biomass-feedstock-finder", "data", "raw", "bps")
INTERIM_DIR = os.path.join("biomass-feedstock-finder", "data", "interim")
DOCS_DIR = os.path.join("biomass-feedstock-finder", "docs")

os.makedirs(RAW_BPS_DIR, exist_ok=True)
os.makedirs(INTERIM_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# Verified public statistics tables on BPS
BPS_PUBLIC_TABLES = [
    {
        "id": "1498_padi_2024",
        "code": "MTQ5OCMy",
        "url": "https://www.bps.go.id/id/statistics-table/2/MTQ5OCMy/table.html",
        "type": "padi_ksa"
    },
    {
        "id": "2204_jagung_2024",
        "code": "MjIwNCMy",
        "url": "https://www.bps.go.id/id/statistics-table/2/MjIwNCMy/table.html",
        "type": "jagung_ksa"
    },
    {
        "id": "132_perkebunan_2023",
        "code": "MTMyIzI=",
        "url": "https://www.bps.go.id/id/statistics-table/2/MTMyIzI=/table.html",
        "type": "perkebunan"
    },
    {
        "id": "2566_perkebunan_2024",
        "code": "MjU2NiMy",
        "url": "https://www.bps.go.id/id/statistics-table/2/MjU2NiMy/table.html",
        "type": "perkebunan"
    },
    {
        "id": "23_pangan_historis",
        "code": "MjMjMg==",
        "url": "https://www.bps.go.id/id/statistics-table/2/MjMjMg==/table.html",
        "type": "pangan_hist"
    },
    {
        "id": "2512_kehutanan_spesies_2023",
        "code": "MjUxMiMy",
        "url": "https://www.bps.go.id/id/statistics-table/2/MjUxMiMy/table.html",
        "type": "kehutanan_spesies"
    },
    {
        "id": "1973_kehutanan_pulau_2022",
        "code": "MTk3MyMy",
        "url": "https://www.bps.go.id/id/statistics-table/2/MTk3MyMy/table.html",
        "type": "kehutanan_pulau"
    }
]

def load_bps_api_key():
    # Check environment variable first
    key = os.environ.get("BPS_API_KEY", "")
    if key:
        return key.strip()
    # Check .env file
    env_paths = [".env", os.path.join("biomass-feedstock-finder", ".env")]
    for p in env_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("BPS_API_KEY="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def fetch_and_parse_public_table(tbl_meta):
    table_id = tbl_meta["id"]
    code = tbl_meta["code"]
    url = tbl_meta["url"]
    tbl_type = tbl_meta["type"]
    
    raw_json_path = os.path.join(RAW_BPS_DIR, f"{table_id}.json")
    
    parsed = None
    if os.path.exists(raw_json_path):
        with open(raw_json_path, "r", encoding="utf-8") as f:
            try:
                parsed = json.load(f)
            except Exception:
                pass
                
    if not parsed:
        print(f"Downloading table {table_id} ({code})...")
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        raw_html = r.text
        
        # Extract embedded JSON from Next.js push
        raw_unescaped = raw_html.encode("utf-8").decode("unicode_escape")
        t_pos = raw_unescaped.find('"turvar"')
        if t_pos == -1:
            print(f"  [Warning] 'turvar' not found in table {table_id}")
            return []
            
        b_start = raw_unescaped.rfind('{"status":', 0, t_pos)
        if b_start == -1:
            b_start = raw_unescaped.rfind('{"data":', 0, t_pos)
        if b_start == -1:
            b_start = raw_unescaped.rfind('{"', 0, t_pos)
            
        count = 0
        b_end = -1
        for i in range(b_start, len(raw_unescaped)):
            if raw_unescaped[i] == '{':
                count += 1
            elif raw_unescaped[i] == '}':
                count -= 1
                if count == 0:
                    b_end = i + 1
                    break
                    
        parsed = json.loads(raw_unescaped[b_start:b_end])
        # Save raw JSON
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
            
        time.sleep(1.5) # Polite sleep
        
    # Extract records from parsed JSON
    var_obj = parsed.get("var", [{}])[0]
    var_val = var_obj.get("val")
    var_unit = str(var_obj.get("unit") or "")
    multiplier = 1000.0 if "ribu" in var_unit.lower() else 1.0
    
    vervar_dict = {str(item["val"]): item["label"] for item in parsed.get("vervar", [])}
    turvar_dict = {str(item["val"]): item["label"] for item in parsed.get("turvar", [])}
    tahun_dict = {str(item["val"]): item["label"] for item in parsed.get("tahun", [])}
    turtahun_dict = {str(item["val"]): item["label"] for item in parsed.get("turtahun", [])}
    datacontent = parsed.get("datacontent", {})
    
    records = []
    for key, val in datacontent.items():
        if val is None or val == "" or str(val).strip() == "-":
            continue
            
        # Parse composite key
        found = False
        for v_code, v_label in vervar_dict.items():
            if key.startswith(v_code):
                rem1 = key[len(v_code):]
                if rem1.startswith(str(var_val)):
                    rem2 = rem1[len(str(var_val)):]
                    for t_code, t_label in turvar_dict.items():
                        if rem2.startswith(t_code):
                            rem3 = rem2[len(t_code):]
                            for th_code, th_label in tahun_dict.items():
                                if rem3.startswith(th_code):
                                    found = True
                                    try:
                                        prod_val = float(val) * multiplier
                                    except ValueError:
                                        break
                                        
                                    clean_prov = v_label.strip().upper()
                                    clean_tur = t_label.strip().lower()
                                    
                                    # Target mapping
                                    comm = None
                                    reg_city = "PROVINCE_TOTAL"
                                    
                                    if tbl_type in ["padi_ksa"]:
                                        if "produksi" in clean_tur and "ton" in clean_tur:
                                            comm = "padi"
                                    elif tbl_type in ["jagung_ksa"]:
                                        if "produksi" in clean_tur and "ton" in clean_tur:
                                            comm = "jagung"
                                    elif tbl_type in ["perkebunan"]:
                                        if "sawit" in clean_tur:
                                            comm = "kelapa_sawit"
                                        elif "tebu" in clean_tur:
                                            comm = "tebu"
                                    elif tbl_type in ["pangan_hist"]:
                                        if clean_tur == "padi":
                                            comm = "padi"
                                        elif clean_tur == "jagung":
                                            comm = "jagung"
                                    elif tbl_type == "kehutanan_spesies":
                                        clean_prov = "INDONESIA"
                                        if "jumlah kayu bulat" in v_label.lower():
                                            comm = "kayu_bulat"
                                            reg_city = "NATIONAL_TOTAL"
                                            prod_val = float(val) * 0.70  # m3 to tons
                                        elif "kayu bakar" in v_label.lower():
                                            comm = "kayu_bakar"
                                            reg_city = "SPECIES_KAYU_BAKAR"
                                            prod_val = float(val) * 0.50  # SM to tons
                                    elif tbl_type == "kehutanan_pulau":
                                        clean_prov = v_label.strip().upper()
                                        reg_city = "ISLAND_TOTAL"
                                        comm = "kayu_bulat"
                                        prod_val = float(val) * 0.70  # m3 to tons
                                            
                                    if comm:
                                        records.append({
                                            "province": clean_prov,
                                            "regency_city": reg_city,
                                            "year": int(th_label),
                                            "commodity": comm,
                                            "production_tons": prod_val,
                                            "source_dataset": f"bps_table_{var_val}"
                                        })
                                    break
                            if found: break
                if found: break
    return records

def check_webapi_with_key(api_key):
    print(f"\n[Info] BPS_API_KEY detected! Testing WebAPI BPS connection...")
    test_url = f"https://webapi.bps.go.id/v1/api/list/model/var/domain/0000/key/{api_key}"
    try:
        r = requests.get(test_url, timeout=15)
        if r.status_code == 200 and r.json().get("status") == "OK":
            print("  WebAPI BPS Key verified successfully!")
        else:
            print(f"  WebAPI BPS response: {r.text[:150]}")
    except Exception as e:
        print(f"  WebAPI request error: {e}")

def main():
    print("=" * 60)
    print("STARTING 03_FETCH_BPS_AGRICULTURE.PY")
    print("=" * 60)
    
    api_key = load_bps_api_key()
    if api_key:
        check_webapi_with_key(api_key)
    else:
        print("[Info] No BPS_API_KEY provided in .env. Using verified public BPS statistics tables.")
        
    all_records = []
    for tbl in BPS_PUBLIC_TABLES:
        print(f"Processing BPS table: {tbl['id']}...")
        recs = fetch_and_parse_public_table(tbl)
        print(f"  Extracted {len(recs)} valid target commodity records.")
        all_records.extend(recs)
        
    df_bps = pd.DataFrame(all_records)
    if df_bps.empty:
        raise RuntimeError("No records extracted from BPS tables.")
        
    # Deduplicate: if duplicate (province, regency_city, year, commodity), keep latest table
    df_bps = df_bps.drop_duplicates(subset=["province", "regency_city", "year", "commodity"], keep="last")
    
    # Sort nicely
    df_bps = df_bps.sort_values(by=["commodity", "year", "province"]).reset_index(drop=True)
    
    out_csv = os.path.join(INTERIM_DIR, "bps_agriculture_clean.csv")
    df_bps.to_csv(out_csv, index=False)
    
    print(f"\nSuccessfully wrote cleaned BPS agriculture dataset to: {out_csv}")
    print(f"Total rows: {len(df_bps):,}")
    print(f"Total columns: {len(df_bps.columns)}")
    
    print("\n--- Missing Value Audit ---")
    missing = df_bps.isnull().mean() * 100
    for col, pct in missing.items():
        print(f"  {col:<20}: {pct:>6.2f}% missing ({df_bps[col].isnull().sum()} rows)")
        
    print("\nBreakdown by Commodity:")
    print(df_bps["commodity"].value_counts().to_string())
    
    print("\nBreakdown by Year:")
    print(df_bps["year"].value_counts().sort_index().to_string())
    
    print("\nDone 03_fetch_bps_agriculture.py successfully!\n")

if __name__ == "__main__":
    main()
