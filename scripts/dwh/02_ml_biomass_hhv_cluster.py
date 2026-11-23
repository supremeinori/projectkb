"""
Step 2 DWH ETL + ML: Pemodelan Machine Learning Biomassa (HHV Regression + K-Means Boiler Grading)
Input:
  - raw_data/03_karakteristik_biomassa_kimia_hhv.csv (2.229 sampel: 315 Mendeley + 1.023 Duran UA + 891 Duran PA)
  - warehouse/tables/dim_feedstock.csv
  - warehouse/tables/dim_data_source.csv
Output:
  - warehouse/tables/fact_biomass_chemistry.csv (2.229 baris terhubung FK ke dim_feedstock & dim_data_source)
  - warehouse/tables/dim_feedstock.csv          (diperkaya avg_hhv, ml_predicted_hhv, avg_ash, avg_sulfur, grade, slagging_risk)
  - warehouse/ml_model_metrics.json
  - warehouse/ML_REPORT.md
"""

import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor, StackingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

TABLES_DIR = Path("warehouse/tables")
WAREHOUSE_DIR = Path("warehouse")

PROX_COLS = ["ash_pct_db", "vm_pct_db", "fc_pct_db"]
ULT_COLS = ["c_pct_db", "h_pct_db", "o_pct_db", "n_pct_db", "s_pct_db"]
ALL_COLS = PROX_COLS + ULT_COLS


def map_material_to_feedstock_key(material_name: str, category: str) -> int:
    """Petakan material_name lab ke salah satu 5 feedstock utama (1..5), RDF (7), atau OTHER_BIOMASS (8)."""
    m = str(material_name or "").lower()
    cat = str(category or "").lower()

    # 1. Sekam Padi (Rice Husk / Hull — bukan jerami padi jika bisa dibedakan, tapi rice husk/hull masuk 1)
    if re.search(r"rice\s*(husk|hull|chaff|bran)", m):
        return 1
    # 2. Tongkol / Batang Jagung (Corn Cob / Corn Stover / Maize)
    if re.search(r"\b(corn|maize)\b", m):
        return 2
    # 3. Kelapa Sawit (Palm Kernel Shell / Oil Palm / EFB / Palm Fiber)
    if re.search(r"(oil\s*palm|palm\s*(kernel|shell|fiber|fibre|frond|trunk|bunch|empty|oil|mesocarp|waste|press)|pks\b|efb\b)", m):
        return 3
    # 4. Ampas Tebu (Sugarcane Bagasse)
    if re.search(r"(bagasse|sugar\s*cane|sugarcane)", m):
        return 4
    # 5. Limbah Kayu / Serbuk Gergaji / Woodchips / Timber / Bark
    if re.search(r"(sawdust|wood\s*chip|woodchip|wood\s*pellet|wood\s*shaving|wood\s*waste|hardwood|softwood|timber|pine\s*wood|oak\s*wood|eucalyptus|acacia|poplar|spruce|beech|birch|willow|teak|wood)", m) or cat == "untreated wood":
        if "olive" not in m and "cotton" not in m and "date palm" not in m:
            return 5
    # 7. RDF / Municipal Solid Waste
    if re.search(r"\b(rdf|refuse\s*derived|municipal\s*solid\s*waste|msw)\b", m):
        return 7
    # 8. Biomassa lainnya (as-is, tidak dipaksakan ke 5 komoditas)
    return 8


def evaluate_regime(X: pd.DataFrame, y: pd.Series, regime_name: str):
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    candidates = {
        "Ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "SVR_RBF": make_pipeline(StandardScaler(), SVR(C=10.0, epsilon=0.2, kernel="rbf")),
        "RandomForest": RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1),
        "ExtraTrees": ExtraTreesRegressor(n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1),
        "GradientBoosting": GradientBoostingRegressor(n_estimators=250, learning_rate=0.05, max_depth=4, random_state=42),
        "StackedHybrid_Ridge_ET_GBR": StackingRegressor(
            estimators=[
                ("ridge", make_pipeline(StandardScaler(), Ridge(alpha=1.0))),
                ("svr", make_pipeline(StandardScaler(), SVR(C=10.0, epsilon=0.2))),
                ("et", ExtraTreesRegressor(n_estimators=250, min_samples_leaf=2, random_state=42, n_jobs=-1)),
                ("gbr", GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=3, random_state=42)),
            ],
            final_estimator=HuberRegressor(max_iter=500),
            cv=5,
            n_jobs=-1,
        ),
    }
    results = {}
    best_name, best_r2, best_oof, best_est = None, -999.0, None, None
    for name, est in candidates.items():
        oof = cross_val_predict(est, X, y, cv=kf)
        r2 = float(r2_score(y, oof))
        rmse = float(np.sqrt(mean_squared_error(y, oof)))
        mae = float(mean_absolute_error(y, oof))
        results[name] = {"cv5_r2": round(r2, 4), "cv5_rmse_mj_kg": round(rmse, 4), "cv5_mae_mj_kg": round(mae, 4)}
        if r2 > best_r2:
            best_name, best_r2, best_oof, best_est = name, r2, oof, est

    # Fit model terbaik pada seluruh data latih Mendeley
    best_est.fit(X, y)
    perm = permutation_importance(best_est, X, y, n_repeats=15, random_state=42, n_jobs=-1)
    feat_imp = {
        col: round(float(imp), 4)
        for col, imp in sorted(zip(X.columns, perm.importances_mean), key=lambda kv: kv[1], reverse=True)
    }
    print(f"  [{regime_name}] Best={best_name} | 5-Fold CV R2={best_r2:.4f} | RMSE={results[best_name]['cv5_rmse_mj_kg']:.4f} MJ/kg | MAE={results[best_name]['cv5_mae_mj_kg']:.4f} MJ/kg")
    return best_name, best_est, best_oof, results, feat_imp


def main():
    print("=== Step 2 DWH + ML: Biomass Chemistry HHV Regression & K-Means Grading ===")
    df = pd.read_csv("raw_data/03_karakteristik_biomassa_kimia_hhv.csv")
    dim_fs = pd.read_csv(TABLES_DIR / "dim_feedstock.csv")
    dim_src = pd.read_csv(TABLES_DIR / "dim_data_source.csv")

    src_map = {
        "mendeley_5xswr8yp34": int(dim_src.loc[dim_src["kode_sumber"] == "MENDELEY_5XSWR8YP34", "source_key"].iloc[0]),
        "github_duran_ua": int(dim_src.loc[dim_src["kode_sumber"] == "GITHUB_DURAN_UA", "source_key"].iloc[0]),
        "github_duran_pa": int(dim_src.loc[dim_src["kode_sumber"] == "GITHUB_DURAN_PA", "source_key"].iloc[0]),
    }

    # Dataset latih berlabel HHV (Mendeley 315 sampel — semua 8 fitur kimia lengkap)
    train_mask = df["hhv_mj_kg"].notna() & df[ALL_COLS].notna().all(axis=1)
    df_train = df.loc[train_mask].copy()
    print(f"Training set (Mendeley measured HHV): {len(df_train)} sampel")

    y_train = df_train["hhv_mj_kg"].astype(float)

    # Latih 3 regime model sesuai ketersediaan fitur pada 3 sumber lab
    m_full_name, m_full, oof_full, res_full, imp_full = evaluate_regime(df_train[ALL_COLS], y_train, "FULL_PROX_ULT (8 fitur)")
    m_ult_name, m_ult, _, res_ult, imp_ult = evaluate_regime(df_train[ULT_COLS], y_train, "ULTIMATE_ONLY (5 fitur)")
    m_prox_name, m_prox, _, res_prox, imp_prox = evaluate_regime(df_train[PROX_COLS], y_train, "PROXIMATE_ONLY (3 fitur)")

    # Isi prediksi HHV untuk seluruh 2.229 sampel sesuai fitur yang tersedia
    pred_hhv = pd.Series(np.nan, index=df.index, dtype=float)
    model_used = pd.Series("NONE", index=df.index, dtype=object)

    # 1. Mendeley (315 baris) -> out-of-fold CV prediction (jujur, anti data-leakage!)
    pred_hhv.loc[train_mask] = oof_full
    model_used.loc[train_mask] = f"OOF_{m_full_name}_FULL_8F"

    # 2. Duran Ultimate-Only (1.023 baris) -> Model Ultimate-Only
    ua_mask = (~train_mask) & df[ULT_COLS].notna().all(axis=1)
    pred_hhv.loc[ua_mask] = m_ult.predict(df.loc[ua_mask, ULT_COLS])
    model_used.loc[ua_mask] = f"{m_ult_name}_ULT_5F"

    # 3. Duran Proximate-Only (891 baris) -> Model Proximate-Only
    pa_mask = (~train_mask) & (~ua_mask) & df[PROX_COLS].notna().all(axis=1)
    pred_hhv.loc[pa_mask] = m_prox.predict(df.loc[pa_mask, PROX_COLS])
    model_used.loc[pa_mask] = f"{m_prox_name}_PROX_3F"

    # K-Means Clustering (k=3) untuk Boiler Suitability Grade berbasis (HHV efektif, Ash, Sulfur)
    hhv_eff = df["hhv_mj_kg"].fillna(pred_hhv)
    ash_med = float(df["ash_pct_db"].median())
    sul_med = float(df["s_pct_db"].median())

    clust_X = pd.DataFrame({
        "hhv_eff": hhv_eff.fillna(hhv_eff.median()),
        "ash_fill": df["ash_pct_db"].fillna(ash_med),
        "s_fill": df["s_pct_db"].fillna(sul_med),
    })
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(clust_X)
    km = KMeans(n_clusters=3, random_state=42, n_init=20)
    raw_labels = km.fit_predict(X_scaled)

    # Urutkan klaster secara semantik: skor energi tinggi & abu/sulfur rendah -> Grade A, lalu B, lalu C
    clust_stats = []
    for cid in range(3):
        sub = clust_X[raw_labels == cid]
        score = float(sub["hhv_eff"].mean()) - 0.35 * float(sub["ash_fill"].mean()) - 2.0 * float(sub["s_fill"].mean())
        clust_stats.append((cid, score, float(sub["hhv_eff"].mean()), float(sub["ash_fill"].mean()), float(sub["s_fill"].mean()), int(len(sub))))
    clust_stats.sort(key=lambda x: x[1], reverse=True)
    grade_names = [
        "Grade A (High Calorie - Low Ash)",
        "Grade B (Moderate / Conditioning Needed)",
        "Grade C (High Ash / Slagging Risk)",
    ]
    cid_to_grade = {clust_stats[i][0]: grade_names[i] for i in range(3)}
    ml_grades = pd.Series([cid_to_grade[c] for c in raw_labels], index=df.index)

    # Susun fact_biomass_chemistry.csv
    fact_rows = []
    for idx, r in df.iterrows():
        fk = map_material_to_feedstock_key(r["material_name"], r["feedstock_category"])
        sk = src_map[r["source_dataset"]]
        ash_v = float(r["ash_pct_db"]) if pd.notna(r["ash_pct_db"]) else None
        s_v = float(r["s_pct_db"]) if pd.notna(r["s_pct_db"]) else None
        pass_ash = (1 if ash_v < 10.0 else 0) if ash_v is not None else None
        pass_s = (1 if s_v < 0.5 else 0) if s_v is not None else None

        fact_rows.append({
            "chem_fact_id": idx + 1,
            "feedstock_key": fk,
            "source_key": sk,
            "sample_id": str(r["sample_id"]).strip(),
            "material_name_raw": str(r["material_name"]).strip(),
            "ash_pct_db": round(ash_v, 4) if ash_v is not None else None,
            "vm_pct_db": round(float(r["vm_pct_db"]), 4) if pd.notna(r["vm_pct_db"]) else None,
            "fc_pct_db": round(float(r["fc_pct_db"]), 4) if pd.notna(r["fc_pct_db"]) else None,
            "c_pct_db": round(float(r["c_pct_db"]), 4) if pd.notna(r["c_pct_db"]) else None,
            "h_pct_db": round(float(r["h_pct_db"]), 4) if pd.notna(r["h_pct_db"]) else None,
            "o_pct_db": round(float(r["o_pct_db"]), 4) if pd.notna(r["o_pct_db"]) else None,
            "n_pct_db": round(float(r["n_pct_db"]), 4) if pd.notna(r["n_pct_db"]) else None,
            "s_pct_db": round(s_v, 4) if s_v is not None else None,
            "hhv_actual_mj_kg": round(float(r["hhv_mj_kg"]), 4) if pd.notna(r["hhv_mj_kg"]) else None,
            "hhv_ml_predicted_mj_kg": round(float(pred_hhv.loc[idx]), 4) if pd.notna(pred_hhv.loc[idx]) else None,
            "hhv_model_used": model_used.loc[idx],
            "ml_cluster_grade": ml_grades.loc[idx],
            "pass_boiler_ash_limit": pass_ash,
            "pass_boiler_sulfur_limit": pass_s,
        })

    df_fact = pd.DataFrame(fact_rows)
    df_fact["pass_boiler_ash_limit"] = df_fact["pass_boiler_ash_limit"].astype("Int64")
    df_fact["pass_boiler_sulfur_limit"] = df_fact["pass_boiler_sulfur_limit"].astype("Int64")
    df_fact.to_csv(TABLES_DIR / "fact_biomass_chemistry.csv", index=False, encoding="utf-8-sig")
    print(f"[fact_biomass_chemistry] {len(df_fact)} baris -> distribusi feedstock_key: {df_fact['feedstock_key'].value_counts().sort_index().to_dict()}")

    # Pastikan kolom string di dim_feedstock bertipe object (Pandas 3 strict dtype)
    for col_s in ["boiler_suitability_grade", "slagging_risk_level"]:
        dim_fs[col_s] = dim_fs[col_s].astype(object)
    for col_f in ["avg_hhv_mj_kg", "ml_predicted_hhv_mj_kg", "avg_ash_pct_db", "avg_sulfur_pct_db"]:
        dim_fs[col_f] = dim_fs[col_f].astype(float)

    # Perkaya dim_feedstock.csv dengan median empiris + prediksi ML dari fact_biomass_chemistry
    for i, frow in dim_fs.iterrows():
        fk = int(frow["feedstock_key"])
        lookup_fk = 5 if fk == 6 else fk
        sub = df_fact[df_fact["feedstock_key"] == lookup_fk]
        if fk == 9:  # NON_COFIRING_COAL placeholder
            dim_fs.loc[i, "boiler_suitability_grade"] = "N/A (Referensi Batu Bara)"
            dim_fs.loc[i, "slagging_risk_level"] = "N/A"
            continue
        if len(sub) > 0:
            avg_hhv = sub["hhv_actual_mj_kg"].median()
            ml_hhv = sub["hhv_ml_predicted_mj_kg"].median()
            if pd.isna(avg_hhv):
                avg_hhv = ml_hhv
            avg_ash = sub["ash_pct_db"].median()
            avg_s = sub["s_pct_db"].median()
            # Tentukan grade & slagging risk dari ash & HHV aktual
            if pd.notna(avg_ash) and avg_ash >= 10.0:
                grade = "Grade C (High Ash / Slagging Risk)"
                slag = "HIGH (Ash >= 10%)"
            elif pd.notna(avg_hhv) and avg_hhv >= 17.5 and (pd.isna(avg_ash) or avg_ash < 6.0):
                grade = "Grade A (High Calorie - Low Ash)"
                slag = "LOW (Ash < 6%)"
            else:
                grade = "Grade B (Moderate / Conditioning Needed)"
                slag = "MODERATE (Ash 6-10%)"
            dim_fs.loc[i, "avg_hhv_mj_kg"] = round(float(avg_hhv), 3) if pd.notna(avg_hhv) else None
            dim_fs.loc[i, "ml_predicted_hhv_mj_kg"] = round(float(ml_hhv), 3) if pd.notna(ml_hhv) else None
            dim_fs.loc[i, "avg_ash_pct_db"] = round(float(avg_ash), 3) if pd.notna(avg_ash) else None
            dim_fs.loc[i, "avg_sulfur_pct_db"] = round(float(avg_s), 4) if pd.notna(avg_s) else None
            dim_fs.loc[i, "boiler_suitability_grade"] = grade
            dim_fs.loc[i, "slagging_risk_level"] = slag

    dim_fs.to_csv(TABLES_DIR / "dim_feedstock.csv", index=False, encoding="utf-8-sig")
    print("\n[dim_feedstock diperkaya ML]:")
    print(dim_fs[["feedstock_key", "kode_feedstock", "avg_hhv_mj_kg", "ml_predicted_hhv_mj_kg", "avg_ash_pct_db", "avg_sulfur_pct_db", "boiler_suitability_grade"]].to_string(index=False))

    # Simpan metrics JSON & ML_REPORT.md
    metrics = {
        "training_samples_measured_hhv": int(len(df_train)),
        "total_samples_scored": int(len(df_fact)),
        "regimes": {
            "FULL_PROX_ULT_8F": {"best_model": m_full_name, "candidates": res_full, "permutation_importance": imp_full},
            "ULTIMATE_ONLY_5F": {"best_model": m_ult_name, "candidates": res_ult, "permutation_importance": imp_ult},
            "PROXIMATE_ONLY_3F": {"best_model": m_prox_name, "candidates": res_prox, "permutation_importance": imp_prox},
        },
        "kmeans_clusters": [
            {
                "grade": cid_to_grade[cid], "n_samples": cnt,
                "mean_hhv_mj_kg": round(mh, 3), "mean_ash_pct_db": round(ma, 3), "mean_sulfur_pct_db": round(ms, 4)
            }
            for cid, _, mh, ma, ms, cnt in clust_stats
        ],
    }
    (WAREHOUSE_DIR / "ml_model_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # Tulis laporan ringkas ML_REPORT.md
    lines = [
        "# Laporan Pemodelan ML Biomassa (HHV Regression & K-Means Boiler Grading)",
        "",
        f"- **Dataset Latih Berlabel HHV (Mendeley):** `{len(df_train)}` sampel (8 fitur Proximate + Ultimate lengkap)",
        f"- **Total Sampel Terprediksi & Terklaster di `fact_biomass_chemistry`:** `{len(df_fact)}` sampel (`315` OOF CV + `{int(ua_mask.sum())}` Ultimate-Only + `{int(pa_mask.sum())}` Proximate-Only)",
        "",
        "## 1. Performa 5-Fold Cross-Validation Prediksi HHV (MJ/kg)",
        "",
        "| Regime Fitur | Model Terbaik | CV5 R² | CV5 RMSE (MJ/kg) | CV5 MAE (MJ/kg) | Top-3 Fitur Terpenting |",
        "| :--- | :--- | :---: | :---: | :---: | :--- |",
    ]
    for rname, rinfo in metrics["regimes"].items():
        bm = rinfo["best_model"]
        st = rinfo["candidates"][bm]
        top3 = ", ".join(f"`{k}` ({v:.3f})" for k, v in list(rinfo["permutation_importance"].items())[:3])
        lines.append(f"| `{rname}` | {bm} | **{st['cv5_r2']:.4f}** | {st['cv5_rmse_mj_kg']:.4f} | {st['cv5_mae_mj_kg']:.4f} | {top3} |")

    lines += [
        "",
        "## 2. Klasterisasi Kelayakan Boiler (K-Means `k=3`)",
        "",
        "| Boiler Suitability Grade | Jumlah Sampel | Rata-rata HHV (MJ/kg) | Rata-rata Ash (% db) | Rata-rata Sulfur (% db) |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for c in metrics["kmeans_clusters"]:
        lines.append(f"| {c['grade']} | {c['n_samples']} | {c['mean_hhv_mj_kg']:.2f} | {c['mean_ash_pct_db']:.2f} | {c['mean_sulfur_pct_db']:.3f} |")

    lines += [
        "",
        "## 3. Profil Empiris & ML per 5 Feedstock Utama (`dim_feedstock`)",
        "",
        "| Feedstock | Sampel Lab | Median HHV Aktual (MJ/kg) | Median HHV ML (MJ/kg) | Median Ash (% db) | Median Sulfur (% db) | Grade Kelayakan | Risiko Slagging |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |",
    ]
    for _, fr in dim_fs[dim_fs["feedstock_key"].isin([1, 2, 3, 4, 5])].iterrows():
        n_s = int((df_fact["feedstock_key"] == int(fr["feedstock_key"])).sum())
        lines.append(
            f"| {fr['nama_limbah_biomassa']} | {n_s} | {fr['avg_hhv_mj_kg']:.2f} | {fr['ml_predicted_hhv_mj_kg']:.2f} | "
            f"{fr['avg_ash_pct_db']:.2f} | {fr['avg_sulfur_pct_db']:.3f} | {fr['boiler_suitability_grade']} | {fr['slagging_risk_level']} |"
        )
    (WAREHOUSE_DIR / "ML_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nSelesai ML enrichment -> warehouse/ML_REPORT.md & warehouse/tables/fact_biomass_chemistry.csv")


if __name__ == "__main__":
    main()
