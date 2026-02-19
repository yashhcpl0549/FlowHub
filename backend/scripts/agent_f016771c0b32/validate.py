#!/usr/bin/env python3
"""
Example validation script for CSV files

Usage: python validate_csv.py <config_json_path>

The config JSON contains:
{
  "job_id": "job_abc123",
  "agent_id": "agent_xyz",
  "files": [
    {
      "filename": "sales_data.csv",
      "storage_type": "gcs",
      "gcs_bucket": "my-bucket",
      "gcs_blob_name": "jobs/job_abc123/0_sales_data.csv",
      "gcs_path": "gs://my-bucket/jobs/job_abc123/0_sales_data.csv"
    }
  ]
}
"""

import sys
import json
import pandas as pd
from google.cloud import storage
import io

def validate_csv(config_path):
    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"Validating files for job: {config['job_id']}")
    
    # Expected columns - customize this for your use case
    EXPECTED_COLUMNS = ['Date', 'Product', 'Quantity', 'Revenue']
    
    for file_info in config['files']:
        filename = file_info['filename']
        
        # Only validate CSV files
        if not filename.lower().endswith('.csv'):
            print(f"Skipping non-CSV file: {filename}")
            continue
        
        print(f"Validating: {filename}")
        
        # Read CSV based on storage type
        if file_info['storage_type'] == 'gcs':
            # Read from GCS
            storage_client = storage.Client()
            bucket = storage_client.bucket(file_info['gcs_bucket'])
            blob = bucket.blob(file_info['gcs_blob_name'])
            csv_content = blob.download_as_text()
            df = pd.read_csv(io.StringIO(csv_content))
        else:
            # Read from local file
            df = pd.read_csv(file_info['local_path'])
        
        # Validate columns
        actual_columns = list(df.columns)
        missing_columns = set(EXPECTED_COLUMNS) - set(actual_columns)
        
        if missing_columns:
            print(f"ERROR: Missing columns in {filename}: {missing_columns}")
            sys.exit(1)
        
        print(f"✓ {filename} validated successfully")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {actual_columns}")
    
    print("\nAll files validated successfully!")
    return 0

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python validate_csv.py <config_json_path>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    sys.exit(validate_csv(config_path))
