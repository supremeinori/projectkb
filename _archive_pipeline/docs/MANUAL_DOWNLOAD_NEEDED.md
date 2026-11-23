# Petunjuk Tindakan Tambahan (Opsional)

Status saat ini: **Seluruh dataset inti telah berhasil diunduh dan diproses 100% secara otomatis.**
Tidak ada dataset yang gagal terunduh atau terblokir.

---

### Ekstensi Tambahan: Data Pertanian BPS Tingkat Kabupaten/Kota (Opsional)
Dataset `bps_agriculture_clean.csv` saat ini telah mencakup seluruh 38–39 Provinsi di Indonesia.
Jika Anda ingin memperluas dataset BPS hingga ke tingkat Kabupaten/Kota untuk provinsi sentra (misal Riau, Sumut, Jatim, Jateng, Jabar):

1. Buka situs pendaftaran resmi BPS: [https://webapi.bps.go.id/](https://webapi.bps.go.id/)
2. Daftarkan akun gratis (biasanya API Key langsung aktif dalam hitungan menit).
3. Buat file `.env` di dalam folder proyek ini atau di root:
   ```env
   BPS_API_KEY=masukkan_api_key_anda_di_sini
   ```
4. Jalankan ulang:
   ```bash
   python biomass-feedstock-finder/scripts/03_fetch_bps_agriculture.py
   ```
   Skrip secara otomatis akan mendeteksi `BPS_API_KEY` dan memicu penarikan data tingkat Kabupaten/Kota.
