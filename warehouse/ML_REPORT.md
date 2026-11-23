# Laporan Pemodelan ML Biomassa (HHV Regression & K-Means Boiler Grading)

- **Dataset Latih Berlabel HHV (Mendeley):** `315` sampel (8 fitur Proximate + Ultimate lengkap)
- **Total Sampel Terprediksi & Terklaster di `fact_biomass_chemistry`:** `2229` sampel (`315` OOF CV + `1023` Ultimate-Only + `891` Proximate-Only)

## 1. Performa 5-Fold Cross-Validation Prediksi HHV (MJ/kg)

| Regime Fitur | Model Terbaik | CV5 R² | CV5 RMSE (MJ/kg) | CV5 MAE (MJ/kg) | Top-3 Fitur Terpenting |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `FULL_PROX_ULT_8F` | ExtraTrees | **0.6589** | 1.4303 | 1.0121 | `c_pct_db` (0.707), `ash_pct_db` (0.123), `h_pct_db` (0.081) |
| `ULTIMATE_ONLY_5F` | Ridge | **0.6523** | 1.4440 | 1.0963 | `c_pct_db` (1.148), `n_pct_db` (0.105), `o_pct_db` (0.051) |
| `PROXIMATE_ONLY_3F` | SVR_RBF | **0.5252** | 1.6873 | 1.2376 | `vm_pct_db` (0.599), `fc_pct_db` (0.504), `ash_pct_db` (0.455) |

## 2. Klasterisasi Kelayakan Boiler (K-Means `k=3`)

| Boiler Suitability Grade | Jumlah Sampel | Rata-rata HHV (MJ/kg) | Rata-rata Ash (% db) | Rata-rata Sulfur (% db) |
| :--- | :---: | :---: | :---: | :---: |
| Grade A (High Calorie - Low Ash) | 103 | 23.15 | 4.86 | 0.874 |
| Grade B (Moderate / Conditioning Needed) | 1952 | 18.82 | 4.28 | 0.136 |
| Grade C (High Ash / Slagging Risk) | 174 | 15.61 | 18.30 | 0.209 |

## 3. Profil Empiris & ML per 5 Feedstock Utama (`dim_feedstock`)

| Feedstock | Sampel Lab | Median HHV Aktual (MJ/kg) | Median HHV ML (MJ/kg) | Median Ash (% db) | Median Sulfur (% db) | Grade Kelayakan | Risiko Slagging |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| Sekam Padi (Rice Husk) | 50 | 15.67 | 16.52 | 17.93 | 0.080 | Grade C (High Ash / Slagging Risk) | HIGH (Ash >= 10%) |
| Tongkol Jagung (Corn Cob) | 56 | 16.25 | 18.47 | 6.51 | 0.110 | Grade B (Moderate / Conditioning Needed) | MODERATE (Ash 6-10%) |
| Cangkang Sawit (Palm Kernel Shell / PKS) | 40 | 18.83 | 18.76 | 6.00 | 0.180 | Grade B (Moderate / Conditioning Needed) | MODERATE (Ash 6-10%) |
| Ampas Tebu (Sugarcane Bagasse) | 57 | 17.37 | 18.53 | 4.07 | 0.065 | Grade B (Moderate / Conditioning Needed) | MODERATE (Ash 6-10%) |
| Serbuk Gergaji & Serpihan Kayu (Sawdust / Woodchips) | 366 | 19.57 | 19.28 | 1.33 | 0.030 | Grade A (High Calorie - Low Ash) | LOW (Ash < 6%) |