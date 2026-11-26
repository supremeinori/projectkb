# Laporan QA Star Schema Data Warehouse V2 (`warehouse_v2/biomass_dwh_v2.sqlite`)

Tanggal QA: 2026-11-25 22:45:48  
Status Validasi Otomatis: 10/10 PASS (0 pelanggaran Foreign Key, 0 duplikat kunci, 0 kebocoran bahan baku Not Eligible)

## 1. Inventaris Tabel & Analytical Views (`warehouse_v2/`)

| Jenis | Nama Objek | Jumlah Baris |
| :--- | :--- | :---: |
| Dimension | `dim_feedstock` | 10 |
| Dimension | `dim_location` | 560 |
| Dimension | `dim_conversion_tech` | 2 |
| Dimension | `dim_time` | 16 |
| Dimension | `dim_power_plant` | 119 |
| Fact | `fact_feedstock_potential` | 69,686 |
| Fact | `fact_pltu_operations` | 548 |
| View | `vw_feedstock_discovery_matrix` | 10 |
| View | `vw_regional_potential_anchor_2022` | 3,920 |
| View | `vw_regional_potential_latest_complete` | 5,222 |
| View | `vw_supply_vs_pltu_5_pulau_dualview` | 10 |
| View | `vw_cofiring_simulator_base` | 20 |

## 2. Pengujian Integritas & Rekonsiliasi Otomatis

| No | Pengujian QA | Status | Bukti Terukur |
| :---: | :--- | :---: | :--- |
| 1 | Foreign Key Integrity (`PRAGMA foreign_key_check`) | PASS | 0 pelanggaran FK |
| 2 | Kelengkapan 7 Tabel & 5 Views Non-Kosong | PASS | 7 tabel (70,941 baris) & 5 views seluruhnya terisi |
| 3 | Konsistensi Jumlah Baris SQLite vs 7 CSV Ekspor | PASS | 100% cocok (`dim_feedstock=10`, `dim_location=560`, `fact_feedstock_potential=69,686`, `fact_pltu_operations=548`) |
| 4 | Rekonsiliasi Kayu KLHK PHL Tahun Jangkar 2022 | PASS | `2022 = 55,260,218.00 m3` (0 provinsi gagal cocok) |
| 5 | Rekonsiliasi Kayu KLHK PHL Tahun Terbaru 2024 | PASS | `2024 = 55,547,094.91 m3` (selisih 0,0 m3 vs PDF KLHK) |
| 6 | Harmonisasi Lokasi & Pulau (`dim_location` vs `dim_power_plant`) | PASS | 560 baris (`514` kab/kota + `38` prov + `7` pulau + `1` nasional), 7 pulau cocok 100% |
| 7 | Staging PLTU & Rekonsiliasi CREA 2024 | PASS | 119 PLTU unik, 548 baris (`500` CT + `48` CREA), CREA 2024 = 18.342,0 MW / 1.457.720,0 ton / 1.506.076,0 MWh |
| 8 | Ketepatan Rumus Energi GJ & MWh (`fact_feedstock_potential`) | PASS | Deviasi maksimum GJ = 0.000753, MWh = 0.000054 (ambang <= 0,01) |
| 9 | Isolasi Feedstock Gugur (`FS04` & `FS05`) | PASS | 0 baris berkode `is_boiler_eligible = 1`, 0 ton masuk ke pasokan layak bakar PLTU |
| 10 | Cakupan `vw_supply_vs_pltu_5_pulau_dualview` | PASS | Tepat 10 baris (5 pulau x 2 mode Dual-View) |

## 3. Ringkasan Suplai Eligible (`Co-Firing 33%`) vs Permintaan PLTU 5 Pulau (`vw_supply_vs_pltu_5_pulau_dualview`)

| Mode Dual-View | Pulau | PLTU CT | Generasi PLTU (GWh) | Target 10% (GWh) | Suplai Eligible (Juta Ton) | Potensi Listrik Eligible (GWh) | Rasio vs Target 10% |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `ANCHOR_2022` | Jawa | 29 | 132,657.2 | 13,265.7 | 9.26 | 9,113.4 | 68.7% |
| `ANCHOR_2022` | Sulawesi | 22 | 35,368.7 | 3,536.9 | 0.96 | 756.4 | 21.4% |
| `ANCHOR_2022` | Sumatera | 25 | 23,642.2 | 2,364.2 | 30.37 | 29,029.3 | 1,227.9% |
| `ANCHOR_2022` | Kalimantan | 16 | 9,198.2 | 919.8 | 6.77 | 6,508.3 | 707.6% |
| `ANCHOR_2022` | Papua | 1 | 2,009.6 | 201.0 | 0.31 | 355.0 | 176.7% |
| `LATEST_COMPLETE_VS_2024` | Jawa | 29 | 129,852.1 | 12,985.2 | 18.94 | 21,648.0 | 166.7% |
| `LATEST_COMPLETE_VS_2024` | Sulawesi | 22 | 47,858.2 | 4,785.8 | 6.75 | 8,256.4 | 172.5% |
| `LATEST_COMPLETE_VS_2024` | Sumatera | 25 | 29,973.9 | 2,997.4 | 36.90 | 36,995.6 | 1,234.3% |
| `LATEST_COMPLETE_VS_2024` | Kalimantan | 16 | 9,048.2 | 904.8 | 7.59 | 7,641.4 | 844.5% |
| `LATEST_COMPLETE_VS_2024` | Papua | 1 | 1,956.6 | 195.7 | 0.25 | 282.7 | 144.5% |
