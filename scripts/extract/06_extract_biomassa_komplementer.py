"""
Ekstraktor Data Komplementer Biomassa (Folder 5: raw_data/05_biomassa_komplementer/)
Sumber: Dokumen DOCX "Biomass Dataset for Higher Heating Value Prediction (n = 315)"
        (Mendeley DOI: 10.17632/5xswr8yp34.3)
Output (Zero-Merge: 1 tabel/daftar = 1 CSV terpisah, UTF-8 BOM):
  1. raw_data/05_biomassa_komplementer/biomass_hhv_315_samples.csv   (315 sampel + flag imputasi N/S + reference_code)
  2. raw_data/05_biomassa_komplementer/biomass_hhv_references.csv    (30 sitasi pustaka [1]..[30])
  3. raw_data/05_biomassa_komplementer/_audit_05_biomassa_komplementer.csv
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import docx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils_raw import (  # noqa: E402
    PROJECT_ROOT,
    RAW_DIR,
    add_provenance_cols,
    ensure_raw_folder_tree,
    write_raw_csv,
)

OUT_DIR = RAW_DIR / "05_biomassa_komplementer"
ARCHIVE_DOC_DIR = PROJECT_ROOT / "_archive_pipeline" / "raw_docs"
ARCHIVED_DOCX = ARCHIVE_DOC_DIR / "biomass_hhv_315_samples_source.docx"
UPLOADED_DOCX = Path(
    r"C:\Users\HYPE AMD\.gemini\antigravity\brain\3cb39480-4062-4b3d-987c-00c8a7f0ccf0\.user_uploaded\media_1795579905405_2a560e06.docx"
)

SUMBER_INSTANSI = "Mendeley Data (Biomass Dataset for HHV Prediction, n=315)"
SUMBER_URL = "https://data.mendeley.com/datasets/5xswr8yp34/3"


def is_bold_brown_imputed(cell) -> bool:
    """Deteksi apakah teks sel bernilai imputed 0.0 (format bold & warna coklat #7B3F00 pada DOCX asli)."""
    has_bold = False
    has_color = False
    for p in cell.paragraphs:
        for r in p.runs:
            if not r.text.strip():
                continue
            if r.bold:
                has_bold = True
            if r.font.color and r.font.color.rgb:
                has_color = True
    return has_bold or has_color


def extract_samples_and_refs(docx_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    doc = docx.Document(docx_path)
    if len(doc.tables) < 2:
        raise ValueError(f"Expected >= 2 tables in {docx_path}, found {len(doc.tables)}")

    tbl = doc.tables[1]
    sample_rows = []
    for row in tbl.rows[1:]:
        vals = [c.text.strip() for c in row.cells]
        if len(vals) != 13:
            raise ValueError(f"Expected 13 columns, got {len(vals)} on row {vals[:2]}")
        sample_rows.append(
            {
                "no": int(vals[0]),
                "material": vals[1],
                "feedstock_category": vals[2].lower(),
                "ash_wt_pct_db": float(vals[3]),
                "vm_wt_pct_db": float(vals[4]),
                "fc_wt_pct_db": float(vals[5]),
                "c_wt_pct_db": float(vals[6]),
                "h_wt_pct_db": float(vals[7]),
                "o_wt_pct_db": float(vals[8]),
                "n_wt_pct_db": float(vals[9]),
                "s_wt_pct_db": float(vals[10]),
                "hhv_mj_kg": float(vals[11]),
                "reference_code": vals[12],
                "is_n_imputed_bold_brown": is_bold_brown_imputed(row.cells[9]),
                "is_s_imputed_bold_brown": is_bold_brown_imputed(row.cells[10]),
            }
        )

    ref_rows = []
    for p in doc.paragraphs:
        txt = p.text.strip()
        m = re.match(r"^\[(\d+)\]\s+(.+)$", txt)
        if m:
            ref_no = int(m.group(1))
            ref_rows.append(
                {
                    "reference_no": ref_no,
                    "reference_code": f"[{ref_no}]",
                    "citation": m.group(2).strip(),
                }
            )

    df_samples = pd.DataFrame(sample_rows)
    df_refs = pd.DataFrame(ref_rows)
    return df_samples, df_refs


def build_audit(df_samples: pd.DataFrame, df_refs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cat, sub in df_samples.groupby("feedstock_category", sort=True):
        rows.append(
            {
                "feedstock_category": cat,
                "jumlah_sampel": int(len(sub)),
                "avg_hhv_mj_kg": round(float(sub["hhv_mj_kg"].mean()), 3),
                "median_hhv_mj_kg": round(float(sub["hhv_mj_kg"].median()), 3),
                "avg_ash_wt_pct_db": round(float(sub["ash_wt_pct_db"].mean()), 3),
                "avg_s_wt_pct_db": round(float(sub["s_wt_pct_db"].mean()), 4),
                "jumlah_n_imputed": int(sub["is_n_imputed_bold_brown"].sum()),
                "jumlah_s_imputed": int(sub["is_s_imputed_bold_brown"].sum()),
                "ref_unik_terpakai": int(sub["reference_code"].nunique()),
                "total_ref_bibliografi": int(len(df_refs)),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Konversi data komplementer biomassa DOCX ke CSV dalam folder.")
    parser.add_argument("--docx", type=Path, default=None, help="Path file DOCX sumber.")
    args = parser.parse_args()

    ensure_raw_folder_tree()
    ARCHIVE_DOC_DIR.mkdir(parents=True, exist_ok=True)

    src_docx = args.docx
    if src_docx is None:
        if UPLOADED_DOCX.exists():
            shutil.copy2(UPLOADED_DOCX, ARCHIVED_DOCX)
            src_docx = ARCHIVED_DOCX
        elif ARCHIVED_DOCX.exists():
            src_docx = ARCHIVED_DOCX
        else:
            raise FileNotFoundError("File DOCX sumber tidak ditemukan.")

    df_samples, df_refs = extract_samples_and_refs(src_docx)

    # Validasi integritas referensi ([1]..[30])
    sample_refs = set(df_samples["reference_code"].unique())
    bib_refs = set(df_refs["reference_code"].unique())
    orphan_refs = sorted(sample_refs - bib_refs)
    if orphan_refs:
        raise ValueError(f"Referensi tidak ditemukan di daftar pustaka: {orphan_refs}")

    df_samples_out = add_provenance_cols(
        df_samples,
        sumber_instansi=SUMBER_INSTANSI,
        sumber_url=SUMBER_URL,
        satuan_asli="Proximate/Ultimate: wt% db (dry basis); HHV: MJ/kg",
        level_wilayah="SAMPEL_LAB",
    )
    df_refs_out = add_provenance_cols(
        df_refs,
        sumber_instansi=SUMBER_INSTANSI,
        sumber_url=SUMBER_URL,
        satuan_asli="Sitasi Pustaka",
        level_wilayah="REFERENSI_LAB",
    )
    df_audit = build_audit(df_samples, df_refs)

    p_samples = write_raw_csv(df_samples_out, OUT_DIR / "biomass_hhv_315_samples.csv")
    p_refs = write_raw_csv(df_refs_out, OUT_DIR / "biomass_hhv_references.csv")
    p_audit = write_raw_csv(df_audit, OUT_DIR / "_audit_05_biomassa_komplementer.csv")

    print(f"Saved: {p_samples} ({len(df_samples_out)} rows x {len(df_samples_out.columns)} cols)")
    print(f"Saved: {p_refs} ({len(df_refs_out)} rows x {len(df_refs_out.columns)} cols)")
    print(f"Saved: {p_audit} ({len(df_audit)} categories)")
    print("\nBreakdown per feedstock_category:")
    print(df_audit.to_string(index=False))


if __name__ == "__main__":
    main()
