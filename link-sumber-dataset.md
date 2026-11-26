# Daftar Sumber LEVEL PROVINSI (baris kabupaten/kota) — FINAL, 23 Nov 2026

Kriteria: satu dataset/tabel mencakup seluruh provinsi, baris per kabupaten/kota. Dataset satu-kabupaten/kecamatan TIDAK dipakai.

## Temuan utama
- **Data limbah level provinsi per kab/kota: TIDAK ADA** untuk kelima komoditas di semua 33 provinsi. Satu-satunya temuan terkait limbah: 2 dataset riset nasional BRIN tentang tandan kosong kelapa sawit (TKKS) di data.go.id (level nasional, bukan provinsi). Semua sumber di bawah adalah data **PRODUKSI**, sesuai aturan fallback.
- **Padi: lengkap 33/33 provinsi**, sudah diekstrak ke CSV (2.614 baris). 29 provinsi full 2020–2025; Aceh 2020–2023 (data.go.id); 4 provinsi Papua pemekaran (Barat Daya, Selatan, Tengah, Pegunungan) tabelnya baru mulai 2022 dan baris 2022 masih kosong (data masih gabung provinsi induk).
- **Jagung 2020–2025 adalah celah terbesar:** tabel dinamis BPS "Produksi Jagung dan Kedelai" di semua provinsi adalah tabel warisan yang berhenti di 2015 (Kepri & Sumut sampai 2018). Yang berhasil diekstrak hanya Aceh (data.go.id, 2020–2023). Sumut & Sumsel punya dataset per-tahun di data.go.id tapi file-nya gagal diunduh (sertifikat rusak/404/500 di server sumber).
- **Tebu:** hanya Aceh & Sumut yang punya data dalam rentang. **Sawit:** yang terpakai hanya Aceh & Sumut (Babel data lama, Jatim isinya kosong). **Kayu:** hanya kayu rakyat Jateng 2025; provinsi lain data lama atau tidak per kab/kota.
- File data gabungan: `data-biomassa-2020-2025.csv` — **3.224 baris** (padi 2.614, sawit 348, tebu 135, jagung 92, kayu 35). Kolom nilai kosong ("–" di sumber) berarti tidak ada produksi/nihil di sumbernya.

Status: **DIEKSTRAK** = data sudah masuk CSV · **TIDAK ADA** = sudah diverifikasi, tidak ada sumber yang memenuhi kriteria.

---

## JAWA (6 provinsi)

### 1. Jawa Barat (kode 32)
- Padi — **DIEKSTRAK** 2020–2025 (162 baris) (2020–2022 dari Galura/Open Data Jabar, 2023–2025 dari BPS) — https://galura.jabarprov.go.id/dataset/produksi-padi-berdasarkan-kabupatenkota-di-jawa-barat
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 2. Banten (kode 36)
- Padi — **DIEKSTRAK** 2020–2025 (48 baris) — https://banten.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMzNjAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-banten.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 3. DKI Jakarta (kode 31)
- Padi — **DIEKSTRAK** 2020–2025 (36 baris) — https://jakarta.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMzMTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-dki-jakarta.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 4. Jawa Tengah (kode 33)
- Padi — **DIEKSTRAK** 2020–2025 (210 baris) — https://jateng.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMzMzAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-jawa-tengah.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **DIEKSTRAK** — kayu rakyat, hanya tahun 2025 (35 baris, satuan m³, total 612.095 m³) — https://jateng.bps.go.id/id/statistics-table/2/NDQ2NyMy/produksi-kayu-rakyat-menurut-kabupaten-kota-dan-jenis-kayu-di-provinsi-jawa-tengah.html

### 5. DI Yogyakarta (kode 34)
- Padi — **DIEKSTRAK** 2020–2025 (30 baris) — https://yogyakarta.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMzNDAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-di-yogyakarta.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 6. Jawa Timur (kode 35)
- Padi — **DIEKSTRAK** 2020–2025 (228 baris) — https://jatim.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMzNTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-jawa-timur.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — ada tapi data lama (2006–2017), di luar rentang
- Kelapa sawit — **DIEKSTRAK** 2020–2022 (114 baris) tapi isinya "–" (kosong) semua kecuali Pacitan 2020 — https://jatim.bps.go.id/id/statistics-table/1/MjYwMCMx/produksi-perkebunan-kelapa-sawit-dan-kelapa-menurut-kabupaten-kota-dan-jenis-tanaman-di-provinsi-jawa-timur-ton-2021-dan-2022.html
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

---

## SUMATRA (10 provinsi)

### 7. Aceh (kode 11)
- Padi — **DIEKSTRAK** 2020–2023 (92 baris) (dari data.go.id; BPS Aceh memakai pola tabel yang sama) — https://data.go.id/dataset/dataset/produksi-padi-dan-beras-bps
- Jagung — **DIEKSTRAK** dari data.go.id 2020–2023 (92 baris) — https://data.go.id/dataset/dataset/produksi-komoditi-jagung-tanaman-pangan
- Tebu — **DIEKSTRAK** dari data.go.id 2021–2023 (69 baris) — https://data.go.id/dataset/dataset/produksi-komoditi-tebu-perkebunan-rakyat
- Kelapa sawit — **DIEKSTRAK** dari data.go.id 2021–2023 (69 baris) — https://data.go.id/dataset/dataset/produksi-komoditas-kelapa-sawit-perkebunan-rakyat-menurut-kabupaten-kota
- Kayu — kayu bulat per kab/kota hanya 2012–2017, di luar rentang

### 8. Sumatera Utara (kode 12)
- Padi — **DIEKSTRAK** 2020–2025 (198 baris) — https://sumut.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMxMjAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-sumatera-utara.html
- Jagung — tabel BPS WARISAN (berhenti 2018); dataset per-tahun data.go.id 2020–2022 ada tapi file XLSX-nya gagal diunduh (sertifikat/404 di server sumber) — BELUM diekstrak
- Tebu — **DIEKSTRAK** dari tabel statis BPS 2020–2021 (66 baris; yang berproduksi hanya Deli Serdang & Langkat) — https://sumut.bps.go.id/id/statistics-table/2/MjE4IzI=/luas-tanaman-dan-produksi-tebu-tanaman-perkebunan-rakyat-menurut-kabupaten-kota.html
- Kelapa sawit — **DIEKSTRAK** dari tabel statis BPS 2020–2024 (165 baris) — https://sumut.bps.go.id/id/statistics-table/2/MjA0IzI=/luas-tanaman-dan-produksi-kelapa-sawit-tanaman-perkebunan-rakyat-menurut-kabupaten-kota.html
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 9. Sumatera Barat (kode 13)
- Padi — **DIEKSTRAK** 2020–2025 (114 baris) — https://sumbar.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMxMzAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-sumatera-barat.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 10. Riau (kode 14)
- Padi — **DIEKSTRAK** 2020–2025 (72 baris) — https://riau.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMxNDAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-riau.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 11. Kepulauan Riau (kode 21)
- Padi — **DIEKSTRAK** 2020–2025 (42 baris) — https://kepri.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMyMTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-kepulauan-riau.html
- Jagung — tabel BPS ada tapi WARISAN — berhenti 2018, tidak ada 2020–2025
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 12. Jambi (kode 15)
- Padi — **DIEKSTRAK** 2020–2025 (66 baris) — https://jambi.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMxNTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-jambi.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 13. Sumatera Selatan (kode 16)
- Padi — **DIEKSTRAK** 2020–2025 (102 baris) — https://sumsel.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMxNjAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-sumatera-selatan.html
- Jagung — tabel BPS WARISAN (berhenti 2015); dataset data.go.id ada tapi unduhannya gagal (error 500) — BELUM diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 14. Kepulauan Bangka Belitung (kode 19)
- Padi — **DIEKSTRAK** 2020–2025 (42 baris) — https://babel.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMxOTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-kepulauan-bangka-belitung.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — ada tapi hanya 2001–2015, di luar rentang
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 15. Bengkulu (kode 17)
- Padi — **DIEKSTRAK** 2020–2025 (60 baris) — https://bengkulu.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMxNzAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-bengkulu.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA** tabel produksi per kab/kota (yang ada hanya jumlah rumah tangga petani kelapa sawit ST2023)
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 16. Lampung (kode 18)
- Padi — **DIEKSTRAK** 2020–2025 (90 baris) — https://lampung.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyMxODAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-lampung.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

---

## KALIMANTAN (5 provinsi)

### 17. Kalimantan Barat (kode 61)
- Padi — **DIEKSTRAK** 2020–2025 (84 baris) — https://kalbar.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM2MTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-kalimantan-barat.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 18. Kalimantan Tengah (kode 62)
- Padi — **DIEKSTRAK** 2020–2025 (84 baris) — https://kalteng.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM2MjAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-kalimantan-tengah.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 19. Kalimantan Selatan (kode 63)
- Padi — **DIEKSTRAK** 2020–2025 (78 baris) — https://kalsel.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM2MzAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-kalimantan-selatan.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 20. Kalimantan Timur (kode 64)
- Padi — **DIEKSTRAK** 2020–2025 (60 baris) — https://kaltim.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM2NDAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-kalimantan-timur.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — kayu olahan per kab/kota hanya 2015, di luar rentang

### 21. Kalimantan Utara (kode 65)
- Padi — **DIEKSTRAK** 2020–2025 (30 baris) — https://kaltara.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM2NTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-kalimantan-utara.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — hanya 2012, di luar rentang

---

## SULAWESI (6 provinsi)

### 22. Sulawesi Utara (kode 71)
- Padi — **DIEKSTRAK** 2020–2025 (90 baris) — https://sulut.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM3MTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-sulawesi-utara.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 23. Sulawesi Tengah (kode 72)
- Padi — **DIEKSTRAK** 2020–2025 (78 baris) — https://sulteng.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM3MjAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-sulawesi-tengah.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 24. Sulawesi Selatan (kode 73)
- Padi — **DIEKSTRAK** 2020–2025 (144 baris) — https://sulsel.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM3MzAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-sulawesi-selatan.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — hanya 2013, di luar rentang

### 25. Sulawesi Tenggara (kode 74)
- Padi — **DIEKSTRAK** 2020–2025 (102 baris) — https://sultra.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM3NDAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-sulawesi-tenggara.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — hanya 2011–2014, di luar rentang

### 26. Gorontalo (kode 75)
- Padi — **DIEKSTRAK** 2020–2025 (36 baris) — https://gorontalo.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM3NTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-gorontalo.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 27. Sulawesi Barat (kode 76)
- Padi — **DIEKSTRAK** 2020–2025 (36 baris) — https://sulbar.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM3NjAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-sulawesi-barat.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

---

## PAPUA (6 provinsi)

### 28. Papua Barat (kode 91)
- Padi — **DIEKSTRAK** 2020–2025 (42 baris) — https://papuabarat.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM5MTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-papua-barat.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 29. Papua Barat Daya (kode 92)
- Padi — **DIEKSTRAK** 2022–2025 (24 baris) — https://papuabarat.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM5MjAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-papua-barat-daya.html
- Jagung — **TIDAK ADA** tabel sama sekali di BPS
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 30. Papua (kode 94)
- Padi — **DIEKSTRAK** 2020–2025 (54 baris) — https://papua.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM5NDAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-papua.html
- Jagung — tabel BPS "Produksi Jagung dan Kedelai" ada tapi WARISAN — isinya berhenti di 2015, tidak ada data 2020–2025, tidak diekstrak
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 31. Papua Selatan (kode 95)
- Padi — **DIEKSTRAK** 2022–2025 (16 baris) — https://papua.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM5NTAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-papua-selatan.html
- Jagung — **TIDAK ADA** tabel sama sekali di BPS
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 32. Papua Tengah (kode 96)
- Padi — **DIEKSTRAK** 2022–2025 (32 baris) — https://papua.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM5NjAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-papua-tengah.html
- Jagung — **TIDAK ADA** tabel sama sekali di BPS
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)

### 33. Papua Pegunungan (kode 97)
- Padi — **DIEKSTRAK** 2022–2025 (32 baris) — https://papua.bps.go.id/id/statistics-table/3/WmpaNk1YbGFjR0pOUjBKYWFIQlBSU3MwVHpOVWR6MDkjMyM5NzAw/luas-panen-produktivitas-dan-produksi-padi-menurut-kabupaten-kota-di-provinsi-papua-pegunungan.html
- Jagung — **TIDAK ADA** tabel sama sekali di BPS
- Tebu — **TIDAK ADA**
- Kelapa sawit — **TIDAK ADA**
- Kayu — **TIDAK ADA** per kab/kota (BPS umumnya menerbitkan kayu per jenis produksi/KPH, bukan per kab/kota)
