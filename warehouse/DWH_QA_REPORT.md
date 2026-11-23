# Laporan QA Star Schema Data Warehouse (`warehouse/biomass_dwh.sqlite`)

> **Tanggal QA:** 2026-11-23 23:20:00  
> **Hasil Validasi Otomatis:** **12/12 PASS** (`0` pelanggaran Foreign Key, `0` double-counting)

## 1. Inventaris Tabel Star Schema (`warehouse/tables/*.csv` & `biomass_dwh.sqlite`)

| Jenis | Nama Tabel | Jumlah Baris |
| :--- | :--- | :---: |
| Dimension | `dim_time` | **29** |
| Dimension | `dim_location` | **590** |
| Dimension | `dim_feedstock` | **9** |
| Dimension | `dim_power_plant` | **142** |
| Dimension | `dim_data_source` | **20** |
| Fact | `fact_commodity_production` | **42,155** |
| Fact | `fact_biomass_chemistry` | **2,229** |
| Fact | `fact_biomass_energy_potential` | **34,764** |
| Fact | `fact_pltu_operations` | **622** |

## 2. Hasil Pengujian Integritas & Rekonsiliasi SQL

| Pengujian QA | Status | Detail Bukti |
| :--- | :---: | :--- |
| Foreign Key Integrity (PRAGMA foreign_key_check) | **PASS** | 0 pelanggaran FK |
| Semua 9 Tabel Terisi Non-Kosong | **PASS** | dim_time=29, dim_location=590, dim_feedstock=9, dim_power_plant=142, dim_data_source=20, fact_commodity_production=42,155, fact_biomass_chemistry=2,229, fact_biomass_energy_potential=34,764, fact_pltu_operations=622 |
| Reconciliation 2024 SEKAM_PADI (BPS 1498#2 Padi 2024) | **PASS** | DWH=53,142,726.94 vs Resmi=53,142,726.94 (selisih=0.00) |
| Reconciliation 2024 TONGKOL_JAGUNG (BPS 2204#2 Jagung 2024) | **PASS** | DWH=15,138,913.25 vs Resmi=15,138,912.00 (selisih=1.25) |
| Reconciliation 2024 CANGKANG_SAWIT (BPS 2566#2 Sawit 2024) | **PASS** | DWH=45,436,220.00 vs Resmi=45,436,200.00 (selisih=20.00) |
| Reconciliation 2024 AMPAS_TEBU (BPS 2566#2 Tebu 2024) | **PASS** | DWH=2,465,520.00 vs Resmi=2,465,510.00 (selisih=10.00) |
| Reconciliation 2024 LIMBAH_KAYU_SERBUK (KLHK PHL 2024 PBPH+Perhutani) | **PASS** | DWH=55,547,094.91 vs Resmi=55,547,094.91 (selisih=0.00) |
| Guard Anomali Sawit Provinsi 2025 (4.84x) | **PASS** | 0 baris bocor ke energy_potential (target: 0) |
| Guard Tahun 2026 Belum Rilis | **PASS** | 0 baris primary di 2026 (target: 0) |
| Climate TRACE Capacity Factor (%) Valid [0..100] | **PASS** | n=500, range=5.30%..71.02% |
| CREA 2025 Tabel A1 (52 PLTU / 18,342 MW / 1,457,720 ton) | **PASS** | n=52, MW=18,342.0, biomass=1,457,720.0 ton |
| 4 Analytical Views Eksekusi Sukses | **PASS** | vw_supply_vs_pltu=5 pulau, vw_prov_2024=5 komoditas, vw_kabkota=31,088 baris, vw_pltu_summary=35 baris |

## 3. Potensi Energi Biomassa Nasional 2024 per Komoditas (`vw_energy_potential_provinsi`, Skenario `BASE_CONSERVATIVE`)

| Komoditas | Limbah Biomassa | Grade Boiler (ML) | Produksi (Juta Ton) | Residu Kering (Juta Ton) | Energi (PJ) | Listrik Konversi (TWh) | Setara Batu Bara (Juta Ton) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| Kelapa Sawit | Cangkang Sawit (Palm Kernel Shell / PKS) | Grade B (Moderate / Conditioning Needed) | 45.44 | 11.80 | 222.10 | 15.70 | 11.69 |
| Padi | Sekam Padi (Rice Husk) | Grade C (High Ash / Slagging Risk) | 53.14 | 9.57 | 149.89 | 10.60 | 7.89 |
| Kayu Bulat | Serbuk Gergaji & Serpihan Kayu (Sawdust / Woodchips) | Grade A (High Calorie - Low Ash) | 33.33 | 7.08 | 138.60 | 9.80 | 7.29 |
| Tebu | Ampas Tebu (Sugarcane Bagasse) | Grade B (Moderate / Conditioning Needed) | 2.47 | 4.93 | 85.65 | 6.06 | 4.51 |
| Jagung | Tongkol Jagung (Corn Cob) | Grade B (Moderate / Conditioning Needed) | 15.14 | 3.51 | 57.09 | 4.04 | 3.00 |

## 4. Supply Biomassa 5 Komoditas vs Demand Co-Firing PLTU 5 Pulau Utama (Tahun 2024 — `vw_supply_vs_pltu_5_pulau_2024`)

| Pulau | PLTU CT 2024 | Kapasitas (MW) | Generasi 2024 (GWh) | Target Co-Firing 10% (GWh) | Realisasi CREA 2024 (Ton) | Suplai Biomassa Kering (Juta Ton) | Potensi Listrik Biomassa (GWh) | Rasio Cakupan vs Target 10% |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Jawa** | 29 | 30,808.5 | 129,852.1 | 12,985.2 | 989,182 | 10.24 | 11,823.8 | **91.1%** |
| **Sulawesi** | 22 | 11,454.6 | 47,858.2 | 4,785.8 | 42,518 | 2.18 | 2,510.5 | **52.5%** |
| **Sumatera** | 25 | 7,074.9 | 29,973.9 | 2,997.4 | 277,960 | 16.34 | 21,239.9 | **708.6%** |
| **Kalimantan** | 16 | 2,130.7 | 9,048.2 | 904.8 | 106,854 | 6.79 | 9,005.4 | **995.3%** |
| **Papua** | 1 | 323.0 | 1,956.6 | 195.7 | 5,402 | 0.34 | 453.4 | **231.7%** |