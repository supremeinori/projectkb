-- =============================================================================
-- STAR SCHEMA DATA WAREHOUSE V2 (PROJECTKB - Biomass & PLTU Co-Firing BI)
-- Kompatibel: SQLite 3 (native), DuckDB, dan portabel ke PostgreSQL
-- Pola: Kimball Multi-Fact Star Schema (5 Conformed Dimensions + 2 Fact Tables)
-- =============================================================================

PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS vw_cofiring_simulator_base;
DROP VIEW IF EXISTS vw_supply_vs_pltu_5_pulau_dualview;
DROP VIEW IF EXISTS vw_regional_potential_latest_complete;
DROP VIEW IF EXISTS vw_regional_potential_anchor_2022;
DROP VIEW IF EXISTS vw_feedstock_discovery_matrix;

DROP TABLE IF EXISTS fact_pltu_operations;
DROP TABLE IF EXISTS fact_feedstock_potential;
DROP TABLE IF EXISTS dim_power_plant;
DROP TABLE IF EXISTS dim_time;
DROP TABLE IF EXISTS dim_conversion_tech;
DROP TABLE IF EXISTS dim_location;
DROP TABLE IF EXISTS dim_feedstock;

-- -----------------------------------------------------------------------------
-- 1. CONFORMED DIMENSIONS (5 TABEL)
-- -----------------------------------------------------------------------------

CREATE TABLE dim_feedstock (
    feedstock_key              INTEGER PRIMARY KEY,
    feedstock_id               TEXT NOT NULL UNIQUE,
    feedstock_name             TEXT NOT NULL,
    komoditas_bps              TEXT NOT NULL,
    basis_produk_primer        TEXT NOT NULL,
    rpr_primer                 REAL NOT NULL,
    basis_alternatif_bps       TEXT NOT NULL,
    rpr_alternatif_bps         REAL NOT NULL,
    recoverability_factor      REAL NOT NULL,
    moisture_lapangan_pct      REAL NOT NULL,
    ash_db                     REAL NOT NULL,
    vm_db                      REAL NOT NULL,
    fc_db                      REAL NOT NULL,
    c_db                       REAL NOT NULL,
    h_db                       REAL NOT NULL,
    o_db                       REAL NOT NULL,
    n_db                       REAL NOT NULL,
    s_db                       REAL NOT NULL,
    cl_db_pct                  REAL,
    alkali_total_db_pct        REAL,
    idt_oxidizing_c            REAL,
    actual_hhv_db              REAL NOT NULL,
    predicted_hhv_prox_db      REAL NOT NULL,
    predicted_hhv_full_db      REAL NOT NULL,
    predicted_hhv_db           REAL NOT NULL,
    effective_lhv_lab_mj_kg    REAL NOT NULL,
    effective_lhv_field_mj_kg  REAL NOT NULL,
    high_moisture_flag         INTEGER NOT NULL CHECK (high_moisture_flag IN (0, 1)),
    boiler_status              TEXT NOT NULL CHECK (boiler_status IN ('Eligible', 'Not Eligible')),
    is_boiler_eligible         INTEGER NOT NULL CHECK (is_boiler_eligible IN (0, 1)),
    alkali_chlorine_flag       TEXT NOT NULL,
    screening_recommendation   TEXT NOT NULL,
    cluster_id                 INTEGER NOT NULL,
    cluster_label              TEXT NOT NULL
);

CREATE TABLE dim_location (
    location_key         INTEGER PRIMARY KEY,
    location_code        TEXT NOT NULL UNIQUE,
    level_wilayah        TEXT NOT NULL CHECK (level_wilayah IN ('NASIONAL', 'PULAU', 'PROVINSI', 'KABKOTA')),
    kode_prov            INTEGER,
    nama_provinsi        TEXT,
    kode_kabkota         INTEGER,
    nama_kabkota         TEXT,
    pulau                TEXT NOT NULL,
    masuk_5_pulau_pltu   INTEGER NOT NULL CHECK (masuk_5_pulau_pltu IN (0, 1)),
    wilayah_pln          TEXT NOT NULL,
    latitude_centroid    REAL,
    longitude_centroid   REAL,
    has_coordinates      INTEGER NOT NULL CHECK (has_coordinates IN (0, 1)),
    is_dob_papua_mapped  INTEGER NOT NULL CHECK (is_dob_papua_mapped IN (0, 1))
);

CREATE TABLE dim_conversion_tech (
    tech_key                  INTEGER PRIMARY KEY,
    tech_code                 TEXT NOT NULL UNIQUE,
    tech_name                 TEXT NOT NULL,
    efficiency_pct            REAL NOT NULL,
    capacity_factor_pct       REAL NOT NULL,
    operating_hours_per_year  REAL NOT NULL,
    ash_limit_pct             REAL NOT NULL,
    sulfur_limit_pct          REAL NOT NULL,
    reference_note            TEXT NOT NULL
);

CREATE TABLE dim_time (
    time_key             INTEGER PRIMARY KEY,
    year                 INTEGER NOT NULL UNIQUE,
    decade               INTEGER NOT NULL,
    is_bps_ksa_era       INTEGER NOT NULL CHECK (is_bps_ksa_era IN (0, 1)),
    is_post_papua_split  INTEGER NOT NULL CHECK (is_post_papua_split IN (0, 1)),
    is_anchor_2022       INTEGER NOT NULL CHECK (is_anchor_2022 IN (0, 1)),
    has_pltu_ct_data     INTEGER NOT NULL CHECK (has_pltu_ct_data IN (0, 1))
);

CREATE TABLE dim_power_plant (
    pltu_key              INTEGER PRIMARY KEY,
    pltu_master_id        TEXT NOT NULL UNIQUE,
    nama_pltu_standar     TEXT NOT NULL UNIQUE,
    nama_climatetrace     TEXT,
    nama_wri_gppd         TEXT,
    nama_crea_2025        TEXT,
    owner_operator        TEXT,
    jenis_boiler          TEXT,
    status_cofiring_2024  TEXT NOT NULL,
    commissioning_year    INTEGER,
    latitude              REAL,
    longitude             REAL,
    has_coordinates       INTEGER NOT NULL CHECK (has_coordinates IN (0, 1)),
    pulau                 TEXT NOT NULL,
    masuk_5_pulau_pltu    INTEGER NOT NULL CHECK (masuk_5_pulau_pltu IN (0, 1)),
    wilayah_pln           TEXT,
    entity_match_method   TEXT NOT NULL,
    name_audit_flag       TEXT NOT NULL
);

-- -----------------------------------------------------------------------------
-- 2. CORE FACT TABLES (2 TABEL)
-- -----------------------------------------------------------------------------

CREATE TABLE fact_feedstock_potential (
    energy_fact_id               INTEGER PRIMARY KEY,
    time_key                     INTEGER NOT NULL,
    location_key                 INTEGER NOT NULL,
    feedstock_key                INTEGER NOT NULL,
    tech_key                     INTEGER NOT NULL,
    level_wilayah_fakta          TEXT NOT NULL CHECK (level_wilayah_fakta IN ('KABKOTA', 'PROVINSI')),
    sumber_data                  TEXT NOT NULL,
    cakupan_data                 TEXT NOT NULL,
    is_anchor_2022               INTEGER NOT NULL CHECK (is_anchor_2022 IN (0, 1)),
    is_latest_complete_year      INTEGER NOT NULL CHECK (is_latest_complete_year IN (0, 1)),
    is_latest_available_year     INTEGER NOT NULL CHECK (is_latest_available_year IN (0, 1)),
    is_boiler_eligible           INTEGER NOT NULL CHECK (is_boiler_eligible IN (0, 1)),
    commodity_production_val     REAL NOT NULL,
    commodity_unit               TEXT NOT NULL,
    rpr_ratio_used               REAL NOT NULL,
    recoverability_factor_used   REAL NOT NULL,
    estimated_supply_gross_tons  REAL NOT NULL,
    estimated_supply_tons        REAL NOT NULL,
    moisture_lapangan_pct        REAL NOT NULL,
    predicted_hhv_mj_kg          REAL NOT NULL,
    effective_lhv_mj_kg          REAL NOT NULL,
    total_energy_potential_gj    REAL NOT NULL,
    estimated_generation_mwh     REAL NOT NULL,
    estimated_capacity_mw        REAL NOT NULL,
    coal_replaced_tons           REAL NOT NULL,
    co2_offset_tons              REAL NOT NULL,
    ash_load_tons                REAL NOT NULL,
    UNIQUE (time_key, location_key, feedstock_key, tech_key),
    FOREIGN KEY (time_key)      REFERENCES dim_time(time_key),
    FOREIGN KEY (location_key)  REFERENCES dim_location(location_key),
    FOREIGN KEY (feedstock_key) REFERENCES dim_feedstock(feedstock_key),
    FOREIGN KEY (tech_key)      REFERENCES dim_conversion_tech(tech_key)
);

CREATE TABLE fact_pltu_operations (
    pltu_fact_id                INTEGER PRIMARY KEY,
    time_key                    INTEGER NOT NULL,
    location_key                INTEGER NOT NULL,
    pltu_key                    INTEGER NOT NULL,
    dataset_role                TEXT NOT NULL CHECK (dataset_role IN ('BASE_OPERATIONS_CT', 'COFIRING_REALIZATION_CREA')),
    kode_sumber                 TEXT NOT NULL,
    crea_block_count            INTEGER NOT NULL,
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
    UNIQUE (time_key, pltu_key, dataset_role),
    FOREIGN KEY (time_key)      REFERENCES dim_time(time_key),
    FOREIGN KEY (location_key)  REFERENCES dim_location(location_key),
    FOREIGN KEY (pltu_key)      REFERENCES dim_power_plant(pltu_key)
);

-- -----------------------------------------------------------------------------
-- 3. INDEXES FOR FAST OLAP QUERIES
-- -----------------------------------------------------------------------------

CREATE INDEX idx_ffp_keys      ON fact_feedstock_potential (time_key, location_key, feedstock_key, tech_key);
CREATE INDEX idx_ffp_dualview  ON fact_feedstock_potential (is_anchor_2022, is_latest_complete_year, is_boiler_eligible, tech_key);
CREATE INDEX idx_fpltu_keys    ON fact_pltu_operations (dataset_role, time_key, pltu_key);

-- -----------------------------------------------------------------------------
-- 4. ANALYTICAL VIEWS (5 VIEWS)
-- -----------------------------------------------------------------------------

-- View 1: Matriks Penyaringan Bahan Bakar (Halaman 1 Dashboard)
CREATE VIEW vw_feedstock_discovery_matrix AS
SELECT
    feedstock_key,
    feedstock_id,
    feedstock_name,
    komoditas_bps,
    ash_db,
    vm_db,
    fc_db,
    s_db,
    cl_db_pct,
    alkali_total_db_pct,
    idt_oxidizing_c,
    moisture_lapangan_pct,
    high_moisture_flag,
    actual_hhv_db,
    predicted_hhv_prox_db,
    predicted_hhv_full_db,
    predicted_hhv_db,
    effective_lhv_field_mj_kg,
    boiler_status,
    is_boiler_eligible,
    alkali_chlorine_flag,
    screening_recommendation,
    cluster_id,
    cluster_label
FROM dim_feedstock;

-- View 2: Potensi Energi Wilayah Tahun Jangkar 2022 (Mode Anchor 2022)
CREATE VIEW vw_regional_potential_anchor_2022 AS
SELECT
    t.year,
    l.pulau,
    l.masuk_5_pulau_pltu,
    l.kode_prov,
    l.nama_provinsi,
    l.kode_kabkota,
    l.nama_kabkota,
    e.level_wilayah_fakta,
    f.feedstock_id,
    f.feedstock_name,
    f.komoditas_bps,
    f.boiler_status,
    e.is_boiler_eligible,
    ct.tech_code,
    ct.tech_name,
    e.cakupan_data,
    e.commodity_production_val,
    e.commodity_unit,
    e.estimated_supply_tons,
    e.effective_lhv_mj_kg,
    e.total_energy_potential_gj,
    e.estimated_generation_mwh,
    e.estimated_capacity_mw,
    e.coal_replaced_tons,
    e.co2_offset_tons,
    e.ash_load_tons
FROM fact_feedstock_potential e
JOIN dim_time t            ON e.time_key = t.time_key
JOIN dim_location l        ON e.location_key = l.location_key
JOIN dim_feedstock f       ON e.feedstock_key = f.feedstock_key
JOIN dim_conversion_tech ct ON e.tech_key = ct.tech_key
WHERE e.is_anchor_2022 = 1;

-- View 3: Potensi Energi Wilayah Tahun Lengkap Terbaru per Komoditas (Mode Latest Complete Year)
CREATE VIEW vw_regional_potential_latest_complete AS
SELECT
    t.year AS data_year,
    l.pulau,
    l.masuk_5_pulau_pltu,
    l.kode_prov,
    l.nama_provinsi,
    l.kode_kabkota,
    l.nama_kabkota,
    e.level_wilayah_fakta,
    f.feedstock_id,
    f.feedstock_name,
    f.komoditas_bps,
    f.boiler_status,
    e.is_boiler_eligible,
    ct.tech_code,
    ct.tech_name,
    e.cakupan_data,
    e.commodity_production_val,
    e.commodity_unit,
    e.estimated_supply_tons,
    e.effective_lhv_mj_kg,
    e.total_energy_potential_gj,
    e.estimated_generation_mwh,
    e.estimated_capacity_mw,
    e.coal_replaced_tons,
    e.co2_offset_tons,
    e.ash_load_tons
FROM fact_feedstock_potential e
JOIN dim_time t            ON e.time_key = t.time_key
JOIN dim_location l        ON e.location_key = l.location_key
JOIN dim_feedstock f       ON e.feedstock_key = f.feedstock_key
JOIN dim_conversion_tech ct ON e.tech_key = ct.tech_key
WHERE e.is_latest_complete_year = 1;

-- View 4: Suplai Layak Bakar vs Permintaan Co-Firing PLTU di 5 Pulau Utama (Dual-View, 10 baris)
CREATE VIEW vw_supply_vs_pltu_5_pulau_dualview AS
WITH sup_anchor AS (
    SELECT
        l.pulau,
        SUM(e.estimated_supply_tons)      AS eligible_supply_tons,
        SUM(e.total_energy_potential_gj)  AS eligible_energy_gj,
        SUM(e.estimated_generation_mwh)   AS eligible_generation_mwh,
        SUM(e.estimated_capacity_mw)      AS eligible_capacity_mw,
        SUM(e.coal_replaced_tons)         AS eligible_coal_replaced_tons,
        SUM(e.co2_offset_tons)            AS eligible_co2_offset_tons
    FROM fact_feedstock_potential e
    JOIN dim_location l        ON e.location_key = l.location_key
    JOIN dim_conversion_tech ct ON e.tech_key = ct.tech_key
    WHERE e.is_anchor_2022 = 1
      AND e.is_boiler_eligible = 1
      AND ct.tech_code = 'TECH01'
      AND l.masuk_5_pulau_pltu = 1
    GROUP BY l.pulau
),
sup_latest AS (
    SELECT
        l.pulau,
        SUM(e.estimated_supply_tons)      AS eligible_supply_tons,
        SUM(e.total_energy_potential_gj)  AS eligible_energy_gj,
        SUM(e.estimated_generation_mwh)   AS eligible_generation_mwh,
        SUM(e.estimated_capacity_mw)      AS eligible_capacity_mw,
        SUM(e.coal_replaced_tons)         AS eligible_coal_replaced_tons,
        SUM(e.co2_offset_tons)            AS eligible_co2_offset_tons
    FROM fact_feedstock_potential e
    JOIN dim_location l        ON e.location_key = l.location_key
    JOIN dim_conversion_tech ct ON e.tech_key = ct.tech_key
    WHERE e.is_latest_complete_year = 1
      AND e.is_boiler_eligible = 1
      AND ct.tech_code = 'TECH01'
      AND l.masuk_5_pulau_pltu = 1
    GROUP BY l.pulau
),
pltu_ct_2022 AS (
    SELECT
        p.pulau,
        COUNT(DISTINCT p.pltu_key)      AS pltu_count_ct,
        SUM(o.capacity_mw)              AS pltu_capacity_mw,
        SUM(o.activity_generation_mwh)  AS pltu_generation_mwh,
        SUM(o.emissions_co2e_ton)       AS pltu_emissions_co2e_ton
    FROM fact_pltu_operations o
    JOIN dim_power_plant p ON o.pltu_key = p.pltu_key
    WHERE o.dataset_role = 'BASE_OPERATIONS_CT'
      AND o.time_key = 2022
      AND p.masuk_5_pulau_pltu = 1
    GROUP BY p.pulau
),
pltu_ct_2024 AS (
    SELECT
        p.pulau,
        COUNT(DISTINCT p.pltu_key)      AS pltu_count_ct,
        SUM(o.capacity_mw)              AS pltu_capacity_mw,
        SUM(o.activity_generation_mwh)  AS pltu_generation_mwh,
        SUM(o.emissions_co2e_ton)       AS pltu_emissions_co2e_ton
    FROM fact_pltu_operations o
    JOIN dim_power_plant p ON o.pltu_key = p.pltu_key
    WHERE o.dataset_role = 'BASE_OPERATIONS_CT'
      AND o.time_key = 2024
      AND p.masuk_5_pulau_pltu = 1
    GROUP BY p.pulau
),
crea_2024 AS (
    SELECT
        p.pulau,
        COUNT(DISTINCT p.pltu_key)      AS crea_cofiring_pltu_count,
        SUM(o.biomass_used_ton)         AS crea_actual_biomass_ton,
        SUM(o.biomass_electricity_mwh)  AS crea_actual_biomass_mwh
    FROM fact_pltu_operations o
    JOIN dim_power_plant p ON o.pltu_key = p.pltu_key
    WHERE o.dataset_role = 'COFIRING_REALIZATION_CREA'
      AND o.time_key = 2024
      AND p.masuk_5_pulau_pltu = 1
    GROUP BY p.pulau
)
SELECT
    'ANCHOR_2022' AS view_mode,
    2022 AS pltu_reference_year,
    pt.pulau,
    pt.pltu_count_ct,
    ROUND(pt.pltu_capacity_mw, 2) AS pltu_capacity_mw,
    ROUND(pt.pltu_generation_mwh, 2) AS pltu_generation_mwh,
    ROUND(pt.pltu_emissions_co2e_ton, 2) AS pltu_emissions_co2e_ton,
    ROUND(pt.pltu_generation_mwh * 0.05, 2) AS target_cofiring_5pct_mwh,
    ROUND(pt.pltu_generation_mwh * 0.10, 2) AS target_cofiring_10pct_mwh,
    ROUND(pt.pltu_generation_mwh * 0.20, 2) AS target_cofiring_20pct_mwh,
    0 AS crea_cofiring_pltu_count,
    NULL AS crea_actual_biomass_ton,
    NULL AS crea_actual_biomass_mwh,
    ROUND(COALESCE(sa.eligible_supply_tons, 0), 2) AS eligible_supply_tons,
    ROUND(COALESCE(sa.eligible_energy_gj, 0), 2) AS eligible_energy_gj,
    ROUND(COALESCE(sa.eligible_generation_mwh, 0), 2) AS eligible_generation_mwh,
    ROUND(COALESCE(sa.eligible_capacity_mw, 0), 2) AS eligible_capacity_mw,
    ROUND(COALESCE(sa.eligible_coal_replaced_tons, 0), 2) AS eligible_coal_replaced_tons,
    ROUND(COALESCE(sa.eligible_co2_offset_tons, 0), 2) AS eligible_co2_offset_tons,
    ROUND((COALESCE(sa.eligible_generation_mwh, 0) / (pt.pltu_generation_mwh * 0.05)) * 100.0, 2) AS coverage_vs_5pct_cofiring_pct,
    ROUND((COALESCE(sa.eligible_generation_mwh, 0) / (pt.pltu_generation_mwh * 0.10)) * 100.0, 2) AS coverage_vs_10pct_cofiring_pct,
    ROUND((COALESCE(sa.eligible_generation_mwh, 0) / (pt.pltu_generation_mwh * 0.20)) * 100.0, 2) AS coverage_vs_20pct_cofiring_pct
FROM pltu_ct_2022 pt
LEFT JOIN sup_anchor sa ON pt.pulau = sa.pulau

UNION ALL

SELECT
    'LATEST_COMPLETE_VS_2024' AS view_mode,
    2024 AS pltu_reference_year,
    pt.pulau,
    pt.pltu_count_ct,
    ROUND(pt.pltu_capacity_mw, 2) AS pltu_capacity_mw,
    ROUND(pt.pltu_generation_mwh, 2) AS pltu_generation_mwh,
    ROUND(pt.pltu_emissions_co2e_ton, 2) AS pltu_emissions_co2e_ton,
    ROUND(pt.pltu_generation_mwh * 0.05, 2) AS target_cofiring_5pct_mwh,
    ROUND(pt.pltu_generation_mwh * 0.10, 2) AS target_cofiring_10pct_mwh,
    ROUND(pt.pltu_generation_mwh * 0.20, 2) AS target_cofiring_20pct_mwh,
    COALESCE(cr.crea_cofiring_pltu_count, 0) AS crea_cofiring_pltu_count,
    ROUND(COALESCE(cr.crea_actual_biomass_ton, 0), 2) AS crea_actual_biomass_ton,
    ROUND(COALESCE(cr.crea_actual_biomass_mwh, 0), 2) AS crea_actual_biomass_mwh,
    ROUND(COALESCE(sl.eligible_supply_tons, 0), 2) AS eligible_supply_tons,
    ROUND(COALESCE(sl.eligible_energy_gj, 0), 2) AS eligible_energy_gj,
    ROUND(COALESCE(sl.eligible_generation_mwh, 0), 2) AS eligible_generation_mwh,
    ROUND(COALESCE(sl.eligible_capacity_mw, 0), 2) AS eligible_capacity_mw,
    ROUND(COALESCE(sl.eligible_coal_replaced_tons, 0), 2) AS eligible_coal_replaced_tons,
    ROUND(COALESCE(sl.eligible_co2_offset_tons, 0), 2) AS eligible_co2_offset_tons,
    ROUND((COALESCE(sl.eligible_generation_mwh, 0) / (pt.pltu_generation_mwh * 0.05)) * 100.0, 2) AS coverage_vs_5pct_cofiring_pct,
    ROUND((COALESCE(sl.eligible_generation_mwh, 0) / (pt.pltu_generation_mwh * 0.10)) * 100.0, 2) AS coverage_vs_10pct_cofiring_pct,
    ROUND((COALESCE(sl.eligible_generation_mwh, 0) / (pt.pltu_generation_mwh * 0.20)) * 100.0, 2) AS coverage_vs_20pct_cofiring_pct
FROM pltu_ct_2024 pt
LEFT JOIN sup_latest sl ON pt.pulau = sl.pulau
LEFT JOIN crea_2024 cr ON pt.pulau = cr.pulau;

-- View 5: Tabel Dasar Simulator What-If Co-Firing 5%, 10%, 20% (Halaman 3 Dashboard)
CREATE VIEW vw_cofiring_simulator_base AS
WITH sup AS (
    SELECT
        'ANCHOR_2022' AS view_mode,
        2022 AS pltu_reference_year,
        l.pulau,
        ct.tech_code,
        ct.tech_name,
        ct.efficiency_pct,
        SUM(e.estimated_supply_tons)    AS eligible_supply_tons,
        SUM(e.estimated_generation_mwh) AS eligible_generation_mwh,
        SUM(e.coal_replaced_tons)       AS max_coal_replaced_tons,
        SUM(e.co2_offset_tons)          AS max_co2_offset_tons
    FROM fact_feedstock_potential e
    JOIN dim_location l        ON e.location_key = l.location_key
    JOIN dim_conversion_tech ct ON e.tech_key = ct.tech_key
    WHERE e.is_anchor_2022 = 1 AND e.is_boiler_eligible = 1 AND l.masuk_5_pulau_pltu = 1
    GROUP BY l.pulau, ct.tech_code, ct.tech_name, ct.efficiency_pct
    UNION ALL
    SELECT
        'LATEST_COMPLETE_VS_2024' AS view_mode,
        2024 AS pltu_reference_year,
        l.pulau,
        ct.tech_code,
        ct.tech_name,
        ct.efficiency_pct,
        SUM(e.estimated_supply_tons)    AS eligible_supply_tons,
        SUM(e.estimated_generation_mwh) AS eligible_generation_mwh,
        SUM(e.coal_replaced_tons)       AS max_coal_replaced_tons,
        SUM(e.co2_offset_tons)          AS max_co2_offset_tons
    FROM fact_feedstock_potential e
    JOIN dim_location l        ON e.location_key = l.location_key
    JOIN dim_conversion_tech ct ON e.tech_key = ct.tech_key
    WHERE e.is_latest_complete_year = 1 AND e.is_boiler_eligible = 1 AND l.masuk_5_pulau_pltu = 1
    GROUP BY l.pulau, ct.tech_code, ct.tech_name, ct.efficiency_pct
),
pltu AS (
    SELECT
        o.time_key AS pltu_reference_year,
        p.pulau,
        SUM(o.capacity_mw)             AS pltu_capacity_mw,
        SUM(o.activity_generation_mwh) AS pltu_generation_mwh,
        SUM(o.emissions_co2e_ton)      AS pltu_emissions_co2e_ton
    FROM fact_pltu_operations o
    JOIN dim_power_plant p ON o.pltu_key = p.pltu_key
    WHERE o.dataset_role = 'BASE_OPERATIONS_CT'
      AND o.time_key IN (2022, 2024)
      AND p.masuk_5_pulau_pltu = 1
    GROUP BY o.time_key, p.pulau
)
SELECT
    sup.view_mode,
    sup.pltu_reference_year,
    sup.pulau,
    sup.tech_code,
    sup.tech_name,
    sup.efficiency_pct,
    ROUND(pltu.pltu_capacity_mw, 2) AS pltu_capacity_mw,
    ROUND(pltu.pltu_generation_mwh, 2) AS pltu_generation_mwh,
    ROUND(sup.eligible_supply_tons, 2) AS eligible_supply_tons,
    ROUND(sup.eligible_generation_mwh, 2) AS eligible_generation_mwh,
    ROUND(MIN(sup.eligible_generation_mwh, pltu.pltu_generation_mwh * 0.05), 2) AS realizable_mwh_at_5pct,
    ROUND(MIN(sup.eligible_generation_mwh, pltu.pltu_generation_mwh * 0.10), 2) AS realizable_mwh_at_10pct,
    ROUND(MIN(sup.eligible_generation_mwh, pltu.pltu_generation_mwh * 0.20), 2) AS realizable_mwh_at_20pct,
    ROUND(((MIN(sup.eligible_generation_mwh, pltu.pltu_generation_mwh * 0.05) * 3.6) / (sup.efficiency_pct / 100.0)) / 20.0, 2) AS coal_replaced_at_5pct_tons,
    ROUND(((MIN(sup.eligible_generation_mwh, pltu.pltu_generation_mwh * 0.10) * 3.6) / (sup.efficiency_pct / 100.0)) / 20.0, 2) AS coal_replaced_at_10pct_tons,
    ROUND(((MIN(sup.eligible_generation_mwh, pltu.pltu_generation_mwh * 0.20) * 3.6) / (sup.efficiency_pct / 100.0)) / 20.0, 2) AS coal_replaced_at_20pct_tons,
    ROUND(((MIN(sup.eligible_generation_mwh, pltu.pltu_generation_mwh * 0.05) * 3.6) / (sup.efficiency_pct / 100.0)) * 0.0946, 2) AS co2_offset_at_5pct_tons,
    ROUND(((MIN(sup.eligible_generation_mwh, pltu.pltu_generation_mwh * 0.10) * 3.6) / (sup.efficiency_pct / 100.0)) * 0.0946, 2) AS co2_offset_at_10pct_tons,
    ROUND(((MIN(sup.eligible_generation_mwh, pltu.pltu_generation_mwh * 0.20) * 3.6) / (sup.efficiency_pct / 100.0)) * 0.0946, 2) AS co2_offset_at_20pct_tons
FROM sup
JOIN pltu ON sup.pltu_reference_year = pltu.pltu_reference_year AND sup.pulau = pltu.pulau;
