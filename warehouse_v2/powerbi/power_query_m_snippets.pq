// =============================================================================
// POWER QUERY (M) SNIPPETS - PROJECTKB POWER BI
// =============================================================================
//
// BAGIAN A: JALUR UTAMA (IMPORT CSV DENGAN PARAMETER FOLDER)
// Langkah 1 di Power Query Editor: Manage Parameters -> New Parameter
//   Name: FolderProjectKB
//   Type: Text
//   Current Value: D:\UPN VY\Semester 5\BI\Tugas\projectkb
//
// Contoh kueri untuk memuat fact_feedstock_potential.csv secara aman (locale en-US
// agar titik desimal "." selalu terbaca benar meskipun Windows berbahasa Indonesia):

let
    Sumber = Csv.Document(
        File.Contents(FolderProjectKB & "\warehouse_v2\tables\fact_feedstock_potential.csv"),
        [Delimiter=",", Columns=27, Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    Header = Table.PromoteHeaders(Sumber, [PromoteAllScalars=true]),
    TipeData = Table.TransformColumnTypes(
        Header,
        {
            {"energy_fact_id", Int64.Type},
            {"time_key", Int64.Type},
            {"location_key", Int64.Type},
            {"feedstock_key", Int64.Type},
            {"tech_key", Int64.Type},
            {"is_anchor_2022", Int64.Type},
            {"is_latest_complete_year", Int64.Type},
            {"is_latest_available_year", Int64.Type},
            {"is_boiler_eligible", Int64.Type},
            {"commodity_production_val", type number},
            {"rpr_ratio_used", type number},
            {"recoverability_factor_used", type number},
            {"estimated_supply_gross_tons", type number},
            {"estimated_supply_tons", type number},
            {"moisture_lapangan_pct", type number},
            {"predicted_hhv_mj_kg", type number},
            {"effective_lhv_mj_kg", type number},
            {"total_energy_potential_gj", type number},
            {"estimated_generation_mwh", type number},
            {"estimated_capacity_mw", type number},
            {"coal_replaced_tons", type number},
            {"co2_offset_tons", type number},
            {"ash_load_tons", type number}
        },
        "en-US"
    )
in
    TipeData


// -----------------------------------------------------------------------------
// BAGIAN B: LAMPIRAN OPSIONAL (KONEKSI SQLITE VIA ODBC DRIVER)
// Prasyarat: Instal "SQLite ODBC Driver (64-bit)" di Windows dan buat User DSN
// bernama "ProjectKB_DWH_v2" mengarah ke warehouse_v2\biomass_dwh_v2.sqlite.
// -----------------------------------------------------------------------------

let
    Sumber = Odbc.DataSource("dsn=ProjectKB_DWH_v2", [HierarchicalNavigation=true]),
    TabelFakta = Sumber{[Name="fact_feedstock_potential", Kind="Table"]}[Data]
in
    TabelFakta
