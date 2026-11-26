# Rencana implementasi Semantic Model Power BI via MCP (`powerbi-modeling`)

> **Untuk agent eksekutor:** Gunakan server MCP `powerbi-modeling` secara berurutan dari Task 1 sampai Task 8. Tandai setiap langkah dengan kotak centang (`- [x]`) setelah bukti verifikasi lulus. Jangan melewati gerbang smoke test di Task 2 atau pengujian 24 patokan DAX di Task 7.

**Goal:** Membangun, me-refresh, dan memverifikasi 100% Semantic Model Power BI Desktop (`.pbix` live) untuk proyek Biomass & Waste-to-Energy Feedstock Finder menggunakan server MCP `powerbi-modeling`, lalu mengekspor cadangan TMDL dan menyerahkan model siap pakai untuk perakitan visual 4 halaman (+ 1 Drill-Through) oleh pengguna berdasarkan Brief PDF.

**Architecture:** Model semantik mengikuti pola Kimball Multi-Fact Star Schema dari `warehouse_v2/` yang terdiri dari 14 tabel: 2 tabel fakta (`fact_feedstock_potential`, `fact_pltu_operations`), 5 dimensi bersama (`dim_feedstock`, `dim_location`, `dim_conversion_tech`, `dim_time`, `dim_power_plant`) yang terhubung lewat 7 relasi aktif satu arah (`Many-to-One`), 4 tabel bantu terpisah tanpa relasi (`dim_view_mode`, `dim_shap_importance`, `dim_ml_model_metrics`, `dim_phyllis2_validation`), 2 tabel kalkulasi What-If (`Param CoFiring Pct`, `Param Coal HHV`), dan 1 tabel wadah measure (`_Measures`) berisi 36 rumus DAX. Seluruh 11 tabel CSV memakai parameter Power Query `FolderProjectKB` dan locale `"en-US"`.

**Tech Stack:** Power BI Desktop (Windows 64-bit, `.pbix` live), server MCP `powerbi-modeling` (`connection_operations`, `named_expression_operations`, `table_operations`, `partition_operations`, `column_operations`, `relationship_operations`, `measure_operations`, `model_operations`, `dax_query_operations`, `database_operations`), Power Query M, DAX, TMDL.

**Spec & Reference Artifacts:**
- Desain visual dan audit WCAG 2.1: `warehouse_v2/powerbi/DESIGN.md` dan `warehouse_v2/powerbi/theme_biomass_bi.json`
- Sumber kanonik 36 rumus DAX: `warehouse_v2/powerbi/dax_measures_projectkb.dax`
- Templat Power Query M: `warehouse_v2/powerbi/power_query_m_snippets.pq`
- 24 angka patokan QA SQLite: `warehouse_v2/powerbi/qa_expected_benchmarks.csv`
- Brief PDF perakitan visual manusia (24 halaman): `docs/Brief_Implementasi_Dashboard_PowerBI_ProjectKB.pdf`
- Wireframe referensi 4+1 halaman: `docs/wireframes/` (`page1_executive_overview.png` sampai `page4_cofiring_simulator.png`, `page3b_drillthrough_detail.png`)

## Global Constraints

- Batas cakupan MCP: `powerbi-modeling` hanya memodifikasi Semantic Model (parameter M, tabel, partisi, kolom, relasi, measure, refresh, kueri DAX, ekspor TMDL). Agent tidak memodifikasi biner visual `.pbix`; perakitan kanvas visual 4+1 halaman dilakukan manusia setelah Task 8 sesuai `docs/Brief_Implementasi_Dashboard_PowerBI_ProjectKB.pdf`.
- Batas baca saja (read-only): dilarang mengubah, memindahkan, atau menghapus isi `raw_data/`, `warehouse/`, `warehouse_v2/tables/*.csv`, dan `warehouse_v2/biomass_dwh_v2.sqlite`.
- Aturan locale CSV: seluruh 11 CSV memakai pemisah kolom koma (`,`), UTF-8 (`Encoding=65001`), dan pemisah desimal titik (`.`). Setiap partisi M wajib memanggil `Table.TransformColumnTypes(..., "en-US")` agar Windows berbahasa Indonesia tidak mengubah angka desimal menjadi ribuan atau tanggal.
- Aturan portabilitas path: seluruh 11 partisi M wajib membaca file lewat parameter `FolderProjectKB` (`D:\UPN VY\Semester 5\BI\Tugas\projectkb`), tanpa menulis path absolut langsung di dalam partisi.
- Aturan isolasi abu tinggi: `FS04` (`rice husk`, Ash 18,03%) dan `FS05` (`rice straw`, Ash 18,53%) memiliki `is_boiler_eligible = 0`. Seluruh measure suplai dan simulator wajib mengunci `is_boiler_eligible = 1` sehingga kontribusi keduanya tepat `0` ton.
- Aturan arah relasi: tepat 7 relasi aktif bertipe `Many` -> `One` dengan `crossFilteringBehavior: "OneDirection"`. Dilarang memakai relasi dua arah (`BothDirections`) dan dilarang menghubungkan 4 tabel bantu, `_Measures`, atau 2 tabel What-If ke tabel fakta.
- Konvensi eksekusi MCP: selalu gunakan `resultMode: "Inline"` pada `dax_query_operations(Execute)` agar hasil JSON langsung terbaca di konteks agent, dan gunakan `options: { "useTransaction": true }` saat batch-create kolom/relasi/measure.

## Review Focus

Lima kelas kegagalan yang paling sering mematahkan implementasi Power BI via MCP pada `.pbix` live, beserta uji penguncinya pada rencana ini:

1. **Kegagalan refresh partisi M file lokal via XMLA di Power BI Desktop:** Pada beberapa versi Desktop, `RefreshWithXMLA` menolak membaca CSV baru yang dibuat via TOM sebelum pengguna menyetujui perubahan kueri di UI Desktop. Dikunci dengan smoke test 2 baris (`dim_conversion_tech`) dan jalur fallback deterministik di **Task 2**.
2. **Kerusakan angka desimal akibat locale Windows `id-ID`:** Nilai `19.845` MJ/kg terbaca `19845` bila `"en-US"` terlewat pada `Table.TransformColumnTypes`. Dikunci dengan uji DAX `actual_hhv_db` untuk `FS01` (`19.845`) dan `ash_db` untuk `FS04` (`18.03`) di **Task 3**.
3. **Penjumlahan ganda teknologi `TECH01` + `TECH02`:** `fact_feedstock_potential` memuat 34.843 baris `TECH01` dan 34.843 baris `TECH02`. Tanpa proteksi `SELECTEDVALUE(..., "TECH01")`, kartu KPI tanpa filter slicer menjumlahkan keduanya (`141,24 TWh`). Dikunci dengan uji DAX tanpa filter teknologi di **Task 7 (QA-04a)**.
4. **Kartu PLTU kosong (blank) saat Drill-Through provinsi/kabupaten:** `fact_pltu_operations` berelasi di baris `level_wilayah = "PULAU"`, sehingga filter `nama_provinsi = "Riau"` mengosongkan angka PLTU bila tanpa `ALL(dim_location) + TREATAS`. Dikunci dengan uji DAX filter `nama_provinsi = "Riau"` di **Task 7 (QA-04c)**.
5. **Kehilangan perubahan `.pbix` karena perubahan TOM hanya berada di memori Desktop:** Perubahan lewat `powerbi-modeling` hilang jika jendela Power BI Desktop ditutup tanpa menekan Ctrl+S. Dikunci dengan ekspor cadangan TMDL (`warehouse_v2/powerbi/tmdl_export/`) dan konfirmasi simpan eksplisit pengguna di **Task 8**.

---

## Peta berkas dan objek target

| Artefak / Target | Peran | Dibuat / Dimodifikasi oleh |
| --- | --- | --- |
| Live Power BI Desktop `.pbix` (`Dashboard_Biomassa_PLTU_ProjectKB.pbix`) | Target Semantic Model (1 parameter M, 14 tabel, 7 relasi, 36 measure) | Agent via `powerbi-modeling` MCP (simpan `.pbix` oleh pengguna di Task 8) |
| `warehouse_v2/powerbi/tmdl_export/` | Cadangan penuh Semantic Model berformat TMDL yang dapat direproduksi | Agent via `database_operations(ExportToTmdlFolder)` di Task 8 |
| `warehouse_v2/powerbi/MCP_SEMANTIC_MODEL_QA_REPORT.md` | Laporan bukti eksekusi 24 patokan DAX + 4 uji invarian + jumlah baris 11 tabel | Agent di Task 7 dan Task 8 |
| `log.md` | Pembaruan `Entri 10` mencatat selesainya pembangunan Semantic Model via MCP | Agent di Task 8 |

---

### Task 1: Koneksi ke instance Power BI Desktop live dan audit kondisi awal

**Target MCP:** `connection_operations`, `model_operations`, `table_operations`, `relationship_operations`

**Interfaces:**
- Consumes: Power BI Desktop terbuka dengan 1 file kosong yang sudah disimpan sebagai `Dashboard_Biomassa_PLTU_ProjectKB.pbix` (atau folder kerja proyek di `d:\UPN VY\Semester 5\BI\Tugas\projectkb`).
- Produces: Koneksi MCP aktif (`connectionName`) ke `localhost:<port>`, audit status model bersih (`0` tabel/relasi sisa tak terpakai).

- [x] **Step 1: Deteksi instance Power BI Desktop lokal**

Panggil `connection_operations` dengan `operation: "ListLocalInstances"`.
Expected: Daftar minimal 1 instance Power BI Desktop lokal beserta `connectionString` (`Data Source=localhost:<port>`). Jika daftar kosong, berhenti dan minta pengguna membuka Power BI Desktop dengan 1 dokumen kosong bernama `Dashboard_Biomassa_PLTU_ProjectKB.pbix`, lalu ulangi langkah ini.

- [x] **Step 2: Sambungkan ke instance target dan verifikasi metadata model**

Panggil `connection_operations` dengan `operation: "Connect"` menggunakan `connectionString` dari Step 1. Kemudian panggil `model_operations` (`operation: "Get"`), `table_operations` (`operation: "List"`), dan `relationship_operations` (`operation: "List"`).
Expected: Koneksi berhasil (`connectionName` tercatat), kompatibilitas model >= `1550`, dan daftar tabel/relasi awal diketahui. Jika sudah ada tabel sisa percobaan sebelumnya, konfirmasi sebelum menimpa atau hapus tabel sisa yang tidak relevan.

- [x] **Step 3: Atur budaya kueri sumber model bila diperlukan**

Jika `sourceQueryCulture` pada hasil `model_operations(Get)` kosong atau berbeda, periksa dengan `model_operations(Update)` agar `discourageImplicitMeasures` tetap `false` (ramah pemula) dan pastikan `Auto Date/Time` tidak membentuk tabel `LocalDateTable_*` (tidak ada kolom tipe Date pada tabel dimensi kita karena `dim_time[year]` bertipe `Int64`).

---

### Task 2: Parameter Power Query `FolderProjectKB` dan smoke test import CSV (`en-US`)

**Target MCP:** `named_expression_operations`, `table_operations`, `dax_query_operations`

**Interfaces:**
- Consumes: Koneksi aktif dari Task 1; file `warehouse_v2/tables/dim_conversion_tech.csv` (2 baris, 9 kolom).
- Produces: Named expression parameter `FolderProjectKB`; tabel teruji `dim_conversion_tech` (2 baris terisi penuh); kepastian jalur refresh lokal (XMLA langsung atau tombol Refresh Desktop).

- [x] **Step 1: Buat parameter Power Query `FolderProjectKB`**

Panggil `named_expression_operations` dengan `operation: "CreateParameter"`, `definitions`:
- `name`: `"FolderProjectKB"`
- `kind`: `"M"`
- `expression`: `"\"d:\\UPN VY\\Semester 5\\BI\\Tugas\\projectkb\" meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]"`
- `description`: `"Folder akar workspace ProjectKB untuk seluruh sumber CSV warehouse_v2."`

Verifikasi dengan `named_expression_operations(Get)` untuk `"FolderProjectKB"`. Expected: parameter terdaftar dengan `kind: "M"`.

- [x] **Step 2: Buat tabel smoke test `dim_conversion_tech` beserta partisi M (`en-US`)**

Panggil `table_operations` dengan `operation: "Create"` untuk `dim_conversion_tech`, deklarasikan 9 kolom secara eksplisit (`tech_key` Int64, `tech_code` String, `tech_name` String, `efficiency_pct` Double, `capacity_factor_pct` Double, `operating_hours_per_year` Double, `ash_limit_pct` Double, `sulfur_limit_pct` Double, `reference_note` String) dan `mExpression` yang membaca `FolderProjectKB & "\warehouse_v2\tables\dim_conversion_tech.csv"` memakai `Csv.Document(..., [Delimiter=",", Columns=9, Encoding=65001, QuoteStyle=QuoteStyle.None])`, `Table.PromoteHeaders`, dan `Table.TransformColumnTypes(..., "en-US")`.

- [x] **Step 3: Uji refresh data dan kueri DAX `COUNTROWS` (Gerbang Smoke Test)**

Panggil `table_operations` (`operation: "RefreshWithXMLA"`, `references: [{"name": "dim_conversion_tech"}]`, `refreshType: "Full"`). Lalu panggil `dax_query_operations` (`operation: "Execute"`, `resultMode: "Inline"`, `query: "EVALUATE ROW(\"Rows\", COUNTROWS(dim_conversion_tech), \"Eff_TECH02\", LOOKUPVALUE(dim_conversion_tech[efficiency_pct], dim_conversion_tech[tech_code], \"TECH02\"))"`).
Expected: `Rows = 2` dan `Eff_TECH02 = 25.45` (memastikan pemisah desimal titik terbaca tepat tanpa dikali 100).

**Aturan fallback deterministik jika Step 3 gagal karena pembatasan kredensial file lokal Desktop:**
1. Jika `RefreshWithXMLA` memunculkan galat privasi/kredensial mashup lokal di Power BI Desktop, lanjutkan pembuatan metadata seluruh 10 tabel CSV di Task 3 terlebih dahulu dalam satu batch.
2. Setelah seluruh 11 definisi tabel CSV tercipta di model, minta pengguna menekan tombol **Refresh** (dan menyetujui dialog privasi lokal bila muncul) satu kali di UI Power BI Desktop, lalu lanjutkan verifikasi `COUNTROWS` di Task 3 Step 3 dan seluruh tugas berikutnya secara otomatis via MCP.

---

### Task 3: Pembuatan 10 tabel CSV tersisa (Star Schema + Helper) dan verifikasi jumlah baris serta locale

**Target MCP:** `table_operations`, `model_operations`, `dax_query_operations`

**Interfaces:**
- Consumes: Parameter `FolderProjectKB` dan jalur refresh terverifikasi dari Task 2; 6 CSV inti tersisa di `warehouse_v2/tables/` + 4 CSV bantu di `warehouse_v2/powerbi/`.
- Produces: Seluruh 11 tabel CSV terisi data penuh dengan tipe kolom presisi dan locale desimal `en-US` terverifikasi.

- [x] **Step 1: Buat 6 tabel CSV Star Schema tersisa via `table_operations(Create)`**

Gunakan pola partisi M yang sama persis dengan Task 2 (`FolderProjectKB & "\warehouse_v2\tables\<file>.csv"`, `Encoding=65001`, `Table.TransformColumnTypes(..., "en-US")`). Deklarasikan setiap kolom beserta `sourceColumn` dan `dataType` sesuai spesifikasi berikut (referensi persis dari `warehouse_v2/ddl_star_schema.sql` dan `warehouse_v2/powerbi/power_query_m_snippets.pq`):

| Tabel | Jumlah kolom | Kolom `Int64` | Kolom `Double` | Kolom `String` |
| --- | --- | --- | --- | --- |
| `dim_time` | 7 | `time_key`, `year`, `decade`, `is_bps_ksa_era`, `is_post_papua_split`, `is_anchor_2022`, `has_pltu_ct_data` | (tidak ada) | (tidak ada) |
| `dim_feedstock` | 34 | `feedstock_key`, `high_moisture_flag`, `is_boiler_eligible`, `cluster_id` | `rpr_primer`, `rpr_alternatif_bps`, `recoverability_factor`, `moisture_lapangan_pct`, `ash_db`, `vm_db`, `fc_db`, `c_db`, `h_db`, `o_db`, `n_db`, `s_db`, `cl_db_pct`, `alkali_total_db_pct`, `idt_oxidizing_c`, `actual_hhv_db`, `predicted_hhv_prox_db`, `predicted_hhv_full_db`, `predicted_hhv_db`, `effective_lhv_lab_mj_kg`, `effective_lhv_field_mj_kg` | `feedstock_id`, `feedstock_name`, `komoditas_bps`, `basis_produk_primer`, `basis_alternatif_bps`, `boiler_status`, `alkali_chlorine_flag`, `screening_recommendation`, `cluster_label` |
| `dim_location` | 14 | `location_key`, `kode_prov`, `kode_kabkota`, `masuk_5_pulau_pltu`, `has_coordinates`, `is_dob_papua_mapped` | `latitude_centroid`, `longitude_centroid` | `location_code`, `level_wilayah`, `nama_provinsi`, `nama_kabkota`, `pulau`, `wilayah_pln` |
| `dim_power_plant` | 18 | `pltu_key`, `commissioning_year`, `has_coordinates`, `masuk_5_pulau_pltu` | `latitude`, `longitude` | `pltu_master_id`, `nama_pltu_standar`, `nama_climatetrace`, `nama_wri_gppd`, `nama_crea_2025`, `owner_operator`, `jenis_boiler`, `status_cofiring_2024`, `pulau`, `wilayah_pln`, `entity_match_method`, `name_audit_flag` |
| `fact_feedstock_potential` | 27 | `energy_fact_id`, `time_key`, `location_key`, `feedstock_key`, `tech_key`, `is_anchor_2022`, `is_latest_complete_year`, `is_latest_available_year`, `is_boiler_eligible` | `commodity_production_val`, `rpr_ratio_used`, `recoverability_factor_used`, `estimated_supply_gross_tons`, `estimated_supply_tons`, `moisture_lapangan_pct`, `predicted_hhv_mj_kg`, `effective_lhv_mj_kg`, `total_energy_potential_gj`, `estimated_generation_mwh`, `estimated_capacity_mw`, `coal_replaced_tons`, `co2_offset_tons`, `ash_load_tons` | `level_wilayah_fakta`, `sumber_data`, `cakupan_data`, `commodity_unit` |
| `fact_pltu_operations` | 17 | `pltu_fact_id`, `time_key`, `location_key`, `pltu_key`, `crea_block_count`, `jumlah_unit` | `capacity_mw`, `activity_generation_mwh`, `capacity_factor_pct`, `emissions_co2e_ton`, `emissions_factor_t_per_mwh`, `cofiring_share_pct`, `biomass_used_ton`, `biomass_electricity_mwh`, `biomass_emissions_tco2` | `dataset_role`, `kode_sumber` |

Catatan khusus kutipan CSV: pada `dim_view_mode.csv` dan `dim_feedstock.csv` atau CSV lain yang mungkin mengandung koma di dalam tanda kutip teks, gunakan `QuoteStyle=QuoteStyle.Csv` pada `Csv.Document(...)` agar kolom tidak bergeser.

- [x] **Step 2: Buat 4 tabel CSV bantu terpisah dari `warehouse_v2/powerbi/` via `table_operations(Create)`**

Gunakan `FolderProjectKB & "\warehouse_v2\powerbi\<file>.csv"`, `QuoteStyle=QuoteStyle.Csv`, dan `"en-US"`:

| Tabel | Jumlah kolom | Kolom `Int64` | Kolom `Double` | Kolom `String` |
| --- | --- | --- | --- | --- |
| `dim_view_mode` | 6 | `view_mode_key`, `pltu_reference_year`, `sort_order` | (tidak ada) | `view_mode_code`, `view_mode_label`, `scope_note_id` |
| `dim_shap_importance` | 8 | `rank_in_scenario` | `mean_abs_shap_mj_kg` | `scenario_code`, `scenario_label`, `feature_code`, `feature_label_id`, `model_algorithm`, `shap_backend` |
| `dim_ml_model_metrics` | 12 | `is_selected_production` | `cv_r2`, `cv_rmse_mj_kg`, `cv_mae_mj_kg`, `cv_mape_pct`, `test_r2`, `test_rmse_mj_kg`, `test_mae_mj_kg`, `test_mape_pct` | `scenario_code`, `scenario_label`, `algorithm` |
| `dim_phyllis2_validation` | 13 | `is_pure_phyllis2` | `actual_hhv_db`, `predicted_hhv_prox_db`, `err_prox_pct`, `predicted_hhv_full_db`, `err_full_pct`, `effective_lhv_field_mj_kg` | `feedstock_id`, `feedstock_name`, `proximate_source`, `boiler_status`, `alkali_chlorine_flag`, `cluster_label` |

- [x] **Step 3: Refresh penuh model dan jalankan uji jumlah baris serta uji locale desimal via `dax_query_operations(Execute)`**

Panggil `model_operations(RefreshWithXMLA, refreshType: "Full")` (atau jalankan fallback tombol Refresh Desktop dari Task 2 jika diperlukan). Kemudian eksekusi kueri DAX berikut (`resultMode: "Inline"`):

```dax
EVALUATE
UNION(
    ROW("Check", "dim_conversion_tech",     "Val", COUNTROWS(dim_conversion_tech)),
    ROW("Check", "dim_time",                "Val", COUNTROWS(dim_time)),
    ROW("Check", "dim_feedstock",           "Val", COUNTROWS(dim_feedstock)),
    ROW("Check", "dim_location",            "Val", COUNTROWS(dim_location)),
    ROW("Check", "dim_power_plant",         "Val", COUNTROWS(dim_power_plant)),
    ROW("Check", "fact_feedstock_potential","Val", COUNTROWS(fact_feedstock_potential)),
    ROW("Check", "fact_pltu_operations",    "Val", COUNTROWS(fact_pltu_operations)),
    ROW("Check", "dim_view_mode",           "Val", COUNTROWS(dim_view_mode)),
    ROW("Check", "dim_shap_importance",     "Val", COUNTROWS(dim_shap_importance)),
    ROW("Check", "dim_ml_model_metrics",    "Val", COUNTROWS(dim_ml_model_metrics)),
    ROW("Check", "dim_phyllis2_validation", "Val", COUNTROWS(dim_phyllis2_validation)),
    ROW("Check", "Locale_FS01_HHV",         "Val", LOOKUPVALUE(dim_feedstock[actual_hhv_db], dim_feedstock[feedstock_id], "FS01")),
    ROW("Check", "Locale_FS04_Ash",         "Val", LOOKUPVALUE(dim_feedstock[ash_db], dim_feedstock[feedstock_id], "FS04"))
)
```

Expected: Exact match `2`, `16`, `10`, `560`, `119`, `69686`, `548`, `2`, `11`, `6`, `10`, `Locale_FS01_HHV = 19.845`, `Locale_FS04_Ash = 18.03`.

---

### Task 4: Pembuatan 2 tabel What-If, wadah `_Measures`, dan pengaturan metadata kolom

**Target MCP:** `table_operations`, `column_operations`, `dax_query_operations`

**Interfaces:**
- Consumes: 11 tabel CSV terisi data dari Task 3.
- Produces: Tabel kalkulasi `Param CoFiring Pct` (16 baris: `0.05`..`0.20`), `Param Coal HHV` (9 baris: `18.0`..`22.0`), tabel wadah `_Measures`, serta seluruh `dataCategory`, `summarizeBy`, `sortByColumn`, dan `isHidden` terpasang rapi.

- [x] **Step 1: Buat 2 tabel parameter What-If (bebas galat pembulatan float) dan tabel wadah `_Measures`**

Panggil `table_operations(Create)` untuk tiga tabel kalkulasi DAX berikut (memakai `GENERATESERIES` berbasis bilangan bulat lalu dibagi dan dibulatkan agar tidak terjadi drift floating-point seperti `0.15000000000000002` pada filter DAX):
1. `Param CoFiring Pct`: `daxExpression: "SELECTCOLUMNS(GENERATESERIES(5, 20, 1), \"Param CoFiring Pct\", ROUND(DIVIDE([Value], 100), 2))"`
2. `Param Coal HHV`: `daxExpression: "SELECTCOLUMNS(GENERATESERIES(36, 44, 1), \"Param Coal HHV\", ROUND(DIVIDE([Value], 2), 1))"`
3. `_Measures`: `daxExpression: "ROW(\"_Dummy\", 0)"`

Lalu panggil `model_operations(RefreshWithXMLA, refreshType: "Calculate")` agar mesin Tabular membentuk kolom dan mengevaluasi seluruh baris kalkulasi.

- [x] **Step 2: Verifikasi nama kolom What-If dan atur format tampilannya**

Panggil `column_operations(List)` pada `Param CoFiring Pct` dan `Param Coal HHV` untuk memastikan nama kolom tepat `Param CoFiring Pct` dan `Param Coal HHV` (jika mesin TOM masih menampilkan nama bawaan `Value`, ganti namanya dengan `column_operations(Rename)`). Lalu panggil `column_operations(Update)` untuk menyetel `summarizeBy: "None"` pada keduanya, `formatString: "0%"` pada `Param CoFiring Pct[Param CoFiring Pct]`, dan `formatString: "0.0"` pada `Param Coal HHV[Param Coal HHV]`.

- [x] **Step 3: Atur `dataCategory`, `summarizeBy`, `sortByColumn`, dan `isHidden` pada kolom model**

Panggil `column_operations(Update)` dalam satu batch transaksi untuk properti berikut:

| Tabel dan kolom | Properti yang diubah |
| --- | --- |
| `dim_location[latitude_centroid]`, `dim_power_plant[latitude]` | `dataCategory: "Latitude"`, `summarizeBy: "None"` |
| `dim_location[longitude_centroid]`, `dim_power_plant[longitude]` | `dataCategory: "Longitude"`, `summarizeBy: "None"` |
| `dim_location[nama_provinsi]` | `dataCategory: "StateOrProvince"` |
| `dim_view_mode[view_mode_label]` | `sortByColumn: "sort_order"` |
| `dim_time[year]` | `summarizeBy: "None"` |
| `dim_location[kode_prov]`, `dim_location[kode_kabkota]` | `summarizeBy: "None"` |
| `fact_feedstock_potential[energy_fact_id]`, `[time_key]`, `[location_key]`, `[feedstock_key]`, `[tech_key]` | `isHidden: true` |
| `fact_pltu_operations[pltu_fact_id]`, `[time_key]`, `[location_key]`, `[pltu_key]` | `isHidden: true` |
| `_Measures[_Dummy]` | `isHidden: true` (setelah Task 6 minimal 1 measure dibuat, atau sekarang juga boleh; di Desktop, tabel menjadi ikon kalkulator segera setelah semua kolom tersembunyi dan memiliki >= 1 measure) |

- [x] **Step 4: Verifikasi tabel What-If via `dax_query_operations(Execute)`**

Eksekusi `EVALUATE ROW("CoFiringRows", COUNTROWS('Param CoFiring Pct'), "CoFiringMin", MIN('Param CoFiring Pct'[Param CoFiring Pct]), "CoFiringMax", MAX('Param CoFiring Pct'[Param CoFiring Pct]), "CoalRows", COUNTROWS('Param Coal HHV'))`.
Expected: `CoFiringRows = 16`, `CoFiringMin = 0.05`, `CoFiringMax = 0.2`, `CoalRows = 9`.

---

### Task 5: Pemodelan tepat 7 relasi Star Schema dan pembersihan relasi otomatis

**Target MCP:** `relationship_operations`, `model_operations`

**Interfaces:**
- Consumes: 14 tabel dari Task 3 dan Task 4.
- Produces: Tepat 7 relasi aktif (`Many -> One`, `OneDirection`) tanpa relasi liar pada tabel bantu maupun What-If.

- [x] **Step 1: Audit dan hapus relasi otomatis yang tidak diinginkan**

Panggil `relationship_operations(List)`. Jika terdapat relasi otomatis yang menyentuh `dim_view_mode`, `dim_shap_importance`, `dim_ml_model_metrics`, `dim_phyllis2_validation`, `Param CoFiring Pct`, `Param Coal HHV`, atau `_Measures`, atau relasi dengan arah `BothDirections`, hapus memakai `relationship_operations(Delete)`.

- [x] **Step 2: Buat 7 relasi Kimball Star Schema via `relationship_operations(Create)`**

Gunakan `fromCardinality: "Many"`, `toCardinality: "One"`, `crossFilteringBehavior: "OneDirection"`, `isActive: true`:

| Nama relasi | `fromTable` / `fromColumn` | `toTable` / `toColumn` |
| --- | --- | --- |
| `rel_ffp_feedstock` | `fact_feedstock_potential` / `feedstock_key` | `dim_feedstock` / `feedstock_key` |
| `rel_ffp_location` | `fact_feedstock_potential` / `location_key` | `dim_location` / `location_key` |
| `rel_ffp_time` | `fact_feedstock_potential` / `time_key` | `dim_time` / `time_key` |
| `rel_ffp_tech` | `fact_feedstock_potential` / `tech_key` | `dim_conversion_tech` / `tech_key` |
| `rel_fpltu_location` | `fact_pltu_operations` / `location_key` | `dim_location` / `location_key` |
| `rel_fpltu_time` | `fact_pltu_operations` / `time_key` | `dim_time` / `time_key` |
| `rel_fpltu_plant` | `fact_pltu_operations` / `pltu_key` | `dim_power_plant` / `pltu_key` |

- [x] **Step 3: Verifikasi daftar relasi final**

Panggil `relationship_operations(List)` dan `model_operations(RefreshWithXMLA, refreshType: "Calculate")`.
Expected: Tepat `7` relasi, seluruhnya `isActive = true`, `fromCardinality = Many`, `toCardinality = One`, `crossFilteringBehavior = OneDirection`, dan `0` galat kalkulasi.

---

### Task 6: Pembuatan seluruh 36 measure DAX di `_Measures` dan validasi sintaks

**Target MCP:** `measure_operations`, `dax_query_operations`

**Interfaces:**
- Consumes: Sumber rumus kanonik `warehouse_v2/powerbi/dax_measures_projectkb.dax`; 14 tabel dan 7 relasi aktif dari Task 4 dan Task 5.
- Produces: 36 measure DAX aktif di tabel `_Measures` tersusun dalam 7 `displayFolder` dengan `formatString` rapi dan status kompilasi `Ready`.

- [x] **Step 1: Baca seluruh ekspresi DAX dari `warehouse_v2/powerbi/dax_measures_projectkb.dax`**

Baca file kanonik tersebut apa adanya tanpa mengubah logika filter `is_boiler_eligible = 1`, `SELECTEDVALUE(..., "TECH01")`, `ALL(dim_location) + TREATAS`, maupun `SUMX(VALUES(dim_location[pulau]), MIN(...))`.

- [x] **Step 2: Buat seluruh 36 measure di tabel `_Measures` via `measure_operations(Create)`**

Kelompokkan dengan `displayFolder` dan `formatString` berikut agar rapi di panel Data Power BI Desktop:

| `displayFolder` | Daftar nama measure persis (total 36) | `formatString` |
| --- | --- | --- |
| `00_Kontrol_Mode` (3) | `Mode Aktif Code`, `Catatan Cakupan Dinamis` | (teks / kosong) |
| `00_Kontrol_Mode` | `Ref Tahun PLTU` | `0` |
| `01_Suplai_Biomassa` (8) | `Teknologi Aktif Code` | (teks / kosong) |
| `01_Suplai_Biomassa` | `Eligible Supply (Ton)`, `Excluded Supply FS04 FS05 (Ton)`, `Eligible Generation (MWh)` | `#,##0` |
| `01_Suplai_Biomassa` | `Eligible Generation (GWh)`, `Total Generation Semua Profil (GWh)` | `#,##0.0` |
| `01_Suplai_Biomassa` | `Eligible Generation (TWh)` | `#,##0.00` |
| `01_Suplai_Biomassa` | `Eligible Capacity (MW)` | `#,##0` |
| `02_KPI_Eksekutif` (5) | `Max Coal Replaced Supply (Mt)`, `Max CO2e Offset Supply (Mt)`, `Weighted Field LHV (MJ/kg)` | `#,##0.00` |
| `02_KPI_Eksekutif` | `Energy Density Index vs Coal (%)`, `Technical Suitability Score (%)` | `0.0%` |
| `03_Operasi_PLTU` (5) | `PLTU Generation CT (MWh)` | `#,##0` |
| `03_Operasi_PLTU` | `PLTU Target 10% Co-Firing (GWh)`, `CREA 2024 Actual Co-Firing (GWh)`, `CREA 2024 Biomass Used (kt)` | `#,##0.0` |
| `03_Operasi_PLTU` | `Coverage vs 10% Target (%)` | `0.0%` |
| `04_Simulator_WhatIf` (11) | `Sim Target Co-Firing (MWh)`, `Sim Realizable Supply-Capped (MWh)` | `#,##0` |
| `04_Simulator_WhatIf` | `Sim Target Co-Firing (GWh)`, `Sim Realizable Supply-Capped (GWh)`, `Sim Defisit Pasokan (GWh)`, `Sim Gap Surplus/Defisit (GWh)`, `CREA 2024 per PLTU (GWh)`, `CREA 2024 Biomassa per PLTU (kt)` | `#,##0.0` |
| `04_Simulator_WhatIf` | `Sim Coal Saved Realizable (Mt)`, `Sim CO2e Offset Realizable (Mt)` | `#,##0.00` |
| `04_Simulator_WhatIf` | `Sim Efisiensi Aktif (Desimal)` | `0.00%` |
| `05_Tren_Historis` (2) | `Tren Potensi Tanaman BDSP Layak (TWh)`, `Tren Potensi Kayu KLHK Layak (TWh)` | `#,##0.00` |
| `06_Format_Warna` (2) | `Warna Status Boiler`, `Warna Gap Simulator` | (teks / kosong) |

- [x] **Step 3: Verifikasi seluruh 36 measure berstatus `Ready` tanpa galat sintaks**

Panggil `model_operations(RefreshWithXMLA, refreshType: "Calculate")` lalu `measure_operations(List, filter: {"tableNames": ["_Measures"]})`. Pastikan kolom `_Measures[_Dummy]` berstatus `isHidden: true`.
Expected: Tepat `36` measure di `_Measures`, seluruhnya `state: "Ready"`, dan `errorMessage: null`.

---

### Task 7: Pengujian QA otomatis via DAX `EVALUATE` (24 patokan SQLite + 4 uji invarian kritis)

**Target MCP:** `dax_query_operations`

**Interfaces:**
- Consumes: 36 measure aktif dari Task 6; berkas pembanding `warehouse_v2/powerbi/qa_expected_benchmarks.csv`.
- Produces: Bukti kelulusan 24/24 patokan angka + 4 uji Review Focus + uji 48 PLTU CREA, ditulis ke `warehouse_v2/powerbi/MCP_SEMANTIC_MODEL_QA_REPORT.md`.

- [x] **Step 1: Jalankan `QA-01` (8 patokan Nasional `LATEST_COMPLETE`, `TECH01`)**

Eksekusi `dax_query_operations(Execute, resultMode: "Inline")`:
```dax
EVALUATE
CALCULATETABLE(
    ROW(
        "Elig_TWh",  ROUND([Eligible Generation (TWh)], 2),
        "Elig_MW",   ROUND([Eligible Capacity (MW)], 0),
        "Elig_Mt",   ROUND(DIVIDE([Eligible Supply (Ton)], 1000000), 2),
        "Excl_Mt",   ROUND(DIVIDE([Excluded Supply FS04 FS05 (Ton)], 1000000), 2),
        "Coal_Mt",   ROUND([Max Coal Replaced Supply (Mt)], 2),
        "CO2_Mt",    ROUND([Max CO2e Offset Supply (Mt)], 2),
        "LHV_MJ",    ROUND([Weighted Field LHV (MJ/kg)], 2),
        "Suit_Pct",  ROUND([Technical Suitability Score (%)] * 100, 1)
    ),
    dim_view_mode[view_mode_code] = "LATEST_COMPLETE",
    dim_conversion_tech[tech_code] = "TECH01"
)
```
Expected (toleransi <= `0.01`): `79.74`, `13003`, `74.26`, `55.17`, `43.49`, `82.29`, `11.71`, `57.4`.

- [x] **Step 2: Jalankan `QA-02` (8 patokan Nasional `ANCHOR_2022`, `TECH01`)**

Ulangi kueri `QA-01` dengan `dim_view_mode[view_mode_code] = "ANCHOR_2022"`.
Expected (toleransi <= `0.01`): `47.06`, `7675`, `48.70`, `49.80`, `25.67`, `48.57`, `10.54`, `49.4`.

- [x] **Step 3: Jalankan `QA-03` (8 patokan Simulator 5 Pulau pada 10% dan 20%, `LATEST_COMPLETE`, `TECH01`)**

Eksekusi `dax_query_operations(Execute, resultMode: "Inline")`:
```dax
EVALUATE
UNION(
    CALCULATETABLE(
        ROW(
            "Skenario", "Sim_10pct",
            "Target_TWh", ROUND(DIVIDE([Sim Target Co-Firing (GWh)], 1000), 2),
            "Real_TWh",   ROUND(DIVIDE([Sim Realizable Supply-Capped (GWh)], 1000), 2),
            "Coal_Mt",    ROUND([Sim Coal Saved Realizable (Mt)], 2),
            "CO2_Mt",     ROUND([Sim CO2e Offset Realizable (Mt)], 2)
        ),
        dim_view_mode[view_mode_code] = "LATEST_COMPLETE",
        dim_conversion_tech[tech_code] = "TECH01",
        dim_location[masuk_5_pulau_pltu] = 1,
        'Param CoFiring Pct'[Param CoFiring Pct] = 0.10,
        'Param Coal HHV'[Param Coal HHV] = 20
    ),
    CALCULATETABLE(
        ROW(
            "Skenario", "Sim_20pct",
            "Target_TWh", ROUND(DIVIDE([Sim Target Co-Firing (GWh)], 1000), 2),
            "Real_TWh",   ROUND(DIVIDE([Sim Realizable Supply-Capped (GWh)], 1000), 2),
            "Coal_Mt",    ROUND([Sim Coal Saved Realizable (Mt)], 2),
            "CO2_Mt",     ROUND([Sim CO2e Offset Realizable (Mt)], 2)
        ),
        dim_view_mode[view_mode_code] = "LATEST_COMPLETE",
        dim_conversion_tech[tech_code] = "TECH01",
        dim_location[masuk_5_pulau_pltu] = 1,
        'Param CoFiring Pct'[Param CoFiring Pct] = 0.20,
        'Param Coal HHV'[Param Coal HHV] = 20
    )
)
```
Expected (toleransi <= `0.01`):
- `Sim_10pct`: `21.87`, `21.87`, `11.93`, `22.57`
- `Sim_20pct`: `43.74`, `37.99`, `20.72`, `39.21`

- [x] **Step 4: Jalankan `QA-04` dan `QA-05` (4 uji Review Focus + 48 PLTU CREA 2024)**

Eksekusi `dax_query_operations(Execute, resultMode: "Inline")`:
```dax
EVALUATE
ROW(
    "Guard_NoTechFilter_TWh",   ROUND([Eligible Generation (TWh)], 2),
    "Guard_FS04_FS05_Ton",      CALCULATE([Eligible Supply (Ton)], dim_feedstock[feedstock_id] IN {"FS04", "FS05"}) + 0,
    "DT_Riau_Elig_GWh",         ROUND(CALCULATE([Eligible Generation (GWh)], dim_location[nama_provinsi] = "Riau"), 1),
    "DT_Riau_Sumatera_PLTU",    ROUND(DIVIDE(CALCULATE([PLTU Generation CT (MWh)], dim_location[nama_provinsi] = "Riau"), 1000), 1),
    "Tech02_Elig_TWh",          ROUND(CALCULATE([Eligible Generation (TWh)], dim_conversion_tech[tech_code] = "TECH02"), 2),
    "CREA_Total_Stations",      CALCULATE(COUNTROWS(fact_pltu_operations), fact_pltu_operations[dataset_role] = "COFIRING_REALIZATION_CREA", dim_time[year] = 2024),
    "CREA_Reported_MWh_Plants", COUNTROWS(FILTER(VALUES(dim_power_plant[nama_pltu_standar]), [CREA 2024 per PLTU (GWh)] > 0)),
    "CREA_Total_GWh",           ROUND([CREA 2024 per PLTU (GWh)], 1),
    "CREA_Total_kt",            ROUND([CREA 2024 Biomassa per PLTU (kt)], 1)
)
```
Expected:
- `Guard_NoTechFilter_TWh = 79.74` (membuktikan tidak terjadi penjumlahan ganda `TECH01 + TECH02`)
- `Guard_FS04_FS05_Ton = 0` (membuktikan isolasi 0 ton residu padi)
- `DT_Riau_Elig_GWh = 12670.9` dan `DT_Riau_Sumatera_PLTU = 29973.9` (membuktikan `TREATAS` menjaga konteks PLTU Sumatera saat Drill-Through ke Riau)
- `Tech02_Elig_TWh = 61.49` (proporsional efisiensi 25,45% / 33,0% dari `79.74 TWh`)
- `CREA_Total_Stations = 48`, `CREA_Reported_MWh_Plants = 42` (6 stasiun tidak melaporkan MWh di CREA), `CREA_Total_GWh = 1506.1`, dan `CREA_Total_kt = 1457.7`

- [x] **Step 5: Tulis laporan bukti QA ke `warehouse_v2/powerbi/MCP_SEMANTIC_MODEL_QA_REPORT.md`**

Catat hasil aktual setiap kueri di atas dalam tabel perbandingan Aktual vs Patokan beserta status `PASS` / `FAIL`. Jika ada satu saja status `FAIL`, hentikan eksekusi, perbaiki sumber perbedaan di model, dan ulangi Task 7 sampai seluruh pengujian `PASS`.

---

### Task 8: Ekspor cadangan TMDL, simpan `.pbix`, pembaruan `log.md`, dan serah terima perakitan visual

**Target MCP & Files:** `database_operations`, `warehouse_v2/powerbi/tmdl_export/`, `log.md`

**Interfaces:**
- Consumes: Semantic Model terverifikasi 100% PASS dari Task 7.
- Produces: Folder cadangan TMDL lengkap di `warehouse_v2/powerbi/tmdl_export/`, catatan `Entri 10` di `log.md`, instruksi simpan Ctrl+S ke pengguna, dan panduan serah terima perakitan visual ke `docs/Brief_Implementasi_Dashboard_PowerBI_ProjectKB.pdf`.

- [x] **Step 1: Ekspor cadangan penuh Semantic Model ke TMDL**

Panggil `database_operations` dengan `operation: "ExportToTmdlFolder"` dan `tmdlFolderPath: "d:\\UPN VY\\Semester 5\\BI\\Tugas\\projectkb\\warehouse_v2\\powerbi\\tmdl_export"`.
Verifikasi bahwa file `database.tmdl`, `model.tmdl`, `relationships.tmdl`, `expressions.tmdl`, dan 14 file tabel `.tmdl` terbentuk tanpa galat di `warehouse_v2/powerbi/tmdl_export/`.

- [x] **Step 2: Minta pengguna menyimpan `.pbix` di Power BI Desktop**

Karena perubahan via `powerbi-modeling` MCP berada di memori instance Power BI Desktop yang sedang terbuka, tampilkan pengingat jelas agar pengguna menekan **Ctrl+S** pada jendela Power BI Desktop untuk menyimpan `Dashboard_Biomassa_PLTU_ProjectKB.pbix` ke disk sebelum menutup aplikasi.

- [x] **Step 3: Perbarui `log.md` dengan `Entri 10`**

Tambahkan `Entri 10` di bagian atas Riwayat Perubahan pada `log.md` yang mencantumkan artefak baru (`warehouse_v2/powerbi/tmdl_export/`, `warehouse_v2/powerbi/MCP_SEMANTIC_MODEL_QA_REPORT.md`), ringkasan 14 tabel / 7 relasi / 36 measure, dan hasil uji 24/24 patokan DAX + 4 uji invarian.

- [x] **Step 4: Serah terima perakitan visual (Fase Manual Pengguna)**

Berikan ringkasan singkat langkah visual tersisa yang dikerjakan langsung di Power BI Desktop dengan mengikuti `docs/Brief_Implementasi_Dashboard_PowerBI_ProjectKB.pdf`:
1. Muat tema `warehouse_v2/powerbi/theme_biomass_bi.json` (Bab 2.1 Brief PDF).
2. Susun kanvas 16:9 untuk 4 halaman utama dan 1 halaman tersembunyi `3B. Detail Wilayah` mengikuti tabel Field Well dan wireframe pada Bab 5 Brief PDF (termasuk unggah `pltu_101_overlay.geojson` ke Reference Layer Azure Map Halaman 3, 2-Tab Bookmark Halaman 2 & 4, Sync Slicers, serta tombol Reset Default Simulator).
3. Selesaikan 7 uji interaktivitas visual pada Bab 6.2 Brief PDF sebelum presentasi.

---

## Definition of Done (DoD)

Eksekusi agent dinyatakan selesai apabila seluruh gerbang berikut terpenuhi secara objektif:

1. **Kelengkapan Semantic Model live:** Seluruh 1 parameter Power Query (`FolderProjectKB`), 14 tabel (11 CSV + 2 What-If + `_Measures`), 7 relasi Star Schema aktif, dan 36 measure DAX telah terbuat di instance Power BI Desktop tanpa satu pun error refresh atau kompilasi.
2. **Keakuratan data dan logika analitik:** Laporan `warehouse_v2/powerbi/MCP_SEMANTIC_MODEL_QA_REPORT.md` tersedia dan membuktikan seluruh kueri `QA-01` sampai `QA-05` lulus 100% langsung dari `dax_query_operations(Execute)`.
3. **Reproduksibilitas cadangan model:** Ekspor TMDL berhasil tersimpan utuh di `warehouse_v2/powerbi/tmdl_export/` (`model.tmdl`, `relationships.tmdl`, `expressions.tmdl`, dan 14 definisi tabel).
4. **Pembaruan dokumentasi proyek:** `log.md` memuat `Entri 10` dengan hasil verifikasi aktual.
5. **Kepatuhan batas baca saja:** Tidak ada satu pun berkas di `raw_data/`, `warehouse/`, `warehouse_v2/tables/`, atau `warehouse_v2/biomass_dwh_v2.sqlite` yang diubah oleh eksekusi rencana ini.
6. **Kesiapan serah terima visual:** Pengingat simpan `Ctrl+S` pada `.pbix` dan panduan lanjutan perakitan visual (`docs/Brief_Implementasi_Dashboard_PowerBI_ProjectKB.pdf`) telah disampaikan kepada pengguna.

## Success Criteria

Seluruh kriteria berikut bersifat terukur (PASS/FAIL) dan diverifikasi langsung dari keluaran tool MCP dan file artefak:

| ID | Kriteria terukur | Ambang lulus (PASS) | Cara verifikasi |
| --- | --- | --- | --- |
| `SC-01` | Kelengkapan tabel Semantic Model | Tepat `14` tabel (`11` CSV + `2` What-If + `_Measures`) | `table_operations(List)` |
| `SC-02` | Kelengkapan parameter Power Query M | Tepat `1` parameter `FolderProjectKB` (`kind: "M"`), dipakai di `11/11` partisi CSV | `named_expression_operations(List)` & `partition_operations(List)` |
| `SC-03` | Ketepatan jumlah baris 11 tabel CSV | `11/11` jumlah baris cocok tepat (`fact_feedstock_potential = 69686`, `fact_pltu_operations = 548`, `dim_location = 560`, `dim_power_plant = 119`, dll.) | `dax_query_operations(Execute)` di Task 3 Step 3 |
| `SC-04` | Integritas locale desimal `"en-US"` | `FS01 actual_hhv_db = 19.845` dan `FS04 ash_db = 18.03` (tidak melonjak 100x atau 1000x) | `dax_query_operations(Execute)` di Task 3 Step 3 |
| `SC-05` | Ketepatan struktur relasi Star Schema | Tepat `7` relasi `Many -> One`, `OneDirection`, `isActive = true`; `0` relasi pada 4 tabel bantu, `_Measures`, dan 2 What-If | `relationship_operations(List)` |
| `SC-06` | Kelengkapan dan kesehatan measure DAX | Tepat `36` measure di `_Measures`, `36/36` berstatus `Ready` dengan `errorMessage = null` | `measure_operations(List)` |
| `SC-07` | Akurasi 24 patokan angka SQLite (`QA-01`..`QA-03`) | `24/24` nilai DAX cocok terhadap `qa_expected_benchmarks.csv` dengan deviasi absolut `<= 0.01` | `dax_query_operations(Execute)` di Task 7 Step 1-3 |
| `SC-08` | Isolasi residu abu tinggi (`FS04`/`FS05`) | `Guard_FS04_FS05_Ton = 0` pada measure suplai layak | `dax_query_operations(Execute)` di Task 7 Step 4 |
| `SC-09` | Proteksi ganda teknologi & Drill-Through `TREATAS` | `Guard_NoTechFilter_TWh = 79.74` (tanpa filter teknologi); filter `Riau` menghasilkan `12670.9 GWh` dan PLTU Sumatera `29973.9 GWh` (tidak blank); `TECH02 = 61.49 TWh`; CREA `48` stasiun (`42` melaporkan MWh) = `1506.1 GWh` dan `1457.7 kt` | `dax_query_operations(Execute)` di Task 7 Step 4 |
| `SC-10` | Cadangan TMDL & batas read-only | Folder `warehouse_v2/powerbi/tmdl_export/` lengkap; `0` file di `warehouse_v2/tables/` atau `warehouse/` termodifikasi | Pemeriksaan berkas di Task 8 Step 1 |
