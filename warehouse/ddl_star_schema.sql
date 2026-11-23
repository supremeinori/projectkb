-- =============================================================================
-- STAR SCHEMA DATA WAREHOUSE DDL (PROJECTKB - Biomass & PLTU Co-Firing BI)
-- Kompatibel: SQLite 3 (native), DuckDB, dan portabel ke PostgreSQL
-- Prinsip: Kimball Multi-Fact Star Schema (5 Conformed Dimensions + 4 Fact Tables)
--          Zero Double-Counting | Multi-Grain Safe | Strict As-Is Audit Flags
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- 1. CONFORMED DIMENSIONS
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_time (
    time_key                INTEGER PRIMARY KEY,
    year                    INTEGER NOT NULL UNIQUE,
    decade                  INTEGER NOT NULL,
    is_post_papua_split     INTEGER NOT NULL CHECK (is_post_papua_split IN (0, 1)),
    is_bps_ksa_era          INTEGER NOT NULL CHECK (is_bps_ksa_era IN (0, 1))
);

CREATE TABLE IF NOT EXISTS dim_location (
    location_key            INTEGER PRIMARY KEY,
    location_code           TEXT NOT NULL UNIQUE,
    level_wilayah           TEXT NOT NULL CHECK (level_wilayah IN ('NASIONAL', 'PULAU', 'PROVINSI', 'KABKOTA')),
    kode_bps_prov           TEXT,
    nama_provinsi           TEXT,
    kode_bps_kabkota        TEXT,
    nama_kabkota            TEXT,
    pulau                   TEXT NOT NULL,
    masuk_5_pulau_pltu      INTEGER NOT NULL CHECK (masuk_5_pulau_pltu IN (0, 1)),
    wilayah_pln             TEXT,
    latitude_centroid       REAL,
    longitude_centroid      REAL
);

CREATE TABLE IF NOT EXISTS dim_feedstock (
    feedstock_key           INTEGER PRIMARY KEY,
    kode_komoditas          TEXT NOT NULL,
    nama_komoditas          TEXT NOT NULL,
    subsektor               TEXT NOT NULL,
    kode_feedstock          TEXT NOT NULL UNIQUE,
    nama_limbah_biomassa    TEXT NOT NULL,
    phyllis_category        TEXT,
    rpr_ratio_default       REAL,
    wood_density_ton_per_m3 REAL,
    moisture_pct_default    REAL,
    avg_hhv_mj_kg           REAL,
    ml_predicted_hhv_mj_kg  REAL,
    avg_ash_pct_db          REAL,
    avg_sulfur_pct_db       REAL,
    boiler_suitability_grade TEXT,
    slagging_risk_level     TEXT,
    rpr_reference_note      TEXT
);

CREATE TABLE IF NOT EXISTS dim_power_plant (
    pltu_key                INTEGER PRIMARY KEY,
    pltu_master_id          TEXT NOT NULL UNIQUE,
    nama_pltu_standar       TEXT NOT NULL,
    nama_climatetrace       TEXT,
    nama_wri_gppd           TEXT,
    nama_crea_2025          TEXT,
    owner_operator          TEXT,
    jenis_boiler            TEXT,
    status_cofiring_2024    TEXT,
    commissioning_year      INTEGER,
    latitude                REAL,
    longitude               REAL,
    pulau                   TEXT NOT NULL,
    masuk_5_pulau_pltu      INTEGER NOT NULL CHECK (masuk_5_pulau_pltu IN (0, 1)),
    wilayah_pln             TEXT,
    entity_match_method     TEXT
);

CREATE TABLE IF NOT EXISTS dim_data_source (
    source_key               INTEGER PRIMARY KEY,
    kode_sumber              TEXT NOT NULL UNIQUE,
    nama_instansi            TEXT NOT NULL,
    nama_dataset             TEXT NOT NULL,
    level_granularity_asli   TEXT NOT NULL,
    ownership_coverage_scope TEXT NOT NULL,
    satuan_asli              TEXT NOT NULL,
    url_sumber               TEXT NOT NULL
);

-- -----------------------------------------------------------------------------
-- 2. FACT TABLES
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fact_commodity_production (
    prod_fact_id               INTEGER PRIMARY KEY,
    time_key                   INTEGER NOT NULL,
    location_key               INTEGER NOT NULL,
    feedstock_key              INTEGER NOT NULL,
    source_key                 INTEGER NOT NULL,
    level_wilayah_fakta        TEXT NOT NULL CHECK (level_wilayah_fakta IN ('NASIONAL', 'PULAU', 'PROVINSI', 'KABKOTA')),
    produksi_nilai_asli        REAL,
    satuan_asli                TEXT NOT NULL,
    produksi_ton_std           REAL,
    produksi_m3_std            REAL,
    luas_panen_atau_tanam_ha   REAL,
    produktivitas_nilai        REAL,
    basis_pelaporan            TEXT NOT NULL,
    is_primary_analysis_row    INTEGER NOT NULL CHECK (is_primary_analysis_row IN (0, 1)),
    quality_flag               TEXT NOT NULL,
    FOREIGN KEY (time_key)      REFERENCES dim_time(time_key),
    FOREIGN KEY (location_key)  REFERENCES dim_location(location_key),
    FOREIGN KEY (feedstock_key) REFERENCES dim_feedstock(feedstock_key),
    FOREIGN KEY (source_key)    REFERENCES dim_data_source(source_key)
);

CREATE TABLE IF NOT EXISTS fact_biomass_chemistry (
    chem_fact_id               INTEGER PRIMARY KEY,
    feedstock_key              INTEGER NOT NULL,
    source_key                 INTEGER NOT NULL,
    sample_id                  TEXT NOT NULL UNIQUE,
    material_name_raw          TEXT NOT NULL,
    ash_pct_db                 REAL,
    vm_pct_db                  REAL,
    fc_pct_db                  REAL,
    c_pct_db                   REAL,
    h_pct_db                   REAL,
    o_pct_db                   REAL,
    n_pct_db                   REAL,
    s_pct_db                   REAL,
    hhv_actual_mj_kg           REAL,
    hhv_ml_predicted_mj_kg     REAL,
    hhv_model_used             TEXT,
    ml_cluster_grade           TEXT,
    pass_boiler_ash_limit      INTEGER CHECK (pass_boiler_ash_limit IN (0, 1)),
    pass_boiler_sulfur_limit   INTEGER CHECK (pass_boiler_sulfur_limit IN (0, 1)),
    FOREIGN KEY (feedstock_key) REFERENCES dim_feedstock(feedstock_key),
    FOREIGN KEY (source_key)    REFERENCES dim_data_source(source_key)
);

CREATE TABLE IF NOT EXISTS fact_biomass_energy_potential (
    energy_fact_id              INTEGER PRIMARY KEY,
    time_key                    INTEGER NOT NULL,
    location_key                INTEGER NOT NULL,
    feedstock_key               INTEGER NOT NULL,
    source_key                  INTEGER NOT NULL,
    level_wilayah_fakta         TEXT NOT NULL CHECK (level_wilayah_fakta IN ('PROVINSI', 'KABKOTA')),
    scenario_code               TEXT NOT NULL,
    commodity_production_ton    REAL,
    rpr_ratio_used              REAL,
    estimated_residue_wet_ton   REAL,
    estimated_residue_dry_ton   REAL,
    hhv_used_mj_kg              REAL,
    total_energy_potential_gj   REAL,
    convertible_electricity_mwh REAL,
    coal_equivalent_ton         REAL,
    estimated_co2_offset_ton    REAL,
    ash_load_ton                REAL,
    FOREIGN KEY (time_key)      REFERENCES dim_time(time_key),
    FOREIGN KEY (location_key)  REFERENCES dim_location(location_key),
    FOREIGN KEY (feedstock_key) REFERENCES dim_feedstock(feedstock_key),
    FOREIGN KEY (source_key)    REFERENCES dim_data_source(source_key)
);

CREATE TABLE IF NOT EXISTS fact_pltu_operations (
    pltu_fact_id                INTEGER PRIMARY KEY,
    time_key                    INTEGER NOT NULL,
    location_key                INTEGER NOT NULL,
    pltu_key                    INTEGER NOT NULL,
    feedstock_key               INTEGER NOT NULL,
    source_key                  INTEGER NOT NULL,
    capacity_mw                 REAL,
    jumlah_unit                 INTEGER,
    activity_generation_mwh     REAL,
    capacity_factor_pct         REAL,
    emissions_co2e_ton          REAL,
    emissions_factor_t_per_mwh  REAL,
    cofiring_share_pct          REAL,
    biomass_used_ton            REAL,
    biomass_electricity_mwh     REAL,
    biomass_emissions_tco2      REAL,
    is_primary_analysis_row     INTEGER NOT NULL CHECK (is_primary_analysis_row IN (0, 1)),
    FOREIGN KEY (time_key)      REFERENCES dim_time(time_key),
    FOREIGN KEY (location_key)  REFERENCES dim_location(location_key),
    FOREIGN KEY (pltu_key)      REFERENCES dim_power_plant(pltu_key),
    FOREIGN KEY (feedstock_key) REFERENCES dim_feedstock(feedstock_key),
    FOREIGN KEY (source_key)    REFERENCES dim_data_source(source_key)
);

-- -----------------------------------------------------------------------------
-- 3. INDEXES FOR FAST OLAP / POWER BI QUERIES
-- -----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_fprod_keys   ON fact_commodity_production (time_key, location_key, feedstock_key, source_key);
CREATE INDEX IF NOT EXISTS idx_fprod_prim   ON fact_commodity_production (is_primary_analysis_row, level_wilayah_fakta);
CREATE INDEX IF NOT EXISTS idx_fchem_fk     ON fact_biomass_chemistry (feedstock_key, ml_cluster_grade);
CREATE INDEX IF NOT EXISTS idx_fener_keys   ON fact_biomass_energy_potential (time_key, location_key, feedstock_key, level_wilayah_fakta);
CREATE INDEX IF NOT EXISTS idx_fpltu_keys   ON fact_pltu_operations (time_key, pltu_key, source_key, is_primary_analysis_row);

-- -----------------------------------------------------------------------------
-- 4. ANALYTICAL VIEWS (READY FOR SQL / POWER BI)
-- -----------------------------------------------------------------------------

-- View 1: Potensi Energi Biomassa Level Provinsi (5 Komoditas Lengkap, All-Ownership, Bebas Anomali 2025)
CREATE VIEW IF NOT EXISTS vw_energy_potential_provinsi AS
SELECT
    t.year,
    l.pulau,
    l.masuk_5_pulau_pltu,
    l.kode_bps_prov,
    l.nama_provinsi,
    f.nama_komoditas,
    f.nama_limbah_biomassa,
    f.boiler_suitability_grade,
    s.kode_sumber,
    s.ownership_coverage_scope,
    e.scenario_code,
    e.commodity_production_ton,
    e.estimated_residue_dry_ton,
    e.hhv_used_mj_kg,
    e.total_energy_potential_gj,
    e.convertible_electricity_mwh,
    e.coal_equivalent_ton,
    e.estimated_co2_offset_ton,
    e.ash_load_ton
FROM fact_biomass_energy_potential e
JOIN dim_time t         ON e.time_key = t.time_key
JOIN dim_location l     ON e.location_key = l.location_key
JOIN dim_feedstock f    ON e.feedstock_key = f.feedstock_key
JOIN dim_data_source s  ON e.source_key = s.source_key
WHERE e.level_wilayah_fakta = 'PROVINSI';

-- View 2: Potensi Energi Biomassa Level Kab/Kota (Komoditas yang Tersedia di Daerah)
CREATE VIEW IF NOT EXISTS vw_energy_potential_kabkota AS
SELECT
    t.year,
    l.pulau,
    l.masuk_5_pulau_pltu,
    l.kode_bps_prov,
    l.nama_provinsi,
    l.kode_bps_kabkota,
    l.nama_kabkota,
    f.nama_komoditas,
    f.nama_limbah_biomassa,
    f.boiler_suitability_grade,
    s.kode_sumber,
    s.ownership_coverage_scope,
    e.scenario_code,
    e.commodity_production_ton,
    e.estimated_residue_dry_ton,
    e.hhv_used_mj_kg,
    e.total_energy_potential_gj,
    e.convertible_electricity_mwh,
    e.coal_equivalent_ton
FROM fact_biomass_energy_potential e
JOIN dim_time t         ON e.time_key = t.time_key
JOIN dim_location l     ON e.location_key = l.location_key
JOIN dim_feedstock f    ON e.feedstock_key = f.feedstock_key
JOIN dim_data_source s  ON e.source_key = s.source_key
WHERE e.level_wilayah_fakta = 'KABKOTA';

-- View 3: Ringkasan Operasi PLTU 5 Pulau (Primary Climate TRACE per Tahun + CREA Co-Firing 2024)
CREATE VIEW IF NOT EXISTS vw_pltu_5_pulau_summary AS
SELECT
    t.year,
    p.pulau,
    s.kode_sumber,
    COUNT(DISTINCT p.pltu_key)                        AS jumlah_pltu,
    ROUND(SUM(o.capacity_mw), 2)                      AS total_capacity_mw,
    ROUND(SUM(o.activity_generation_mwh), 2)          AS total_generation_mwh,
    ROUND(AVG(o.capacity_factor_pct), 2)              AS avg_capacity_factor_pct,
    ROUND(SUM(o.emissions_co2e_ton), 2)               AS total_emissions_co2e_ton,
    ROUND(SUM(o.biomass_used_ton), 2)                 AS total_biomass_used_2024_ton,
    ROUND(SUM(o.biomass_electricity_mwh), 2)          AS total_biomass_elec_2024_mwh
FROM fact_pltu_operations o
JOIN dim_time t         ON o.time_key = t.time_key
JOIN dim_power_plant p  ON o.pltu_key = p.pltu_key
JOIN dim_data_source s  ON o.source_key = s.source_key
WHERE p.masuk_5_pulau_pltu = 1
GROUP BY t.year, p.pulau, s.kode_sumber;

-- View 4: Supply Biomassa vs Demand Co-Firing PLTU 5 Pulau Utama (Tahun Acuan 2024)
CREATE VIEW IF NOT EXISTS vw_supply_vs_pltu_5_pulau_2024 AS
WITH bio AS (
    SELECT
        l.pulau,
        SUM(e.estimated_residue_dry_ton)   AS biomass_supply_dry_ton,
        SUM(e.total_energy_potential_gj)   AS biomass_energy_gj,
        SUM(e.convertible_electricity_mwh) AS biomass_convertible_mwh,
        SUM(e.coal_equivalent_ton)         AS biomass_coal_eq_ton
    FROM fact_biomass_energy_potential e
    JOIN dim_time t     ON e.time_key = t.time_key
    JOIN dim_location l ON e.location_key = l.location_key
    WHERE t.year = 2024
      AND e.level_wilayah_fakta = 'PROVINSI'
      AND e.scenario_code = 'BASE_CONSERVATIVE'
      AND l.masuk_5_pulau_pltu = 1
    GROUP BY l.pulau
),
pltu AS (
    SELECT
        p.pulau,
        COUNT(DISTINCT p.pltu_key)       AS pltu_count_ct2024,
        SUM(o.capacity_mw)               AS pltu_capacity_mw,
        SUM(o.activity_generation_mwh)   AS pltu_generation_mwh,
        SUM(o.emissions_co2e_ton)        AS pltu_emissions_co2e_ton
    FROM fact_pltu_operations o
    JOIN dim_time t        ON o.time_key = t.time_key
    JOIN dim_power_plant p ON o.pltu_key = p.pltu_key
    JOIN dim_data_source s ON o.source_key = s.source_key
    WHERE t.year = 2024
      AND s.kode_sumber = 'CLIMATETRACE_V6'
      AND p.masuk_5_pulau_pltu = 1
    GROUP BY p.pulau
),
crea AS (
    SELECT
        p.pulau,
        COUNT(DISTINCT p.pltu_key)       AS pltu_cofiring_crea_count,
        SUM(o.biomass_used_ton)          AS crea_actual_biomass_2024_ton,
        SUM(o.biomass_electricity_mwh)   AS crea_actual_biomass_2024_mwh
    FROM fact_pltu_operations o
    JOIN dim_time t        ON o.time_key = t.time_key
    JOIN dim_power_plant p ON o.pltu_key = p.pltu_key
    JOIN dim_data_source s ON o.source_key = s.source_key
    WHERE t.year = 2024
      AND s.kode_sumber = 'CREA_MEI_2025'
      AND p.masuk_5_pulau_pltu = 1
    GROUP BY p.pulau
)
SELECT
    pltu.pulau,
    pltu.pltu_count_ct2024,
    ROUND(pltu.pltu_capacity_mw, 1)                        AS pltu_capacity_mw,
    ROUND(pltu.pltu_generation_mwh, 1)                     AS pltu_generation_mwh,
    ROUND(pltu.pltu_generation_mwh * 0.05, 1)              AS target_cofiring_5pct_mwh,
    ROUND(pltu.pltu_generation_mwh * 0.10, 1)              AS target_cofiring_10pct_mwh,
    COALESCE(crea.pltu_cofiring_crea_count, 0)             AS pltu_cofiring_crea_count,
    ROUND(COALESCE(crea.crea_actual_biomass_2024_ton, 0), 1) AS crea_actual_biomass_2024_ton,
    ROUND(COALESCE(crea.crea_actual_biomass_2024_mwh, 0), 1) AS crea_actual_biomass_2024_mwh,
    ROUND(COALESCE(bio.biomass_supply_dry_ton, 0), 1)      AS biomass_supply_dry_ton,
    ROUND(COALESCE(bio.biomass_energy_gj, 0), 1)           AS biomass_energy_gj,
    ROUND(COALESCE(bio.biomass_convertible_mwh, 0), 1)     AS biomass_convertible_mwh,
    ROUND(COALESCE(bio.biomass_coal_eq_ton, 0), 1)         AS biomass_coal_eq_ton,
    ROUND(CASE WHEN pltu.pltu_generation_mwh > 0
               THEN (COALESCE(bio.biomass_convertible_mwh, 0) / (pltu.pltu_generation_mwh * 0.10)) * 100.0
               ELSE NULL END, 1)                           AS coverage_vs_10pct_cofiring_pct
FROM pltu
LEFT JOIN bio  ON pltu.pulau = bio.pulau
LEFT JOIN crea ON pltu.pulau = crea.pulau
ORDER BY pltu.pltu_capacity_mw DESC;
