# Memori Proyek: Business Intelligence untuk Pencarian Sumber Energi Alternatif (Biomassa & Waste-to-Energy)

Dokumen ini menyimpan seluruh konteks, keputusan arsitektur, referensi jurnal, dan daftar dataset dari sesi diskusi sebelumnya. Anda dapat mengunggah atau menempelkan isi file ini di awal sesi baru agar pengerjaan proyek langsung berlanjut tanpa mengulang dari awal.

## 1. Konteks Proyek & Keputusan Utama

* **Tema Awal:** Proyek Business Intelligence (BI) bertema *finding alternative/green energy resources* dengan integrasi metode Data Mining, AI, dan Machine Learning.
* **Koreksi Fokus (Penting):** Fokus proyek **bukan** sekadar mengelompokkan atau memetakan lokasi geografis (*site selection* PLTS/angin), melainkan berfokus pada penemuan, identifikasi, dan penyaringan **jenis bahan baku/sumber energi alternatif itu sendiri**.
* **Skenario Terpilih:** **Skenario 1: Sistem Pencarian & Evaluasi Bahan Baku Energi Alternatif dari Biomassa dan Limbah (*Biomass & Waste-to-Energy Feedstock Finder*)**.
* **Masalah Bisnis (*Business Case*):** Indonesia memiliki potensi bioenergi sebesar 56,97 GW dari limbah pertanian, perkebunan (kelapa sawit, tebu, padi, jagung, kayu), dan sampah perkotaan ([Buku Saku Bioenergi Ditjen EBTKE ESDM](https://ebtke.esdm.go.id/api/storage/2025/elibrary/file/xlYZhs1MO6_11022025023103.pdf)). Industri dan pembangkit listrik (seperti program *co-firing* PLTU atau pabrik *biopellet*) kesulitan menentukan jenis limbah atau biomassa yang layak dijadikan bahan bakar alternatif karena variasi nilai kalor (*Higher Heating Value* / HHV), risiko kadar abu (*ash content*) terhadap *boiler*, serta fluktuasi pasokan musiman.
* **Tujuan Sistem:** Membangun sistem pendukung keputusan berbasis data yang menggunakan Machine Learning untuk memprediksi dan menyaring kualitas energi kandidat bahan baku limbah, lalu menggabungkannya dengan data volume pasokan daerah ke dalam *Data Warehouse* dan *Dashboard BI*.

## 2. Referensi Jurnal Ilmiah

### A. Jurnal Utama (Fokus "Finding & Identifying" Sumber Energi Alternatif)

| Judul Jurnal & Tahun | Fokus Penemuan Sumber Energi | Metode AI / Data Mining / BI | Temuan Utama & Relevansi |
| :--- | :--- | :--- | :--- |
| [Valorizing Residue Biomass into Bioenergy: An Explainable Hybrid Machine Learning Framework (2026)](https://www.mdpi.com/2071-1050/18/16/8412) | Menyaring 344 kandidat biomassa dan limbah pertanian bernilai kalor (HHV) tinggi. | *Stacked Hybrid Ensemble* (*Random Forest*, *XGBoost*, *ANN*) + *SHAP* & *LIME* | Memprediksi HHV dari komposisi elemen (C, H, O, N, S) dengan $R^2 = 0,99$ tanpa uji kalorimetri lab mahal. Menjadi acuan utama pemodelan ML di proyek ini. |
| [Comparative Analysis of Machine Learning Methods for Predicting Energy Recovery from Waste (2024)](https://www.mdpi.com/2076-3417/14/7/2997) | Mengidentifikasi potensi limbah padat perkotaan (*Waste-to-Energy*). | *ElasticNet*, *Decision Trees*, *Neural Networks* | Memodelkan besaran energi yang dapat diekstraksi dari karakteristik limbah untuk menilai kelayakan ekonomi dan teknologi konversi. |
| [Integrated Waste-to-Energy Process Optimization for Municipal Solid Waste (2024)](https://www.mdpi.com/1996-1073/17/2/497) | Menemukan kombinasi limbah kertas dan plastik (*co-pyrolysis*) untuk menghasilkan *bio-oil* dan *biochar*. | *Dense Neural Network* (DNN), *C&RT*, *XGBoost*, *SHAP* | Mengidentifikasi efek sinergis campuran limbah padat untuk menemukan komposisi *feedstock* dengan hasil bahan bakar tertinggi. |
| [A Comprehensive Study of Machine Learning for Waste-to-Energy Systems and Green Hydrogen Mixes (2025)](https://www.mdpi.com/2227-9717/13/9/2691) | Menemukan bauran *Green Hydrogen* (20% hingga 80%) dan limbah untuk bahan bakar sintetis. | *SVM*, *Gaussian Process Regression* (GPR), *XGBoost*, *Particle Swarm Optimization* (PSO) | Mengoptimalkan proporsi campuran hidrogen hijau dan limbah untuk skenario produksi bahan bakar rendah emisi. |
| [Identifying Alternative Energy Sources: A Multi-Criteria Intuitionistic Fuzzy Approach to Sustainable Alternatives (2025)](https://www.researchgate.net/publication/395466387_Identifying_alternative_energy_sources_A_multi-criteria_intuitionistic_fuzzy_approach_to_sustainable_alternatives) | Memeringkat jenis sumber energi alternatif (Energi Laut, Panas Bumi, Bioenergi, Surya, Angin). | *Multi-Criteria Decision Making* (MCDM), *Entropy Weighting*, *Intuitionistic Fuzzy VIKOR* | Acuan logika pembobotan multi-kriteria (teknis, ekonomi, sosial) di sisi *backend* BI. |
| [An MCDM-based Optimization Approach for Identifying Efficient Renewable Energy Sources (2026)](https://ada-journal.org/index.php/ada/article/view/27) | Menyaring efisiensi kandidat sumber energi terbarukan di tengah ketidakpastian data. | *Fermatean Fuzzy MCDM* & Optimasi | Membandingkan rasio efisiensi dan keberlanjutan antar-opsi energi hijau. |

### B. Jurnal Pendukung (Arsitektur Kerangka Kerja BI & DSS)

Jurnal berikut diambil dari pencarian awal khusus sebagai referensi perancangan arsitektur *Data Warehouse*, ETL, dan *Dashboard BI* (bukan untuk pendekatan klaster lokasi):

* [A Business Intelligence & Analytics Framework for Clean and Affordable Energy Data Analysis (2021)](https://www.mdpi.com/2071-1050/13/2/638): Acuan perancangan arsitektur BI hulu-ke-hilir menggunakan *Design Science Research* (DSR), ETL, pemodelan data multidimensi (OLAP), dan KPI indikator SDG 7.
* [ENER-BI: Integrating Energy and Spatial Data for Cities' Decarbonisation Planning (2021)](https://www.mdpi.com/2071-1050/13/1/383): Acuan integrasi data energi dan spasial pada Power BI sebagai *Decision Support System*.
* [A Customized Decision Support System for Renewable Energy Application by Housing Association (2019)](https://www.mdpi.com/2071-1050/11/16/4377): Contoh agregasi model energi ke dalam visualisasi interaktif Tableau.

## 3. Daftar Sumber Dataset Publik (Siap Unduh)

| Kategori Data | Sumber Dataset & Tautan | Variabel / Fitur Utama | Peran dalam Proyek |
| :--- | :--- | :--- | :--- |
| Karakteristik Kimia & HHV Biomassa | [Mendeley Data: Biomass Dataset for HHV Prediction (315 Sampel)](https://data.mendeley.com/datasets/5xswr8yp34) | *Proximate Analysis* (Ash, *Volatile Matter*, *Fixed Carbon*), *Ultimate Analysis* (% C, H, O, N, S), kategori bahan baku, dan target **HHV (MJ/kg)**. | Dataset utama pelatihan model regresi ML untuk prediksi nilai kalor bahan baku alternatif. |
| Database Standar Biomassa & Limbah | [Phyllis2 Database for Biomass and Waste (ECN/TNO)](https://knowledge-for-policy.ec.europa.eu/dataset/beo-ecnphyllis_en) | Hampir 3.000 rekaman komposisi biokimia (selulosa, hemiselulosa, lignin), kadar air (*moisture*), logam alkali, LHV/HHV. | Pengayaan tabel dimensi `Dim_Feedstock` dan acuan batas aman teknis *boiler*. |
| Eksperimen Biochar & Pirolisis | [Mendeley Data: Biomass Raw Materials](https://data.mendeley.com/datasets/2xd3tc5dr3) dan [Kaggle Biomass Dataset](https://www.kaggle.com/datasets/narayana2020/biomass) | Komposisi elemen (C, H, O, N), suhu pirolisis (200°C sampai 800°C), persentase *yield biochar*, HHV. | Data tambahan jika ingin memasukkan fitur simulasi konversi termokimia (pirolisis/gasifikasi). |
| Timbulan & Komposisi Sampah Indonesia | [SIPSN KLHK: Komposisi Sampah](https://sampahnasional.kemenlh.go.id/portal-indikatif/data/komposisi-sampah) dan [SIPSN KLHK: Timbulan Sampah](https://sampahnasional.kemenlh.go.id/portal-indikatif/data/timbulan-sampah) | Volume timbulan sampah harian/tahunan per kabupaten/kota di Indonesia dan persentase jenis sampah (sisa makanan, kayu/ranting, kertas, plastik, karet). | Menghitung suplai bahan baku *Waste-to-Energy* (RDF / *Refuse Derived Fuel*) di Indonesia. |
| Parameter Bioenergi & Co-Firing Indonesia | [Buku Saku Bioenergi ESDM](https://ebtke.esdm.go.id/api/storage/2025/elibrary/file/xlYZhs1MO6_11022025023103.pdf) dan [Laporan Co-Firing Biomassa CREA](https://energyandcleanair.org/wp/wp-content/uploads/2025/05/ID-IDN-Biomass-co-firing-in-Indonesia.pdf) | Rasio residu komoditas (sawit, tebu, padi, jagung), kapasitas pembangkit, dan radius pasokan ekonomis (50 sampai 100 km). | Parameter konversi tonase komoditas menjadi estimasi energi listrik (MWh) dan logistik. |

## 4. Rancangan Arsitektur Teknis (*End-to-End Pipeline*)

### Tahap 1: Akuisisi Data & ETL
* **Tools:** Python (Pandas) atau Pentaho Data Integration.
* **Proses:** Ekstraksi data kimia biomassa dari Mendeley/Phyllis2 dan data sampah/komoditas wilayah dari SIPSN KLHK. Normalisasi satuan ke basis kering (*dry basis* wt%), pembersihan duplikasi, dan penerapan *Residue-to-Product Ratio* (RPR) untuk memperoleh tonase bahan baku kering.

### Tahap 2: Pemodelan Machine Learning (Data Mining)
* **Tools:** Scikit-Learn, XGBoost, SHAP.
* **Model 1 (Supervised Regression):** Melatih *Random Forest* dan *XGBoost* dengan input *Proximate* (Ash, VM, FC) dan *Ultimate* (C, H, O, N, S) untuk memprediksi **Higher Heating Value (HHV)** dalam MJ/kg, dilengkapi **SHAP values** untuk interpretabilitas fitur kimia.
* **Model 2 (Unsupervised Clustering):** Menggunakan *K-Means Clustering* untuk mengelompokkan kandidat limbah ke dalam 3 sampai 4 kelas kelayakan (*Grade A: High Calorie - Low Ash*, *Grade B: Medium Calorie - High Moisture*, *Grade C: Slagging Risk / High Ash-Sulfur*).

### Tahap 3: Data Warehouse (*Star Schema*)
* **Tools:** PostgreSQL, Google BigQuery, atau SQL Server.
* **Tabel Fakta (`Fact_Feedstock_Potential`):** Menyimpan metrik kuantitatif `Estimated_Supply_Tons`, `Predicted_HHV_MJ_kg`, `Total_Energy_Potential_GJ`, `Ash_Content_Pct`, `Estimated_Generation_MWh`, dan `CO2_Offset_Tons`.
* **Tabel Dimensi:**
  * `Dim_Feedstock`: ID bahan baku, nama limbah, kategori taksonomi TNO, dan *grade* hasil klasterisasi.
  * `Dim_Location`: Provinsi, kabupaten/kota, dan koordinat.
  * `Dim_Conversion_Tech`: Jenis teknologi konversi (pirolisis, gasifikasi, *co-firing* PCC/FBC, insinerasi RDF).
  * `Dim_Time`: Tahun dan kuartal/musim panen.

### Tahap 4: Dashboard BI & Simulasi *What-If*
* **Tools:** Power BI, Tableau, atau Looker Studio.
* **Halaman 1 (`Feedstock Discovery & Screening Matrix`):** *Scatter plot* interaktif `Predicted HHV (MJ/kg)` vs `Ash & Sulfur Content (%)` untuk menyaring kandidat bahan baku paling bersih dan berenergi tinggi.
* **Halaman 2 (`Regional Supply & Resource Mapping`):** Peta sebaran ketersediaan tonase limbah pertanian dan sampah perkotaan per wilayah beserta potensi daya listriknya (MW).
* **Halaman 3 (`Co-Firing & Substitution Simulator`):** Simulasi *What-If Parameter* untuk menguji skenario substitusi batu bara (misalnya 5%, 10%, 20% menggunakan cangkang sawit/RDF) terhadap penghematan batu bara dan penurunan emisi karbon.

## 5. Daftar KPI Utama Dashboard BI

* **Feedstock Energy Density Index (MJ/kg):** Rata-rata nilai kalor tertimbang kandidat bahan baku alternatif dibandingkan acuan batu bara kalori rendah/menengah (~18 sampai 22 MJ/kg).
* **Technical Suitability Score (%):** Persentase jenis limbah di suatu wilayah yang lolos batas aman *boiler* (kadar abu di bawah 10% dan sulfur di bawah 0,5%).
* **Convertible Bioenergy Capacity (GWh / MW):** Estimasi total energi listrik dari residu biomassa/sampah terkelola dengan efisiensi pembangkit sekitar 25,45% untuk gasifikasi biomassa ([studi tekno-ekonomi KTH 2026](https://kth.diva-portal.org/smash/get/diva2:2117730/FULLTEXT01.pdf)).
* **Coal Substitution & Carbon Offset Potential (Ton CO2e):** Estimasi tonase batu bara yang tergantikan dan reduksi emisi gas rumah kaca per tahun.

## 6. Status Terakhir & Pilihan Langkah Selanjutnya

Rancangan konseptual, referensi literatur, dan sumber dataset sudah selesai disusun. Belum ada kode Python, skrip SQL, maupun file *dashboard* yang dibuat. Pada sesi berikutnya, Anda dapat langsung memilih salah satu langkah eksekusi berikut:

1. **Pembuatan Script Python (ETL & ML):** Menyusun kode pembersihan data biomassa, pelatihan model regresi prediksi HHV (*XGBoost* / *Random Forest* + *SHAP*), dan klasterisasi *K-Means* hingga menghasilkan tabel siap muat ke *Data Warehouse*.
2. **Perancangan Skrip SQL (DDL & OLAP):** Membuat skrip pembuatan tabel *Star Schema* (`Fact_Feedstock_Potential` beserta seluruh tabel dimensi) dan contoh *query* agregasi OLAP.
3. **Wireframe & Rumus DAX Power BI:** Merancang tata letak visual untuk 3 halaman *dashboard* beserta rumus DAX untuk menghitung 4 KPI utama dan parameter simulasi *co-firing*.
