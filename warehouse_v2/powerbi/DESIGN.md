# Spesifikasi desain Power BI: Tema terang editorial energi

Dokumen ini menetapkan token warna, tipografi, aturan tata letak, dan hasil audit kontras WCAG 2.1 untuk dashboard Power BI ProjectKB pada [theme_biomass_bi.json](file:///d:/UPN%20VY/Semester%205/BI/Tugas/projectkb/warehouse_v2/powerbi/theme_biomass_bi.json).

## Palet warna dan peran semantik

| Peran visual | Kode hex | Penggunaan di Power BI |
| --- | --- | --- |
| Latar kanvas halaman | `#F7F6F2` | Latar belakang 16:9 seluruh halaman (linen terang hangat) |
| Permukaan kartu visual | `#FFFFFF` | Latar kartu KPI, grafik, slicer, dan tabel |
| Latar header dan baris bantu | `#EFECE4` | Header tabel, pita catatan dinamis, panel navigasi |
| Garis batas lembut | `#D5D0C5` | Border kartu 1 px dengan sudut 6 px |
| Garis batas kontrol interaktif | `#6E767E` | Border slicer, slider, dan tombol fokus (>= 3:1) |
| Teks utama | `#1C252C` | Judul halaman, angka KPI, teks isi tabel |
| Teks sekunder | `#47535E` | Subjudul grafik, label sumbu, catatan kaki |
| Data 1: Suplai layak bakar | `#1B5E42` | Batang suplai biomassa layak, status Eligible, tombol tab aktif |
| Data 2: Target PLTU dan ambang | `#B45309` | Target co-firing PLTU, penanda kadar air >= 50%, garis putus historis |
| Data 3: Realisasi aktual CREA | `#0E646E` | Realisasi co-firing CREA 2024, residu kayu KLHK |
| Data 4: Peringatan dan defisit | `#B42318` | Status Not Eligible (FS04/FS05), batas Ash > 10%, defisit simulator |
| Data 5: Seri tanaman pendukung | `#2F5577` | Seri pembanding tanaman dan peta regional |

## Tipografi dan tata letak kanvas

Ukuran kanvas seluruh halaman adalah `1280 x 720` piksel (rasio 16:9). Judul visual memakai `Segoe UI Semibold` 12 pt, nilai KPI memakai `DIN` 24 pt, label sumbu dan sel tabel memakai `Segoe UI` 9 sampai 10 pt. Setiap halaman memiliki satu grafik fokal utama yang menempati minimal 40% area kerja, panel navigasi kiri selebar `158` piksel, dan jarak antar kartu `12` sampai `14` piksel tanpa bayangan berat.

## Aturan aksesibilitas visual

Setiap sinyal warna wajib dipasangkan dengan teks atau bentuk agar tetap terbaca pada tampilan monokrom atau oleh pembaca buta warna: status `Not Eligible` selalu ditulis eksplisit bersama angka kadar abu, zona defisit memakai pola garis putus dan label angka negatif, dan titik PLTU memakai bentuk belah ketupat untuk membedakannya dari lingkaran potensi provinsi.

## Audit kontras WCAG 2.1

| Pasangan elemen | Warna teks/elemen | Warna latar | Rasio terukur | Ambang minimum | Hasil |
| --- | --- | --- | --- | --- | --- |
| Primary ink on card white | `#1C252C` | `#FFFFFF` | 15.55:1 | >= 4.5:1 | PASS |
| Primary ink on page linen | `#1C252C` | `#F7F6F2` | 14.38:1 | >= 4.5:1 | PASS |
| Primary ink on surface alt | `#1C252C` | `#EFECE4` | 13.17:1 | >= 4.5:1 | PASS |
| Secondary ink on card white | `#47535E` | `#FFFFFF` | 7.87:1 | >= 4.5:1 | PASS |
| Secondary ink on page linen | `#47535E` | `#F7F6F2` | 7.28:1 | >= 4.5:1 | PASS |
| Forest green text on card white | `#1B5E42` | `#FFFFFF` | 7.70:1 | >= 4.5:1 | PASS |
| Forest green text on forest tint | `#1B5E42` | `#E7F2EC` | 6.72:1 | >= 4.5:1 | PASS |
| White text on forest green | `#FFFFFF` | `#1B5E42` | 7.70:1 | >= 4.5:1 | PASS |
| Amber text on card white | `#9A4409` | `#FFFFFF` | 6.55:1 | >= 4.5:1 | PASS |
| Amber text on amber tint | `#9A4409` | `#FDF1DC` | 5.86:1 | >= 4.5:1 | PASS |
| Teal text on card white | `#0E646E` | `#FFFFFF` | 6.85:1 | >= 4.5:1 | PASS |
| Teal text on teal tint | `#0E646E` | `#E4F2F4` | 5.97:1 | >= 4.5:1 | PASS |
| Crimson text on card white | `#B42318` | `#FFFFFF` | 6.57:1 | >= 4.5:1 | PASS |
| Crimson text on crimson tint | `#B42318` | `#FCEAE8` | 5.66:1 | >= 4.5:1 | PASS |
| White text on crimson alert | `#FFFFFF` | `#B42318` | 6.57:1 | >= 4.5:1 | PASS |
| UI control border on card white | `#6E767E` | `#FFFFFF` | 4.61:1 | >= 3.0:1 | PASS |
| UI control border on page linen | `#6E767E` | `#F7F6F2` | 4.26:1 | >= 3.0:1 | PASS |
| Amber bar on card white | `#B45309` | `#FFFFFF` | 5.02:1 | >= 3.0:1 | PASS |
| Slate blue bar on card white | `#2F5577` | `#FFFFFF` | 7.82:1 | >= 3.0:1 | PASS |
| Olive bar on card white | `#4C6B2A` | `#FFFFFF` | 6.10:1 | >= 3.0:1 | PASS |
