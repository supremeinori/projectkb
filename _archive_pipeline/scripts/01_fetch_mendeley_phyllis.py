"""
Script 01: Fetch and Standardize Biomass Chemical Composition Datasets
Sources:
1. Mendeley Data: DOI 10.17632/5xswr8yp34.3 (315 biomass samples with Proximate, Ultimate, and HHV)
2. Phyllis2 / Verified Fallback: GitHub duran-aranguren/biomass_composition (PA: 891 samples, UA: 1023 samples)
Output:
- Raw files saved in data/raw/
- Standardized interim file: data/interim/biomass_chemistry_clean.csv
"""

import os
import sys
import time
import requests
import pandas as pd
import docx

RAW_DIR = os.path.join("biomass-feedstock-finder", "data", "raw")
INTERIM_DIR = os.path.join("biomass-feedstock-finder", "data", "interim")
GITHUB_RAW_DIR = os.path.join(RAW_DIR, "github_biomass_composition")
DOCS_DIR = os.path.join("biomass-feedstock-finder", "docs")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(INTERIM_DIR, exist_ok=True)
os.makedirs(GITHUB_RAW_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_mendeley_data():
    print("[1/3] Fetching Mendeley Biomass HHV Dataset (DOI: 10.17632/5xswr8yp34.3)...")
    raw_docx_path = os.path.join(RAW_DIR, "mendeley_biomass_hhv.docx")
    
    # Check if already downloaded
    if not os.path.exists(raw_docx_path):
        api_url = "https://data.mendeley.com/api/datasets/5xswr8yp34/files"
        r = requests.get(api_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        files = r.json()
        download_url = None
        for f in files:
            if "download_url" in f.get("content_details", {}):
                download_url = f["content_details"]["download_url"]
                break
        
        if not download_url:
            raise RuntimeError("Could not find download URL for Mendeley dataset.")
            
        print(f"Downloading Mendeley raw file from {download_url}...")
        resp = requests.get(download_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        with open(raw_docx_path, "wb") as f:
            f.write(resp.content)
        print(f"Saved raw Mendeley docx to {raw_docx_path} ({len(resp.content)} bytes)")
    else:
        print(f"Raw Mendeley docx already exists at {raw_docx_path}")
        
    # Parse docx table
    print("Parsing Mendeley docx Table 1...")
    doc = docx.Document(raw_docx_path)
    if len(doc.tables) < 2:
        raise ValueError("Expected at least 2 tables in Mendeley docx.")
    
    target_table = doc.tables[1] # Table 1 contains the 315 samples
    rows = target_table.rows
    headers = [cell.text.strip().replace("\n", " ") for cell in rows[0].cells]
    
    records = []
    for row in rows[1:]:
        vals = [cell.text.strip() for cell in row.cells]
        if len(vals) == len(headers):
            row_dict = dict(zip(headers, vals))
            records.append(row_dict)
            
    df_mendeley = pd.DataFrame(records)
    print(f"Mendeley raw parsed: {len(df_mendeley)} rows, {len(df_mendeley.columns)} columns.")
    
    # Standardize columns
    # Expected headers: ['No.', 'Material', 'Feedstock Category', 'Ash (wt% db)', 'VM (wt% db)', 'FC (wt% db)', 'C (wt% db)', 'H (wt% db)', 'O (wt% db)', 'N (wt% db)', 'S (wt% db)', 'HHV (MJ/kg)', 'Reference']
    clean_records = []
    for idx, r in df_mendeley.iterrows():
        clean_records.append({
            "sample_id": f"MENDELEY_{r.get('No.', idx+1)}",
            "material_name": r.get("Material", "").strip(),
            "feedstock_category": r.get("Feedstock Category", "").strip().lower(),
            "ash_pct_db": pd.to_numeric(r.get("Ash (wt% db)", None), errors="coerce"),
            "vm_pct_db": pd.to_numeric(r.get("VM (wt% db)", None), errors="coerce"),
            "fc_pct_db": pd.to_numeric(r.get("FC (wt% db)", None), errors="coerce"),
            "c_pct_db": pd.to_numeric(r.get("C (wt% db)", None), errors="coerce"),
            "h_pct_db": pd.to_numeric(r.get("H (wt% db)", None), errors="coerce"),
            "o_pct_db": pd.to_numeric(r.get("O (wt% db)", None), errors="coerce"),
            "n_pct_db": pd.to_numeric(r.get("N (wt% db)", None), errors="coerce"),
            "s_pct_db": pd.to_numeric(r.get("S (wt% db)", None), errors="coerce"),
            "hhv_mj_kg": pd.to_numeric(r.get("HHV (MJ/kg)", None), errors="coerce"),
            "source_dataset": "mendeley_5xswr8yp34"
        })
    return pd.DataFrame(clean_records)

def fetch_github_fallback_data():
    print("[2/3] Fetching GitHub Biomass Composition Fallback (duran-aranguren/biomass_composition)...")
    base_raw_url = "https://raw.githubusercontent.com/duran-aranguren/biomass_composition/main"
    files = {
        "PA": "Composition_database_2022_PA.xlsx",
        "UA": "Composition_database_2022_UA.xlsx",
        "NREL": "Composition_database_2022_NREL.xlsx"
    }
    
    downloaded_paths = {}
    for key, filename in files.items():
        dest = os.path.join(GITHUB_RAW_DIR, filename)
        downloaded_paths[key] = dest
        if not os.path.exists(dest):
            u = f"{base_raw_url}/{filename}"
            print(f"Downloading {filename}...")
            r = requests.get(u, headers=HEADERS, timeout=30)
            r.raise_for_status()
            with open(dest, "wb") as f:
                f.write(r.content)
            time.sleep(1.5)
        else:
            print(f"File {filename} already exists locally.")
            
    # Read PA and UA datasets
    df_pa = pd.read_excel(downloaded_paths["PA"])
    df_ua = pd.read_excel(downloaded_paths["UA"])
    print(f"GitHub PA dataset: {len(df_pa)} rows; UA dataset: {len(df_ua)} rows.")
    
    # Standardize PA
    # Cols: ['Biomass', 'VM', 'FC', 'Ash', 'Reference/Source']
    pa_records = []
    for idx, r in df_pa.iterrows():
        pa_records.append({
            "sample_id": f"GITHUB_PA_{idx+1}",
            "material_name": str(r.get("Biomass", "")).strip(),
            "feedstock_category": "unclassified_biomass",
            "ash_pct_db": pd.to_numeric(r.get("Ash", None), errors="coerce"),
            "vm_pct_db": pd.to_numeric(r.get("VM", None), errors="coerce"),
            "fc_pct_db": pd.to_numeric(r.get("FC", None), errors="coerce"),
            "c_pct_db": None,
            "h_pct_db": None,
            "o_pct_db": None,
            "n_pct_db": None,
            "s_pct_db": None,
            "hhv_mj_kg": None,
            "source_dataset": "github_duran_pa"
        })
    df_pa_clean = pd.DataFrame(pa_records)
    
    # Standardize UA
    # Cols: ['Biomass', 'C', 'H', 'O', 'N', 'S', 'Reference/Source']
    ua_records = []
    for idx, r in df_ua.iterrows():
        ua_records.append({
            "sample_id": f"GITHUB_UA_{idx+1}",
            "material_name": str(r.get("Biomass", "")).strip(),
            "feedstock_category": "unclassified_biomass",
            "ash_pct_db": None,
            "vm_pct_db": None,
            "fc_pct_db": None,
            "c_pct_db": pd.to_numeric(r.get("C", None), errors="coerce"),
            "h_pct_db": pd.to_numeric(r.get("H", None), errors="coerce"),
            "o_pct_db": pd.to_numeric(r.get("O", None), errors="coerce"),
            "n_pct_db": pd.to_numeric(r.get("N", None), errors="coerce"),
            "s_pct_db": pd.to_numeric(r.get("S", None), errors="coerce"),
            "hhv_mj_kg": None,
            "source_dataset": "github_duran_ua"
        })
    df_ua_clean = pd.DataFrame(ua_records)
    
    return pd.concat([df_pa_clean, df_ua_clean], ignore_index=True)

def main():
    print("=" * 60)
    print("STARTING 01_FETCH_MENDELEY_PHYLLIS.PY")
    print("=" * 60)
    
    df_mendeley = fetch_mendeley_data()
    df_github = fetch_github_fallback_data()
    
    print("[3/3] Combining and standardizing all biomass chemistry samples...")
    df_combined = pd.concat([df_mendeley, df_github], ignore_index=True)
    
    out_csv = os.path.join(INTERIM_DIR, "biomass_chemistry_clean.csv")
    df_combined.to_csv(out_csv, index=False)
    print(f"\nSuccessfully wrote standardized dataset to: {out_csv}")
    print(f"Total rows: {len(df_combined):,}")
    print(f"Total columns: {len(df_combined.columns)}")
    
    print("\n--- Missing Value Audit ---")
    missing = df_combined.isnull().mean() * 100
    for col, pct in missing.items():
        print(f"  {col:<20}: {pct:>6.2f}% missing ({df_combined[col].isnull().sum()} rows)")
        
    print("\nBreakdown by source_dataset:")
    print(df_combined["source_dataset"].value_counts().to_string())
    print("\nDone 01_fetch_mendeley_phyllis.py successfully!\n")

if __name__ == "__main__":
    main()
