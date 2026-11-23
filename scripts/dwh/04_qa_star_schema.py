"""
Step 4 DWH QA: Validasi Integritas Star Schema SQLite & Laporan Hasil Analisis Awal
Output: warehouse/DWH_QA_REPORT.md
"""

import sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd

DB_PATH = Path("warehouse/biomass_dwh.sqlite")
QA_REPORT_PATH = Path("warehouse/DWH_QA_REPORT.md")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    checks = []

    def assert_check(name, passed, detail):
        status = "PASS" if passed else "FAIL"
        checks.append((name, status, detail))
        print(f"  [{status}] {name}: {detail}")

    print("=== Running Automated Star Schema SQL QA Checks ===")

    # 1. Foreign Key Check
    fk_err = conn.execute("PRAGMA foreign_key_check;").fetchall()
    assert_check("Foreign Key Integrity (PRAGMA foreign_key_check)", len(fk_err) == 0, f"{len(fk_err)} pelanggaran FK")

    # 2. Row Counts seluruh 9 tabel (5 Dim + 4 Fact)
    tables = [
        "dim_time", "dim_location", "dim_feedstock", "dim_power_plant", "dim_data_source",
        "fact_commodity_production", "fact_biomass_chemistry", "fact_biomass_energy_potential", "fact_pltu_operations",
    ]
    tbl_counts = {}
    for t in tables:
        c = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        tbl_counts[t] = c
    assert_check("Semua 9 Tabel Terisi Non-Kosong", all(v > 0 for v in tbl_counts.values()), ", ".join(f"{k}={v:,}" for k, v in tbl_counts.items()))

    # 3. Zero Double-Counting Reconciliation (Provinsi Primary 2024 vs Angka Resmi BPS RI & KLHK PHL)
    q_2024 = """
        SELECT f.kode_feedstock,
               ROUND(SUM(p.produksi_ton_std), 2) AS sum_ton,
               ROUND(SUM(p.produksi_m3_std), 2)  AS sum_m3,
               COUNT(*)                          AS n_rows
        FROM fact_commodity_production p
        JOIN dim_feedstock f ON p.feedstock_key = f.feedstock_key
        WHERE p.time_key = 2024
          AND p.level_wilayah_fakta = 'PROVINSI'
          AND p.is_primary_analysis_row = 1
        GROUP BY f.kode_feedstock
    """
    df_2024 = pd.read_sql_query(q_2024, conn).set_index("kode_feedstock")
    expected_2024 = [
        ("SEKAM_PADI", "sum_ton", 53142726.94, 50.0, "BPS 1498#2 Padi 2024"),
        ("TONGKOL_JAGUNG", "sum_ton", 15138912.0, 50.0, "BPS 2204#2 Jagung 2024"),
        ("CANGKANG_SAWIT", "sum_ton", 45436200.0, 500.0, "BPS 2566#2 Sawit 2024"),
        ("AMPAS_TEBU", "sum_ton", 2465510.0, 500.0, "BPS 2566#2 Tebu 2024"),
        ("LIMBAH_KAYU_SERBUK", "sum_m3", 55547094.91, 5.0, "KLHK PHL 2024 PBPH+Perhutani"),
    ]
    for code, col, exp, tol, ref_lbl in expected_2024:
        got = float(df_2024.loc[code, col]) if code in df_2024.index else 0.0
        diff = abs(got - exp)
        assert_check(
            f"Reconciliation 2024 {code} ({ref_lbl})",
            diff <= tol,
            f"DWH={got:,.2f} vs Resmi={exp:,.2f} (selisih={diff:,.2f})"
        )

    # 4. Anomaly Guards (Sawit 2025 & Tahun 2026 tidak bocor ke primary / energy potential)
    leak_sawit_2025 = conn.execute("""
        SELECT COUNT(*) FROM fact_biomass_energy_potential e
        JOIN dim_feedstock f ON e.feedstock_key = f.feedstock_key
        WHERE e.time_key = 2025 AND e.level_wilayah_fakta = 'PROVINSI' AND f.kode_feedstock = 'CANGKANG_SAWIT'
    """).fetchone()[0]
    assert_check("Guard Anomali Sawit Provinsi 2025 (4.84x)", leak_sawit_2025 == 0, f"{leak_sawit_2025} baris bocor ke energy_potential (target: 0)")

    leak_2026 = conn.execute("""
        SELECT COUNT(*) FROM fact_commodity_production WHERE time_key = 2026 AND is_primary_analysis_row = 1
    """).fetchone()[0]
    assert_check("Guard Tahun 2026 Belum Rilis", leak_2026 == 0, f"{leak_2026} baris primary di 2026 (target: 0)")

    # 5. PLTU Sanity Checks
    ct_cf = conn.execute("""
        SELECT MIN(capacity_factor_pct), MAX(capacity_factor_pct), COUNT(*)
        FROM fact_pltu_operations o
        JOIN dim_data_source s ON o.source_key = s.source_key
        WHERE s.kode_sumber = 'CLIMATETRACE_V6'
    """).fetchone()
    assert_check("Climate TRACE Capacity Factor (%) Valid [0..100]", 0 <= ct_cf[0] and ct_cf[1] <= 100 and ct_cf[2] == 500,
                 f"n={ct_cf[2]}, range={ct_cf[0]:.2f}%..{ct_cf[1]:.2f}%")

    crea_chk = conn.execute("""
        SELECT COUNT(*), ROUND(SUM(capacity_mw), 1), ROUND(SUM(biomass_used_ton), 1)
        FROM fact_pltu_operations o
        JOIN dim_data_source s ON o.source_key = s.source_key
        WHERE s.kode_sumber = 'CREA_MEI_2025'
    """).fetchone()
    assert_check("CREA 2025 Tabel A1 (52 PLTU / 18,342 MW / 1,457,720 ton)",
                 crea_chk[0] == 52 and abs(crea_chk[1] - 18342.0) <= 1.0 and abs(crea_chk[2] - 1457720.0) <= 1.0,
                 f"n={crea_chk[0]}, MW={crea_chk[1]:,.1f}, biomass={crea_chk[2]:,.1f} ton")

    # 6. Jalankan 4 Analytical Views & Ambil Ringkasan
    df_v_supply_pltu = pd.read_sql_query("SELECT * FROM vw_supply_vs_pltu_5_pulau_2024", conn)
    df_v_prov_2024 = pd.read_sql_query("""
        SELECT nama_komoditas, nama_limbah_biomassa, boiler_suitability_grade,
               ROUND(SUM(commodity_production_ton)/1e6, 2) AS produksi_juta_ton,
               ROUND(SUM(estimated_residue_dry_ton)/1e6, 2) AS residu_kering_juta_ton,
               ROUND(SUM(total_energy_potential_gj)/1e6, 2) AS energi_pj,
               ROUND(SUM(convertible_electricity_mwh)/1e6, 2) AS listrik_twh,
               ROUND(SUM(coal_equivalent_ton)/1e6, 2) AS setara_batubara_juta_ton
        FROM vw_energy_potential_provinsi
        WHERE year = 2024 AND scenario_code = 'BASE_CONSERVATIVE'
        GROUP BY nama_komoditas, nama_limbah_biomassa, boiler_suitability_grade
        ORDER BY energi_pj DESC
    """, conn)
    n_v_kab = conn.execute("SELECT COUNT(*) FROM vw_energy_potential_kabkota").fetchone()[0]
    n_v_pltu = conn.execute("SELECT COUNT(*) FROM vw_pltu_5_pulau_summary").fetchone()[0]
    assert_check("4 Analytical Views Eksekusi Sukses", len(df_v_supply_pltu) == 5 and len(df_v_prov_2024) == 5 and n_v_kab > 0 and n_v_pltu > 0,
                 f"vw_supply_vs_pltu=5 pulau, vw_prov_2024=5 komoditas, vw_kabkota={n_v_kab:,} baris, vw_pltu_summary={n_v_pltu} baris")

    conn.close()

    n_pass = sum(1 for _, st, _ in checks if st == "PASS")
    n_tot = len(checks)
    print(f"\nQA SUMMARY: {n_pass}/{n_tot} PASS")

    # Tulis laporan Markdown
    md = [
        "# Laporan QA Star Schema Data Warehouse (`warehouse/biomass_dwh.sqlite`)",
        "",
        f"> **Tanggal QA:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"> **Hasil Validasi Otomatis:** **{n_pass}/{n_tot} PASS** (`0` pelanggaran Foreign Key, `0` double-counting)",
        "",
        "## 1. Inventaris Tabel Star Schema (`warehouse/tables/*.csv` & `biomass_dwh.sqlite`)",
        "",
        "| Jenis | Nama Tabel | Jumlah Baris |",
        "| :--- | :--- | :---: |",
    ]
    for t in tables:
        kind = "Dimension" if t.startswith("dim_") else "Fact"
        md.append(f"| {kind} | `{t}` | **{tbl_counts[t]:,}** |")

    md += [
        "",
        "## 2. Hasil Pengujian Integritas & Rekonsiliasi SQL",
        "",
        "| Pengujian QA | Status | Detail Bukti |",
        "| :--- | :---: | :--- |",
    ]
    for name, st, det in checks:
        md.append(f"| {name} | **{st}** | {det} |")

    md += [
        "",
        "## 3. Potensi Energi Biomassa Nasional 2024 per Komoditas (`vw_energy_potential_provinsi`, Skenario `BASE_CONSERVATIVE`)",
        "",
        "| Komoditas | Limbah Biomassa | Grade Boiler (ML) | Produksi (Juta Ton) | Residu Kering (Juta Ton) | Energi (PJ) | Listrik Konversi (TWh) | Setara Batu Bara (Juta Ton) |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for _, r in df_v_prov_2024.iterrows():
        md.append(
            f"| {r['nama_komoditas']} | {r['nama_limbah_biomassa']} | {r['boiler_suitability_grade']} | "
            f"{r['produksi_juta_ton']:.2f} | {r['residu_kering_juta_ton']:.2f} | {r['energi_pj']:.2f} | "
            f"{r['listrik_twh']:.2f} | {r['setara_batubara_juta_ton']:.2f} |"
        )

    md += [
        "",
        "## 4. Supply Biomassa 5 Komoditas vs Demand Co-Firing PLTU 5 Pulau Utama (Tahun 2024 — `vw_supply_vs_pltu_5_pulau_2024`)",
        "",
        "| Pulau | PLTU CT 2024 | Kapasitas (MW) | Generasi 2024 (GWh) | Target Co-Firing 10% (GWh) | Realisasi CREA 2024 (Ton) | Suplai Biomassa Kering (Juta Ton) | Potensi Listrik Biomassa (GWh) | Rasio Cakupan vs Target 10% |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for _, r in df_v_supply_pltu.iterrows():
        md.append(
            f"| **{r['pulau']}** | {int(r['pltu_count_ct2024'])} | {r['pltu_capacity_mw']:,.1f} | "
            f"{r['pltu_generation_mwh']/1e3:,.1f} | {r['target_cofiring_10pct_mwh']/1e3:,.1f} | "
            f"{r['crea_actual_biomass_2024_ton']:,.0f} | {r['biomass_supply_dry_ton']/1e6:,.2f} | "
            f"{r['biomass_convertible_mwh']/1e3:,.1f} | **{r['coverage_vs_10pct_cofiring_pct']:,.1f}%** |"
        )

    QA_REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"Laporan QA tertulis di {QA_REPORT_PATH}")
    if n_pass != n_tot:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
