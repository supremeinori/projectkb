"""
Tahap 3: Klasifikasi & Ringkasan Data Kandungan Kimia per Kategori (5 Limbah)
Sumber: raw_data/03_karakteristik_biomassa_kimia_hhv.csv (Mendeley DOI: 10.17632/5xswr8yp34.3
        & Duran-Aranguren GitHub Biomass Composition Database).
Prinsip Saintis:
- Tidak mengimputasi / mengisi nilai lab yang kosong (dibiarkan NULL/NaN as-is).
- Filter ketat agar nol false-positive (misal acorn bukan jagung, palmaria/date palm bukan kelapa sawit).
"""

import os
import re
import numpy as np
import pandas as pd

RAW_DIR = "raw_data"
SRC_CSV = os.path.join(RAW_DIR, "03_karakteristik_biomassa_kimia_hhv.csv")

SOURCE_URL_MAP = {
    "mendeley_5xswr8yp34": "https://data.mendeley.com/datasets/5xswr8yp34 (DOI: 10.17632/5xswr8yp34.3)",
    "github_duran_aranguren_PA": "https://github.com/duran-aranguren/biomass_composition (Composition_database_2022_PA.xlsx)",
    "github_duran_aranguren_UA": "https://github.com/duran-aranguren/biomass_composition (Composition_database_2022_UA.xlsx)",
    "github_duran_aranguren_NREL": "https://github.com/duran-aranguren/biomass_composition (Composition_database_2022_NREL.xlsx)",
}

# Referensi RPR resmi (terpisah dari hasil uji lab, untuk kemudahan referensi)
RPR_REF = {
    "jagung": (0.28, "Tongkol/bonggol jagung (28% jagung pipilan)", 18.0, "Balitsereal Kementan & Buku Saku Bioenergi ESDM"),
    "sekam_padi": (0.20, "Sekam padi (20% Gabah Kering Giling / GKG)", 12.0, "Ditjen EBTKE ESDM & Kementan"),
    "kayu": (0.25, "Limbah tebangan/sawmill kayu bulat (25% massa kayu; densitas 0,70 ton/m3)", 30.0, "Ditjen EBTKE ESDM & KLHK"),
    "tebu": (0.30, "Ampas tebu / bagasse (30% tebu giling)", 49.0, "P3GI & Ditjen Perkebunan Kementan"),
    "sawit": (0.42, "Total residu padat pabrik sawit: Cangkang 6,5% + Serat 13,5% + TKKS 22% dari TBS", 38.0, "Buku Saku Bioenergi Ditjen EBTKE ESDM"),
}


def classify_5_limbah(name: str):
    if not isinstance(name, str) or not name.strip():
        return None, None
    s = name.lower().strip()

    # 1. SAWIT (kelapa sawit murni — exclude kurma/date palm, peach palm, palmaria macroalgae, olive)
    if not re.search(r"palmaria|date\s*palm|peach\s*palm|olive|pine\s*kernel|coco", s):
        if re.search(r"oil\s*palm|palm\s*kernel|palm\s*empty|palm\s*fruit|palm\s*fib|palm\s*frond|palm\s*trunk|palm\s*pit|palm\s*shell|palm\s*leave|palm\s*tree|palm\s*mesocarp|\bpks\b|\befb\b", s):
            if re.search(r"shell|kernel|pit|\bpks\b", s):
                sub = "cangkang_sawit"
            elif re.search(r"empty|\befb\b", s):
                sub = "tandan_kosong_sawit"
            elif re.search(r"fib|mesocarp", s):
                sub = "serat_sawit"
            else:
                sub = "pelepah_batang_sawit"
            return "sawit", sub

    # 2. SEKAM PADI (khusus sekam/husk/hull — exclude rice straw & rice bran murni)
    if re.search(r"(rice|paddy).*(husk|hull|shell)|(husk|hull).*(rice|paddy)", s) and not re.search(r"\bbran\b|\bstraw\b", s):
        return "sekam_padi", "sekam_padi"

    # 3. TEBU (sugarcane / bagasse tebu — exclude guayule, sorghum, agave, cassava, grape)
    if not re.search(r"guayule|sorghum|agave|cassava|grape|olive|beet", s):
        if re.search(r"sugarcane|sugar\s*cane|^bagasse\b|cane\s*bagasse", s):
            return "tebu", "ampas_tebu_bagasse"

    # 4. JAGUNG (corn cob / stover / stalk / straw / maize — exclude acorn, popcorn, oil, starch)
    if not re.search(r"acorn|popcorn|corn\s*oil|corn\s*starch|corn\s*syrup|gluten", s):
        if re.search(r"\bcorn\b|\bcorncob|\bmaize\b", s):
            if re.search(r"cob", s):
                sub = "bonggol_jagung"
            else:
                sub = "batang_jerami_jagung"
            return "jagung", sub

    # 5. KAYU (limbah kayu/serbuk gergaji/kayu murni — exclude treated/plywood/char/coal/acorn/cone)
    if not re.search(r"acorn|pine\s*kernel|pine\s*cone|plywood|mdf|particle\s*board|demolition|creosote|\bcca\b|treated|sewage|sludge|\bcoal\b|biochar|charcoal|torrefied|pyroly", s):
        if re.search(r"\bwood\b|sawdust|acacia|eucalyptus|\bpine\b|\bspruce\b|\boak\b|\bpoplar\b|\bbeech\b|\bbirch\b|\bwillow\b|\bteak\b|mahogany|rubberwood|wood\s*chip|wood\s*pellet|wood\s*shaving|hardwood|softwood|timber", s):
            if re.search(r"sawdust", s):
                sub = "serbuk_gergaji"
            elif re.search(r"bark", s):
                sub = "kulit_kayu"
            elif re.search(r"chip|pellet|shaving", s):
                sub = "serpihan_pelet_kayu"
            else:
                sub = "kayu_murni"
            return "kayu", sub

    return None, None


def main():
    df = pd.read_csv(SRC_CSV)
    classified = df["material_name"].apply(classify_5_limbah)
    df["kategori_limbah"] = [c[0] for c in classified]
    df["sub_kategori_limbah"] = [c[1] for c in classified]

    sub = df[df["kategori_limbah"].notna()].copy()
    sub["hhv_kcal_kg"] = np.where(sub["hhv_mj_kg"].notna(), (sub["hhv_mj_kg"] * 238.8459).round(2), np.nan)
    sub["status_data"] = "TERSEDIA_LAB_TERVERIFIKASI"
    sub["sumber_url"] = sub["source_dataset"].map(lambda x: SOURCE_URL_MAP.get(x, str(x)))
    sub["catatan_fakta"] = sub.apply(
        lambda r: (
            "Lengkap (Proksimat + Ultimat + HHV)"
            if pd.notna(r["hhv_mj_kg"]) and pd.notna(r["ash_pct_db"]) and pd.notna(r["c_pct_db"])
            else (
                "Hanya Proksimat (Ultimat & HHV NULL as-is dari sumber PA)"
                if pd.notna(r["ash_pct_db"]) and pd.isna(r["c_pct_db"]) and pd.isna(r["hhv_mj_kg"])
                else (
                    "Hanya Ultimat (Proksimat & HHV NULL as-is dari sumber UA)"
                    if pd.notna(r["c_pct_db"]) and pd.isna(r["ash_pct_db"]) and pd.isna(r["hhv_mj_kg"])
                    else "Sebagian parameter tersedia (nilai kosong dibiarkan NULL as-is)"
                )
            )
        ),
        axis=1,
    )

    detail_cols = [
        "sample_id", "kategori_limbah", "sub_kategori_limbah", "material_name",
        "ash_pct_db", "vm_pct_db", "fc_pct_db",
        "c_pct_db", "h_pct_db", "o_pct_db", "n_pct_db", "s_pct_db",
        "hhv_mj_kg", "hhv_kcal_kg",
        "status_data", "source_dataset", "sumber_url", "catatan_fakta",
    ]
    sub = sub[detail_cols].sort_values(["kategori_limbah", "sub_kategori_limbah", "sample_id"]).reset_index(drop=True)

    # Ringkasan per kategori (5 kategori utama)
    num_cols = ["ash_pct_db", "vm_pct_db", "fc_pct_db", "c_pct_db", "h_pct_db", "o_pct_db", "n_pct_db", "s_pct_db", "hhv_mj_kg", "hhv_kcal_kg"]
    summary_rows = []
    for kat in ["jagung", "sekam_padi", "kayu", "tebu", "sawit"]:
        g = sub[sub["kategori_limbah"] == kat]
        rpr_val, rpr_ket, moist_ref, rpr_src = RPR_REF[kat]
        row = {
            "kategori_limbah": kat,
            "jumlah_total_sampel": len(g),
            "n_sampel_proksimat": int(g["ash_pct_db"].notna().sum()),
            "n_sampel_ultimat": int(g["c_pct_db"].notna().sum()),
            "n_sampel_hhv": int(g["hhv_mj_kg"].notna().sum()),
        }
        for c in num_cols:
            vals = g[c].dropna()
            row[f"mean_{c}"] = round(float(vals.mean()), 3) if len(vals) else np.nan
            row[f"median_{c}"] = round(float(vals.median()), 3) if len(vals) else np.nan
            row[f"min_{c}"] = round(float(vals.min()), 3) if len(vals) else np.nan
            row[f"max_{c}"] = round(float(vals.max()), 3) if len(vals) else np.nan

        mean_ash = row["mean_ash_pct_db"]
        mean_s = row["mean_s_pct_db"]
        row["lolos_batas_abu_pln_10pct"] = (bool(mean_ash <= 10.0) if pd.notna(mean_ash) else None)
        row["lolos_batas_sulfur_pln_0_5pct"] = (bool(mean_s <= 0.5) if pd.notna(mean_s) else None)
        row["ref_rpr_resmi"] = rpr_val
        row["ref_keterangan_rpr"] = rpr_ket
        row["ref_kadar_air_tipikal_pct"] = moist_ref
        row["ref_sumber_rpr"] = rpr_src
        row["status_data"] = "TERSEDIA_LAB_TERVERIFIKASI" if len(g) > 0 else "TIDAK_TERSEDIA"
        row["sumber_url"] = "https://data.mendeley.com/datasets/5xswr8yp34 & https://github.com/duran-aranguren/biomass_composition"
        row["catatan_fakta"] = f"Agregasi murni dari {len(g)} sampel lab terklasifikasi ketat (basis kering / dry basis wt%, tanpa imputasi)"
        summary_rows.append(row)

    df_summary = pd.DataFrame(summary_rows)

    out_xlsx = os.path.join(RAW_DIR, "02_kandungan_per_kategori_5_limbah.xlsx")
    out_csv = os.path.join(RAW_DIR, "02_kandungan_per_kategori_5_limbah.csv")
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="ringkasan_per_kategori", index=False)
        sub.to_excel(writer, sheet_name="detail_sampel_lab", index=False)
    sub.to_csv(out_csv, index=False)

    print("=== TAHAP 3 SELESAI: KANDUNGAN PER KATEGORI 5 LIMBAH ===")
    print(df_summary[["kategori_limbah", "jumlah_total_sampel", "n_sampel_hhv", "mean_ash_pct_db", "mean_s_pct_db", "mean_hhv_mj_kg", "mean_hhv_kcal_kg"]].to_string(index=False))
    print(f"\nSaved: {out_xlsx} (2 sheets) & {out_csv} ({len(sub)} rows)")


if __name__ == "__main__":
    main()
