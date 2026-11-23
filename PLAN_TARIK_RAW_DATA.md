# Plan Fase 2: Penarikan Raw Data ke 4 Folder Terpisah (100% Mentah per CSV)

> **Prasyarat:** Fase 1 (*Link of Sources* di `raw_data/daftar_sumber_data.xlsx`) sudah selesai & seluruh URL sudah lolos verifikasi HTTP + anti soft-404.
>
> **Fokus Fase 2:** Menarik **raw data 100% mentah apa adanya (*as-is*)** dari seluruh sumber terverifikasi ke dalam **4 folder utama terpisah**, seluruhnya dalam format **CSV (`.csv`)**, dengan prinsip ketat **`1 tarikan asli dari sumber = 1 file .csv`** (nol penggabungan antar-tahun, antar-provinsi, maupun antar-sumber). Kerapian dijaga lewat **struktur subfolder yang konsisten + 1 file index (`_INDEX_RAW_DATA.csv`)**.
>
> **Masih Di Luar Scope Fase 2 (Dikerjakan Setelah Raw Data Disetujui):**
> - Data kandungan kimia & HHV biomassa (sudah tersedia di `raw_data/03_karakteristik_biomassa_kimia_hhv.*` — **tidak disentuh**).
> - Penggabungan (*merge/harmonisasi*), cleaning destruktif, perhitungan potensi limbah, rasio RPR, kebutuhan energi/batu bara harian PLTU, Data Warehouse, ML, & Power BI.

---

## Aturan Emas Penyimpanan Raw Data (*Strict Scientist / Zero-Merge*)

1. **Zero Merge / Zero Append (`1 tarikan asli = 1 file .csv`):**
   - Jika sumber mengembalikan data per provinsi (misal BDSP Kab/Kota), simpan **1 provinsi = 1 file CSV**.
   - Jika sumber mengembalikan data per tahun dropdown (misal tabel BPS RI `2512#2` tahun 2020, 2021, 2022, 2023), simpan **1 tahun = 1 file CSV**.
   - Jika sumber berupa buku PDF dengan beberapa tabel (misal KLHK PHL Tabel 3.9 vs Tabel 3.12), simpan **1 tabel = 1 file CSV**.
   - Jika sumber berupa API per tahun (misal Climate TRACE 2021–2025), simpan **1 tahun API = 1 file CSV**.
2. **Rapi di Subfolder & Penamaan Berurutan:**
   - Seluruh nama folder & file menggunakan huruf kecil (`lowercase`), diawali kode BPS (`11_aceh.csv` … `97_papua_pegunungan.csv`) atau tahun (`2020.csv` … `2025.csv`) agar otomatis urut rapi di Windows Explorer.
   - Tidak ada ratusan file mentah bertumpuk di satu folder datar.
3. **Standar Format CSV:**
   - Encoding **`UTF-8 with BOM` (`utf-8-sig`)**, delimiter koma (`,`), angka desimal titik (`.`) tanpa pemisah ribuan, supaya langsung terbaca benar di Excel Windows maupun Python/Power BI.
   - Setiap file menyertakan metadata asal yang jelas (`sumber_instansi`, `sumber_url`, `satuan_asli`, `level_wilayah`, `tanggal_tarik`) tanpa mengubah struktur angka aslinya.
4. **Ketat Membedakan `NULL` vs `0`:**
   - Data kosong / `"-"` / tidak dipublikasikan di sumber → disimpan kosong (**`NULL` / `NaN`**).
   - Data eksplisit `0` / `0,00` di sumber → dicatat apa adanya + dicatat dalam audit.
5. **Satu Peta Utama (`_INDEX_RAW_DATA.csv`) & Auto-Audit (`AUDIT_RAW_DATA.md`):**
   - Meskipun file mentah terpisah satu per satu, seluruh file diindeks otomatis di `raw_data/_INDEX_RAW_DATA.csv` (berisi path file, sumber, rentang tahun, jumlah baris, dan status validasi) agar gampang diaudit dari satu tempat.

---

## Struktur Target: 4 Folder Raw Data (100% Terpisah per CSV)

```text
PROJECTKB/
├── PLAN.md                                           # Plan Fase 1 (Link of Sources - Selesai)
├── PLAN_TARIK_RAW_DATA.md                            # Plan Fase 2 (Dokumen ini)
├── scripts/
│   └── extract/
│       ├── 01_extract_bdsp_kementan.py               # Ekstraktor Folder 1
│       ├── 02_extract_bps.py                         # Ekstraktor Folder 2
│       ├── 03_extract_klhk_phl_kayu.py               # Ekstraktor Folder 3
│       ├── 04_extract_pltu_5_pulau.py                # Ekstraktor Folder 4
│       └── 05_audit_and_index_raw.py                 # Generator Index + Laporan Audit Kualitas
└── raw_data/
    ├── daftar_sumber_data.xlsx                       # Katalog Link of Sources (Fase 1)
    ├── 03_karakteristik_biomassa_kimia_hhv.*         # Data kimia existing (tidak disentuh)
    │
    ├── 01_bdsp_kementan/                             # [FOLDER 1] BDSP & Satu Data Kementan
    │   ├── padi/
    │   │   ├── kabkota/
    │   │   │   ├── 11_aceh.csv                       # 1 tarikan POST (2010-2025) = 1 CSV
    │   │   │   ├── 12_sumatera_utara.csv
    │   │   │   └── ... (38 file: 11_aceh.csv s.d. 97_papua_pegunungan.csv)
    │   │   └── provinsi/
    │   │       └── bdsp_padi_38_provinsi.csv         # 1 tarikan POST level Provinsi
    │   ├── kelapa_sawit/
    │   │   ├── kabkota/                              # 38 file (11_aceh.csv s.d. 97_papua_pegunungan.csv)
    │   │   └── provinsi/
    │   │       └── bdsp_kelapa_sawit_38_provinsi.csv
    │   ├── tebu/
    │   │   ├── kabkota/                              # 38 file (11_aceh.csv s.d. 97_papua_pegunungan.csv)
    │   │   └── provinsi/
    │   │       └── bdsp_tebu_38_provinsi.csv
    │   ├── jagung/
    │   │   ├── kabkota/                              # 38 file (as-is: terisi 2010-2017/2022, 2018+ 0/null)
    │   │   └── provinsi/
    │   │       └── bdsp_jagung_38_provinsi.csv       # Lengkap 2010-2025 level Provinsi
    │   ├── satudata_kementan/
    │   │   └── sawit_kabkota_2023.csv                # Konversi mentah 1:1 dari XLSX resmi (555 baris)
    │   └── _audit_01_bdsp_kementan.csv
    │
    ├── 02_bps/                                       # [FOLDER 2] BPS RI & BPS Provinsi
    │   ├── bps_ri/
    │   │   ├── 1498_padi/                            # 1 tahun dropdown = 1 CSV sendiri
    │   │   │   ├── 2018.csv
    │   │   │   ├── ...
    │   │   │   └── 2024.csv
    │   │   ├── 2204_jagung/
    │   │   │   ├── 2020.csv
    │   │   │   ├── ...
    │   │   │   └── 2024.csv
    │   │   ├── 2566_perkebunan/                      # Sawit, Tebu, dll. per Provinsi
    │   │   │   ├── 2023.csv
    │   │   │   └── 2024.csv
    │   │   ├── 132_perkebunan_historis/
    │   │   │   └── {tahun}.csv
    │   │   ├── 2512_kayu_jenis_pohon/                # Tabel Kehutanan per Jenis Produksi
    │   │   │   ├── 2020.csv
    │   │   │   ├── 2021.csv
    │   │   │   ├── 2022.csv
    │   │   │   └── 2023.csv
    │   │   └── 1973_kayu_hph_pulau/
    │   │       └── {tahun}.csv
    │   ├── bps_provinsi/                             # [Opsional - bila pakai BPS_API_KEY / tarik daerah]
    │   │   ├── 11_aceh/
    │   │   │   └── {id_tabel}_{tahun}.csv
    │   │   ├── 12_sumatera_utara/
    │   │   │   └── {id_tabel}_{tahun}.csv
    │   │   └── ... (terpisah per provinsi, per tabel, per tahun)
    │   └── _audit_02_bps.csv
    │
    ├── 03_klhk_phl_kayu/                             # [FOLDER 3] Kayu Bulat Ditjen PHL KLHK
    │   ├── buku_2024/                                # Ekstrak PDF Statistik PHL 2024 (2020-2024)
    │   │   ├── tabel_3_9_pbph_provinsi_2020_2024.csv
    │   │   └── tabel_3_12_perhutani_provinsi_2020_2024.csv
    │   ├── buku_2022/                                # Ekstrak PDF Statistik PHL 2022 (2018-2022)
    │   │   ├── tabel_pbph_provinsi_2018_2022.csv
    │   │   └── tabel_perhutani_provinsi_2018_2022.csv
    │   └── _audit_03_klhk_phl_reconciliation.csv     # Cek SUM(provinsi) vs baris JUMLAH PDF
    │
    ├── 04_pltu_5_pulau/                              # [FOLDER 4] PLTU 5 Pulau Utama
    │   ├── climatetrace/                             # 1 tahun API = 1 CSV sendiri
    │   │   ├── 2021.csv
    │   │   ├── 2022.csv
    │   │   ├── 2023.csv
    │   │   ├── 2024.csv
    │   │   └── 2025.csv
    │   ├── wri_gppd/
    │   │   └── wri_gppd_coal_idn.csv                 # 70 PLTU Indonesia as-is dari CSV WRI
    │   ├── crea_2025/
    │   │   └── tabel_a1_52_pltu_cofiring_2024.csv    # 52 PLTU PLN Co-Firing dari PDF CREA Mei 2025
    │   ├── gem_gcpt/                                 # [Opsional/Manual] tempat taruh Excel/CSV GEM
    │   │   └── gem_gcpt_coal_idn.csv
    │   └── _audit_04_pltu_5_pulau.csv
    │
    ├── _INDEX_RAW_DATA.csv                           # Daftar isi seluruh file CSV lintas 4 folder
    └── AUDIT_RAW_DATA.md                             # Laporan QA & validasi lintas sumber
```

---

## Langkah Eksekusi Step-by-Step

### Step 0: Persiapan Folder & Utilitas Bersama
- Membuat seluruh hierarki 4 folder raw di `raw_data/` serta folder skrip `scripts/extract/`.
- Membuat utilitas standar:
  - Parser angka format Indonesia (`1.234.567,89` → `1234567.89`),
  - Writer CSV `utf-8-sig` (tanpa mengubah atau menggabungkan file mentah),
  - HTTP retry + pencatatan log per request agar jika ada 1 provinsi/tahun gagal, langsung terlihat & bisa diulang parsial.

---

### Step 1: Ekstraksi Folder 1 — `raw_data/01_bdsp_kementan/`
**Skrip:** `scripts/extract/01_extract_bdsp_kementan.py`

1. **Inisialisasi Sesi:** `GET https://bdsp2.pertanian.go.id/bdsp/id/lokasi` untuk cookie sesi valid.
2. **Tarik Level Kab/Kota (`level=03`, rentang `2010–2026`, `sts_angka=6` Angka Tetap, satuan Ton):**
   - Loop **4 komoditas** (`padi` `01059`, `kelapa_sawit` `02027`, `tebu` `02051`, `jagung` `01027`) × **38 provinsi** (`11`–`97`).
   - Setiap 1 request POST disimpan menjadi **1 file CSV tersendiri** di `raw_data/01_bdsp_kementan/{komoditas}/kabkota/{kode}_{nama_provinsi}.csv` (persis tabel keluaran BDSP — tidak digabung).
3. **Tarik Level Provinsi (`level=02`, rentang `2010–2026`):**
   - Tarik 1 file per komoditas di `raw_data/01_bdsp_kementan/{komoditas}/provinsi/bdsp_{komoditas}_38_provinsi.csv` (terutama penting untuk **Jagung 2018–2025** dan validasi silang total provinsi).
4. **Konversi Direct Excel Satu Data Kementan (Sawit 2023):**
   - Unduh `45_Luas_perkebunan_kelapa_sawit_di_kabupaten.xlsx` → ekspor mentah 1:1 ke `raw_data/01_bdsp_kementan/satudata_kementan/sawit_kabkota_2023.csv` (555 baris).
5. **Audit Folder 1:** Tulis `_audit_01_bdsp_kementan.csv` berisi status HTTP, jumlah baris, jumlah kab/kota non-nol, dan rentang tahun aktual per file.

---

### Step 2: Ekstraksi Folder 2 — `raw_data/02_bps/`
**Skrip:** `scripts/extract/02_extract_bps.py`

1. **Tahap 2A — 6 Tabel Utama BPS RI (Otomatis, Tanpa API Key, 1 Tahun = 1 CSV):**
   - Untuk masing-masing dari 6 tabel nasional resmi (`1498#2` Padi, `2204#2` Jagung, `2566#2` Perkebunan, `132#2` Perkebunan Historis, `2512#2` Kayu Jenis Pohon, `1973#2` Kayu HPH Pulau):
     - Deteksi seluruh tahun yang tersedia pada *year selector* halaman resmi BPS.
     - Ambil data **per tahun** (via tombol resmi **Unduh Excel** BPS / payload Next.js) lalu simpan mentah 1:1 menjadi **1 CSV per tahun** di `raw_data/02_bps/bps_ri/{id_tabel}_{topik}/{tahun}.csv`.
     - **Tidak ada penggabungan antar-tahun** di tahap raw ini.
2. **Tahap 2B — BPS 34 Provinsi (Opsional, Jika Pakai `BPS_API_KEY`):**
   - Jika `BPS_API_KEY` tersedia, skrip query WebAPI BPS untuk 34 domain provinsi (`1100`–`9400`) lalu menyimpan setiap tabel daerah terpisah di `raw_data/02_bps/bps_provinsi/{kode}_{provinsi}/{id_tabel}_{tahun}.csv`.
   - Jika belum memakai API key, Tahap 2B dilewati secara bersih dan dicatat di `_audit_02_bps.csv`.
3. **Audit Folder 2:** Tulis `_audit_02_bps.csv` berisi tabel ID, tahun yang berhasil ditarik, path CSV, jumlah baris, dan satuan asli (`ton`, `ribu_ton`, `m3`).

---

### Step 3: Ekstraksi Folder 3 — `raw_data/03_klhk_phl_kayu/`
**Skrip:** `scripts/extract/03_extract_klhk_phl_kayu.py`

1. **Verifikasi 2 PDF Resmi:**
   - Memakai/mengunduh `klhk_phl_2024.pdf` (Statistik PHL 2024, cakupan `2020–2024`) dan `klhk_phl_2.pdf` (Statistik PHL 2022, cakupan `2018–2022`).
   - *(PDF 2023 di-skip karena scan gambar 0 teks & seluruh angkanya sudah ter-cover di PDF 2024).*
2. **Ekstraksi 1 Tabel PDF = 1 CSV Mentah:**
   - `buku_2024/tabel_3_9_pbph_provinsi_2020_2024.csv` (via `pdfplumber`, hal. 152, satuan `m3`).
   - `buku_2024/tabel_3_12_perhutani_provinsi_2020_2024.csv` (via `pdfplumber`, hal. 155, satuan `m3`).
   - `buku_2022/tabel_pbph_provinsi_2018_2022.csv` (via `PyMuPDF`, hal. 113–114, satuan `m3`).
   - `buku_2022/tabel_perhutani_provinsi_2018_2022.csv` (via `PyMuPDF`, hal. 117, satuan `m3`).
   - Tanda `"-"` di PDF disimpan sebagai `NULL` (`NaN`).
3. **Reconciliation Check Wajib:**
   - Bandingkan `SUM(semua provinsi)` hasil ekstrak terhadap baris `JUMLAH` tercetak di PDF untuk setiap tahun (`2018–2024`) → simpan ke `_audit_03_klhk_phl_reconciliation.csv`.

---

### Step 4: Ekstraksi Folder 4 — `raw_data/04_pltu_5_pulau/`
**Skrip:** `scripts/extract/04_extract_pltu_5_pulau.py`

1. **Climate TRACE v6 (`climatetrace/2021.csv` … `2025.csv`):**
   - Loop `year = 2021..2025`, hit `GET /v6/assets?countries=IDN&sectors=power&year={yr}&limit=500`, filter `coal`, simpan **1 tahun = 1 CSV mentah** (seluruh kolom asli API + estimasi pulau dari koordinat).
2. **WRI Global Power Plant Database (`wri_gppd/wri_gppd_coal_idn.csv`):**
   - Unduh CSV WRI → filter `country == 'IDN'` & `primary_fuel == 'Coal'` → simpan 70 baris as-is beserta seluruh kolom asli WRI.
3. **CREA Mei 2025 (`crea_2025/tabel_a1_52_pltu_cofiring_2024.csv`):**
   - Ekstrak Lampiran Tabel A1 via `pdfplumber` → simpan 52 PLTU PLN Co-Firing mentah + cek total jumlah unit (`52`) dan total MW (`~18.342 MW`).
4. **GEM Global Coal Plant Tracker (`gem_gcpt/gem_gcpt_coal_idn.csv`, Opsional/Semi-Manual):**
   - Jika user menaruh Excel unduhan manual GEM di `raw_data/04_pltu_5_pulau/gem_gcpt/`, skrip otomatis memfilter `Country == Indonesia` dan mengekspornya ke CSV raw. Jika belum ada, dicatat jujur di audit.
5. **Audit Folder 4:** Tulis `_audit_04_pltu_5_pulau.csv` (jumlah PLTU per sumber, sebaran 5 pulau utama *Jawa, Sumatera, Kalimantan, Sulawesi, Papua*, kelengkapan koordinat & MW).

---

### Step 5: Indeks Global & Audit Kualitas Lintas 4 Folder (Read-Only terhadap Raw CSV)
**Skrip:** `scripts/extract/05_audit_and_index_raw.py`

1. **Generate `raw_data/_INDEX_RAW_DATA.csv`:** Peta otomatis seluruh file CSV di 4 folder (`folder_utama`, `subfolder`, `nama_file`, `path_relatif`, `jumlah_baris`, `jumlah_kolom`, `rentang_tahun`, `ukuran_kb`, `status_qc`).
2. **Generate `raw_data/AUDIT_RAW_DATA.md`:**
   - Hasil rekonsiliasi PDF KLHK PHL (`SUM` vs `JUMLAH`) & CREA (`52 PLTU / 18.342 MW`).
   - *Cross-check* total `SUM(Kab/Kota BDSP)` vs `Provinsi BDSP` vs `BPS RI` (hanya laporan selisih, **tidak mengubah raw CSV**).
   - Deteksi karakter rusak, angka ribuan/desimal terbalik, serta daftar celah data (*known gaps*) secara jujur.

---

### Step 6: Checkpoint Review Manual oleh User
- Kamu cek langsung file mentah di 4 folder + peta `_INDEX_RAW_DATA.csv` + `AUDIT_RAW_DATA.md`.
- Setelah raw data tervalidasi 100%, barulah kita masuk ke **Fase 3** (Cleaning/Harmonisasi Wilayah → Perhitungan Biomassa → Matching Spasial PLTU 5 Pulau → Modeling/BI).

---

## Catatan Eksekusi (Default Siap Jalan)
- **Lokasi 4 folder:** di dalam `raw_data/` (`01_bdsp_kementan/`, `02_bps/`, `03_klhk_phl_kayu/`, `04_pltu_5_pulau/`).
- **Eksekusi default pertama:** jalan otomatis penuh tanpa `BPS_API_KEY` (4 folder: BDSP + 6 tabel BPS RI per tahun + KLHK PHL + Climate TRACE/WRI/CREA). Slot `bps_provinsi/` dan `gem_gcpt/` sudah disiapkan rapi bila nanti ingin ditambahkan.
