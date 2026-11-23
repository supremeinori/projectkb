"""
Step 2: Ekstraksi Folder 2 — raw_data/02_bps/
Prinsip Strict Scientist / Zero-Merge:
- Tahap 2A — 6 Tabel Utama BPS RI (Otomatis, Tanpa API Key, 1 Tahun = 1 CSV):
  1. bps_ri/1498_padi/{tahun}.csv                 (2018-2024)
  2. bps_ri/2204_jagung/{tahun}.csv               (2020-2024)
  3. bps_ri/2566_perkebunan/{tahun}.csv           (2024)
  4. bps_ri/132_perkebunan_historis/{tahun}.csv   (2008-2023)
  5. bps_ri/2512_kayu_jenis_pohon/{tahun}.csv     (2020-2023)
  6. bps_ri/1973_kayu_hph_pulau/{tahun}.csv       (2019-2022)
  Mekanisme resmi: membaca daftar tahun (listTahun) pada halaman Next.js BPS lalu mengambil
  setiap tahun satu per satu lewat payload SSR (tahun default) & Next.js Server Action resmi
  `getDataTable` (tahun lainnya). Tanpa penggabungan antar-tahun dan tanpa konversi satuan.
- Tahap 2B — BPS Provinsi (Opsional, hanya bila BPS_API_KEY tersedia di env / .env):
  Jika belum ada BPS_API_KEY, dilewati bersih dan dicatat di _audit_02_bps.csv.
- Audit lengkap ke _audit_02_bps.csv.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils_raw import (  # noqa: E402
    PROVINCES_38,
    RAW_DIR,
    RequestLogger,
    add_provenance_cols,
    ensure_raw_folder_tree,
    load_bps_api_key,
    make_http_session,
    today_iso,
    write_raw_csv,
)

FOLDER_2 = RAW_DIR / "02_bps"
DEFAULT_GET_DATA_TABLE_ACTION = "40aa0e277138bb29bcbcd63375edee677219577bb0"

BPS_RI_TABLES = [
    {
        "folder": "1498_padi",
        "table_id": "1498#2",
        "code": "MTQ5OCMy",
        "level_wilayah": "PROVINSI",
        "satuan_fallback": "Luas Panen: ha; Produktivitas: ku/ha; Produksi: ton",
    },
    {
        "folder": "2204_jagung",
        "table_id": "2204#2",
        "code": "MjIwNCMy",
        "level_wilayah": "PROVINSI",
        "satuan_fallback": "Luas Panen: ha; Produktivitas: ku/ha; Produksi: ton",
    },
    {
        "folder": "2566_perkebunan",
        "table_id": "2566#2",
        "code": "MjU2NiMy",
        "level_wilayah": "PROVINSI",
        "satuan_fallback": "Ribu Ton",
    },
    {
        "folder": "132_perkebunan_historis",
        "table_id": "132#2",
        "code": "MTMyIzI=",
        "level_wilayah": "PROVINSI",
        "satuan_fallback": "Ribu Ton",
    },
    {
        "folder": "2512_kayu_jenis_pohon",
        "table_id": "2512#2",
        "code": "MjUxMiMy",
        "level_wilayah": "NASIONAL",
        "satuan_fallback": "m3 / SM / Ton / Batang (sesuai label baris asli)",
    },
    {
        "folder": "1973_kayu_hph_pulau",
        "table_id": "1973#2",
        "code": "MTk3MyMy",
        "level_wilayah": "PULAU",
        "satuan_fallback": "m3",
    },
]


def discover_get_data_table_action(session, page_html: str) -> str:
    """Cari hash Server Action `getDataTable` dari chunk Next.js BPS, fallback ke default."""
    try:
        chunks = sorted(set(re.findall(r"/_next/static/chunks/[^\"'\\]+\.js", page_html)))
        # Cari dulu chunk yang memuat mapping 89746 -> chunk tabel
        candidates = []
        for c in chunks:
            if "32vg" in c or "09pnc" in c or "3wp2v" in c:
                candidates.insert(0, c)
        for c in candidates + [x for x in chunks if x not in candidates]:
            js = session.get("https://www.bps.go.id" + c, timeout=15).text
            m = re.search(r'createServerReference\)\("([0-9a-f]{32,64})"[^)]*"getDataTable"', js)
            if m:
                return m.group(1)
            # Jika chunk merujuk ke chunk lain (seperti 09pnco0 -> 3wp2v)
            sub_chunks = re.findall(r"static/chunks/[^\"']+\.js", js)
            for sc in sub_chunks:
                if sc not in seen_sub:
                    seen_sub.add(sc)
                    sjs = session.get("https://www.bps.go.id/_next/" + sc, timeout=15).text
                    m2 = re.search(r'createServerReference\)\("([0-9a-f]{32,64})"[^)]*"getDataTable"', sjs)
                    if m2:
                        return m2.group(1)
            if len(seen_sub) > 12:
                break
    except Exception:
        pass
    return DEFAULT_GET_DATA_TABLE_ACTION


seen_sub: set[str] = set()


def extract_initial_page_payload(html_text: str):
    """Ekstrak listTahun dan JSON data tabel awal (tahun default) dari HTML Next.js BPS."""
    unesc = html_text.encode("utf-8").decode("unicode_escape", errors="ignore")

    m_lt = re.search(r'"listTahun"\s*:\s*(\[[^\]]*\])', unesc)
    list_tahun = json.loads(m_lt.group(1)) if m_lt else []

    t_pos = unesc.find('"turvar"')
    if t_pos == -1:
        return list_tahun, None
    b_start = unesc.rfind('{"status":', 0, t_pos)
    if b_start == -1:
        b_start = unesc.rfind('{"', 0, t_pos)

    depth = 0
    b_end = -1
    for i in range(b_start, len(unesc)):
        ch = unesc[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                b_end = i + 1
                break
    if b_end == -1:
        return list_tahun, None
    data_obj = json.loads(unesc[b_start:b_end])
    return list_tahun, data_obj


def fetch_year_via_server_action(session, page_url: str, code: str, th_id: int | str, action_id: str):
    """Panggil Next.js Server Action `getDataTable` resmi BPS untuk satu tahun spesifik."""
    headers = {
        "Accept": "text/x-component",
        "Content-Type": "text/plain;charset=UTF-8",
        "Next-Action": action_id,
        "Referer": page_url,
        "Origin": "https://www.bps.go.id",
    }
    body = json.dumps([{"locale": "id", "id": code, "year": str(th_id)}])
    r = session.post(page_url, headers=headers, data=body, timeout=30)
    r.raise_for_status()
    for ln in r.text.splitlines():
        if '"datacontent"' in ln or '"data-availability"' in ln:
            idx = ln.find("{")
            if idx != -1:
                parsed = json.loads(ln[idx:])
                if parsed.get("status") and isinstance(parsed.get("response"), dict):
                    return r.status_code, parsed["response"]
    return r.status_code, None


def clean_label(text: str) -> str:
    s = html_lib.unescape(str(text or ""))
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_bps_cell(val):
    """Ketat bedakan NULL vs 0: None/'-'/'' -> NaN; 0/0.0 -> 0.0."""
    if val is None:
        return np.nan
    if isinstance(val, (int, float, np.number)):
        return float(val) if not pd.isna(val) else np.nan
    s = str(val).strip()
    if not s or s.lower() in {"-", "–", "—", "...", "n/a", "na", "null", "none"}:
        return np.nan
    try:
        return float(s.replace(",", ".")) if ("," in s and "." not in s) else float(s)
    except ValueError:
        return np.nan


def bps_json_to_dataframe(data_obj: dict, th_id: int | str, th_label: str, tbl_cfg: dict, page_url: str, tanggal_tarik: str):
    """Ubah payload JSON BPS satu tahun menjadi DataFrame 1:1 mentah (tanpa konversi satuan)."""
    var0 = (data_obj.get("var") or [{}])[0]
    var_val = str(var0.get("val", ""))
    var_label = clean_label(var0.get("label", ""))
    var_unit = clean_label(var0.get("unit", "")) or tbl_cfg["satuan_fallback"]

    vervars = sorted(data_obj.get("vervar") or [], key=lambda x: int(x["val"]) if str(x["val"]).isdigit() else str(x["val"]))
    turvars = sorted(data_obj.get("turvar") or [], key=lambda x: int(x["val"]) if str(x["val"]).isdigit() else str(x["val"]))
    turtahuns = sorted(data_obj.get("turtahun") or [], key=lambda x: int(x["val"]) if str(x["val"]).isdigit() else str(x["val"]))
    datacontent = data_obj.get("datacontent") or {}

    single_dummy_turvar = len(turvars) == 1 and str(turvars[0].get("val")) == "0"
    single_turtahun = len(turtahuns) == 1

    # Susun daftar kolom nilai secara deterministik
    val_specs = []
    for tv in turvars:
        tv_val = str(tv["val"])
        tv_lbl = clean_label(tv["label"])
        for tt in turtahuns:
            tt_val = str(tt["val"])
            tt_lbl = clean_label(tt["label"])
            if single_dummy_turvar and single_turtahun:
                col_name = "nilai"
            elif single_dummy_turvar:
                col_name = tt_lbl
            elif single_turtahun:
                col_name = tv_lbl
            else:
                col_name = f"{tv_lbl} - {tt_lbl}"
            val_specs.append((tv_val, tt_val, col_name))

    rows = []
    stats = {"n_pos": 0, "n_zero": 0, "n_null": 0}
    for vv in vervars:
        vv_val = str(vv["val"])
        vv_lbl = clean_label(vv["label"])
        rec = {
            "kode_baris": vv_val,
            "label_baris": vv_lbl,
            "tahun": int(th_label) if str(th_label).isdigit() else th_label,
        }
        for tv_val, tt_val, col_name in val_specs:
            key = f"{vv_val}{var_val}{tv_val}{th_id}{tt_val}"
            raw_v = datacontent.get(key, None)
            num_v = parse_bps_cell(raw_v)
            rec[col_name] = num_v
            if pd.isna(num_v):
                stats["n_null"] += 1
            elif num_v == 0.0:
                stats["n_zero"] += 1
            else:
                stats["n_pos"] += 1
        rec["id_tabel_bps"] = tbl_cfg["table_id"]
        rec["nama_variabel"] = var_label
        rows.append(rec)

    df = pd.DataFrame(rows)
    df = add_provenance_cols(
        df,
        sumber_instansi="Badan Pusat Statistik (BPS RI)",
        sumber_url=page_url,
        satuan_asli=var_unit,
        level_wilayah=tbl_cfg["level_wilayah"],
        tanggal_tarik=tanggal_tarik,
    )
    return df, var_unit, stats


def main():
    ensure_raw_folder_tree()
    tanggal_tarik = today_iso()
    session = make_http_session(retries=3, backoff_factor=0.8)
    logger = RequestLogger("02_extract_bps")

    print("=" * 72, flush=True)
    print("STEP 2: EKSTRAKSI FOLDER 2 — raw_data/02_bps/", flush=True)
    print("=" * 72, flush=True)

    audit_rows = []
    action_id = DEFAULT_GET_DATA_TABLE_ACTION
    action_verified = False

    print("\n[Tahap 2A] Menarik 6 Tabel Utama BPS RI (1 Tahun = 1 CSV, Tanpa API Key)...", flush=True)
    for tbl in BPS_RI_TABLES:
        folder = tbl["folder"]
        code = tbl["code"]
        table_id = tbl["table_id"]
        page_url = f"https://www.bps.go.id/id/statistics-table/2/{code}/table.html"
        out_dir = FOLDER_2 / "bps_ri" / folder

        t0 = time.perf_counter()
        try:
            r_page = session.get(page_url, timeout=30)
            elapsed_page = (time.perf_counter() - t0) * 1000
            r_page.raise_for_status()
            logger.log(f"bps_page_{folder}", "GET", page_url, r_page.status_code, elapsed_page)

            if not action_verified:
                action_id = discover_get_data_table_action(session, r_page.text)
                action_verified = True
                print(f"  [Next-Action] getDataTable hash: {action_id}", flush=True)

            list_tahun, initial_data = extract_initial_page_payload(r_page.text)
            if not initial_data:
                raise RuntimeError("Gagal mem-parse payload JSON awal dari halaman BPS")

            # Tahun yang sudah terkandung di payload SSR awal
            init_th_list = initial_data.get("tahun") or []
            init_th_id = str(init_th_list[0]["val"]) if init_th_list else None

            if not list_tahun and init_th_list:
                list_tahun = [{"th_id": init_th_list[0]["val"], "th": init_th_list[0]["label"]}]

            # Urutkan ascending berdasarkan tahun agar log rapi (misal 2018 -> 2024)
            years_sorted = sorted(list_tahun, key=lambda x: int(x["th"]) if str(x["th"]).isdigit() else 0)
            print(
                f"\n  [{table_id}] {folder} -> terdeteksi {len(years_sorted)} tahun: {[x['th'] for x in years_sorted]}",
                flush=True,
            )

            for y_item in years_sorted:
                th_id = y_item["th_id"]
                th_lbl = str(y_item["th"]).strip()
                out_path = out_dir / f"{th_lbl}.csv"

                t1 = time.perf_counter()
                try:
                    if str(th_id) == init_th_id:
                        data_obj = initial_data
                        http_st = r_page.status_code
                        method_used = "SSR_NEXTJS_JSON"
                    else:
                        http_st, data_obj = fetch_year_via_server_action(session, page_url, code, th_id, action_id)
                        method_used = "NEXTJS_SERVER_ACTION_getDataTable"
                        time.sleep(0.35)

                    elapsed_y = (time.perf_counter() - t1) * 1000
                    if not data_obj or data_obj.get("data-availability") != "available":
                        raise RuntimeError(f"Data tidak tersedia di BPS untuk th_id={th_id} ({th_lbl})")

                    df, satuan_asli, stats = bps_json_to_dataframe(
                        data_obj, th_id, th_lbl, tbl, page_url, tanggal_tarik
                    )
                    write_raw_csv(df, out_path)
                    rel = str(out_path.relative_to(RAW_DIR)).replace("\\", "/")

                    logger.log(
                        f"bps_{folder}_{th_lbl}", "POST" if method_used.startswith("NEXTJS") else "GET",
                        page_url, http_st, elapsed_y, rows=len(df), output_file=rel,
                    )
                    print(
                        f"    - {th_lbl}.csv | rows={len(df):2d} | cols={len(df.columns):2d} | pos={stats['n_pos']:3d}, zero={stats['n_zero']:2d}, null={stats['n_null']:2d} | [{method_used}]",
                        flush=True,
                    )
                    audit_rows.append(
                        {
                            "tahap": "2A_BPS_RI",
                            "tabel_id": table_id,
                            "topik_folder": folder,
                            "tahun": th_lbl,
                            "th_id_bps": th_id,
                            "file_relatif": rel,
                            "metode_ekstrak": method_used,
                            "status_http": http_st,
                            "status_ekstrak": "OK",
                            "jumlah_baris": len(df),
                            "jumlah_kolom": len(df.columns),
                            "satuan_asli": satuan_asli,
                            "sel_positif": stats["n_pos"],
                            "sel_nol_eksplisit": stats["n_zero"],
                            "sel_null": stats["n_null"],
                            "catatan": "1 tahun = 1 CSV mentah as-is (tanpa konversi satuan)",
                        }
                    )
                except Exception as exc_y:
                    elapsed_y = (time.perf_counter() - t1) * 1000
                    logger.log(f"bps_{folder}_{th_lbl}", "POST", page_url, "ERROR", elapsed_y, error=str(exc_y))
                    print(f"    [ERR] {folder}/{th_lbl}: {exc_y}", flush=True)
                    audit_rows.append(
                        {
                            "tahap": "2A_BPS_RI",
                            "tabel_id": table_id,
                            "topik_folder": folder,
                            "tahun": th_lbl,
                            "th_id_bps": th_id,
                            "file_relatif": str(out_path.relative_to(RAW_DIR)).replace("\\", "/"),
                            "metode_ekstrak": "NEXTJS_SERVER_ACTION",
                            "status_http": "ERROR",
                            "status_ekstrak": "ERROR",
                            "jumlah_baris": 0,
                            "jumlah_kolom": 0,
                            "satuan_asli": tbl["satuan_fallback"],
                            "sel_positif": 0,
                            "sel_nol_eksplisit": 0,
                            "sel_null": 0,
                            "catatan": str(exc_y),
                        }
                    )
        except Exception as exc:
            logger.log(f"bps_page_{folder}", "GET", page_url, "ERROR", (time.perf_counter() - t0) * 1000, error=str(exc))
            print(f"  [ERR TABLE] {folder}: {exc}", flush=True)
            audit_rows.append(
                {
                    "tahap": "2A_BPS_RI",
                    "tabel_id": table_id,
                    "topik_folder": folder,
                    "tahun": "",
                    "th_id_bps": "",
                    "file_relatif": f"02_bps/bps_ri/{folder}/",
                    "metode_ekstrak": "SSR_NEXTJS_JSON",
                    "status_http": "ERROR",
                    "status_ekstrak": "ERROR",
                    "jumlah_baris": 0,
                    "jumlah_kolom": 0,
                    "satuan_asli": tbl["satuan_fallback"],
                    "sel_positif": 0,
                    "sel_nol_eksplisit": 0,
                    "sel_null": 0,
                    "catatan": str(exc),
                }
            )
        time.sleep(0.4)

    # Tahap 2B: BPS Provinsi (Opsional jika BPS_API_KEY ada)
    print("\n[Tahap 2B] Memeriksa BPS_API_KEY untuk penarikan BPS Provinsi (opsional)...", flush=True)
    api_key = load_bps_api_key()
    if not api_key:
        print("  [SKIP BERSIH] BPS_API_KEY belum diset -> Tahap 2B dilewati sesuai default plan & dicatat di audit.", flush=True)
        audit_rows.append(
            {
                "tahap": "2B_BPS_PROVINSI",
                "tabel_id": "WEBAPI_34_DOMAIN",
                "topik_folder": "bps_provinsi",
                "tahun": "",
                "th_id_bps": "",
                "file_relatif": "02_bps/bps_provinsi/",
                "metode_ekstrak": "WEBAPI_BPS",
                "status_http": "SKIPPED_NO_API_KEY",
                "status_ekstrak": "SKIPPED_OPSIONAL",
                "jumlah_baris": 0,
                "jumlah_kolom": 0,
                "satuan_asli": "",
                "sel_positif": 0,
                "sel_nol_eksplisit": 0,
                "sel_null": 0,
                "catatan": "BPS_API_KEY tidak ditemukan di environment/.env. Slot folder 02_bps/bps_provinsi/ disiapkan bila nanti ingin ditambahkan.",
            }
        )
    else:
        print("  [INFO] BPS_API_KEY terdeteksi! Mengambil katalog variabel pertanian (subject=557) 34 domain BPS provinsi...", flush=True)
        for kd2, dom4, prov_name, prov_slug, _pulau, _sub in PROVINCES_38:
            if kd2 in {"92", "95", "96", "97"}:
                continue  # 4 provinsi pemekaran Papua belum punya domain mandiri
            url_api = f"https://webapi.bps.go.id/v1/api/list/model/var/domain/{dom4}/subject/557/key/{api_key}"
            try:
                ra = session.get(url_api, timeout=20)
                jsa = ra.json()
                if jsa.get("status") == "OK" and jsa.get("data-availability") == "available":
                    items = jsa.get("data", [None, []])[1]
                    df_cat = pd.DataFrame(items)
                    out_p = FOLDER_2 / "bps_provinsi" / f"{kd2}_{prov_slug}" / f"katalog_var_subject557_{dom4}.csv"
                    df_cat = add_provenance_cols(
                        df_cat,
                        sumber_instansi=f"BPS Provinsi {prov_name} (WebAPI)",
                        sumber_url=f"https://webapi.bps.go.id/v1/api/list/model/var/domain/{dom4}/subject/557",
                        satuan_asli="metadata_katalog",
                        level_wilayah="PROVINSI",
                        tanggal_tarik=tanggal_tarik,
                    )
                    write_raw_csv(df_cat, out_p)
                    audit_rows.append(
                        {
                            "tahap": "2B_BPS_PROVINSI",
                            "tabel_id": f"var_list_{dom4}",
                            "topik_folder": f"bps_provinsi/{kd2}_{prov_slug}",
                            "tahun": "",
                            "th_id_bps": "",
                            "file_relatif": str(out_p.relative_to(RAW_DIR)).replace("\\", "/"),
                            "metode_ekstrak": "WEBAPI_BPS",
                            "status_http": ra.status_code,
                            "status_ekstrak": "OK",
                            "jumlah_baris": len(df_cat),
                            "jumlah_kolom": len(df_cat.columns),
                            "satuan_asli": "metadata",
                            "sel_positif": len(df_cat),
                            "sel_nol_eksplisit": 0,
                            "sel_null": 0,
                            "catatan": f"Katalog variabel subject 557 domain {dom4}",
                        }
                    )
            except Exception as exc_p:
                print(f"    [ERR API {dom4}] {exc_p}", flush=True)
            time.sleep(0.25)

    df_audit = pd.DataFrame(audit_rows)
    audit_path = FOLDER_2 / "_audit_02_bps.csv"
    write_raw_csv(df_audit, audit_path)

    n_ok = int((df_audit["status_ekstrak"] == "OK").sum())
    n_err = int((df_audit["status_ekstrak"] == "ERROR").sum())
    print("\n" + "=" * 72, flush=True)
    print(f"SELESAI STEP 2: {n_ok} file CSV BPS RI berhasil diekstrak | Error: {n_err}", flush=True)
    print(f"Audit disimpan ke: {audit_path}", flush=True)
    print("=" * 72, flush=True)


if __name__ == "__main__":
    main()
