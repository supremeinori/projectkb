# Plan: Pencarian & Verifikasi Daftar Sumber Data (*Link of Sources*)

> **Fokus Plan Ini:** Khusus **mencari, mengetes (*live hit*), dan mendokumentasikan daftar sumber data (*Link of Sources*)** ke dalam **1 file Excel multi-tab (`daftar_sumber_data.xlsx`)** agar bisa kamu **cek manual dulu** sebelum ada penarikan raw data besar-besaran.
>
> **Di Luar Scope Plan Ini (Ditunda / Sudah Ada):**
> - *Kandungan kimia per kategori limbah* — **dikeluarkan** (datanya sudah ada di `raw_data/03_karakteristik_biomassa_kimia_hhv.*`).
> - *Perhitungan energi & batu bara harian PLTU* — **ditunda dulu** (fokus sekarang cukup daftar sumber data PLTU-nya dulu).
> - *Eksekusi penarikan penuh raw data, ML, Data Warehouse, & Power BI* — dilakukan **setelah** kamu cek manual & setujui daftar sumber di Excel.

---

## Prinsip Saintis & Aturan Pelaporan *As-Is* (Wajib Dipatuhi)

1. **Tampilkan Apa Adanya (*As-Is*):** Jika suatu portal, provinsi, komoditas, atau sumber PLTU **tidak ketemu, mati, diblokir, atau datanya kosong**, tampilkan jujur apa adanya (`NULL` / status error aktual). Dilarang keras mengarang link, mengarang tahun, atau menebak ketersediaan tanpa mengetes (*live hit*).
2. **Wajib *Live Hit Test*:** Setiap URL/endpoint yang masuk Excel harus benar-benar di-hit (`GET`/`POST`/`HEAD`) untuk membuktikan:
   - Status HTTP aktual (`200 OK`, `403`, `404`, `SSL_ERROR`, `DNS_NOT_FOUND`, `TIMEOUT`),
   - Metode ambil datanya (`API_JSON`, `POST_HTML_TABLE`, `DIRECT_DOWNLOAD_CSV`, `DIRECT_DOWNLOAD_XLSX`, `DIRECT_DOWNLOAD_PDF`, `BUTUH_API_KEY`, `MANUAL_FORM_DOWNLOAD`),
   - Apakah datanya benar-benar bisa dibaca/diekstrak otomatis (misal: PDF berteks vs PDF scan gambar).
3. **Rentang Tahun Target (`2010–2026`) + Kolom Tahun Aktual:**
   - Target pencarian data adalah rentang **minimal 2010 sampai paling tinggi 2026**.
   - Setiap baris sumber **wajib** memiliki kolom `tahun_awal_tersedia`, `tahun_akhir_tersedia`, dan `rentang_tahun_aktual` untuk memberi tahu secara jujur tahun berapa saja data itu benar-benar ditemukan di sumbernya (jika di sumber resmi cuma ada 2015–2017 atau 2018–2022, tulis apa adanya).

---

## Target Output: 1 File Excel Multi-Tab (`daftar_sumber_data.xlsx`)

Disimpan di root proyek (atau folder `raw_data/` — default: `raw_data/daftar_sumber_data.xlsx`), terdiri dari **4 Tab (Sheet)** terpisah:

### Tab 1: `Ringkasan_Sumber`
Ringkasan eksekutif seluruh sumber utama lintas kategori (Produksi 5 Komoditas & PLTU 5 Pulau) agar gampang diaudit dari atas.
- **Kolom:** `no`, `kategori_data`, `cakupan_komoditas_atau_topik`, `nama_sumber_instansi`, `url_endpoint`, `metode_akses`, `status_http`, `bisa_ambil_otomatis`, `level_wilayah`, `tahun_awal_tersedia`, `tahun_akhir_tersedia`, `rentang_tahun_aktual`, `bukti_hasil_hit`, `catatan_fakta`, `status_review_manual` *(kosong untuk diisi user)*, `catatan_user` *(kosong untuk diisi user)*.

### Tab 2: `Portal_38_Provinsi`
Daftar lengkap seluruh **38 provinsi Indonesia** (34 provinsi klasik + 4 provinsi pemekaran Papua) beserta endpoint portal BPS Provinsi dan portal Satu Data Pemprov-nya.
- **Kolom:** `kode_prov_bps`, `kode_domain_webapi`, `provinsi`, `pulau`, `masuk_5_pulau_pltu`, `url_bps_provinsi`, `url_tabel_statistik_bps`, `status_http_bps`, `endpoint_webapi_bps`, `url_satudata_pemprov`, `status_http_pemprov`, `metode_akses_rekomendasi`, `status_data`, `catatan_fakta`, `status_review_manual`, `catatan_user`.
- **Cakupan 38 Provinsi:**
  - Sumatera (10), Jawa (6), Kalimantan (5), Sulawesi (6), Papua (6 — termasuk 4 provinsi pemekaran), serta Bali-Nusa Tenggara-Maluku (5).

### Tab 3: `Sumber_5_Komoditas_38_Prov`
Peta verifikasi *as-is* sumber data produksi untuk **5 Komoditas Utama** (**Jagung**, **Padi / Sekam Padi**, **Kayu**, **Tebu**, **Sawit**) di **setiap 38 provinsi** (total 38 × 5 = **190 baris** agar tidak ada satu pun provinsi yang terlewat atau disembunyikan!).
- **Sumber yang Di-hit & Dicek (Rentang 2010–2026):**
  1. **BDSP Kementerian Pertanian** (`https://bdsp2.pertanian.go.id/bdsp/id/lokasi` — POST tabel HTML level Kabupaten/Kota untuk Padi, Jagung, Kelapa Sawit, Tebu di seluruh 38 provinsi, cek rentang 2010–2026).
  2. **BPS RI (Statistik Nasional/Provinsi & Subdomain Provinsi `*.bps.go.id`)** — cek pelengkap untuk tahun terbaru (misal Jagung KSA 2024, Perkebunan 2023–2024, Padi 2024, Kehutanan).
  3. **Statistik Ditjen PHL Kementerian Kehutanan / KLHK** (`phl.kehutanan.go.id` — PDF resmi produksi Kayu Bulat PBPH & Perhutani per provinsi, serta cek PDF mana yang punya teks bisa diekstrak vs scan gambar).
  4. **Satu Data Pertanian** (`satudata.pertanian.go.id/datasets`) — cek tambahan bila ada dataset spesifik Kab/Kota terbaru.
- **Kolom:** `kode_prov`, `provinsi`, `pulau`, `komoditas`, `level_wilayah_tertinggi` (`KABKOTA` / `PROVINSI` / `PULAU` / `TIDAK_TERSEDIA`), `sumber_utama`, `url_endpoint`, `metode_akses`, `status_http`, `bisa_ambil_otomatis`, `tahun_awal_tersedia`, `tahun_akhir_tersedia`, `rentang_tahun_aktual`, `jumlah_kabkota_ada_data`, `status_data`, `catatan_fakta`, `status_review_manual`, `catatan_user`.

### Tab 4: `Sumber_PLTU_5_Pulau`
Daftar sumber data **PLTU di 5 Pulau Utama** (**Jawa, Sumatera, Kalimantan, Sulawesi, Papua**) — fokus pada ketersediaan daftar unit/lokasi PLTU, koordinat, dan kapasitas MW (tanpa menghitung energi harian dulu).
- **Sumber yang Di-hit & Dicek (Rentang 2010–2026):**
  1. **WRI Global Power Plant Database** (GitHub Direct CSV — cek jumlah PLTU Indonesia per 5 pulau, koordinat, tahun operasi).
  2. **Laporan Co-Firing Biomassa Indonesia — CREA (Mei 2025)** (Direct PDF — cek Lampiran Tabel A1 52 PLTU PLN per 5 pulau).
  3. **Global Energy Monitor — Global Coal Plant Tracker (GCPT)** (portal download Excel resmi — cek status akses form/manual & cakupan tahun terbaru).
  4. **Statistik Ketenagalistrikan / RUPTL (Ditjen Gatrik ESDM / PLN)** — cek tautan dokumen publik yang aktif (atau catat *as-is* jika terblokir/butuh unduh manual).
- **Kolom:** `no`, `nama_sumber`, `instansi`, `url_sumber`, `metode_akses`, `status_http`, `bisa_ambil_otomatis`, `cakupan_pulau` (`Jawa`, `Sumatera`, `Kalimantan`, `Sulawesi`, `Papua`, dll.), `jumlah_pltu_terdeteksi`, `tahun_awal_tersedia`, `tahun_akhir_tersedia`, `rentang_tahun_aktual`, `kolom_utama_tersedia`, `status_data`, `catatan_fakta`, `status_review_manual`, `catatan_user`.

---

## Langkah Eksekusi (Setelah Plan Disetujui)

1. **Verifikasi 38 Portal Provinsi:** Jalankan *live hit test* ke 38 subdomain `*.bps.go.id` dan portal Satu Data Pemprov untuk mengisi Tab `Portal_38_Provinsi`.
2. **Verifikasi Ketersediaan 5 Komoditas × 38 Provinsi (Rentang 2010–2026):** Cek rentang tahun aktual (`2010–2026`) di BDSP Kementan, BPS RI, dan PDF KLHK PHL untuk mengisi 190 baris Tab `Sumber_5_Komoditas_38_Prov` secara *as-is* (tanpa menyimpan raw data masif dulu — cukup cek metadata, tahun tersedia, dan jumlah Kab/Kota yang ada angkanya).
3. **Verifikasi Sumber PLTU 5 Pulau:** Jalankan *live hit test* ke WRI GPPD, PDF CREA 2025, GEM GCPT, dan portal ESDM/PLN untuk mengisi Tab `Sumber_PLTU_5_Pulau`.
4. **Susun `Ringkasan_Sumber` & Ekspor ke Excel Multi-Tab:** Simpan ke `raw_data/daftar_sumber_data.xlsx` dengan format tabel rapi (header jelas, lebar kolom terbaca, link bisa diklik) supaya nyaman kamu cek manual.
5. **Review Manual oleh Kamu:** Kamu cek Excel-nya, isi kolom `status_review_manual` / `catatan_user`, baru kita lanjut ke tahap penarikan raw data dari sumber-sumber yang kamu setujui.

---

## Catatan / Editan dari Kamu (Opsional)
- *(Silakan edit langsung di sini jika ada tambahan sumber, kolom tertentu di Excel, atau penyesuaian lain sebelum saya eksekusi pembuatan Excel `daftar_sumber_data.xlsx`.)*
