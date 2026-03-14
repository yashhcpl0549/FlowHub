#!/usr/bin/env python3
"""
Sale Register Agent - File Validation Script
Run before main.py to catch errors early.

Usage: python validate.py <config.json>
Exit:  0 = OK, 1 = Failed
"""

import sys, json, os, zipfile, warnings, tempfile, shutil
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from google.cloud import storage, bigquery
from google.oauth2.service_account import Credentials

warnings.filterwarnings("ignore")

GCS_BUCKET        = "honasa-flow-hub"
TEMPLATE_GCS_PATH = "ke30_template/Sale_Register_Template.xlsx"
CREDENTIALS_PATH  = os.environ.get("GCS_CREDENTIALS_PATH", "/app/credentials/gcs-credentials.json")
BQ_PROJECT        = "mamaearth-262312"
BQ_PM_TABLE       = "mamaearth-262312.SAP.Product_Master"
BQ_GST_TABLE      = "mamaearth-262312.reporting_tables.BI_F9_Product_Master_Import"

def find_file(files, *patterns):
    for f in files:
        name = f["filename"].lower()
        for p in patterns:
            if p.lower() in name:
                return f
    return None

def find_files(files, *patterns):
    result = []
    for f in files:
        name = f["filename"].lower()
        for p in patterns:
            if p.lower() in name:
                result.append(f); break
    return result

def read_excel_safe(path, nrows=5):
    df_test = pd.read_excel(path, engine="openpyxl", nrows=1)
    if df_test.iloc[0].isna().all() or str(df_test.columns[0]).startswith("Unnamed"):
        return pd.read_excel(path, engine="openpyxl", skiprows=1, nrows=nrows)
    return pd.read_excel(path, engine="openpyxl", nrows=nrows)

# ── Download inputs from GCS ─────────────────────────────────────────────────
def download_inputs_from_gcs(files, dest_dir):
    client = storage.Client.from_service_account_json(CREDENTIALS_PATH)
    bucket = client.bucket(GCS_BUCKET)
    for f in files:
        gcs_path = f.get("gcs_path", "")
        if gcs_path:
            local_path = os.path.join(dest_dir, f["filename"])
            bucket.blob(gcs_path).download_to_filename(local_path)
            f["local_path"] = local_path
    return files

# ── Validators ────────────────────────────────────────────────────────────────

def validate_ke30(files, errors, warns):
    ke30s = find_files(files, "ke30")
    if not ke30s:
        errors.append("❌ No KE30 files — name must contain 'ke30'"); return
    print(f"\n[KE30] {len(ke30s)} file(s) found")
    required = ["Customer","Posting date","Product","Plant","Val/COArea Crcy",
                "Total Quantity","Billing Type","Reference procedure","Distribution Channel",
                "Brand Text","Cost Element"]
    for f in ke30s:
        try:
            df = read_excel_safe(f["local_path"])
            missing = [c for c in required if c not in df.columns]
            if missing:
                errors.append(f"  ❌ {f['filename']}: Missing columns: {missing}")
            else:
                print(f"  ✅ {f['filename']}: OK ({df.shape[1]} cols)")
            has_soi = "Sales Order Item" in df.columns or "Sales order item" in df.columns
            if not has_soi:
                errors.append(f"  ❌ {f['filename']}: Missing 'Sales Order Item'")
        except Exception as e:
            errors.append(f"  ❌ {f['filename']}: Cannot read — {e}")

def validate_customer_mapping(files, errors, warns):
    f = find_file(files, "customer_mapping", "final_customer")
    if not f:
        errors.append("❌ Customer mapping CSV not found — name must contain 'customer_mapping'"); return
    print(f"\n[Customer Mapping] {f['filename']}")
    try:
        df = pd.read_csv(f["local_path"])
        required = ["Customer Code", "Channel", "Updated Strat Heads For MIS"]
        missing  = [c for c in required if c not in df.columns]
        if missing: errors.append(f"  ❌ Missing columns: {missing}")
        else:       print(f"  ✅ Required columns present | {len(df)} records")
    except Exception as e:
        errors.append(f"  ❌ Cannot read: {e}")

def validate_mrp(files, errors, warns):
    f = find_file(files, "zmrp", "mrp")
    if not f:
        errors.append("❌ MRP file not found — name must contain 'zmrp' or 'mrp'"); return
    print(f"\n[MRP File] {f['filename']}")
    try:
        df = read_excel_safe(f["local_path"])
        required = ["Material Number","Plant","Condition type","Validity From","Validity To","Amount"]
        missing  = [c for c in required if c not in df.columns]
        if missing: errors.append(f"  ❌ Missing columns: {missing}")
        else:
            df_check = read_excel_safe(f["local_path"], nrows=5000)
            if "Condition type" in df_check.columns and "ZMRP" not in df_check["Condition type"].astype(str).values:
                warns.append("  ⚠️  No 'ZMRP' in first 5000 rows — check Condition type column")
            else:
                print(f"  ✅ Required columns present, ZMRP condition found")
    except Exception as e:
        errors.append(f"  ❌ Cannot read: {e}")

def validate_freebie(files, errors, warns):
    f = find_file(files, "freebie", "bxgy")
    if not f:
        errors.append("❌ Freebie file not found — name must contain 'freebie' or 'bxgy'"); return
    print(f"\n[Freebie File] {f['filename']}")
    try:
        sheets = pd.read_excel(f["local_path"], sheet_name=None, nrows=5)
        df     = pd.concat(sheets.values(), ignore_index=True)
        required = ["year_month","coupon_code","SKU","brand","quantity","MRP"]
        missing  = [c for c in required if c not in df.columns]
        if missing: errors.append(f"  ❌ Missing columns: {missing}")
        else:       print(f"  ✅ Required columns present | {len(sheets)} sheet(s): {list(sheets.keys())}")
    except Exception as e:
        errors.append(f"  ❌ Cannot read: {e}")

def validate_bigquery_pm(errors, warns):
    print(f"\n[BigQuery Product Master] {BQ_PM_TABLE}")
    try:
        bq_client = bigquery.Client.from_service_account_json(CREDENTIALS_PATH, project=BQ_PROJECT)
        query = f"SELECT COUNT(*) as cnt FROM `{BQ_PM_TABLE}`"
        result = bq_client.query(query).to_dataframe()
        cnt = result["cnt"].iloc[0]
        if cnt == 0:
            warns.append("  ⚠️  Product Master table is empty")
        else:
            print(f"  ✅ Accessible | {cnt:,} rows in table")
    except Exception as e:
        errors.append(f"  ❌ Cannot access BigQuery Product Master: {e}")

def validate_gcs_template(errors, warns):
    print(f"\n[GCS Template] gs://{GCS_BUCKET}/{TEMPLATE_GCS_PATH}")
    try:
        client = storage.Client.from_service_account_json(CREDENTIALS_PATH)
        blob   = client.bucket(GCS_BUCKET).blob(TEMPLATE_GCS_PATH)
        if not blob.exists():
            errors.append(f"  ❌ Template not found in GCS at {TEMPLATE_GCS_PATH}")
            return
        # Download to temp and check sheets
        import tempfile
        tmp = tempfile.mktemp(suffix=".xlsx")
        blob.download_to_filename(tmp)
        with zipfile.ZipFile(tmp,"r") as z:
            with z.open("xl/workbook.xml") as wb_xml:
                root   = ET.parse(wb_xml).getroot()
                sheets = [sh.attrib["name"] for sh in
                          root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")]
        required = ["RAW_Website_EBO","RAW_b2c","RAW_Remaining","RAW_S1S2"]
        missing  = [s for s in required if s not in sheets]
        if missing: errors.append(f"  ❌ Template missing sheets: {missing} | Found: {sheets}")
        else:       print(f"  ✅ Template accessible, all 4 RAW sheets present")
        os.remove(tmp)
    except Exception as e:
        errors.append(f"  ❌ Cannot access GCS template: {e}")

def validate_gsheet(errors, warns):
    print(f"\n[BigQuery GST Mapping] {BQ_GST_TABLE}")
    try:
        bq_client = bigquery.Client.from_service_account_json(CREDENTIALS_PATH, project=BQ_PROJECT)
        result = bq_client.query(f"SELECT COUNT(*) as cnt FROM `{BQ_GST_TABLE}`").to_dataframe()
        cnt = result["cnt"].iloc[0]
        if cnt == 0:
            warns.append("  ⚠️  GST mapping table is empty")
        else:
            print(f"  ✅ Accessible | {cnt:,} rows in table")
    except Exception as e:
        errors.append(f"  ❌ Cannot access BigQuery GST table: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────
def validate(config_path):
    with open(config_path) as fh:
        config = json.load(fh)
    files  = config["files"]
    errors = []
    warns  = []

    print("=" * 60)
    print("  Sale Register Agent — File Validation")
    print("=" * 60)
    print(f"\nFiles uploaded: {len(files)}")
    for f in files:
        print(f"  • {f['filename']}")

    # Download files from GCS to temp dir for local validation
    tmp_dir = tempfile.mkdtemp(prefix="sr_validate_")
    try:
        files = download_inputs_from_gcs(files, tmp_dir)
    except Exception as e:
        print(f"\n❌ Failed to download files from GCS: {e}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)

    validate_ke30(files, errors, warns)
    validate_customer_mapping(files, errors, warns)
    validate_mrp(files, errors, warns)
    validate_freebie(files, errors, warns)
    validate_bigquery_pm(errors, warns)
    validate_gcs_template(errors, warns)
    validate_gsheet(errors, warns)

    shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n" + "=" * 60)
    if warns:
        print("\nWARNINGS (non-blocking):")
        for w in warns: print(w)
    if errors:
        print("\nVALIDATION FAILED:")
        for e in errors: print(e)
        print("\n❌ Fix the above before running the agent.")
        sys.exit(1)
    else:
        print("\n✅ All validations passed — ready to run!")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate.py <config.json>"); sys.exit(1)
    validate(sys.argv[1])
