# Laporan QA Semantic Model Power BI via MCP (`Dashboard_Biomassa_PLTU_ProjectKB`)

Tanggal QA: 2026-11-26 14:27:08 +07:00  
Koneksi Power BI Desktop: `PBIDesktop-Untitled - Power BI Desktop-54836` (`localhost:54836`, judul jendela `Dashboard_Biomassa_PLTU_ProjectKB`, kompatibilitas `1550`)  
Status Validasi Keseluruhan: 10/10 Success Criteria PASS (14 tabel, 1 parameter M `FolderProjectKB`, 7 relasi aktif satu arah, 36/36 measure berstatus `Ready`, 24/24 patokan angka SQLite cocok tepat)

## 1. Inventaris objek Semantic Model dan uji jumlah baris (`SC-01` s.d. `SC-06`)

Seluruh 11 sumber CSV dimuat lewat parameter Power Query `FolderProjectKB` (`"D:\UPN VY\Semester 5\BI\Tugas\projectkb"`) menggunakan `Encoding=65001`, `QuoteStyle=QuoteStyle.Csv`, dan `Table.TransformColumnTypes(..., "en-US")`.

| Kategori | Nama tabel / objek | Jumlah baris (Aktual DAX) | Patokan | Status |
| :--- | :--- | :---: | :---: | :---: |
| Dimensi inti | `dim_conversion_tech` | 2 | 2 | PASS |
| Dimensi inti | `dim_time` | 16 | 16 | PASS |
| Dimensi inti | `dim_feedstock` | 10 | 10 | PASS |
| Dimensi inti | `dim_location` | 560 | 560 | PASS |
| Dimensi inti | `dim_power_plant` | 119 | 119 | PASS |
| Fakta inti | `fact_feedstock_potential` | 69,686 | 69,686 | PASS |
| Fakta inti | `fact_pltu_operations` | 548 | 548 | PASS |
| Tabel bantu terpisah | `dim_view_mode` | 2 | 2 | PASS |
| Tabel bantu terpisah | `dim_shap_importance` | 11 | 11 | PASS |
| Tabel bantu terpisah | `dim_ml_model_metrics` | 6 | 6 | PASS |
| Tabel bantu terpisah | `dim_phyllis2_validation` | 10 | 10 | PASS |
| Parameter What-If | `Param CoFiring Pct` (`0.05`..`0.20`) | 16 | 16 | PASS |
| Parameter What-If | `Param Coal HHV` (`18.0`..`22.0`) | 9 | 9 | PASS |
| Wadah measure | `_Measures` (36 measure, `_Dummy` tersembunyi) | 1 | 1 | PASS |

### Pemeriksaan struktur model dan locale desimal (`en-US`)

| Uji struktur / locale | Hasil aktual | Syarat lulus | Status |
| :--- | :---: | :---: | :---: |
| Parameter `FolderProjectKB` (`kind: M`) | 1 parameter, dipakai di 11/11 partisi CSV | 11/11 partisi memakai `FolderProjectKB` | PASS |
| Smoke test `dim_conversion_tech[efficiency_pct]` (`TECH02`) | 25.45 | 25.45 | PASS |
| Locale `dim_feedstock[actual_hhv_db]` (`FS01`) | 19.845 | 19.845 | PASS |
| Locale `dim_feedstock[ash_db]` (`FS04`) | 18.03 | 18.03 | PASS |
| Relasi Star Schema (`relationship_operations(List)`) | 7 relasi aktif `Many -> One`, `OneDirection` | Tepat 7 relasi aktif, 0 pada tabel bantu & What-If | PASS |
| Status kompilasi measure (`measure_operations(Get)`) | 36/36 berstatus `Ready`, 0 galat | 36/36 `Ready` tanpa pesan galat | PASS |

## 2. Pengujian 24 patokan angka SQLite (`QA-01` s.d. `QA-03`, `SC-07`)

Seluruh nilai dieksekusi langsung melalui `dax_query_operations(Execute)` dengan `resultMode: "Inline"` terhadap model live dan dibandingkan dengan `warehouse_v2/powerbi/qa_expected_benchmarks.csv`.

### QA-01: Nasional (`LATEST_COMPLETE`, `TECH01`)

| Metrik | Aktual DAX | Patokan SQLite | Deviasi absolut | Status |
| :--- | :---: | :---: | :---: | :---: |
| Eligible Generation (TWh) | 79.74 | 79.74 | 0.00 | PASS |
| Eligible Capacity (MW) | 13,003 | 13,003.0 | 0.00 | PASS |
| Eligible Biomass Supply (Mt) | 74.26 | 74.26 | 0.00 | PASS |
| Excluded FS04/FS05 Volume (Mt) | 55.17 | 55.17 | 0.00 | PASS |
| Max Coal Replaced (Mt) | 43.49 | 43.49 | 0.00 | PASS |
| Max CO2e Offset (Mt CO2e) | 82.29 | 82.29 | 0.00 | PASS |
| Weighted Field LHV (MJ/kg) | 11.71 | 11.71 | 0.00 | PASS |
| Technical Suitability Score (%) | 57.4 | 57.4 | 0.00 | PASS |

### QA-02: Nasional (`ANCHOR_2022`, `TECH01`)

| Metrik | Aktual DAX | Patokan SQLite | Deviasi absolut | Status |
| :--- | :---: | :---: | :---: | :---: |
| Eligible Generation (TWh) | 47.06 | 47.06 | 0.00 | PASS |
| Eligible Capacity (MW) | 7,675 | 7,675.0 | 0.00 | PASS |
| Eligible Biomass Supply (Mt) | 48.7 | 48.7 | 0.00 | PASS |
| Excluded FS04/FS05 Volume (Mt) | 49.8 | 49.8 | 0.00 | PASS |
| Max Coal Replaced (Mt) | 25.67 | 25.67 | 0.00 | PASS |
| Max CO2e Offset (Mt CO2e) | 48.57 | 48.57 | 0.00 | PASS |
| Weighted Field LHV (MJ/kg) | 10.54 | 10.54 | 0.00 | PASS |
| Technical Suitability Score (%) | 49.4 | 49.4 | 0.00 | PASS |

### QA-03: Simulator 5 Pulau (`LATEST_COMPLETE`, `TECH01`, `Param Coal HHV = 20`)

| Skenario | Metrik | Aktual DAX | Patokan SQLite | Deviasi absolut | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Co-Firing 10% | Target Co-Firing (TWh) | 21.87 | 21.87 | 0.00 | PASS |
| Co-Firing 10% | Realizable Supply-Capped (TWh) | 21.87 | 21.87 | 0.00 | PASS |
| Co-Firing 10% | Coal Saved Realizable (Mt) | 11.93 | 11.93 | 0.00 | PASS |
| Co-Firing 10% | CO2e Offset Realizable (Mt CO2e) | 22.57 | 22.57 | 0.00 | PASS |
| Co-Firing 20% | Target Co-Firing (TWh) | 43.74 | 43.74 | 0.00 | PASS |
| Co-Firing 20% | Realizable Supply-Capped (TWh) | 37.99 | 37.99 | 0.00 | PASS |
| Co-Firing 20% | Coal Saved Realizable (Mt) | 20.72 | 20.72 | 0.00 | PASS |
| Co-Firing 20% | CO2e Offset Realizable (Mt CO2e) | 39.21 | 39.21 | 0.00 | PASS |

## 3. Uji invarian Review Focus dan realisasi CREA 2024 (`QA-04`, `QA-05`, `SC-08`, `SC-09`)

| Pengujian | Nilai aktual | Nilai target | Fungsi yang diverifikasi | Status |
| :--- | :---: | :---: | :--- | :---: |
| `Guard_NoTechFilter_TWh` | 79.74 | 79.74 | `SELECTEDVALUE(..., "TECH01")` mencegah penjumlahan ganda `TECH01 + TECH02` | PASS |
| `Guard_FS04_FS05_Ton` | 0 | 0 | Isolasi residu abu tinggi `FS04` dan `FS05` tepat 0 ton | PASS |
| `DT_Riau_Elig_GWh` | 12,670.9 | 12,670.9 | Potensi listrik layak provinsi Riau | PASS |
| `DT_Riau_Sumatera_PLTU` | 29,973.9 | 29,973.9 | `ALL(dim_location) + TREATAS` menjaga konteks PLTU Pulau Sumatera saat Drill-Through ke Riau | PASS |
| `Tech02_Elig_TWh` | 61.49 | 61.49 | Rasio teknologi gasifikasi `TECH02` (25.45% vs 33.0%) | PASS |
| `CREA_Total_Stations` | 48 | 48 | Jumlah baris realisasi PLTU CREA 2024 | PASS |
| `CREA_Reported_MWh_Plants` | 42 | 42 | Jumlah PLTU dengan laporan MWh > 0 pada CREA 2024 | PASS |
| `CREA_Total_GWh` | 1,506.1 | 1,506.1 | Total listrik biomassa CREA 2024 | PASS |
| `CREA_Total_kt` | 1,457.7 | 1,457.7 | Total biomassa terpakai CREA 2024 | PASS |

## 4. Verifikasi ekspor cadangan TMDL dan batas read-only (`SC-10`)

Ekspor TMDL via `database_operations(ExportToTmdlFolder)` ke `warehouse_v2/powerbi/tmdl_export/` menghasilkan 19 berkas (`database.tmdl`, `model.tmdl`, `relationships.tmdl`, `expressions.tmdl`, `cultures/en-US.tmdl`, dan 14 definisi tabel di `tables/*.tmdl`). Pemeriksaan `git status` memastikan tidak ada satu pun berkas di `raw_data/`, `warehouse/`, `warehouse_v2/tables/`, atau `warehouse_v2/biomass_dwh_v2.sqlite` yang dimodifikasi.
