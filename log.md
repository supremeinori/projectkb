# Log dokumentasi dan perubahan proyek

Dokumen ini mencatat seluruh keputusan teknis, perubahan file, progres pengerjaan, dan hasil verifikasi pada proyek Biomass & Waste-to-Energy Feedstock Finder. Setiap kali ada perubahan rencana, pembuatan notebook, pembersihan data, atau eksperimen model baru, tambahkan entri terbaru pada bagian riwayat perubahan agar seluruh anggota kelompok dapat melacak status proyek dengan cepat.

## Status tahapan proyek

| Tahap | Cakupan utama | Artefak target | Status | Terakhir diperbarui |
| :--- | :--- | :--- | :--- | :--- |
| Tahap 0 | Audit data mentah, penyelarasan Project Brief, dan penyusunan rencana kerja | `implementation_plan.md`, `log.md` | Selesai | 2026-11-25 |
| Tahap 1 | EDA, pembersihan Mendeley (termasuk normalisasi 14 baris DAF), kurasi 10 profil Phyllis2 + RPR, dan migrasi penuh produksi ke BDSP Kementan `kabkota` (514 kab/kota kanonik) + BPS Kayu dengan strategi *Dual-View* | `notebooks/01_eda_and_cleaning.ipynb`, 9 file CSV di `data/processed/` (+ `phyllis2_10_validated.csv` dari Tahap 2B), 2 grafik EDA | Selesai & Terverifikasi | 2026-11-25 |
| Tahap 2A | Pelatihan model regresi HHV (Skenario A dan B), evaluasi internal, audit residual, dan interpretabilitas SHAP | `notebooks/02_ml_hhv_training_and_shap.ipynb`, 2 model `.joblib`, `metrics_summary.json`, 8 grafik evaluasi & SHAP | Selesai & Terverifikasi | 2026-11-25 |
| Tahap 2B | Validasi eksternal pada `FS01`-`FS10`, konversi LHV lapangan, screening boiler, dan *K-Means* | `notebooks/03_external_validation_and_screening.ipynb`, `phyllis2_10_validated.csv`, `kmeans_feedstock_profile.joblib`, 4 grafik validasi & klaster | Selesai & Terverifikasi | 2026-11-25 |
| Tahap 3 | Pembersihan kayu KLHK PHL, *staging* ringan PLTU, kalkulasi energi/listrik/CO2e, dan pembangunan *Star Schema* 2-fakta + 5-dimensi di `warehouse_v2/` | `notebooks/04_dwh_etl_and_star_schema.ipynb`, `klhk_kayu_provinsi_clean.csv`, `warehouse_v2/` (SQLite, DDL, 7 CSV, laporan QA) | Selesai & Terverifikasi | 2026-11-25 |
| Tahap 4 | Perancangan dan paket implementasi *Dashboard* Power BI 4 halaman (+ 1 *Drill-Through* tersembunyi), wireframe Obsidian Excalidraw/PNG, tema JSON WCAG AA, helper CSV, DAX/PQ, dan Brief PDF pemula | `docs/wireframes/` (6 PNG + 7 `.excalidraw.md`), `warehouse_v2/powerbi/` (10 file), `docs/Brief_Implementasi_Dashboard_PowerBI_ProjectKB.pdf` | Paket Desain & Brief Selesai (Siap Rakit `.pbix`) | 2026-11-26 |

## Keputusan teknis yang disepakati

Tabel berikut merangkum keputusan utama yang ditetapkan sebelum eksekusi kode agar alasan di balik setiap aturan pembersihan dan pemodelan mudah ditelusuri oleh anggota tim lain.

| ID | Topik | Keputusan | Alasan dan dasar data |
| :--- | :--- | :--- | :--- |
| `DEC-01` | Sumber data proyek | Hanya memakai 4 sumber data di `raw_data/`: `biomass_hhv_315_samples.csv`, `phyllis2_all_18_wide-v3.csv`, `ref_rpr_parameters.csv`, dan seluruh isi `raw_data/02_bps/bps_ri/` | Mengunci ruang lingkup pada data biomassa pertanian, perkebunan, dan kayu yang tersedia saat ini tanpa SIPSN KLHK; file lain di direktori proyek diabaikan |
| `DEC-02` | Cakupan profil Phyllis2 | Menyaring `phyllis2_all_18_wide-v3.csv` hanya pada 10 profil `FS01`-`FS10` | `FS01`-`FS10` berpasangan satu-ke-satu dengan `ref_rpr_parameters.csv` dan komoditas BPS, sedangkan `FS11`-`FS18` mencakup sampah/RDF/plastik dan kategori umum di luar cakupan data pasokan saat ini |
| `DEC-03` | Nilai kosong `VM` dan `FC` pada `FS01` | Mengimputasi `vm_db` (75,04%) dan `fc_db` (21,04%) pada `FS01` (`palm kernel shell`) dari rasio rata-rata 4 sampel PKS bersih di Mendeley, dengan kolom penanda `proximate_source` | `FS01` kosong pada `VM_dry_pct` dan `FC_dry_pct` di Phyllis2; imputasi berbasis rasio non-abu menjaga neraca massa 100% dan memungkinkan evaluasi penuh Skenario A dan B, sembari tetap melaporkan metrik eksternal terpisah untuk 10 profil dan 9 profil murni tanpa `FS01` |
| `DEC-04` | Pembersihan anomali Mendeley | Menghapus 16 duplikat fitur-target, mempertahankan seluruh 6 kategori (termasuk `manure`), dan menyaring 31 anomali ekstrem (`prox_sum` atau `ult_sum` di luar 90%-105%, atau HHV di luar 10-28 MJ/kg) | Menghilangkan risiko kebocoran data latih-uji dan membuang kesalahan entri neraca massa parah (terutama referensi `[26]` yang mencatat `VM+FC` basis *daf* ditambah abu), menyisakan 268 sampel bersih plus flag `mass_balance_warning` untuk deviasi ringan |
| `DEC-05` | Cakupan dan granularitas data BPS | Membersihkan seluruh tahun historis (37 file CSV) dan memisahkannya ke 3 tabel sesuai level wilayah: provinsi (perkebunan 2008-2024, padi 2018-2024, jagung 2020-2024), pulau (kayu HPH 2019-2022), dan nasional (12 sub-jenis kayu bulat HTI 2020-2023) | Menghindari disagregasi fiktif data kayu ke provinsi dan mencegah penghitungan ganda pada total `A. JUMLAH KAYU BULAT (M3)` maupun baris `INDONESIA`; seluruh nilai kosong BPS dicatat di log tanpa imputasi sesuai Project Brief |
| `DEC-06` | Kadar air untuk konversi LHV dan parameter alkali | Memakai `moisture_lapangan_pct` dari `ref_rpr_parameters.csv` untuk menghitung `effective_lhv_field_mj_kg`, serta mengonversi `K2O_ash_pct`/`Na2O_ash_pct` ke basis kering saat `K_dry_mg_kg`/`Na_dry_mg_kg` kosong | Project Brief mensyaratkan LHV berbasis kadar air tipikal lapangan, sedangkan `Moisture_ar_pct` Phyllis2 berupa sampel uji lab yang lebih kering; konversi oksida abu melengkapi screening alkali pada `FS03`, `FS07`, `FS08`, dan `FS10` |
| `DEC-07` | Fokus rencana dan standar dokumentasi | Memangkas sementara Fase 3-4 dari `implementation_plan.md` hingga Tahap 1-2 selesai, dan mewajibkan dokumentasi rinci di setiap sel notebook serta pembaruan `log.md` | Memastikan pembersihan data dan model ML diverifikasi terlebih dahulu dan seluruh anggota tim kelompok dapat memahami tiap langkah beserta alasannya |
| `DEC-08` | Normalisasi DAF Mendeley & kalibrasi target internal R² | Menambahkan normalisasi basis *Dry Ash-Free* (DAF) ke *Dry Basis* untuk 14 baris Mendeley (`C+H+O+N+S ≈ 100%`, `ult_sum > 102%`) serta mengkalibrasi target uji internal (Skenario B: R² ≥ 0,65, RMSE ≤ 1,10 MJ/kg, MAPE ≤ 6%; Skenario A: R² ≥ 0,45, RMSE ≤ 1,40 MJ/kg, MAPE ≤ 7,5%), sambil mempertahankan target eksternal MAPE ≤ 10% | Audit empiris Channiwala-Parikh (`R² = 0,293` pada 268 baris) membuktikan adanya *noise* literatur bawaan di Mendeley dan penyempitan varians setelah penghapusan *outlier* 4,2-9,9 MJ/kg; model terlatih tetap mencatat MAPE eksternal 3,27%-3,40% pada profil Phyllis2 terkurasi |
| `DEC-09` | Aturan pemilihan model `.joblib` utama | Mengunci model `.joblib` utama per skenario ke algoritma *tree-based* terbaik (*Random Forest* atau *XGBoost* berdasarkan 5-Fold CV RMSE terendah), dengan *Ridge Regression* tetap dicatat sebagai *baseline* linear | Menyelaraskan model prediksi utama dengan penekanan Project Brief pada *ensemble* + SHAP `TreeExplainer`, sekaligus menjaga konsistensi antara model `.joblib`, interpretasi SHAP, dan validasi eksternal (Random Forest Skenario B mencapai MAPE eksternal 3,40% pada 10 profil dan 3,27% pada 9 profil murni) |
| `DEC-10` | Migrasi produksi ke BDSP Kementan `kabkota` + BPS Kayu | Memindahkan sumber produksi Padi, Jagung, Kelapa Sawit, dan Tebu dari level provinsi BPS RI ke 152 file `raw_data/01_bdsp_kementan/*/kabkota/` dengan harmonisasi 541 kode wilayah mentah menjadi 514 kab/kota resmi (memetakan 26 kode lama 4 DOB Papua + kode nama lama `9437` ke `9408` tanpa penghitungan ganda), sambil mempertahankan kayu bulat BPS (`1973_kayu_hph_pulau` dan `2512_kayu_jenis_pohon`) | Meningkatkan ketajaman analisis spasial untuk radius ekonomi pasok 50-100 km (`Dim_Location` tingkat kab/kota), sembari mempertahankan pasokan kayu untuk `FS09` dan `FS10` yang tidak tersedia di Kementan |
| `DEC-11` | Strategi Dual-View & audit kekosongan BDSP tanpa imputasi | Menerapkan *Dual-View* (`is_anchor_2022` untuk komparasi satu tahun kalender yang sama dan `is_latest_complete_year` untuk tahun penuh terbaru tiap komoditas: Padi 2025, Sawit PR 2024, Tebu 2022, Jagung 2017, Kayu Pulau 2022, Kayu Nasional 2023) plus kolom `cakupan_data`; mengubah anomali sawit 2015 (`1507`: 37,96 juta ton) dan kekosongan pelaporan massal (`Jagung` 2023-2025, `Kelapa Sawit` Aceh 2025) menjadi `NaN` tanpa imputasi di `production_audit_log.csv` | Menangani perbedaan rentang tahun dan cakupan antar komoditas BDSP (Sawit PR saja sejak 2018, Tebu parsial sejak 2023, Jagung 9 provinsi pada 2020-2022 dan nol total pada 2023-2025) secara jujur tanpa membuang sentra jagung nasional atau menipu grafik tren dengan angka nol palsu |
| `DEC-12` | Arsitektur Star Schema Tahap 3 (`warehouse_v2/`), Kayu KLHK PHL, dan Integrasi PLTU | Membangun *Data Warehouse* baru di folder terpisah `warehouse_v2/` memakai pola Kimball 2-fakta (`fact_feedstock_potential` + `fact_pltu_operations`) + 5-dimensi bersama (`dim_feedstock`, `dim_location`, `dim_conversion_tech`, `dim_time`, `dim_power_plant`) melalui `notebooks/04_dwh_etl_and_star_schema.ipynb`; menggunakan kayu bulat KLHK PHL (`PBPH + Perum Perhutani`, level provinsi 2018-2024) dan data PLTU dari `warehouse/tables/` (*read-only*) setelah pembersihan ringan (agregasi 3 stasiun multi-blok CREA, pemisahan peran Climate TRACE vs CREA, dan pengeluaran WRI 2017 sekunder) | Menjaga `warehouse/` lama tetap utuh, memetakan 100% volume kayu bulat nasional (55,55 juta m3 pada 2024 termasuk Perhutani Pulau Jawa) ke level provinsi, menghadirkan sisi permintaan PLTU nyata untuk simulator *co-firing*, serta menerapkan seluruh hasil bersih Tahap 1-2 (10 profil Phyllis2, LHV lapangan, `recoverability_factor`, *rule-based boiler screening*, dan 514 kab/kota kanonik *Dual-View*) |
| `DEC-13` | Arsitektur Dashboard Power BI 4 Halaman (+ 1 Drill-Through), Jalur Koneksi CSV + Lampiran ODBC, dan Tema Terang Editorial Energi | Menetapkan Power BI Desktop dengan arsitektur 4 halaman utama (Ringkasan Eksekutif, Penyaringan & ML SHAP, Peta Pasokan & PLTU, Simulator Co-Firing) ditambah 1 halaman tersembunyi `3B. Detail Wilayah` (*Drill-Through*), memakai import CSV langsung + parameter `FolderProjectKB` sebagai jalur utama (dan lampiran SQLite ODBC opsional), `pltu_101_overlay.geojson` untuk *Reference Layer* Azure Map, serta *Tema Terang Editorial Energi* (`theme_biomass_bi.json`) terverifikasi WCAG 2.1 AA (20/20 PASS) | Memudahkan anggota tim dengan kemampuan Power BI tingkat dasar merakit `.pbix` tanpa instalasi driver ODBC wajib, menghindari penjumlahan ganda `TECH01 + TECH02` lewat proteksi DAX `SELECTEDVALUE`, mencegah kartu PLTU kosong saat *Drill-Through* provinsi lewat pola `ALL(dim_location) + TREATAS`, dan memverifikasi hasil terhadap 24 angka patokan SQLite |

## Riwayat perubahan

### [2026-11-26] Entri 09: Wireframe Excalidraw/PNG, Paket Pendukung Power BI (`warehouse_v2/powerbi/`), dan Brief PDF Implementasi

- Ruang lingkup: Tahap 4 (perancangan wireframe 4+1 halaman, pembuatan paket aset siap impor Power BI, dan penyusunan Brief PDF langkah demi langkah untuk pengguna Power BI dasar).
- File dibuat:
  - `docs/wireframes/` (6 gambar PNG terinspeksi visual + 7 file Obsidian Excalidraw `.excalidraw.md` termasuk kanvas gabungan `dashboard_all_pages_master.excalidraw.md`)
  - `warehouse_v2/powerbi/` (10 file: `dim_view_mode.csv`, `dim_shap_importance.csv`, `dim_ml_model_metrics.csv`, `dim_phyllis2_validation.csv`, `pltu_101_overlay.geojson` berisi 101 titik PLTU, `qa_expected_benchmarks.csv` berisi 24 angka patokan, `theme_biomass_bi.json`, `dax_measures_projectkb.dax`, `power_query_m_snippets.pq`, `DESIGN.md`)
  - `docs/Brief_Implementasi_Dashboard_PowerBI_ProjectKB.pdf` (24 halaman A4 bergambar wireframe, diagram SVG Star Schema, Power Query M, seluruh 6 grup rumus DAX, pengaturan Field Well per visual, 24 angka patokan QA, dan lampiran SQLite ODBC)
- File diubah: `log.md`.
- Ringkasan perubahan: menyusun cetak biru visual 4 halaman utama + 1 halaman Drill-Through berbasis angka aktual `warehouse_v2`, mengekstrak seluruh metrik SHAP dan validasi Phyllis2 dari `metrics_summary.json` menjadi CSV siap impor, membuat layer GeoJSON 101 PLTU untuk Azure Map, memvalidasi 20/20 rasio kontras WCAG 2.1 pada *Tema Terang Editorial Energi*, serta merakit brief PDF lengkap ramah pemula Power BI.
- Hasil verifikasi:
  - Seluruh 20/20 pasangan warna pada `theme_biomass_bi.json` lulus audit kontras WCAG 2.1 (teks normal 5,66:1 hingga 15,55:1 >= 4,5:1; kontrol/batang 4,26:1 hingga 7,82:1 >= 3,0:1).
  - Seluruh 7 file `.excalidraw.md` valid Excalidraw v2 JSON dengan 100% sinkronisasi `Text Elements`; seluruh 6 PNG wireframe dan 24 halaman PDF lulus inspeksi visual langsung tanpa tumpang tindih atau pemotongan kode.
  - Direktori baca saja `raw_data/` dan `warehouse/` lama tetap utuh tanpa modifikasi.

### [2026-11-25] Entri 08: Eksekusi & verifikasi penuh Tahap 3 (`04_dwh_etl_and_star_schema.ipynb` & `warehouse_v2/`)

- Ruang lingkup: Tahap 3 (integrasi kayu KLHK PHL, *staging* ringan PLTU, kalkulasi energi/listrik/batu bara/CO2e, dan pembangunan *Data Warehouse* Star Schema `warehouse_v2/`).
- File dibuat:
  - `notebooks/04_dwh_etl_and_star_schema.ipynb` (22 sel: 14 Markdown, 8 kode, 0 galat)
  - `data/processed/klhk_kayu_provinsi_clean.csv` (281 baris: gabungan `PBPH` 2018-2024 dan `Perum Perhutani` 2018-2024 di 37 provinsi, 15 kolom dengan flag *Dual-View*)
  - `warehouse_v2/ddl_star_schema.sql` (skrip DDL 7 tabel + indeks + 5 *analytical views*)
  - `warehouse_v2/biomass_dwh_v2.sqlite` (database SQLite lengkap dengan `PRAGMA foreign_keys = ON`)
  - `warehouse_v2/tables/` (7 CSV siap BI: `dim_feedstock.csv` 10 baris, `dim_location.csv` 560 baris, `dim_conversion_tech.csv` 2 baris, `dim_time.csv` 16 baris, `dim_power_plant.csv` 119 baris, `fact_feedstock_potential.csv` 69.686 baris, `fact_pltu_operations.csv` 548 baris)
  - `warehouse_v2/DWH_V2_QA_REPORT.md` (laporan QA otomatis 10/10 PASS)
  - `outputs/figures/04_dwh_supply_vs_pltu_dualview.png`
- File diubah: `implementation_plan.md`, `log.md`.
- Ringkasan perubahan: mengeksekusi seluruh pipeline Tahap 3 dari hulu ke hilir, menyatukan `PBPH + Perum Perhutani` KLHK PHL (2018-2024), membersihkan ringan data PLTU (`100` CT + `19` CREA-only = `119` stasiun unik; agregasi 3 stasiun multi-blok CREA menjadi `48` baris stasiun tanpa mengubah total `18.342,0 MW` & `1.457.720,0 ton`), menghitung potensi energi daerah memakai `recoverability_factor` dan `effective_lhv_field_mj_kg` untuk *Co-Firing PLTU* (`33,0%`) serta *Gasifikasi Biomassa* (`25,45%`), dan memuat seluruh tabel serta 5 *views* ke `warehouse_v2/`.
- Hasil verifikasi:
  - `PRAGMA foreign_key_check` menghasilkan `0` pelanggaran FK; 100% jumlah baris CSV cocok dengan SQLite (`70.941` total baris tabel).
  - Rekonsiliasi kayu KLHK PHL tepat `55.260.218,00 m3` (2022) dan `55.547.094,91 m3` (2024); deviasi maksimum rumus energi GJ = `0,000753` dan MWh = `0,000054` (ambang <= `0,01`).
  - Isolasi bahan baku gugur lulus dengan `0 ton` kontribusi `FS04`/`FS05` ke `is_boiler_eligible = 1` maupun `vw_supply_vs_pltu_5_pulau_dualview` (`10` baris: 5 pulau x 2 mode *Dual-View*).
  - Direktori baca saja `raw_data/` dan `warehouse/` lama terverifikasi utuh tanpa perubahan.

### [2026-11-25] Entri 07: Penyusunan rencana Tahap 3 (KLHK PHL, Staging PLTU, & Star Schema `warehouse_v2/`)

- Ruang lingkup: Perencanaan Tahap 3 (`implementation_plan.md` dan `log.md`, belum ada eksekusi kode Tahap 3).
- File diubah: `implementation_plan.md`, `log.md`.
- Ringkasan perubahan: mencatat `DEC-12`, menambahkan Bagian 5 di `implementation_plan.md` untuk desain `notebooks/04_dwh_etl_and_star_schema.ipynb` (pembersihan kayu KLHK PHL 2018-2024, pembersihan ringan data PLTU dari `warehouse/tables/`, rumus konversi energi GJ/MWh/MW/batu bara/CO2e berbasis LHV lapangan dan `recoverability_factor`, arsitektur 2-fakta + 5-dimensi beserta 5 *analytical views* di `warehouse_v2/`), serta memperluas Bagian 6 *Definition of Done* dan *Success Criteria* dengan 4 dimensi verifikasi terukur baru untuk Tahap 3.
- Hasil verifikasi: seluruh nama provinsi KLHK PHL (3 selisih nama), 8 baris ganda blok CREA/WRI, 2 nama PLTU kembar, dan 18 PLTU tanpa koordinat teraudit langsung dari sumber sebelum eksekusi.

### [2026-11-25] Entri 06: Migrasi penuh data produksi ke BDSP Kementan `kabkota` + BPS Kayu dengan Strategi Dual-View

- Ruang lingkup: Revisi Tahap 1 (`notebooks/01_eda_and_cleaning.ipynb`), pembaruan `implementation_plan.md` dan `log.md`, serta verifikasi invariansi Tahap 2 (`02` dan `03`).
- File dibuat/diperbarui:
  - `data/processed/bdsp_dim_kabkota.csv` (514 kab/kota kanonik di 38 provinsi, 6 kolom)
  - `data/processed/bdsp_kabkota_clean.csv` (32.896 baris: 514 kab/kota x 16 tahun 2010-2025 x 4 komoditas, 15 kolom lengkap dengan `cakupan_data`, `is_anchor_2022`, `is_latest_complete_year`, `is_latest_available_year`)
  - `data/processed/bps_kayu_pulau_clean.csv` (20 baris, ditambah flag Dual-View)
  - `data/processed/bps_kayu_nasional_clean.csv` (48 baris, ditambah flag Dual-View)
  - `data/processed/bps_kayu_nasional_reference.csv` (8 baris referensi total nasional kayu HPH & baris `A` HTI)
  - `data/processed/production_audit_log.csv` (8 catatan audit anomali, harmonisasi Papua, & konversi `0 -> NaN` tanpa imputasi)
  - `outputs/figures/01_eda_production_dualview.png`
  - `notebooks/01_eda_and_cleaning.ipynb` (23 sel: 15 Markdown, 8 kode, 0 galat)
  - `implementation_plan.md`, `log.md`.
- File lama dihapus: `data/processed/bps_provinsi_clean.csv`, `data/processed/bps_nasional_reference.csv`, `data/processed/bps_missing_audit_log.csv`, dan `outputs/figures/01_eda_bps_trends.png`.
- Ringkasan perubahan: menerapkan `DEC-10` dan `DEC-11`, mengonsolidasi 152 file CSV BDSP `kabkota` dan 8 file CSV kayu BPS, menyelaraskan 26 kode pemekaran 4 DOB Papua serta 1 kode nama lama `9437` (`Kab. Yapen Waropen`, 3.280,09 ton Padi 2017 -> `9408` `Kab. Kepulauan Yapen`) dengan 0 penghitungan ganda, mengonversi anomali skala sawit 2015 `1507` dan kekosongan pelaporan massal (`Jagung` 2023-2025 & `Kelapa Sawit` Aceh 2025) menjadi `NaN`, serta memverifikasi bahwa output Mendeley dan Phyllis2 tetap identik secara byte sehingga model ML dan validasi eksternal pada Notebook 02 dan 03 tetap utuh.
- Hasil verifikasi:
  - Invariansi SHA-256 lulus 100% pada `mendeley_clean.csv`, `mendeley_cleaning_log.csv`, dan `phyllis2_10_clean.csv`.
  - Seluruh 3 notebook (`01`: 23 sel, `02`: 15 sel, `03`: 15 sel) memiliki 0 galat dan 0 sel kode tak tereksekusi.
  - Seluruh 10 file CSV di `data/processed/`, 3 model `.joblib`, 14 grafik `.png`, dan `outputs/metrics_summary.json` lulus verifikasi *Definition of Done* dan *Success Criteria* pasca-migrasi.

### [2026-11-25] Entri 05: Eksekusi & verifikasi penuh Tahap 2A dan 2B (`02_ml_hhv_training_and_shap.ipynb` & `03_external_validation_and_screening.ipynb`)

- Ruang lingkup: Tahap 2A dan Tahap 2B (pelatihan ML, SHAP, validasi eksternal, konversi LHV, screening boiler, dan klasterisasi *K-Means*).
- File dibuat:
  - `notebooks/02_ml_hhv_training_and_shap.ipynb` (15 sel: 10 Markdown, 5 kode, 0 galat)
  - `notebooks/03_external_validation_and_screening.ipynb` (15 sel: 10 Markdown, 5 kode, 0 galat)
  - `models/best_hhv_proximate_only.joblib` (Random Forest, `max_depth=3`, `min_samples_leaf=2`, `n_estimators=180`)
  - `models/best_hhv_full_features.joblib` (Random Forest, `max_depth=6`, `min_samples_leaf=2`, `n_estimators=180`)
  - `models/kmeans_feedstock_profile.joblib` (`StandardScaler + KMeans`, `k=5`)
  - `data/processed/phyllis2_10_validated.csv` (10 baris, 52 kolom)
  - `outputs/metrics_summary.json`
  - 12 grafik `.png` di `outputs/figures/` (`02_internal_actual_vs_predicted.png`, `02_internal_residuals.png`, 6 plot SHAP Skenario A & B, `03_external_validation_actual_vs_pred.png`, `03_lhv_and_boiler_screening_matrix.png`, `03_kmeans_elbow_silhouette.png`, `03_kmeans_pca_projection.png`)
- File diubah: `implementation_plan.md`, `log.md`.
- Ringkasan perubahan: menerapkan `DEC-08` dan `DEC-09`, melatih Ridge/Random Forest/XGBoost dengan 5-Fold Stratified CV pada split 80/20 (214 latih / 54 uji), menghasilkan plot SHAP `TreeExplainer` untuk Skenario A & B, menguji model pada `FS01`-`FS10` dan `FS02`-`FS10`, menghitung `effective_lhv_field_mj_kg` berbasis kadar air lapangan (`FS02` 55% dan `FS06` 50% ditandai `high_moisture_flag = True`), menerapkan *rule-based boiler screening* (`FS04` dan `FS05` berstatus `Not Eligible`; `FS09` dan `FS10` berstatus `Low Risk`; `FS01` berstatus `Data Unavailable`), serta melatih *K-Means* (`k=5`, Silhouette `0,2976`) pada 268 sampel Mendeley sebelum memproyeksikan `FS01`-`FS10`.
- Hasil verifikasi:
  - Skenario A (Random Forest): `CV R2 = 0,3941`, `Test R2 = 0,4859`, `Test RMSE = 1,3292 MJ/kg`, `Test MAPE = 6,62%` (Ridge *baseline*: `Test R2 = 0,5501`, `Test RMSE = 1,2435`).
  - Skenario B (Random Forest): `CV R2 = 0,5241`, `Test R2 = 0,6884`, `Test RMSE = 1,0349 MJ/kg`, `Test MAPE = 4,94%` (Ridge *baseline*: `Test R2 = 0,6980`, `Test RMSE = 1,0188`).
  - Validasi Eksternal Skenario B: `MAPE = 3,40%` (`RMSE = 0,7564 MJ/kg`) pada 10 profil (`FS01`-`FS10`) dan `MAPE = 3,27%` (`RMSE = 0,7385 MJ/kg`) pada 9 profil murni (`FS02`-`FS10`). Validasi Eksternal Skenario A: `MAPE = 5,17%` (10 profil) dan `4,96%` (9 profil).
  - Seluruh gerbang *Definition of Done* dan *Success Criteria* di `implementation_plan.md` lulus tanpa galat.

### [2026-11-25] Entri 04: Eksekusi penuh Tahap 1 (`notebooks/01_eda_and_cleaning.ipynb`)

- Ruang lingkup: Tahap 1 (EDA dan pembersihan Mendeley, kurasi 10 profil Phyllis2 + RPR, dan standarisasi seluruh tahun BPS RI).
- File dibuat:
  - `notebooks/01_eda_and_cleaning.ipynb` (20 sel: 13 Markdown, 7 kode, 0 galat)
  - `data/processed/mendeley_clean.csv` (268 baris, 19 kolom; 14 baris ternormalisasi DAF ke *dry basis*)
  - `data/processed/mendeley_cleaning_log.csv` (47 baris: 16 duplikat fitur-target + 31 anomali ekstrem)
  - `data/processed/phyllis2_10_clean.csv` (10 baris `FS01`-`FS10`, 37 kolom lengkap dengan parameter RPR & kadar air lapangan)
  - `data/processed/bps_provinsi_clean.csv` (1.748 baris: Kelapa Sawit & Tebu 2008-2024, Padi 2018-2024, Jagung 2020-2024 di 38 provinsi)
  - `data/processed/bps_kayu_pulau_clean.csv` (20 baris: kayu bulat HPH 2019-2022 di 5 wilayah pulau)
  - `data/processed/bps_kayu_nasional_clean.csv` (48 baris: 12 sub-jenis kayu bulat HTI 2020-2023)
  - `data/processed/bps_nasional_reference.csv` (54 baris referensi agregat `INDONESIA` dan total `A. JUMLAH KAYU BULAT (M3)`)
  - `data/processed/bps_missing_audit_log.csv` (491 baris audit nilai kosong BPS tanpa imputasi)
  - `outputs/figures/01_eda_mendeley_overview.png` dan `outputs/figures/01_eda_bps_trends.png`
- Ringkasan perubahan: menjalankan pipeline pembersihan menyeluruh dari 4 sumber di `raw_data/` dengan dokumentasi rinci per sel dan menyimpan seluruh artefak Tahap 1 ke `data/processed/` serta `outputs/figures/`.
- Hasil verifikasi: 0 `NaN` pada fitur dan target ML (`mendeley_clean.csv` & `phyllis2_10_clean.csv`), neraca proksimat `FS01` genap `100,0%`, 0 baris `INDONESIA` di tabel wilayah BPS, dan selisih penjumlahan 12 sub-jenis kayu HTI terhadap baris `A` ≤ 2 m³.

### [2026-11-25] Entri 03: Penambahan Definition of Done dan Success Criteria di `implementation_plan.md`

- Ruang lingkup: Tahap 0 (penguncian kriteria selesai sebelum eksekusi kode).
- File diubah: `implementation_plan.md`, `log.md`.
- Ringkasan perubahan: memperluas Bagian 5 di `implementation_plan.md` dengan gerbang *Definition of Done* (kelengkapan artefak Tahap 1, 2A, 2B, standar dokumentasi notebook, pembaruan `log.md`, dan integritas `raw_data/` *read-only*) serta tabel *Success Criteria* terukur untuk 8 dimensi evaluasi (integritas Mendeley, Phyllis2 + RPR, BPS, performa ML Skenario B dan A, validasi eksternal 10 dan 9 profil, konsistensi fisika LHV, serta screening boiler dan klasterisasi).
- Hasil verifikasi: `implementation_plan.md` dan `log.md` tersimpan rapi; belum ada notebook atau kode pipeline yang dieksekusi.

### [2026-11-25] Entri 02: Pembuatan `log.md` dan penambahan standar dokumentasi notebook

- Ruang lingkup: Tahap 0 (persiapan kolaborasi tim sebelum eksekusi kode).
- File dibuat: `log.md`.
- File diubah: `implementation_plan.md` (menambahkan `log.md` di struktur direktori, menambahkan subbagian standar dokumentasi notebook untuk tugas kelompok, dan menambahkan langkah pencatatan `log.md` pada daftar periksa).
- Ringkasan perubahan: menyusun buku log pelacakan perubahan proyek, mencatat 7 keputusan teknis awal (`DEC-01` sampai `DEC-07`), dan menetapkan format dokumentasi wajib per tahap pada ketiga notebook yang akan dibuat.
- Hasil verifikasi: `log.md` terbuat di akar proyek dan seluruh standar dokumentasi tersinkronisasi dengan `implementation_plan.md`.

### [2026-11-25] Entri 01: Audit empat dataset mentah dan pembaruan `implementation_plan.md`

- Ruang lingkup: Tahap 0 (penyelarasan rencana terhadap Project Brief dan kondisi file aktual).
- File diubah: `implementation_plan.md`.
- File diperiksa (baca saja): `Project Brief - Biomass & Waste-to-Energy Feedstock Finder (1).pdf`, `raw_data/05_biomassa_komplementer/biomass_hhv_315_samples.csv`, `raw_data/05_biomassa_komplementer/phyllis2_all_18_wide-v3.csv`, `raw_data/05_biomassa_komplementer/ref_rpr_parameters.csv`, dan 37 file CSV di 6 subfolder `raw_data/02_bps/bps_ri/`.
- Ringkasan temuan dan perubahan:
  - Menemukan 16 duplikat fitur-target dan 31 anomali ekstrem neraca massa/HHV pada data Mendeley (315 baris mentah menjadi 268 sampel bersih setelah pembersihan).
  - Menemukan ketiadaan `VM_dry_pct`, `FC_dry_pct`, `Cl`, `K`, dan `Na` pada `FS01` (`palm kernel shell`) serta ketiadaan `Cl` pada `FS03` (`palm fiber`) di `phyllis2_all_18_wide-v3.csv`.
  - Menemukan perbedaan urutan kolom `Teh`/`Tebu` dan ketiadaan kolom `Tembakau` antara `132_perkebunan_historis` (2008-2023) dan `2566_perkebunan` (2024), nilai kosong akibat pemekaran 4 provinsi Papua dan `DKI JAKARTA`, serta perbedaan level agregasi pada kedua dataset kayu BPS.
  - Memperbarui `implementation_plan.md` agar seluruh path input, nama kolom, rumus pembersihan, strategi validasi eksternal (10 profil dan 9 profil murni), konversi LHV lapangan, screening boiler, dan klasterisasi *K-Means* sesuai dengan kondisi data aktual, serta memangkas sementara Fase 3 dan Fase 4.
- Hasil verifikasi: seluruh path input di `implementation_plan.md` terverifikasi ada di direktori kerja dan format penulisan bersih.

## Template entri log untuk pembaruan berikutnya

Salin blok berikut ke bagian paling atas di bawah judul "Riwayat perubahan" setiap kali menyelesaikan satu tahap atau revisi penting:

```markdown
### [YYYY-MM-DD] Entri XX: Judul singkat perubahan

- Ruang lingkup: Tahap X (nama tahap atau notebook).
- File dibuat: daftar file baru (jika ada).
- File diubah: daftar file yang dimodifikasi (jika ada).
- Ringkasan perubahan: uraian singkat apa yang dikerjakan dan alasan teknisnya.
- Hasil verifikasi: angka metrik utama, jumlah baris output, pengecekan `NaN`/duplikat, atau status eksekusi sel notebook.
```
