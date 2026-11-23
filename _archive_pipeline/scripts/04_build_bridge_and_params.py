"""
Script 04: Build Bridge Feedstock Mapping & Conversion Technology Dimension
Creates:
1. data/processed/Dim_Conversion_Tech.csv (Co-Firing PLTU, Gasifikasi Biomassa)
2. data/processed/Bridge_Feedstock_Mapping.csv (Commodity & RDF to chemical categories, RPR, moisture, source_url)
3. data/processed/Fact_Feedstock_Supply.csv (Merged regional supply from BPS & SIPSN ready for Star Schema)
"""

import os
import sys
import pandas as pd
import numpy as np

PROCESSED_DIR = os.path.join("biomass-feedstock-finder", "data", "processed")
INTERIM_DIR = os.path.join("biomass-feedstock-finder", "data", "interim")
DOCS_DIR = os.path.join("biomass-feedstock-finder", "docs")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(INTERIM_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

def build_dim_conversion_tech():
    print("[1/3] Building Dim_Conversion_Tech.csv...")
    tech_data = [
        {
            "tech_id": "TECH_COFIRING",
            "tech_name": "Co-Firing PLTU",
            "efficiency_min": 0.30,
            "efficiency_max": 0.35,
            "efficiency_default": 0.325,
            "ash_limit_pct": 10.0,
            "sulfur_limit_pct": 0.5,
            "preferred_feedstock_type": "densified_pellet_or_low_ash_solid",
            "source_standard": "Perdir PLN No. 001.P/DIR/2020 tentang Pedoman Standardisasi Biomassa Co-Firing"
        },
        {
            "tech_id": "TECH_GASIFIKASI",
            "tech_name": "Gasifikasi Biomassa",
            "efficiency_min": 0.22,
            "efficiency_max": 0.28,
            "efficiency_default": 0.2545,
            "ash_limit_pct": 10.0,
            "sulfur_limit_pct": 0.5,
            "preferred_feedstock_type": "syngas_compatible_woody_or_agricultural_residue",
            "source_standard": "Buku Panduan Teknis Pembangkit Listrik Biomassa Skala Kecil ESDM"
        }
    ]
    df_tech = pd.DataFrame(tech_data)
    out_tech = os.path.join(PROCESSED_DIR, "Dim_Conversion_Tech.csv")
    df_tech.to_csv(out_tech, index=False)
    print(f"  Wrote {len(df_tech)} technologies to {out_tech}")
    return df_tech

def build_bridge_feedstock_mapping():
    print("[2/3] Building Bridge_Feedstock_Mapping.csv...")
    # Exact specification commodities:
    # cangkang_sawit, serat_sawit, tandan_kosong_sawit, sekam_padi, jerami_padi, ampas_tebu, bonggol_jagung, rdf_kayu_ranting, rdf_kertas, rdf_plastik
    mapping_data = [
        {
            "feedstock_id": "FS_CANGKANG_SAWIT",
            "feedstock_name": "cangkang_sawit",
            "source_type": "BPS_AGRICULTURE",
            "source_commodity": "kelapa_sawit",
            "target_chemical_category": "husk/shell/pit",
            "rpr_value": 0.065, # 6.5% dari TBS
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 15.0,
            "source_url": "https://ebtke.esdm.go.id/ (Buku Saku Bioenergi Ditjen EBTKE ESDM)"
        },
        {
            "feedstock_id": "FS_SERAT_SAWIT",
            "feedstock_name": "serat_sawit",
            "source_type": "BPS_AGRICULTURE",
            "source_commodity": "kelapa_sawit",
            "target_chemical_category": "straw/stalk/cob/ear",
            "rpr_value": 0.135, # 13.5% dari TBS
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 37.0,
            "source_url": "https://ebtke.esdm.go.id/ (Buku Saku Bioenergi Ditjen EBTKE ESDM)"
        },
        {
            "feedstock_id": "FS_TANDAN_KOSONG_SAWIT",
            "feedstock_name": "tandan_kosong_sawit",
            "source_type": "BPS_AGRICULTURE",
            "source_commodity": "kelapa_sawit",
            "target_chemical_category": "straw/stalk/cob/ear",
            "rpr_value": 0.220, # 22% dari TBS
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 62.0,
            "source_url": "https://ebtke.esdm.go.id/ (Buku Saku Bioenergi Ditjen EBTKE ESDM)"
        },
        {
            "feedstock_id": "FS_SEKAM_PADI",
            "feedstock_name": "sekam_padi",
            "source_type": "BPS_AGRICULTURE",
            "source_commodity": "padi",
            "target_chemical_category": "husk/shell/pit",
            "rpr_value": 0.200, # 20% dari GKG
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 12.0,
            "source_url": "https://pangan.pertanian.go.id/ & https://ebtke.esdm.go.id/"
        },
        {
            "feedstock_id": "FS_JERAMI_PADI",
            "feedstock_name": "jerami_padi",
            "source_type": "BPS_AGRICULTURE",
            "source_commodity": "padi",
            "target_chemical_category": "straw/stalk/cob/ear",
            "rpr_value": 1.000, # 100% dari gabah
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 18.0, # Kering lapangan
            "source_url": "https://pangan.pertanian.go.id/ & Balitbangtan Kementan"
        },
        {
            "feedstock_id": "FS_AMPAS_TEBU",
            "feedstock_name": "ampas_tebu",
            "source_type": "BPS_AGRICULTURE",
            "source_commodity": "tebu",
            "target_chemical_category": "straw/stalk/cob/ear",
            "rpr_value": 0.300, # 30% dari tebu batang
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 49.0,
            "source_url": "https://perkebunan.pertanian.go.id/ (P3GI & Ditjen Perkebunan)"
        },
        {
            "feedstock_id": "FS_BONGGOL_JAGUNG",
            "feedstock_name": "bonggol_jagung",
            "source_type": "BPS_AGRICULTURE",
            "source_commodity": "jagung",
            "target_chemical_category": "straw/stalk/cob/ear",
            "rpr_value": 0.280, # 28% dari jagung pipilan
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 18.0,
            "source_url": "https://pangan.pertanian.go.id/ & Balitsereal Maros"
        },
        {
            "feedstock_id": "FS_RDF_KAYU_RANTING",
            "feedstock_name": "rdf_kayu_ranting",
            "source_type": "SIPSN_WASTE",
            "source_commodity": "pct_kayu_ranting",
            "target_chemical_category": "untreated wood",
            "rpr_value": 1.000, # direct mass fraction from SIPSN
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 35.0,
            "source_url": "https://sampahnasional.kemenlh.go.id/ (SIPSN KemenLH)"
        },
        {
            "feedstock_id": "FS_RDF_KERTAS",
            "feedstock_name": "rdf_kertas",
            "source_type": "SIPSN_WASTE",
            "source_commodity": "pct_kertas_karton",
            "target_chemical_category": "organic residue/product",
            "rpr_value": 1.000, # direct mass fraction from SIPSN
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 20.0,
            "source_url": "https://sampahnasional.kemenlh.go.id/ (SIPSN KemenLH)"
        },
        {
            "feedstock_id": "FS_RDF_PLASTIK",
            "feedstock_name": "rdf_plastik",
            "source_type": "SIPSN_WASTE",
            "source_commodity": "pct_plastik",
            "target_chemical_category": "organic residue/product",
            "rpr_value": 1.000, # direct mass fraction from SIPSN
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 12.0,
            "source_url": "https://sampahnasional.kemenlh.go.id/ (SIPSN KemenLH)"
        },
        {
            "feedstock_id": "FS_LIMBAH_KAYU",
            "feedstock_name": "serpihan_kayu_bulat",
            "source_type": "BPS_AGRICULTURE",
            "source_commodity": "kayu_bulat",
            "target_chemical_category": "untreated wood",
            "rpr_value": 0.250, # 25% logging/processing residue ratio (ESDM & KLHK standard)
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 30.0,
            "source_url": "https://ebtke.esdm.go.id/ & https://www.bps.go.id/ (Tabel 2512#2 & 1973#2)"
        },
        {
            "feedstock_id": "FS_KAYU_BAKAR",
            "feedstock_name": "kayu_bakar",
            "source_type": "BPS_AGRICULTURE",
            "source_commodity": "kayu_bakar",
            "target_chemical_category": "untreated wood",
            "rpr_value": 1.000, # Direct fuelwood feedstock
            "rpr_status": "VERIFIED_OFFICIAL",
            "typical_moisture_pct": 25.0,
            "source_url": "https://www.bps.go.id/ (Tabel 2512#2)"
        }
    ]
    df_bridge = pd.DataFrame(mapping_data)
    out_bridge = os.path.join(PROCESSED_DIR, "Bridge_Feedstock_Mapping.csv")
    df_bridge.to_csv(out_bridge, index=False)
    print(f"  Wrote {len(df_bridge)} feedstock mappings to {out_bridge}")
    return df_bridge

def build_fact_feedstock_supply(df_bridge):
    print("[3/3] Building unified Fact_Feedstock_Supply.csv...")
    bps_path = os.path.join(INTERIM_DIR, "bps_agriculture_clean.csv")
    sipsn_path = os.path.join(INTERIM_DIR, "sipsn_clean.csv")
    
    fact_records = []
    
    # 1. Process BPS residues
    if os.path.exists(bps_path):
        df_bps = pd.read_csv(bps_path)
        bps_map = df_bridge[df_bridge["source_type"] == "BPS_AGRICULTURE"]
        for _, b_row in bps_map.iterrows():
            sub = df_bps[df_bps["commodity"] == b_row["source_commodity"]]
            for _, r in sub.iterrows():
                raw_prod = r["production_tons"]
                rpr = b_row["rpr_value"]
                res_pot = raw_prod * rpr if pd.notnull(raw_prod) and pd.notnull(rpr) else 0.0
                fact_records.append({
                    "feedstock_id": b_row["feedstock_id"],
                    "feedstock_name": b_row["feedstock_name"],
                    "feedstock_category": b_row["target_chemical_category"],
                    "province": r["province"],
                    "regency_city": r["regency_city"],
                    "year": int(r["year"]),
                    "primary_production_tons": raw_prod,
                    "rpr": rpr,
                    "residue_potential_tons": res_pot,
                    "typical_moisture_pct": b_row["typical_moisture_pct"],
                    "source_dataset": r["source_dataset"]
                })
                
    # 2. Process SIPSN RDF fractions
    if os.path.exists(sipsn_path):
        df_sipsn = pd.read_csv(sipsn_path)
        sipsn_map = df_bridge[df_bridge["source_type"] == "SIPSN_WASTE"]
        for _, s_row in sipsn_map.iterrows():
            col_pct = s_row["source_commodity"]
            for _, r in df_sipsn.iterrows():
                timb_th = r["timbulan_tahunan_ton"]
                pct_val = r.get(col_pct, np.nan)
                if pd.notnull(timb_th) and pd.notnull(pct_val) and pct_val > 0:
                    rdf_tons = timb_th * (pct_val / 100.0)
                else:
                    rdf_tons = np.nan
                    
                fact_records.append({
                    "feedstock_id": s_row["feedstock_id"],
                    "feedstock_name": s_row["feedstock_name"],
                    "feedstock_category": s_row["target_chemical_category"],
                    "province": str(r["provinsi"]).strip().upper(),
                    "regency_city": str(r["kabkota"]).strip(),
                    "year": int(r["tahun"]),
                    "primary_production_tons": timb_th,
                    "rpr": 1.0,
                    "residue_potential_tons": rdf_tons,
                    "typical_moisture_pct": s_row["typical_moisture_pct"],
                    "source_dataset": "sipsn_kemenlh"
                })
                
    df_fact = pd.DataFrame(fact_records)
    out_fact = os.path.join(PROCESSED_DIR, "Fact_Feedstock_Supply.csv")
    df_fact.to_csv(out_fact, index=False)
    print(f"  Wrote {len(df_fact):,} fact rows to {out_fact}")
    return df_fact

def main():
    print("=" * 60)
    print("STARTING 04_BUILD_BRIDGE_AND_PARAMS.PY")
    print("=" * 60)
    
    df_tech = build_dim_conversion_tech()
    df_bridge = build_bridge_feedstock_mapping()
    df_fact = build_fact_feedstock_supply(df_bridge)
    
    print("\n--- Summary of Processed Datasets ---")
    print(f"Dim_Conversion_Tech: {len(df_tech)} rows")
    print(f"Bridge_Feedstock_Mapping: {len(df_bridge)} rows")
    print(f"Fact_Feedstock_Supply: {len(df_fact):,} rows")
    
    print("\nBreakdown of Fact Feedstock Supply by Feedstock Name:")
    print(df_fact["feedstock_name"].value_counts().to_string())
    
    print("\nDone 04_build_bridge_and_params.py successfully!\n")

if __name__ == "__main__":
    main()
