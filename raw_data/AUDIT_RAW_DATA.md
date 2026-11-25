# AUDIT RAW DATA — Fase 2 (100% Mentah per CSV, Zero-Merge)

> **Tanggal Audit:** 2026-11-25 11:24:48  
> **Mode Audit:** *Read-Only* (seluruh raw CSV di 4 folder tidak dimodifikasi)  
> **Total File Raw CSV Terindeks:** **207 file** (5,133 total baris, 3,270.8 KB)  
> **Indeks Global:** `raw_data/_INDEX_RAW_DATA.csv`

---

## 1. Ringkasan Eksekutif Lintas Folder Raw

| Folder Utama | Jumlah File Raw CSV | Total Baris | Total Ukuran (KB) | QC PASS | UTF-8 BOM | Karakter Rusak |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `01_bdsp_kementan/` | 157 | 2,868 | 855.7 | 157/157 | 157/157 | 0 |
| `02_bps/` | 37 | 1,219 | 299.8 | 37/37 | 37/37 | 0 |
| `03_klhk_phl_kayu/` | 4 | 79 | 18.3 | 4/4 | 4/4 | 0 |
| `04_pltu_5_pulau/` | 7 | 622 | 2,000.1 | 7/7 | 7/7 | 0 |
| `05_biomassa_komplementer/` | 2 | 345 | 96.8 | 2/2 | 2/2 | 0 |
| **TOTAL** | **207** | **5,133** | **3,270.8** | **207/207** | **207/207** | **0** |

- **Integritas file eksisting:** `raw_data/03_karakteristik_biomassa_kimia_hhv.*` dan `raw_data/daftar_sumber_data.xlsx` **tidak disentuh**.
- **Aturan Zero-Merge:** Terpenuhi 100% (`1 tarikan asli = 1 file CSV`: 152 file BDSP kab/kota per provinsi + 4 provinsi + 1 Excel Satu Data; 37 file BPS RI per tahun; 4 tabel PDF KLHK PHL; 5 file API tahunan Climate TRACE + 1 WRI + 1 CREA; serta 2 tabel komplementer biomassa 315 sampel & 30 referensi).

---

## 2. Rekonsiliasi PDF KLHK PHL Kayu Bulat (`SUM(provinsi)` vs `JUMLAH` PDF)

**Status Rekonsiliasi:** **20/20 MATCH** (toleransi pembulatan `<= 0,05 m3`). Tanda `"-"` di PDF disimpan sebagai **`NULL` (kosong)**, bukan `0`.

| Buku | Tabel | Tahun | Baris Prov | Prov > 0 | Prov NULL (`-`) | SUM Ekstrak (m³) | JUMLAH PDF (m³) | Selisih (m³) | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `buku_2024` | Tabel 3.9 PBPH (2020-2024) | 2020 | 37 | 21 | 16 | 50,661,576.25 | 50,661,576.25 | 0.00 | **MATCH** |
| `buku_2024` | Tabel 3.9 PBPH (2020-2024) | 2021 | 37 | 21 | 16 | 52,483,838.00 | 52,483,838.00 | 0.00 | **MATCH** |
| `buku_2024` | Tabel 3.9 PBPH (2020-2024) | 2022 | 37 | 21 | 16 | 54,325,550.00 | 54,325,550.00 | 0.00 | **MATCH** |
| `buku_2024` | Tabel 3.9 PBPH (2020-2024) | 2023 | 37 | 24 | 13 | 57,341,829.00 | 57,341,829.00 | 0.00 | **MATCH** |
| `buku_2024` | Tabel 3.9 PBPH (2020-2024) | 2024 | 37 | 24 | 13 | 54,730,862.01 | 54,730,862.01 | 0.00 | **MATCH** |
| `buku_2024` | Tabel 3.12 Perhutani (2020-2024) | 2020 | 4 | 4 | 0 | 853,701.00 | 853,701.00 | 0.00 | **MATCH** |
| `buku_2024` | Tabel 3.12 Perhutani (2020-2024) | 2021 | 4 | 4 | 0 | 988,708.00 | 988,708.00 | 0.00 | **MATCH** |
| `buku_2024` | Tabel 3.12 Perhutani (2020-2024) | 2022 | 4 | 4 | 0 | 934,668.00 | 934,668.00 | 0.00 | **MATCH** |
| `buku_2024` | Tabel 3.12 Perhutani (2020-2024) | 2023 | 4 | 4 | 0 | 925,101.00 | 925,101.00 | 0.00 | **MATCH** |
| `buku_2024` | Tabel 3.12 Perhutani (2020-2024) | 2024 | 4 | 4 | 0 | 816,232.90 | 816,232.90 | -0.00 | **MATCH** |
| `buku_2022` | Tabel 3.9 PBPH (2018-2022) | 2018 | 34 | 22 | 12 | 47,113,117.97 | 47,113,117.97 | 0.00 | **MATCH** |
| `buku_2022` | Tabel 3.9 PBPH (2018-2022) | 2019 | 34 | 23 | 11 | 45,763,754.22 | 45,763,754.22 | -0.00 | **MATCH** |
| `buku_2022` | Tabel 3.9 PBPH (2018-2022) | 2020 | 34 | 21 | 13 | 50,661,576.25 | 50,661,576.25 | 0.00 | **MATCH** |
| `buku_2022` | Tabel 3.9 PBPH (2018-2022) | 2021 | 34 | 21 | 13 | 52,483,838.00 | 52,483,838.00 | 0.00 | **MATCH** |
| `buku_2022` | Tabel 3.9 PBPH (2018-2022) | 2022 | 34 | 21 | 13 | 54,325,550.00 | 54,325,550.00 | 0.00 | **MATCH** |
| `buku_2022` | Tabel 3.12 Perhutani (2018-2022) | 2018 | 4 | 4 | 0 | 809,934.00 | 809,934.00 | 0.00 | **MATCH** |
| `buku_2022` | Tabel 3.12 Perhutani (2018-2022) | 2019 | 4 | 4 | 0 | 807,888.00 | 807,888.00 | 0.00 | **MATCH** |
| `buku_2022` | Tabel 3.12 Perhutani (2018-2022) | 2020 | 4 | 4 | 0 | 853,701.00 | 853,701.00 | 0.00 | **MATCH** |
| `buku_2022` | Tabel 3.12 Perhutani (2018-2022) | 2021 | 4 | 4 | 0 | 988,708.00 | 988,708.00 | 0.00 | **MATCH** |
| `buku_2022` | Tabel 3.12 Perhutani (2018-2022) | 2022 | 4 | 4 | 0 | 934,668.00 | 934,668.00 | 0.00 | **MATCH** |

### Cross-Check Kayu Bulat: KLHK PHL (Buku 2022 vs Buku 2024) vs BPS RI (`2512#2` & `1973#2`)

| Tahun | KLHK PBPH Buku 2022 (m³) | KLHK PBPH Buku 2024 (m³) | KLHK Perhutani (m³) | KLHK Total PBPH+Perh (m³) | BPS 2512#2 Kayu Bulat (m³) | BPS 1973#2 HPH Pulau (m³) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2018 | 47,113,117.97 | — | 809,934.00 | 47,923,051.97 | — | — |
| 2019 | 45,763,754.22 | — | 807,888.00 | 46,571,642.22 | — | 6,174,811.00 |
| 2020 | 50,661,576.25 | 50,661,576.25 | 853,701.00 | 51,515,277.25 | 46,487,679.00 | 5,260,750.00 |
| 2021 | 52,483,838.00 | 52,483,838.00 | 988,708.00 | 53,472,546.00 | 47,562,910.00 | 6,055,524.00 |
| 2022 | 54,325,550.00 | 54,325,550.00 | 934,668.00 | 55,260,218.00 | 49,694,376.00 | 5,764,419.00 |
| 2023 | — | 57,341,829.00 | 925,101.00 | 58,266,930.00 | 53,961,325.00 | — |
| 2024 | — | 54,730,862.01 | 816,232.90 | 55,547,094.91 | — | — |

> **Catatan Fakta:** Tahun tumpang-tindih `2020–2022` antara Buku PHL 2022 dan Buku PHL 2024 **identik hingga 2 angka desimal**. Angka BPS `2512#2` (perusahaan pembudidaya tanaman kehutanan/HTI) dan `1973#2` (HPH/hutan alam per pulau) memiliki cakupan izin berbeda dari total PBPH+Perhutani KLHK sehingga wajar berbeda.

---

## 3. Audit Sumber PLTU 5 Pulau (`04_pltu_5_pulau/`)

| Sumber | Tahun | Status | Jumlah PLTU | Jawa | Sumatera | Kalimantan | Sulawesi | Papua | Lainnya | Koordinat | Total MW |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `climatetrace_v6` | 2021 | `OK` | 100 | 29 | 25 | 16 | 22 | 1 | 7 | 100/100 | 41,306.7 |
| `climatetrace_v6` | 2022 | `OK` | 100 | 29 | 25 | 16 | 22 | 1 | 7 | 100/100 | 48,514.7 |
| `climatetrace_v6` | 2023 | `OK` | 100 | 29 | 25 | 16 | 22 | 1 | 7 | 100/100 | 53,928.7 |
| `climatetrace_v6` | 2024 | `OK` | 100 | 29 | 25 | 16 | 22 | 1 | 7 | 100/100 | 56,263.7 |
| `climatetrace_v6` | 2025 | `OK` | 100 | 29 | 25 | 16 | 22 | 1 | 7 | 100/100 | 59,718.7 |
| `wri_gppd` | commissioning 1998-2017; est_gen 2013-2017 | `OK` | 70 | 24 | 17 | 8 | 17 | 1 | 3 | 70/70 | 29,333.0 |
| `crea_mei_2025_tabel_a1` | 2024 | `OK` | 52 | 15 | 13 | 10 | 6 | 1 | 7 | 0/52 (PDF tidak memuat lat/lon) | 18,342.0 |
| `gem_gcpt_manual` | — | `BELUM_DIUNDUH_MANUAL` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | — |

- **Verifikasi CREA Mei 2025 Tabel A1:** Tepat **52 PLTU PLN** dengan total kapasitas terpasang **18.342,0 MW** (cocok target `~18.342 MW`) dan total realisasi biomassa 2024 sebesar **1.457.720 ton** (6 PLTU bernilai `NULL` apa adanya: 5 PLTU target co-firing + 1 PLTU `"-"`).

---

## 4. Cross-Check Nasional: `SUM(Kab/Kota BDSP)` vs `Provinsi BDSP` vs `BPS RI`

> *Catatan:* Perbandingan ini dilakukan **hanya di memori audit** (raw CSV tidak diubah). Untuk `kelapa_sawit` dan `tebu`, angka BPS RI (`Ribu Ton`) dikalikan `1.000` khusus pada tabel perbandingan ini agar setara `Ton`.

| Komoditas | Tahun | SUM(38 Kab/Kota BDSP) (Ton) | SUM(Provinsi BDSP) (Ton) | BPS RI Nasional (Ton) | Selisih Kab vs Prov (%) | Selisih BDSP Prov vs BPS (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `padi` | 2017 | 74,420,212 | 81,148,594 | — | -8.29% | — |
| `padi` | 2018 | 59,200,534 | 59,200,534 | 59,200,534 | 0.00% | 0.00% |
| `padi` | 2019 | 54,604,033 | 54,604,033 | 54,604,033 | 0.00% | -0.00% |
| `padi` | 2020 | 54,649,202 | 54,649,202 | 54,649,202 | 0.00% | -0.00% |
| `padi` | 2021 | 53,776,236 | 54,415,296 | 54,415,294 | -1.17% | 0.00% |
| `padi` | 2022 | 54,338,410 | 54,748,977 | 54,748,977 | -0.75% | -0.00% |
| `padi` | 2023 | 53,788,029 | 53,980,993 | 53,980,993 | -0.36% | 0.00% |
| `padi` | 2024 | 53,142,727 | 53,142,727 | 53,142,727 | 0.00% | 0.00% |
| `padi` | 2025 | 60,206,844 | 60,206,844 | — | -0.00% | — |
| `jagung` | 2017 | 25,769,782 | 28,924,016 | — | -10.91% | — |
| `jagung` | 2018 | 8,031,885 | 21,655,171 | — | -62.91% | — |
| `jagung` | 2019 | 6,696,020 | 22,586,209 | — | -70.35% | — |
| `jagung` | 2020 | 5,585,561 | 12,928,943 | 12,928,941 | -56.80% | 0.00% |
| `jagung` | 2021 | 5,555,630 | 13,414,924 | 13,414,922 | -58.59% | 0.00% |
| `jagung` | 2022 | 5,583,972 | 16,527,272 | 16,527,273 | -66.21% | -0.00% |
| `jagung` | 2023 | 0 | 14,774,430 | 14,774,433 | -100.00% | -0.00% |
| `jagung` | 2024 | 0 | 15,138,910 | 15,138,912 | -100.00% | -0.00% |
| `jagung` | 2025 | 0 | 16,159,167 | — | -100.00% | — |
| `kelapa_sawit` | 2017 | 37,764,694 | 37,965,226 | 34,940,300 | -0.53% | 8.66% |
| `kelapa_sawit` | 2018 | 15,296,807 | 42,883,630 | 42,883,500 | -64.33% | 0.00% |
| `kelapa_sawit` | 2019 | 14,925,878 | 47,120,246 | 47,120,200 | -68.32% | 0.00% |
| `kelapa_sawit` | 2020 | 15,495,525 | 46,765,592 | 48,296,900 | -66.87% | -3.17% |
| `kelapa_sawit` | 2021 | 15,503,844 | 45,121,480 | 46,223,300 | -65.64% | -2.38% |
| `kelapa_sawit` | 2022 | 16,310,610 | 46,819,672 | 46,819,700 | -65.16% | -0.00% |
| `kelapa_sawit` | 2023 | 16,223,443 | 47,100,685 | 47,084,300 | -65.56% | 0.03% |
| `kelapa_sawit` | 2024 | 16,970,694 | 45,436,197 | 45,436,200 | -62.65% | -0.00% |
| `kelapa_sawit` | 2025 | 17,106,122 | 219,884,298 | — | -92.22% | — |
| `tebu` | 2017 | 2,118,049 | 2,121,672 | 2,191,000 | -0.17% | -3.16% |
| `tebu` | 2018 | 2,170,309 | 2,170,948 | 2,171,700 | -0.03% | -0.03% |
| `tebu` | 2019 | 2,227,046 | 2,227,046 | 2,227,000 | 0.00% | 0.00% |
| `tebu` | 2020 | 2,130,720 | 2,130,719 | 2,130,700 | 0.00% | 0.00% |
| `tebu` | 2021 | 2,350,810 | 2,350,810 | 2,418,400 | -0.00% | -2.79% |
| `tebu` | 2022 | 2,405,907 | 2,405,908 | 2,402,600 | -0.00% | 0.14% |
| `tebu` | 2023 | 1,449,769 | 2,271,010 | 2,234,240 | -36.16% | 1.65% |
| `tebu` | 2024 | 1,613,023 | 2,465,515 | 2,465,510 | -34.58% | 0.00% |
| `tebu` | 2025 | 1,786,614 | 2,668,074 | — | -33.04% | — |

- **Cross-Check Satu Data Kementan Sawit 2023 (Perkebunan Rakyat):** Total produksi 514 baris Kab/Kota = **16,223,443.22 Ton** (khusus Perkebunan Rakyat; wajar lebih rendah dari total seluruh pengusahaan sawit di BDSP/BPS ~47 juta Ton).

### Deteksi Selisih Internal BDSP (`SUM(Kab/Kota)` vs `Baris Provinsi` > 0,05%)

Ditemukan **544 kasus** selisih antara penjumlahan file Kab/Kota BDSP dan angka pada tabel Provinsi BDSP (data mentah dibiarkan *as-is* sesuai sumber resmi). Menampilkan hingga 20 kasus dengan selisih absolut terbesar:

| Komoditas | Tahun | Kode | Provinsi | SUM Kab/Kota BDSP (Ton) | Provinsi BDSP (Ton) | Selisih (Ton) | Selisih (%) |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| `kelapa_sawit` | 2025 | `14` | Riau | 5,540,091.31 | 45,353,448.46 | -39,813,357.15 | 87.78% |
| `kelapa_sawit` | 2025 | `62` | Kalimantan Tengah | 1,082,670.66 | 33,836,494.10 | -32,753,823.44 | 96.80% |
| `kelapa_sawit` | 2025 | `61` | Kalimantan Barat | 1,432,215.32 | 24,375,170.55 | -22,942,955.23 | 94.12% |
| `kelapa_sawit` | 2025 | `12` | Sumatera Utara | 1,820,009.77 | 23,780,093.70 | -21,960,083.93 | 92.35% |
| `kelapa_sawit` | 2025 | `64` | Kalimantan Timur | 589,250.54 | 19,393,787.32 | -18,804,536.78 | 96.96% |
| `kelapa_sawit` | 2025 | `16` | Sumatera Selatan | 1,861,276.82 | 18,439,007.30 | -16,577,730.48 | 89.91% |
| `kelapa_sawit` | 2025 | `15` | Jambi | 1,373,401.60 | 9,562,930.01 | -8,189,528.41 | 85.64% |
| `kelapa_sawit` | 2023 | `62` | Kalimantan Tengah | 1,037,765.00 | 8,466,673.00 | -7,428,908.00 | 87.74% |
| `kelapa_sawit` | 2022 | `62` | Kalimantan Tengah | 1,031,734.00 | 8,363,763.00 | -7,332,029.00 | 87.66% |
| `kelapa_sawit` | 2019 | `62` | Kalimantan Tengah | 502,182.26 | 7,664,841.00 | -7,162,658.74 | 93.45% |
| `kelapa_sawit` | 2020 | `62` | Kalimantan Tengah | 934,919.59 | 8,072,879.00 | -7,137,959.41 | 88.42% |
| `kelapa_sawit` | 2025 | `13` | Sumatera Barat | 986,305.21 | 8,112,138.40 | -7,125,833.19 | 87.84% |
| `kelapa_sawit` | 2018 | `62` | Kalimantan Tengah | 277,702.00 | 7,230,094.00 | -6,952,392.00 | 96.16% |
| `kelapa_sawit` | 2024 | `62` | Kalimantan Tengah | 1,095,978.12 | 7,458,143.00 | -6,362,164.88 | 85.30% |
| `kelapa_sawit` | 2021 | `62` | Kalimantan Tengah | 982,722.00 | 7,280,743.00 | -6,298,021.00 | 86.50% |
| `kelapa_sawit` | 2025 | `63` | Kalimantan Selatan | 150,803.22 | 6,114,249.17 | -5,963,445.95 | 97.53% |
| `kelapa_sawit` | 2025 | `11` | Aceh | 0.00 | 5,510,149.04 | -5,510,149.04 | 100.00% |
| `kelapa_sawit` | 2025 | `17` | Bengkulu | 1,039,164.53 | 6,262,211.57 | -5,223,047.04 | 83.41% |
| `kelapa_sawit` | 2020 | `14` | Riau | 4,731,887.63 | 9,887,675.00 | -5,155,787.37 | 52.14% |
| `padi` | 2017 | `12` | Sumatera Utara | 0.00 | 5,136,186.00 | -5,136,186.00 | 100.00% |

---

## 5. Audit Ketat `NULL` vs `0` Eksplisit

- **Folder 1 (`01_bdsp_kementan/`):** total sel positif = **19,443**, sel `0` eksplisit (`0,00` di BDSP/Excel) = **23,527**, sel `NULL` = **266**. Seluruh 157 file sukses HTTP `200` (`Error: 0`).
- **Folder 2 (`02_bps/`):** **37 file CSV** tahunan dari 6 tabel BPS RI; total sel positif = **4,504**, sel `0` eksplisit = **774**, sel `NULL` (tidak dipublikasikan / provinsi pemekaran pra-2023) = **1,479**.
- **Folder 3 (`03_klhk_phl_kayu/`):** 4 tabel PDF; seluruh tanda `"-"` tersimpan sebagai **`NULL`** (total **136** sel `NULL`, **0** sel nol buatan).
- **Folder 4 (`04_pltu_5_pulau/`):** nilai `"-"` / `N/A` pada realisasi co-firing CREA tersimpan sebagai **`NULL`** (6 PLTU), koordinat/MW kosong di WRI/Climate TRACE disimpan sebagai **`NULL`**.

---

## 6. Daftar Celah Data & Temuan Anomali Sumber Resmi (*Known Gaps* — Dilaporkan Jujur *As-Is*)

1. **Kelapa Sawit BDSP Kab/Kota (`2018–2025`) Khusus Perkebunan Rakyat (Temuan Penting Audit):** Mulai 2018, total `SUM(38 Kab/Kota BDSP)` Kelapa Sawit (`16,22 juta Ton` pada 2023) **identik 100%** dengan Excel Satu Data Kementan `sawit_kabkota_2023.csv` (**16.223.443,22 Ton**, khusus *Perkebunan Rakyat*), sedangkan `Provinsi BDSP` (`47,10 juta Ton`) dan `BPS RI` (`47,08 juta Ton`) mencakup total *PR + PBN + PBS* (~65% selisih). Di Fase 3, jangan menyamakan BDSP Kab/Kota Sawit 2018+ sebagai total seluruh pengusahaan tanpa mencatat cakupannya.
2. **Lonjakan Kelapa Sawit BDSP Provinsi Tahun `2025` (`219,88 juta Ton`, naik 4,84× vs 2024 `45,44 juta Ton`):** Pada keluaran asli BDSP Provinsi 2025 terjadi lonjakan ~4,8× lintas provinsi sentra (misal Riau `45,35 juta Ton`, Kalteng `33,84 juta Ton`). Indikasi kuat perubahan basis pelaporan hulu di BDSP 2025 dari **CPO** ke **TBS (Tandan Buah Segar)** (`1 Ton CPO ≈ 4,5–5 Ton TBS`). Raw CSV dibiarkan *as-is*; wajib diverifikasi & dipisahkan sebelum agregasi di Fase 3.
3. **Tebu BDSP Kab/Kota (`2023–2025`) Lebih Rendah ~33–36% vs Provinsi:** Pada `2018–2022`, `SUM(Kab/Kota BDSP)` cocok `0,00%` dengan `Provinsi BDSP` (~2,13–2,41 juta Ton), namun pada `2023–2025` turun menjadi `1,45–1,79 juta Ton` dibanding `Provinsi BDSP` (`2,27–2,67 juta Ton`, yang cocok dengan `BPS RI 2024 = 2,465 juta Ton`) — indikasi cakupan Kab/Kota Tebu 2023+ hanya mencakup Perkebunan Rakyat.
4. **Jagung Level Kab/Kota (BDSP):** Mulai `2018–2022` hanya sebagian provinsi yang terisi di BDSP Kab/Kota (`5,56–8,03 juta Ton` vs `12,93–22,59 juta Ton` Provinsi), dan pada **`2023–2025` seluruhnya `0,00`** di level Kab/Kota. Untuk `2020–2024`, data level **Provinsi** di `bdsp_jagung_38_provinsi.csv` cocok **`0,00%`** dengan `BPS RI 2204#2`.
5. **Tahun `2026` di BDSP:** Seluruh tabel BDSP menampilkan kolom `2026` bernilai `0,00` (belum ada rilis Angka Tetap 2026); data aktual terbaru BDSP berada pada **2025**.
6. **Kayu Bulat Level Kab/Kota:** Belum tersedia seragam secara nasional di BDSP maupun BPS RI; cakupan resmi terlengkap saat ini adalah **Level Provinsi (`2018–2024`)** dari 2 buku PDF Statistik Ditjen PHL KLHK (`03_klhk_phl_kayu/`, rekonsiliasi **20/20 MATCH**) dan **Level Pulau/Nasional** di BPS RI (`1973#2`, `2512#2`).
7. **4 Provinsi Pemekaran Papua (`92` Papua Barat Daya, `95` Papua Selatan, `96` Papua Tengah, `97` Papua Pegunungan):** Data historis sebelum 2023 masih tergabung di provinsi induk (`91` Papua Barat / `94` Papua), sehingga bernilai `0` atau `NULL` pada tahun pra-pemekaran. Di PDF KLHK PHL 2024 (Tabel 3.9), Papua Pegunungan (kode `97`) belum tercantum sebagai baris tersendiri (total 37 provinsi tercetak).
8. **BPS Provinsi (`02_bps/bps_provinsi/`):** Dilewati bersih (`SKIPPED_OPSIONAL`) karena `BPS_API_KEY` belum dikonfigurasi; dapat dijalankan kapan saja dengan mengisi `BPS_API_KEY` di `.env`.
9. **GEM Global Coal Plant Tracker (`04_pltu_5_pulau/gem_gcpt/`):** Memerlukan unduhan form manual; slot sudah disiapkan dan akan terkonversi otomatis oleh skrip `04_extract_pltu_5_pulau.py` jika Excel resmi GEM diletakkan di folder tersebut.
10. **Koordinat CREA & Tahun WRI GPPD:** Lampiran Tabel A1 CREA (52 PLTU PLN) tidak memuat kolom koordinat `lat/lon` (hanya nama lokasi kab/kota & provinsi), sedangkan WRI GPPD (70 PLTU) memuat koordinat lengkap tetapi berhenti pada rilis v1.3.0 (`commissioning <= 2017`, estimasi generasi `2013–2017`). Climate TRACE v6 (`2021–2025`) melengkapi keduanya dengan 100 PLTU batu bara per tahun lengkap dengan koordinat, kapasitas MW, aktivitas MWh, dan emisi.
